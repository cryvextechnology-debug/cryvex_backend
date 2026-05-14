import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class IPSentryTracker:
    """Local, in-memory IP tracker to drop DDoS traffic at $0 cost."""
    def __init__(self):
        # Maps IP -> {"count": int, "start_time": float}
        self.request_counts = defaultdict(lambda: {"count": 0, "start_time": time.time()})
        # Maps IP -> block_expiry_timestamp
        self.blocked_ips = {}
        
    def check_ip(self, ip: str) -> bool:
        """Returns True if allowed, False if blocked."""
        now = time.time()
        
        # 1. Check if currently blocked
        if ip in self.blocked_ips:
            if now < self.blocked_ips[ip]:
                return False
            else:
                del self.blocked_ips[ip] # Block expired
                
        # 2. Track rate (Max 5 requests per second)
        tracker = self.request_counts[ip]
        if now - tracker["start_time"] > 1.0:
            tracker["count"] = 1
            tracker["start_time"] = now
        else:
            tracker["count"] += 1
            if tracker["count"] > 5:
                # Block for 60 seconds
                self.blocked_ips[ip] = now + 60
                return False
                
        return True

ip_sentry = IPSentryTracker()

class IPSentryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "0.0.0.0"  # nosec B104
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0]
            
        if not ip_sentry.check_ip(client_ip):
            return JSONResponse(status_code=429, content={"error": "IP Blocked. Too many requests."})
            
        return await call_next(request)
