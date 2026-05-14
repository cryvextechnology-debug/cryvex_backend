import time
import asyncio
import logging
import os
from typing import Any, Awaitable
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from fastapi import HTTPException

from app.schemas import VisitorID


# ==========================================
# NoSQL Injection Prevention Layer
# ==========================================
def sanitize_mongodb_input(data: Any, ip: str = "Unknown") -> Any:
    """
    Recursively inspects dictionaries and strings for MongoDB operator injection.
    Raises HTTP 400 immediately if any key or string value starts with '$'.
    This is the global "No-Dollar" sanitizer for all untrusted input flowing into .find() / .find_one().
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and key.startswith("$"):
                security_logger.log_event("NOSQL_INJECTION_ATTEMPT", "CRITICAL", ip, f"Illegal key detected: '{key}'")
                raise HTTPException(status_code=400, detail=f"Illegal key detected: '{key}'")
            sanitize_mongodb_input(value, ip)
    elif isinstance(data, list):
        for item in data:
            sanitize_mongodb_input(item, ip)
    elif isinstance(data, str):
        if data.startswith("$"):
            security_logger.log_event("NOSQL_INJECTION_ATTEMPT", "CRITICAL", ip, f"Illegal value detected: '{data}'")
            raise HTTPException(status_code=400, detail=f"Illegal value detected: '{data}'")
    return data


def safe_visitor_id(raw_id: Any) -> str:
    """
    Validates and sanitizes a visitor_id in one step.
    1. Rejects non-string types (blocks dict-based operator injection).
    2. Validates format via Pydantic regex (alphanumeric + _ + - only).
    3. Returns the clean string, safe for direct use in MongoDB queries.
    """
    if not isinstance(raw_id, str):
        raise HTTPException(status_code=400, detail="visitor_id must be a string")
    try:
        validated = VisitorID(visitor_id=raw_id)
        return validated.visitor_id
    except Exception as e:
        # Catch-all for any validation or pattern mismatch errors
        security_logger.log_event("VALIDATION_ERROR", "WARNING", "Unknown", f"Blocked malicious/invalid Visitor ID: {raw_id}")
        raise HTTPException(status_code=400, detail="Invalid visitor ID format.")


# ==========================================
# Task 3: Resilience & Graceful Degradation
# ==========================================
class CircuitBreaker:
    """Circuit Breaker for Redis operations to prevent total site blackout."""
    def __init__(self, timeout_ms: int = 1000):
        self.timeout_sec = timeout_ms / 1000.0

    async def execute(self, coro: Awaitable[Any], fallback: Any = None) -> Any:
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout_sec)
        except asyncio.TimeoutError:
            print(f"[SHIELD] Circuit Breaker Tripped! Fallback engaged. Error: Timeout (> {self.timeout_sec}s)")
            return fallback
        except Exception as e:
            print(f"[SHIELD] Circuit Breaker Tripped! Fallback engaged. Error: {e}")
            return fallback

circuit_breaker = CircuitBreaker(timeout_ms=1000)

# ==========================================
# Task 2, Layer C: Payload Hardening
# ==========================================
class PulsePayloadValidator(BaseModel):
    """Strict Pydantic Validator for WebSocket incoming packets."""
    model_config = ConfigDict(extra='forbid') # Drop connection if unknown keys exist
    current_page: str = Field(default="Home", max_length=100)
    current_section: str = Field(default="Entry Section", max_length=100)
    scroll_depth: int = Field(default=0, ge=0, le=50000) # Capped at 50k px
    actions: list[str] = Field(default_factory=list, max_length=50)
    visitor_id: str = Field(default="", min_length=10, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")

# ==========================================
# Task 1: The Token Bucket Middleware
# ==========================================
class TokenBucketRateLimiter:
    """Redis-backed Token Bucket algorithm."""
    def __init__(self, redis_client, burst: int = 5, rate: int = 1):
        self.redis = redis_client
        self.burst = burst
        self.rate = rate
        # Atomic Lua script for thread safety across 10k concurrent users
        self.lua_script = """
        local key = KEYS[1]
        local burst = tonumber(ARGV[1])
        local rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local amount = tonumber(ARGV[4])
        
        local bucket = redis.call("HMGET", key, "tokens", "last_update")
        local tokens = tonumber(bucket[1])
        local last_update = tonumber(bucket[2])
        
        if not tokens or not last_update then
            tokens = burst
            last_update = now
        else
            local time_passed = math.max(0, now - last_update)
            tokens = math.min(burst, tokens + time_passed * rate)
        end
        
        if tokens >= amount then
            tokens = tokens - amount
            redis.call("HMSET", key, "tokens", tokens, "last_update", now)
            redis.call("EXPIRE", key, math.ceil(burst / rate) + 2)
            return 1
        else
            redis.call("HMSET", key, "tokens", tokens, "last_update", now)
            redis.call("EXPIRE", key, math.ceil(burst / rate) + 2)
            return 0
        end
        """

    async def is_allowed(self, key: str, amount: int = 1) -> bool:
        # Fallback for MockRedis in local dev mode which lacks eval()
        if hasattr(self.redis, 'data'):
            # Basic in-memory bucket for Mock mode
            now = time.time()
            if not hasattr(self, '_mock_buckets'):
                self._mock_buckets = {}
            
            bucket = self._mock_buckets.get(key, {"tokens": self.burst, "last": now})
            passed = max(0, now - bucket["last"])
            bucket["tokens"] = min(self.burst, bucket["tokens"] + passed * self.rate)
            bucket["last"] = now
            
            if bucket["tokens"] >= amount:
                bucket["tokens"] -= amount
                self._mock_buckets[key] = bucket
                return True
            return False

        now = int(time.time())
        # The circuit breaker wraps this execution in main.py
        if self.redis.__class__.__module__.startswith('upstash_redis'):
            result = await self.redis.eval(
                self.lua_script, 
                keys=[key],
                args=[self.burst, self.rate, now, amount]
            )
        else:
            result = await self.redis.eval(
                self.lua_script, 
                1, # number of keys
                key, 
                self.burst, 
                self.rate, 
                now, 
                amount
            )
        return bool(result)

# ==========================================
# Task 4: Security Flight Recorder
# ==========================================
class SecurityLogger:
    """Flight Recorder for security events."""
    def __init__(self, log_file="security.log"):
        self.logger = logging.getLogger("cryvex_security")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            os.makedirs(os.path.dirname(os.path.abspath(log_file)) or ".", exist_ok=True)
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, level: str, ip: str, detail: str):
        masked_ip = self.mask_ip(ip)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] [{level}] [{masked_ip}] {detail}"
        self.logger.info(log_entry)
        # Also print to stdout for container logs
        print(f"!!! SECURITY ALERT: {log_entry}")

    @staticmethod
    def mask_ip(ip: str) -> str:
        if not ip or ip == "Unknown":
            return "0.0.0.0"  # nosec B104
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.XXX"
        return "XXX.XXX.XXX.XXX"

security_logger = SecurityLogger()

# ==========================================
# Task 5: Email Service (SMTP / Mock)
# ==========================================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from app.config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = settings.BREVO_SMTP_SERVER
        self.smtp_port = settings.BREVO_SMTP_PORT
        self.smtp_user = settings.BREVO_SMTP_LOGIN
        self.smtp_pass = settings.BREVO_SMTP_PASSWORD
        self.api_key = settings.BREVO_API_KEY or settings.BREVO_SMTP_PASSWORD
        # Use verified sender email (falls back to SMTP login if not set)
        self.sender_email = settings.BREVO_SENDER_EMAIL or settings.BREVO_SMTP_LOGIN
        self.sender_name = settings.BREVO_SENDER_NAME
        self.is_configured = bool((self.smtp_user and self.smtp_pass) or self.api_key)

    def _build_professional_html(self, subject: str, body_html: str) -> str:
        """Wraps body content in a professional, branded Cryvex email template."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f2;font-family:'Inter','Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f2;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <!-- Header -->
    <tr>
        <td style="background:linear-gradient(135deg,#3525CD 0%,#4F46E5 100%);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:800;letter-spacing:-0.5px;">Cryvex AI</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:13px;letter-spacing:1px;text-transform:uppercase;">Intelligent Business Growth Engine</p>
        </td>
    </tr>
    <!-- Body -->
    <tr>
        <td style="padding:40px;">
            {body_html}
        </td>
    </tr>
    <!-- Footer -->
    <tr>
        <td style="background-color:#f9f9f7;padding:24px 40px;border-top:1px solid #e8e8e6;">
            <p style="margin:0 0 8px;font-size:12px;color:#777587;text-align:center;">
                This report was generated exclusively for you by Cryvex AI.
            </p>
            <p style="margin:0;font-size:11px;color:#999;text-align:center;">
                &copy; {__import__('datetime').datetime.now().year} Cryvex Organic Digital &bull; Tamil Tech Soul
            </p>
            <p style="margin:8px 0 0;font-size:11px;color:#999;text-align:center;">
                <a href="https://cryvex.in" style="color:#4F46E5;text-decoration:none;">cryvex.in</a>
            </p>
        </td>
    </tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    def build_strategy_email(self, business_name: str, strategy_text: str) -> str:
        """Builds a professional Strategy email body."""
        # Convert markdown-like sections to HTML
        # Identify section headers (UPPERCASE LINES) and make them bold/branded
        lines = strategy_text.split('\n')
        formatted_lines = []
        for line in lines:
            trimmed = line.strip()
            # If line is short and uppercase (header)
            if trimmed and trimmed.isupper() and len(trimmed) < 60:
                formatted_lines.append(f'<h3 style="margin:24px 0 12px;color:#3525CD;font-size:16px;font-weight:700;border-bottom:1px solid #eef0ff;padding-bottom:8px;">{trimmed}</h3>')
            else:
                formatted_lines.append(line)
        
        strategy_text = '\n'.join(formatted_lines)
        # Use divs to avoid nested p tags, and handle paragraph breaks
        formatted = strategy_text.replace('\n\n', '</div><div style="margin:0 0 12px;color:#1a1c1b;font-size:14px;line-height:1.7;">')
        formatted = formatted.replace('\n', '<br/>')
        
        body = f"""
        <h2 style="margin:0 0 8px;color:#1a1c1b;font-size:22px;font-weight:700;">Your AI Strategy Report</h2>
        <p style="margin:0 0 24px;color:#4F46E5;font-size:14px;font-weight:600;">Prepared for: {business_name}</p>
        <div style="background:#f9f9f7;border-left:4px solid #4F46E5;border-radius:8px;padding:24px;margin:0 0 24px;">
            <div style="margin:0;color:#1a1c1b;font-size:14px;line-height:1.7;">{formatted}</div>
        </div>
        <table cellpadding="0" cellspacing="0" style="margin:24px 0;">
        <tr><td style="background:linear-gradient(135deg,#3525CD,#4F46E5);border-radius:8px;padding:14px 32px;">
            <a href="https://cryvex.in/strategy" style="color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;">Generate Another Strategy &rarr;</a>
        </td></tr>
        </table>
        <p style="margin:0;font-size:13px;color:#777585;">
            Have questions? Reply to this email or reach us at <a href="https://cryvex.in" style="color:#4F46E5;">cryvex.in</a>.
        </p>"""
        return self._build_professional_html(f"Your Cryvex AI Strategy for {business_name}", body)

    def build_roi_email(self, business_name: str, calc: dict) -> str:
        """Builds a professional ROI email body with all scenario data."""
        scenarios_html = ""
        for scenario_key in ["conservative", "realistic", "aggressive"]:
            s = calc.get(scenario_key)
            if not s:
                continue
            label = scenario_key.capitalize()
            color = "#777585" if scenario_key == "conservative" else ("#4F46E5" if scenario_key == "realistic" else "#3525CD")
            bg = "#f9f9f7" if scenario_key == "conservative" else ("#eef0ff" if scenario_key == "realistic" else "#e8e4ff")
            
            scenarios_html += f"""
            <div style="background:{bg};border-radius:12px;padding:20px;margin:0 0 16px;border-left:4px solid {color};">
                <h3 style="margin:0 0 12px;color:{color};font-size:16px;font-weight:700;">{label} Scenario</h3>
                <table width="100%" cellpadding="4" cellspacing="0" style="font-size:13px;color:#1a1c1b;">
                    <tr>
                        <td style="font-weight:600;">Net Monthly Profit</td>
                        <td style="text-align:right;font-weight:700;color:{color};">₹{s.get('net_profit', 0):,.0f}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">Annual Impact</td>
                        <td style="text-align:right;font-weight:700;color:{color};">₹{s.get('annual_impact', 0):,.0f}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">Efficiency Score</td>
                        <td style="text-align:right;">{s.get('efficiency_score', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">Subscription Cost</td>
                        <td style="text-align:right;">₹{s.get('subscription_cost', 0):,.0f}/mo</td>
                    </tr>
                </table>"""
            
            breakdown = s.get("breakdown", {})
            if breakdown:
                scenarios_html += '<div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(0,0,0,0.08);">'
                for bk, bv in breakdown.items():
                    scenarios_html += f"""
                    <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#1a1c1b;">{bv.get('title', '')}</p>
                    <div style="margin:0 0 12px;font-size:12px;color:#555;">{bv.get('how', '')}</div>"""
                scenarios_html += '</div>'
            scenarios_html += '</div>'
        
        body = f"""
        <h2 style="margin:0 0 8px;color:#1a1c1b;font-size:22px;font-weight:700;">Your ROI Analysis Report</h2>
        <p style="margin:0 0 24px;color:#4F46E5;font-size:14px;font-weight:600;">Prepared for: {business_name}</p>
        {scenarios_html}
        <table cellpadding="0" cellspacing="0" style="margin:24px 0;">
        <tr><td style="background:linear-gradient(135deg,#3525CD,#4F46E5);border-radius:8px;padding:14px 32px;">
            <a href="https://cryvex.in/roi" style="color:#ffffff;text-decoration:none;font-weight:700;font-size:14px;">Recalculate Your ROI &rarr;</a>
        </td></tr>
        </table>
        <p style="margin:0;font-size:13px;color:#777585;">
            Have questions? Reply to this email or reach us at <a href="https://cryvex.in" style="color:#4F46E5;">cryvex.in</a>.
        </p>"""
        return self._build_professional_html(f"Your Cryvex ROI Analysis for {business_name}", body)

    async def send_prediction_email(self, to_email: str, subject: str, html_content: str):
        """Sends an email using either the Brevo API (primary) or SMTP relay (fallback)."""
        if not self.is_configured:
            print(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
            print(f"[MOCK EMAIL CONTENT]\n{html_content[:200]}...\n[/MOCK EMAIL CONTENT]")
            return True

        # Try API first (best for dynamic IPs)
        if self.api_key:
            try:
                print(f"[EMAIL] Attempting dispatch via Brevo API for {to_email}...")
                success = await self._send_api(to_email, subject, html_content)
                if success:
                    return True
            except RuntimeError as re:
                # This catches our explicit RuntimeError from _send_api
                print(f"[EMAIL API FAIL] Brevo API rejected the request: {str(re)}")
                print("[EMAIL] Falling back to SMTP relay...")
            except Exception as e:
                print(f"[EMAIL API FAIL] Unexpected API error, falling back to SMTP: {str(e)}")
        else:
            print("[EMAIL] No API key found, using SMTP relay...")

        # Fallback to SMTP
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, to_email, subject, html_content)

    async def _send_api(self, to_email: str, subject: str, html_content: str) -> bool:
        """Dispatches email via Brevo Transactional API v3."""
        import httpx
        url = "https://api.brevo.com/v3/smtp/email"
        # Sanitize key just in case
        clean_key = self.api_key.strip()
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": clean_key,
            "x-sib-api-key": clean_key # Fallback header for older keys
        }
        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [201, 202, 200]:
                print(f"[EMAIL API OK] Successfully dispatched via API to {to_email}")
                return True
            else:
                try:
                    error_data = response.json()
                    # Capture specific Brevo error codes
                    error_msg = f"Brevo API Error ({response.status_code}): {error_data.get('message', 'Unknown error')} (Code: {error_data.get('code', 'N/A')})"
                except:
                    error_msg = f"Brevo API Error ({response.status_code}): {response.text}"
                print(f"[EMAIL API FAIL] {error_msg}")
                raise RuntimeError(error_msg)

    def _send_sync(self, to_email: str, subject: str, html_content: str):
        try:
            print(f"[EMAIL ATTEMPT] From: {self.sender_email} | To: {to_email} | Subject: {subject}")
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((self.sender_name, self.sender_email))
            msg["To"] = to_email
            msg["Reply-To"] = self.sender_email

            # Plain-text fallback (anti-spam best practice)
            import re
            # Better plain text conversion: replace block tags with newlines
            text_content = html_content
            for tag in ['</p>', '</div>', '<br/>', '<br>', '</h1>', '</h2>', '</h3>', '</td>']:
                text_content = text_content.replace(tag, '\n')
            
            plain_text = re.sub(r'<[^>]+>', '', text_content)
            plain_text = re.sub(r'[ \t]+', ' ', plain_text) # Collapse horizontal whitespace
            plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text).strip() # Normalize paragraph breaks
            
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
            server.set_debuglevel(1) # Enable debug output for logs
            server.ehlo()
            if server.has_extn('starttls'):
                server.starttls()
                server.ehlo()
            
            server.login(self.smtp_user, self.smtp_pass)
            # Use bare sender email for SMTP envelope, not the formatted display name
            server.sendmail(self.sender_email, to_email, msg.as_string())
            server.quit()
            print(f"[EMAIL OK] Successfully dispatched to {to_email}: {subject}")
            return True
        except smtplib.SMTPResponseException as e:
            error_msg = f"SMTP Error ({e.smtp_code}): {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}"
            print(f"[EMAIL FAIL] {error_msg}")
            security_logger.log_event("EMAIL_SEND_ERROR", "CRITICAL", "Backend", error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected failure sending email to {to_email}: {str(e)}"
            print(f"[EMAIL FAIL] {error_msg}")
            security_logger.log_event("EMAIL_SEND_ERROR", "ERROR", "Backend", error_msg)
            raise RuntimeError(error_msg) from e

email_service = EmailService()

