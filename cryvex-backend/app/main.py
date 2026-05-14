import os
import json
import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
import csv
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware
import pathlib
import socketio
from dotenv import load_dotenv
load_dotenv()

from app.prediction_engine import LeadPredictor
from app import db as custom_db
from app.roi import roi_engine, ROIRequest
from app.strategy import CryvexStrategist
from app.admin_analysis import audit_engine
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict
from app.r1_core.agent_logic import agent
from app.r1_core.knowledge_manager import knowledge_manager
from app.industry_knowledge import IndustryKnowledge
from app.utils import (
    TokenBucketRateLimiter, circuit_breaker, PulsePayloadValidator, 
    safe_visitor_id, sanitize_mongodb_input, security_logger
)
from app.middleware import IPSentryMiddleware, ip_sentry
from app.config import settings
from app.auth import create_access_token, verify_token, require_token, require_admin, require_admin_jwt
import time
MONGODB_URI = settings.MONGODB_URI
UPSTASH_REDIS_REST_URL = settings.UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN = settings.UPSTASH_REDIS_REST_TOKEN

# Setup FastAPI and Socket.IO
fastapi_app = FastAPI(title="Cryvex Lead Intelligence Engine")

from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from brotli_asgi import BrotliMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

fastapi_app.add_middleware(SecurityHeadersMiddleware)
fastapi_app.add_middleware(BrotliMiddleware, quality=4, minimum_size=1000)
fastapi_app.add_middleware(IPSentryMiddleware)
@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    client_ip = request.client.host if request.client else "Unknown"
    security_logger.log_event("VALIDATION_ERROR", "WARNING", client_ip, f"Input validation failed: {exc}")
    return await request_validation_exception_handler(request, exc)

# ── CORS & Security Middleware Configuration ─────────────────────────
# Parse base origins from environment
base_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

# Hardened Origin List: Include production URL and common dev origins
# This ensures that even if CORS_ORIGINS is misconfigured, core functionality remains.
allowed_origins = list(set(base_origins + [
    "https://cryvex-backend.onrender.com",  # Production Backend
    "https://cryvex.ai",                   # Potential Custom Domain
    "http://localhost:3000",                # React Default
    "http://localhost:5173",                # Vite Default
    "http://localhost:8000",                # FastAPI Default
    "http://localhost:5500",                # VS Code Live Server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
]))

# Logic: If '*' is present, we MUST disable allow_credentials for FastAPI compliance.
# However, if we have specific origins, we prioritize them to enable credentials.
if "*" in allowed_origins and len(allowed_origins) > 1:
    # Remove '*' to allow credentials for the specific listed origins
    allowed_origins = [o for o in allowed_origins if o != "*"]
    use_credentials = True
elif "*" in allowed_origins:
    use_credentials = False
else:
    use_credentials = True

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=use_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            # Cache static assets for 1 year (Edge caching strategy)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

fastapi_app.mount("/frontend", CachedStaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")), name="frontend")

sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins=allowed_origins if not (len(allowed_origins) == 1 and allowed_origins[0] == "*") else "*"
)

predictor = LeadPredictor()
strategist = None

db_client = None
db = None
redis_client = None
rate_limiter = None
MOCK_MODE = False

# ── AI Agent Session Memory ──────────────────────────────────────────
AGENT_SESSIONS: Dict[str, List[Dict[str, str]]] = {}


# ── Mock Adapters (used when Redis/MongoDB are offline) ──────────────
class MockRedis:
    """In-memory Redis simulator for local dev without Docker."""
    def __init__(self):
        self.data = {}

    async def set(self, name, value):
        self.data[name] = str(value)

    async def get(self, name):
        return self.data.get(name)

    async def exists(self, name):
        return 1 if name in self.data else 0

    async def ping(self):
        """Simulator for Redis ping."""
        return True

    async def execute_command(self, cmd, *args, **kwargs):
        """Simulator for Redis execute_command."""
        if cmd.upper() == "PING":
            return True
        return None

    async def hset(self, name, key=None, value=None, values=None):
        if name not in self.data or not isinstance(self.data[name], dict):
            self.data[name] = {}
        # Support both hset(n, k, v) and hset(n, values={...})
        if values:
            for k, v in values.items():
                self.data[name][str(k)] = str(v)
        if key is not None and not isinstance(key, dict):
            self.data[name][str(key)] = str(value)
        elif isinstance(key, dict):
            for k, v in key.items():
                self.data[name][str(k)] = str(v)

    async def hgetall(self, name):
        val = self.data.get(name, {})
        return val if isinstance(val, dict) else {}

    async def delete(self, name):
        if name in self.data:
            del self.data[name]

    async def close(self):
        pass


class MockCollection:
    """In-memory MongoDB collection simulator."""
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        self.docs[doc.get("visitor_id", id(doc))] = doc

    async def update_one(self, query, update, upsert=False):
        vid = query.get("visitor_id")
        doc = self.docs.get(vid, query.copy() if upsert else None)
        if doc and "$set" in update:
            doc.update(update["$set"])
            self.docs[vid] = doc

    async def delete_one(self, query):
        vid = query.get("visitor_id")
        if vid and vid in self.docs:
            del self.docs[vid]


class MockDB:
    def __init__(self):
        self.visitors = MockCollection()
        self.predictions = MockCollection()
        self.roi_calculations = MockCollection()
        self.strategy_prediction = MockCollection()

    def close(self):
        pass


# ── Startup / Shutdown ───────────────────────────────────────────────
@fastapi_app.on_event("startup")
async def startup_db_client():
    global db_client, db, redis_client, rate_limiter, MOCK_MODE

    from motor.motor_asyncio import AsyncIOMotorClient
    from upstash_redis.asyncio import Redis as UpstashRedis

    MOCK_MODE = False

    # 1. Connect to MongoDB independently
    try:
        # Use MONGODB_URI from env if set (supports both Atlas and Docker),
        # otherwise build an authenticated URI for Docker's internal network.
        mongo_uri = MONGODB_URI
        if not mongo_uri:
            mongo_uri = f"mongodb://{settings.MONGO_USER}:{settings.MONGO_PASSWORD}@mongodb:27017/cryvex?authSource=admin"
        
        print(f"[STARTUP] Attempting MongoDB connection...")
        # Increased timeout to 5000ms for better stability in live connections
        # Added maxPoolSize and minPoolSize for production concurrency, maxIdleTimeMS to clean up idle connections
        _mongo = AsyncIOMotorClient(
            mongo_uri, 
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=60000
        )
        await _mongo.server_info()
        db_client = _mongo
        db = _mongo["cryvex"]
        print("[OK] PRODUCTION MODE — Connected to LIVE MongoDB (cryvex)")
    except Exception as exc:
        if not settings.ALLOW_MOCK_FALLBACK:
            print(f"[FATAL] MongoDB connection failed and ALLOW_MOCK_FALLBACK=false. Refusing to start with mock store.")
            print(f"[-] DIAGNOSTIC: {exc}")
            raise RuntimeError(f"MongoDB connection failed: {exc}") from exc
        db_client = MockDB()
        db = db_client
        MOCK_MODE = True
        print(f"[!] DEV MODE — MongoDB offline. Falling back to Mock store (ALLOW_MOCK_FALLBACK=true).")
        print(f"[-] DIAGNOSTIC: {exc}")

    # 2. Connect to Upstash Redis via REST API
    try:
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            print("[STARTUP] Connecting to Upstash Redis (REST)...")
            _redis = UpstashRedis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
            # Upstash-redis asyncio doesn't have .ping(), but we can test with .get()
            await _redis.get("ping") 
            redis_client = _redis
            print("[OK] PRODUCTION MODE — Connected to Upstash Redis (REST)")
        else:
            # Fallback to local/Docker redis with password authentication
            from redis.asyncio import Redis as AsyncRedis
            
            print("[STARTUP] Connecting to Local Redis (Async)...")
            # Smart URI handling: if REDIS_URI doesn't have a password but REDIS_PASSWORD is set, use it.
            redis_uri = settings.REDIS_URI
            password = settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None
            
            # If URI is default but we have a password, we should prefer the password
            _redis = AsyncRedis.from_url(
                redis_uri, 
                password=password, 
                decode_responses=True, 
                max_connections=50
            )
            # Use execute_command which is explicitly async to satisfy type checkers
            await _redis.execute_command("PING")
            
            redis_client = _redis
            print(f"[OK] REDIS MODE — Connected to {redis_uri}")
    except Exception as exc:
        if not settings.ALLOW_MOCK_FALLBACK:
            print(f"[FATAL] Redis connection failed and ALLOW_MOCK_FALLBACK=false. Refusing to start with mock store.")
            print(f"[-] DIAGNOSTIC: {exc}")
            raise RuntimeError(f"Redis connection failed: {exc}") from exc
        redis_client = MockRedis()
        print(f"[WARN] DEV MODE — Redis offline. Falling back to Mock store (ALLOW_MOCK_FALLBACK=true). Error: {exc}")

    rate_limiter = TokenBucketRateLimiter(redis_client, burst=5, rate=3)

    # 3. Initialize Strategist
    api_key = settings.OPENROUTER_API_KEY
    if api_key:
        global strategist
        strategist = CryvexStrategist(api_key)
        print("[OK] STRATEGY ENGINE — Ready")
    else:
        print("[WARN] STRATEGY ENGINE — Missing OPENROUTER_API_KEY in .env")

    # 4. Start Background Model Loading (delayed to not block Uvicorn startup)
    knowledge_manager.start_background_loading()
    print("[OK] KNOWLEDGE MANAGER — Model warming up in background")

@fastapi_app.on_event("shutdown")
async def shutdown_db_client():
    """Ensure all connections are forcefully closed to prevent connection leaks during restarts."""
    print("[SHUTDOWN] Initiating graceful shutdown of database connections...")
    if db_client and not MOCK_MODE:
        try:
            db_client.close()
            print("[SHUTDOWN] MongoDB connection closed.")
        except Exception as e:
            print(f"[SHUTDOWN ERROR] Failed to close MongoDB: {e}")
    if redis_client:
        try:
            await redis_client.close()
            print("[SHUTDOWN] Redis connection closed.")
        except Exception as e:
            print(f"[SHUTDOWN ERROR] Failed to close Redis: {e}")


# ── R1 Support Core Endpoints ────────────────────────────────────────
class SupportRequest(BaseModel):
    session_id: str = Field(..., max_length=128)
    message: str = Field(..., max_length=2048)
    language_preference: Optional[str] = Field(None, max_length=50)

@fastapi_app.post("/chat/advanced")
async def chat_advanced(req: SupportRequest, _user: dict = Depends(require_token)):
    """
    Advanced AI Support endpoint powered by DeepSeek-R1.
    Handles RAG, CoT reasoning, and vernacular adaptation.
    Requires a valid JWT Bearer token.
    """
    session_id = req.session_id
    
    # 1. Manage Session History (Keep last 5 turns)
    if session_id not in AGENT_SESSIONS:
        AGENT_SESSIONS[session_id] = []
    
    history = AGENT_SESSIONS[session_id]
    
    # 2. RAG: Retrieve context
    context = knowledge_manager.search_context(req.message)
    
    # 3. Agent Logic: Get R1 Response
    # Pass language preference if provided to influence the prompt
    user_msg = req.message
    if req.language_preference:
        user_msg = f"[Language Preference: {req.language_preference}] {user_msg}"
        
    result = await agent.chat(user_msg, history, context)
    
    if "error" in result:
        return {"status": "error", "message": result["error"]}

    # 4. Update History
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["final_answer"]})
    
    # Prune history to 5 turns (10 messages)
    if len(history) > 10:
        AGENT_SESSIONS[session_id] = history[-10:]
    else:
        AGENT_SESSIONS[session_id] = history

    return {
        "status": "success",
        "reasoning": result["reasoning"],
        "answer": result["final_answer"],
        "context_used": context != "No context available (Vector store not initialized)."
    }

@fastapi_app.post("/agent/vectorize")
async def trigger_vectorization(_admin: bool = Depends(require_admin)):
    """Manually trigger document vectorization from the data directory. Requires admin credentials."""
    try:
        knowledge_manager.vectorize_documents()
        return {"status": "success", "message": "Documents vectorized successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── HTTP Endpoints ───────────────────────────────────────────────────
def serve_html(filename):
    # Try looking in app folder first
    html_path_app = pathlib.Path(__file__).parent / filename
    # Try looking in the frontend folder next
    html_path_frontend = pathlib.Path(__file__).parent.parent / "frontend" / filename
    # Try looking in the frontend/pages folder
    html_path_pages = pathlib.Path(__file__).parent.parent / "frontend" / "pages" / filename
    
    if html_path_app.exists():
        with open(html_path_app, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    elif html_path_frontend.exists():
        with open(html_path_frontend, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    elif html_path_pages.exists():
        with open(html_path_pages, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
            
    return HTMLResponse(f"Frontend '{filename}' not found", status_code=404)

@fastapi_app.get("/")
async def get_frontend():
    return serve_html("index.html")

@fastapi_app.get("/support-ai")
async def get_support_ui():
    return serve_html("support_ai.html")

@fastapi_app.get("/textile")
async def get_textile():
    return serve_html("textile.html")
    
@fastapi_app.get("/manufacturing")
async def get_mfg():
    return serve_html("manufacturing.html")
    
@fastapi_app.get("/e-commerce")
async def get_ecomm():
    return serve_html("ecommerce.html")

@fastapi_app.get("/about")
async def get_about():
    return serve_html("about.html")

@fastapi_app.get("/blog")
async def get_blog():
    return serve_html("blog.html")

@fastapi_app.get("/roi")
async def get_roi():
    return serve_html("roi.html")

@fastapi_app.get("/strategy")
async def get_strategy_page():
    return serve_html("strategy.html")

@fastapi_app.get("/audit")
async def get_admin_audit_page():
    return serve_html("admin_audit.html")

@fastapi_app.get("/admin/login")
async def get_admin_login_page():
    return serve_html("admin_login.html")

@fastapi_app.get("/admin")
async def get_admin_dashboard_page():
    return serve_html("admin_dashboard.html")

class StrategyRequest(BaseModel):
    business_type: str = Field(..., max_length=100)
    problem: str = Field(..., max_length=2048)
    business_name: str = Field(default="Unknown", max_length=256)
    language: str = Field(default="English", max_length=50)
    visitor_id: str = Field(default="Unknown", max_length=128)
    target_audience: str = Field(default="Unknown", max_length=256)
    primary_goal: str = Field(default="Unknown", max_length=256)


@fastapi_app.get("/status")
async def health_check():
    return {
        "status": "online",
        "mode": "production" if not MOCK_MODE else "local-dev",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@fastapi_app.get("/api/visitor/init")
async def init_visitor():
    """Generates a new visitor ID, creates DB entry, and returns it."""
    visitor_id = f"cryvex_enc_{uuid.uuid4().hex}"
    # Create the visitor document following the required schema
    await custom_db.init_visitor_db(db, visitor_id)
    return {"visitor_id": visitor_id, "status": "initialized"}

@fastapi_app.get("/api/v1/auth/token")
async def get_token(visitor_id: str):
    """Token Vending Machine: returns a signed RS256 JWT only for verified visitor IDs."""
    clean_id = safe_visitor_id(visitor_id)
    # Only issue tokens for properly formatted Cryvex visitor IDs
    if not clean_id.startswith("cryvex_enc_"):
        raise HTTPException(status_code=400, detail="Invalid visitor ID format.")
    # Proof-of-identity: verify the visitor actually exists in the database
    if db is not None:
        existing = await db.visitors.find_one({"visitor_id": clean_id}) if not MOCK_MODE else (
            db.visitors.docs.get(clean_id) if hasattr(db, 'visitors') and hasattr(db.visitors, 'docs') else None
        )
        if not existing:
            print(f"[AUTH] Token request rejected: Visitor ID {clean_id} not found in database.")
            raise HTTPException(status_code=404, detail="Visitor ID not found. Call /api/visitor/init first.")
    token = create_access_token({"sub": clean_id})
    return {"token": token}

@fastapi_app.post("/api/roi/calculate")
async def calculate_roi(data: ROIRequest, _user: dict = Depends(require_token)):
    try:
        # 1. High Personalization: Check MongoDB for visitor history if industry is unknown
        industry = data.industry
        if industry == "General" and data.visitor_id != "Unknown":
            clean_vid = safe_visitor_id(data.visitor_id)
            v_data = await db.visitors.find_one({"visitor_id": clean_vid})
            if v_data and v_data.get("category") and v_data.get("category") != "Unknown":
                industry = v_data.get("category")

        # 2. Generate detailed results
        results = roi_engine.analyze_scenarios(data)
        
        # 3. Store the record to MongoDB for investor-ready reporting
        business_info = {
            "business_name": data.business_name,
            "industry": industry,
            "inputs": {
                "traffic": data.traffic,
                "conv_rate": data.conv_rate,
                "lead_value": data.lead_value,
                "hourly_rate": data.hourly_rate,
                "manual_hours": data.manual_hours
            }
        }
        await custom_db.save_roi_record(db, data.visitor_id, business_info, results)

        return {
            "status": "success",
            "message": "ROI Analysis Complete",
            "detected_industry": industry,
            "owner_id": data.visitor_id,
            "scenarios": results
        }
    except Exception as e:
        print(f"ROI Calculation Error: {e}")
        return {"status": "error", "message": str(e)}

@fastapi_app.post("/api/strategy/generate")
async def generate_strategy_api(request: StrategyRequest, _user: dict = Depends(require_token)):
    """Generates a localized business strategy directly mapped to the master visitor ID."""
    if not strategist:
        return {"status": "error", "message": "Strategist engine not initialized. Check API Key."}
    
    # Establish single truth identity map (foreign key)
    biz_owner_id = request.visitor_id
    if not biz_owner_id or biz_owner_id == "Unknown" or biz_owner_id == 'null':
        biz_owner_id = str(uuid.uuid4())

    try:
        # Generate the strategy via LLM
        strategy_text = await strategist.generate_strategy({
            "business_type": request.business_type,
            "problem": request.problem,
            "business_name": request.business_name,
            "language": request.language,
            "target_audience": request.target_audience,
            "primary_goal": request.primary_goal
        })

        # Persist to MongoDB strategy_prediction table
        await custom_db.save_strategy_prediction(
            db=db,
            visitor_id=biz_owner_id,
            business_data={
                "business_name": request.business_name,
                "business_type": request.business_type,
                "problem": request.problem,
                "target_audience": request.target_audience,
                "primary_goal": request.primary_goal
            },
            strategy_output=strategy_text
        )

        return {
            "status": "success",
            "owner_id": biz_owner_id,
            "strategy": strategy_text
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

class UnlockRequest(BaseModel):
    visitor_id: str = Field(..., max_length=128)
    # Relaxed pattern to support subdomains and complex TLDs
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9-.]+$")

@fastapi_app.post("/api/unlock/strategy")
async def unlock_strategy(req: UnlockRequest, _user: dict = Depends(require_token)):
    from app.utils import email_service
    try:
        clean_id = safe_visitor_id(req.visitor_id)
        # Verify the record exists
        record = await db.strategy_prediction.find_one({"visitor_id": clean_id})
        if not record:
            return {"status": "error", "message": "Prediction not found. Please generate a strategy first."}
        
        # Update email in DB
        await custom_db.update_strategy_email(db, clean_id, req.email)
        
        # Prepare professional email content
        strategy = record.get("generated_strategy", "")
        business = record.get("business_name", "your business")
        html = email_service.build_strategy_email(business, strategy)
        
        # Dispatch email with error handling
        try:
            await email_service.send_prediction_email(
                to_email=req.email,
                subject=f"Cryvex AI: Your Exclusive Strategy for {business}",
                html_content=html
            )
        except RuntimeError as email_err:
            print(f"[EMAIL FAIL] Strategy unlock email failed: {email_err}")
            # Still return the strategy data even if email fails
            return {"status": "success", "message": "Strategy unlocked! However, we couldn't send the email right now. Your full strategy is shown below.", "strategy": strategy, "email_sent": False}
        
        return {"status": "success", "message": "Unlocked successfully. A copy has been sent to your email.", "strategy": strategy, "email_sent": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.post("/api/unlock/roi")
async def unlock_roi(req: UnlockRequest, _user: dict = Depends(require_token)):
    from app.utils import email_service
    try:
        clean_id = safe_visitor_id(req.visitor_id)
        record = await db.roi_calculations.find_one({"visitor_id": clean_id}, sort=[("calculated_at", -1)])
        if not record:
            return {"status": "error", "message": "ROI calculation not found. Please run the ROI calculator first."}

        # Update email in DB
        await custom_db.update_roi_email(db, clean_id, req.email)

        # Prepare professional email content
        calc = record.get("calculated_ROI", {})
        business = record.get("business_name", "your business")
        html = email_service.build_roi_email(business, calc)

        # Dispatch email with error handling
        try:
            await email_service.send_prediction_email(
                to_email=req.email,
                subject=f"Cryvex AI: Your ROI Analysis for {business}",
                html_content=html
            )
        except RuntimeError as email_err:
            print(f"[EMAIL FAIL] ROI unlock email failed: {email_err}")
            return {"status": "success", "message": "ROI unlocked! However, we couldn't send the email right now. Your full report is shown below.", "roi": calc, "email_sent": False}

        return {"status": "success", "message": "Unlocked successfully. A copy has been sent to your email.", "roi": calc, "email_sent": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/admin/audit/{visitor_id}")
async def generate_advanced_audit(visitor_id: str, _admin: bool = Depends(require_admin)):
    try:
        clean_id = safe_visitor_id(visitor_id)
        report = await audit_engine.generate_audit(db, clean_id)
        return report
    except Exception as e:
        print(f"Audit Generation Error: {e}")
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/admin/export_csv")
async def export_database_csv(_admin: bool = Depends(require_admin)):
    """Exports all leads and their latest ROI into a CSV. Requires admin credentials."""
    try:
        if db is None:
            return {"status": "error", "message": "Database not initialized"}
            
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Visitor ID", "First Visit", "Last Visited", "Status", "Persona", 
            "Lead Score", "Category/Industry", "Most Visited Section", 
            "Business Name", "Traffic", "Conv Rate", "Lead Value", "Human Cost", "AI Cost", "Net Potential ROI"
        ])
        
        if MOCK_MODE:
            visitors = list(db.visitors.docs.values())
        else:
            visitors_cursor = db.visitors.find({})
            visitors = await visitors_cursor.to_list(length=10000)
            
        for v in visitors:
            vid = v.get("visitor_id")
            
            if MOCK_MODE:
                rois = [r for r in db.roi_calculations.docs.values() if r.get("visitor_id") == vid]
                roi_doc = sorted(rois, key=lambda x: x.get("calculated_at", ""), reverse=True)[0] if rois else None
            else:
                roi_doc = await db.roi_calculations.find_one({"visitor_id": vid}, sort=[("calculated_at", -1)])
                
            b_name = "Unknown"
            traffic = 0.0
            cvr = 0.0
            lv = 0.0
            h_cost = 0.0
            a_cost = 0.0
            net_roi = 0.0
            
            if roi_doc:
                b_name = roi_doc.get("business_name", "Unknown")
                inputs = roi_doc.get("input_datas", {})
                calc = roi_doc.get("calculated_ROI", {})
                
                # Bulletproof float casting for UI inputs
                traffic = float(inputs.get("traffic") or 0)
                cvr = float(inputs.get("conv_rate") or 0)
                lv = float(inputs.get("lead_value") or 0)
                manual_h = float(inputs.get("manual_hours") or 0)
                hourly_r = float(inputs.get("hourly_rate") or 0)
                
                h_cost = manual_h * hourly_r
                
                if "realistic" in calc:
                    a_cost = float(calc["realistic"].get("subscription_cost", 0))
                    net_roi = float(calc["realistic"].get("net_profit", 0))
                else:
                    a_cost = 4900 if h_cost < 20000 else (14900 if h_cost < 75000 else 39900)
                    base_roi = (traffic * (cvr/100.0) * lv * 0.25)
                    net_roi = (base_roi + h_cost) - a_cost

            writer.writerow([
                vid,
                v.get("first_visit", ""),
                v.get("last_visited", ""),
                v.get("status", ""),
                v.get("persona", "Unknown"),
                v.get("lead_prediction_score", 0),
                v.get("category", "Unknown"),
                v.get("long_time_visited_section", "Unknown"),
                b_name,
                traffic,
                cvr,
                lv,
                h_cost,
                a_cost,
                round(net_roi, 2)
            ])
            
        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=cryvex_database_export.csv"
        return response
    except Exception as e:
        print(f"CSV Export Error: {e}")
        return Response(content=f"Error exporting data: {str(e)}", status_code=500)


@fastapi_app.delete("/api/admin/roi/{visitor_id}")
async def delete_roi_record(visitor_id: str, _admin: bool = Depends(require_admin)):
    """Admin endpoint to delete an ROI user record. Requires admin credentials."""
    if db is None:
        return {"status": "error", "message": "Database not initialized"}
    try:
        clean_id = safe_visitor_id(visitor_id)
        await db.roi_calculations.delete_one({"visitor_id": clean_id})
        return {"status": "success", "message": "Record deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.delete("/api/admin/strategy/{visitor_id}")
async def delete_strategy_record(visitor_id: str, _admin: bool = Depends(require_admin)):
    """Admin endpoint to delete a Strategy AI user record. Requires admin credentials."""
    if db is None:
        return {"status": "error", "message": "Database not initialized"}
    try:
        clean_id = safe_visitor_id(visitor_id)
        await db.strategy_prediction.delete_one({"visitor_id": clean_id})
        return {"status": "success", "message": "Record deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.delete("/api/admin/visitor/{visitor_id}")
async def delete_visitor_record(visitor_id: str, _admin: bool = Depends(require_admin)):
    """Admin endpoint to delete a base visitor record. Requires admin credentials."""
    if db is None:
        return {"status": "error", "message": "Database not initialized"}
    try:
        clean_id = safe_visitor_id(visitor_id)
        await db.visitors.delete_one({"visitor_id": clean_id})
        return {"status": "success", "message": "Record deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@fastapi_app.post("/api/admin/login")
async def admin_login(req: AdminLoginRequest, request: Request):
    """Authenticates the admin via username and password and returns a JWT."""
    client_ip = request.client.host if request.client else "Unknown"
    
    # Constant-time comparison
    import secrets
    is_user_valid = secrets.compare_digest(req.username, settings.ADMIN_USERNAME)
    is_pass_valid = secrets.compare_digest(req.password, settings.ADMIN_PASSWORD)
    
    if not (is_user_valid and is_pass_valid):
        security_logger.log_event("ADMIN_LOGIN_FAILED", "CRITICAL", client_ip, f"Failed login attempt for user: {req.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate admin JWT
    token = create_access_token({"sub": "admin_root", "role": "admin"})
    security_logger.log_event("ADMIN_LOGIN_SUCCESS", "INFO", client_ip, "Admin successfully logged in.")
    return {"access_token": token, "token_type": "bearer"}

@fastapi_app.get("/api/admin/dashboard_data")
async def get_admin_dashboard_data(admin_payload: dict = Depends(require_admin_jwt)):
    """Fetches high-level aggregated data for the admin dashboard. Protected by Admin JWT."""
    if db is None:
        return {"status": "error", "message": "Database not initialized"}
    
    try:
        data = await audit_engine.generate_audit(db, "admin")
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── Socket.IO Event Handlers ────────────────────────────────────────
@sio.on("connect")
async def connect(sid, environ, auth=None):
    # Extract Client IP from ASGI scope, supporting reverse proxies
    scope = environ.get('asgi.scope', {})
    headers = dict(scope.get('headers', []))
    client_ip = headers.get(b'x-forwarded-for', b'').decode().split(',')[0].strip()
    if not client_ip:
        client_ip = scope.get('client', ['0.0.0.0'])[0]  # nosec B104
    
    # Layer 1: Fast-Path RAM IP-Sentry
    if not ip_sentry.check_ip(client_ip):
        security_logger.log_event("WS_CONNECT_REJECTED", "CRITICAL", client_ip, "IP-Sentry Blocked connection.")
        raise ConnectionRefusedError('IP Blocked')
    
    # Layer B: Per-IP Enforcement (Blocklist Check)
    is_blocked = await circuit_breaker.execute(redis_client.exists(f"blocked:{client_ip}"), fallback=False)
    if is_blocked:
        security_logger.log_event("WS_CONNECT_REJECTED", "CRITICAL", client_ip, "IP is in blocklist.")
        raise ConnectionRefusedError('IP Blocked')

    # Gatekeeper: Token Extraction & Verification
    token = auth.get("token") if auth else None
    if not token:
        security_logger.log_event("WS_CONNECT_REJECTED", "WARNING", client_ip, "Missing Token.")
        raise ConnectionRefusedError('Missing Token')

    payload = verify_token(token)
    if not payload or not payload.get("sub"):
        security_logger.log_event("WS_CONNECT_REJECTED", "WARNING", client_ip, "Invalid or Expired Token.")
        raise ConnectionRefusedError('Invalid Token')
        
    visitor_id = payload.get("sub")
    if not visitor_id.startswith("cryvex_enc_"):
        security_logger.log_event("WS_CONNECT_REJECTED", "CRITICAL", client_ip, f"Malformed Visitor ID: {visitor_id}")
        raise ConnectionRefusedError('Invalid Visitor ID')

    # Binding: save to session
    await sio.save_session(sid, {"visitor_id": visitor_id, "token": token})

    await redis_client.set(f"sid:{sid}", visitor_id)
    await redis_client.set(f"ip:{sid}", client_ip)
    
    session_exists = await redis_client.exists(f"visitor:state:{visitor_id}")
    if not session_exists:
        await redis_client.hset(f"visitor:state:{visitor_id}", values={
            "status": "connected",
            "freq_map": json.dumps({"Home": 0}),
            "section_freq_map": json.dumps({"Entry Section": 0}),
            "scroll_memory": json.dumps({}),
            "actions_taken": json.dumps([])
        })

        try:
            await db.visitors.update_one(
                {"visitor_id": visitor_id},
                {"$set": {"status": "connected"}},
                upsert=True
            )
        except Exception:
            pass
    print(f"[ON] Client connected: {sid} (Visitor: {visitor_id}, IP: {client_ip})")


@sio.on("disconnect")
async def disconnect(sid):
    visitor_id = await redis_client.get(f"sid:{sid}")
    print(f"[OFF] Client disconnected: {sid} (Visitor: {visitor_id})")
    if not visitor_id:
        return
        
    session_data = await redis_client.hgetall(f"visitor:state:{visitor_id}")
    if session_data:
        freq_map = json.loads(session_data.get("freq_map", "{}"))
        section_freq_map = json.loads(session_data.get("section_freq_map", "{}"))
        lead_score = int(session_data.get("score", 0))
        most_time_spent_page = session_data.get("most_time_spent_page", "Unknown")
        most_time_spent_section = session_data.get("most_time_spent_section", "Unknown")

        # Determine persona from score
        if lead_score >= 86:
            persona = "Hot Lead"
        elif lead_score >= 61:
            persona = "Interested Prospect"
        elif lead_score >= 31:
            persona = "Explorer"
        else:
            persona = "Casual Visitor"

        await custom_db.update_visitor_db(
            db=db,
            visitor_id=visitor_id,
            lead_score=lead_score,
            category=most_time_spent_page,  # Maps exactly to page topics like 'Textile', 'Manufacturing'
            persona=persona,
            long_section=most_time_spent_section,
            freq_map=freq_map,
            section_freq_map=section_freq_map
        )
        await db.visitors.update_one({"visitor_id": visitor_id}, {"$set": {"status": "disconnected"}})
    # Note: We delete sid mapping, but KEEP session:{visitor_id} intact for persistent multi-page routing
    await redis_client.delete(f"sid:{sid}")


@sio.on("heartbeat")
async def handle_heartbeat(sid, current_pulse):
    """The Heartbeat: Receives pulses every 1-2s and triggers prediction."""
    session = await sio.get_session(sid)
    visitor_id = session.get("visitor_id")
    token = session.get("token")
    
    client_ip = await redis_client.get(f"ip:{sid}")
    
    # Continuous Verification: re-validate token expiration
    if token:
        payload = verify_token(token)
        if not payload:
            security_logger.log_event("WS_SESSION_EXPIRED", "WARNING", client_ip, f"Session expired for {visitor_id}. Disconnecting.")
            await sio.disconnect(sid)
            return

    # Fallback to redis if session is somehow missing
    if not visitor_id:
        visitor_id = await redis_client.get(f"sid:{sid}")
        if visitor_id:
            await sio.save_session(sid, {"visitor_id": visitor_id})

    client_ip = await redis_client.get(f"ip:{sid}")
    if not visitor_id:
        return

    # Layer C: Payload Hardening (Size check)
    if isinstance(current_pulse, str):
        if len(current_pulse) > 2048:
            print(f"[SHIELD] Payload Too Large (>2KB) from {client_ip}. Dropping.")
            await sio.disconnect(sid)
            return
        try:
            current_pulse = json.loads(current_pulse)
        except Exception:
            return
    elif isinstance(current_pulse, dict):
        if len(json.dumps(current_pulse)) > 2048:
            print(f"[SHIELD] Payload Too Large (>2KB) from {client_ip}. Dropping.")
            await sio.disconnect(sid)
            return

    # Event-Level Anti-Hijacking
    packet_visitor_id = current_pulse.get("visitor_id")
    if packet_visitor_id and packet_visitor_id != visitor_id:
        print(f"[SHIELD] Security Breach! Visitor ID mismatch. Session: {visitor_id}, Packet: {packet_visitor_id}")
        await sio.emit("security_alert", {"status": 1008, "message": "Policy Violation"}, to=sid)
        await sio.disconnect(sid)
        return

    # Layer 1: Fast-Path RAM IP-Sentry
    if not ip_sentry.check_ip(client_ip):
        print(f"[SHIELD] IP-Sentry blocked heartbeat from {client_ip}")
        await sio.disconnect(sid)
        return

    # Security Hardening
    if not visitor_id.startswith("cryvex_enc_"):
        await sio.disconnect(sid)
        return

    # Layer A: The Global Guard (Max 10,000 pulses/sec)
    current_sec = int(time.time())
    bucket_key = f"global_pulse_bucket:{current_sec}"
    global_pulses = await circuit_breaker.execute(redis_client.incr(bucket_key), fallback=0)
    if global_pulses == 1:
        await circuit_breaker.execute(redis_client.expire(bucket_key, 2))
    if global_pulses > 10000:
        print(f"[SHIELD] Global Guard Tripped! Pulses: {global_pulses}/sec")
        return

    # Layer C: Payload Hardening (Strict Pydantic Check)
    try:
        validated_pulse = PulsePayloadValidator(**current_pulse)
        current_pulse = validated_pulse.model_dump()
    except ValidationError as e:
        security_logger.log_event("PAYLOAD_VALIDATION_ERROR", "WARNING", client_ip, f"Malformed pulse from {visitor_id}: {e}")
        await sio.disconnect(sid)
        return
    except Exception as e:
        security_logger.log_event("WS_ERROR", "ERROR", client_ip, f"Unexpected pulse error: {e}")
        await sio.disconnect(sid)
        return

    current_page = current_pulse.get("current_page", "Home")

    # 1. Fetch current session state
    session_data = await redis_client.hgetall(f"visitor:state:{visitor_id}")
    freq_map = json.loads(session_data.get("freq_map", "{}"))
    section_freq_map = json.loads(session_data.get("section_freq_map", "{}"))
    scroll_memory = json.loads(session_data.get("scroll_memory", "{}"))
    actions_taken = set(json.loads(session_data.get("actions_taken", "[]")))
    previous_score = int(session_data.get("score", 0))

    current_section = current_pulse.get("current_section", "Entry Section")
    scroll_depth = current_pulse.get("scroll_depth", 0)
    current_actions = current_pulse.get("actions", [])

    # Accumulate permanent actions
    for act in current_actions:
        actions_taken.add(act)

    # Increment frequency maps
    freq_map[current_page] = freq_map.get(current_page, 0) + 1
    section_freq_map[current_section] = section_freq_map.get(current_section, 0) + 1
    
    # Update scroll memory
    mem_key = f"{current_page}_{current_section}"
    current_max = scroll_memory.get(mem_key, 0)
    if scroll_depth > current_max:
        scroll_memory[mem_key] = scroll_depth

    historical_stats = {
        "freq_map": freq_map,
        "section_freq_map": section_freq_map,
        "scroll_memory": scroll_memory,
        "actions_taken": list(actions_taken)
    }

    # 2. Generate Prediction (Ensure strictly additive and non-decreasing)
    prediction_result = predictor.predict(current_pulse, historical_stats)
    new_calculated_score = prediction_result.get("lead_score", 0)
    score = max(previous_score, new_calculated_score)
    most_time_spent_page = prediction_result.get("most_time_spent_page", "Unknown")
    most_time_spent_section = prediction_result.get("most_time_spent_section", "Unknown")
    frontend_hint = prediction_result.get("frontend_hint")
    tier = prediction_result.get("tier", 0)
    engagement_persona = prediction_result.get("engagement_persona", "Casual Browser")
    conversion_readiness = prediction_result.get("conversion_readiness", 0.0)
    page_journey = prediction_result.get("page_journey", [current_page])
    dominant_interest = prediction_result.get("dominant_interest", current_page)
    actions_summary = prediction_result.get("actions_summary", {})

    # 3. Determine suggested message based on thresholds
    if frontend_hint:
        suggested_message = f"💡 {frontend_hint}"
    elif score >= 86:
        suggested_message = "🔥 Hot Lead / Convert Now"
    elif score >= 61:
        suggested_message = "📊 High Intent / Show ROI Calculator"
    elif score >= 31:
        suggested_message = "📋 Medium Intent / Show Use Case"
    else:
        suggested_message = "👋 General Welcome"

    # 3b. Industry Knowledge Payload
    visit_count = 0
    try:
        sec_visits = section_freq_map.get(current_section, 0)
        visit_count = int(float(sec_visits)) if sec_visits else 0
    except (ValueError, TypeError):
        visit_count = 0
    knowledge_payload = IndustryKnowledge.get_knowledge(
        vertical=current_page,
        section=current_section,
        tier=tier,
        visit_count=visit_count
    )

    # 4. Atomic Lua Execution: Token Bucket + State Update
    state_json_args = [
        json.dumps(freq_map),
        json.dumps(section_freq_map),
        json.dumps(scroll_memory),
        json.dumps(list(actions_taken)),
        most_time_spent_page,
        most_time_spent_section
    ]
    # process_pulse_atomic(redis_client, visitor_id, increment_time, score, now, state_json_args)
    # increment_time = 1 (1 sec per pulse usually, but this satisfies the logic)
    # now = current_sec
    # fallback to False (fail-closed) if circuit breaker trips — blocks pulse to prevent rate limiting bypass
    is_allowed = await circuit_breaker.execute(
        custom_db.process_pulse_atomic(redis_client, visitor_id, 1, score, current_sec, state_json_args), 
        fallback=False
    )
    
    if not is_allowed:
        print(f"[SHIELD] Token Bucket Empty for Visitor {visitor_id}. Emitting 429.")
        await sio.emit("error", {"status": 429, "message": "Too Many Requests"}, to=sid)
        await sio.disconnect(sid)
        return

    # 5. Real-Time Push back to frontend — enriched personalization payload
    await sio.emit("prediction_update", {
        "score": score,
        "most_time_spent_page": most_time_spent_page,
        "most_time_spent_section": most_time_spent_section,
        "suggested_message": suggested_message,
        "frontend_hint": frontend_hint,
        "engagement_persona": engagement_persona,
        "conversion_readiness": conversion_readiness,
        "page_journey": page_journey,
        "dominant_interest": dominant_interest,
        "actions_summary": actions_summary,
        "tier": tier,
        "knowledge": knowledge_payload,
    }, to=sid)

    # 6. Check for CTA Interaction (Status marker only)
    if "CTA" in current_section or "click" in current_actions:
        await db.visitors.update_one({"visitor_id": visitor_id}, {"$set": {"status": "engaged_cta"}})


# ── ASGI Application ────────────────────────────────────────────────
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
