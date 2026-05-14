from datetime import datetime, timezone
from app.utils import safe_visitor_id, sanitize_mongodb_input

async def init_visitor_db(db, visitor_id: str):
    """Create a new visitor in the Database with the requested schema format."""
    clean_id = safe_visitor_id(visitor_id)
    now = datetime.now(timezone.utc).isoformat()
    await db.visitors.insert_one({
        "visitor_id": clean_id,
        "first_visit": now,
        "persona": "Unknown",
        "lead_prediction_score": 0,
        "category": "Unknown",
        "long_time_visited_section": "Entry Section",
        "history": {},
        "section_history": {}
    })

async def update_visitor_db(db, visitor_id: str, lead_score: int, category: str, persona: str, long_section: str, freq_map: dict, section_freq_map: dict):
    """Updates an existing visitor entry with their most recent calculated actions."""
    clean_id = safe_visitor_id(visitor_id)
    await db.visitors.update_one(
        {"visitor_id": clean_id},
        {"$set": {
            "lead_prediction_score": lead_score,
            "category": category,
            "persona": persona,
            "long_time_visited_section": long_section,
            "history": freq_map,
            "section_history": section_freq_map,
            "last_visited": datetime.now(timezone.utc).isoformat()
        }}
    )

async def save_roi_record(db, visitor_id: str, business_data: dict, results: dict):
    """Saves a detailed ROI calculation record to the database."""
    clean_id = safe_visitor_id(visitor_id)
    sanitize_mongodb_input(business_data)
    record = {
        "visitor_id": clean_id,
        "business_name": business_data.get("business_name", "Unknown"),
        "business_industry": business_data.get("industry", "General"),
        "email": business_data.get("email", None),
        "input_datas": business_data.get("inputs", {}),
        "calculated_ROI": results,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.roi_calculations.insert_one(record)
    return True

async def save_strategy_prediction(db, visitor_id: str, business_data: dict, strategy_output: str):
    """Saves a detailed business strategy prediction to the database."""
    clean_id = safe_visitor_id(visitor_id)
    sanitize_mongodb_input(business_data)
    record = {
        "visitor_id": clean_id,
        "business_name": business_data.get("business_name", "Unknown"),
        "business_type": business_data.get("business_type", "Unknown"),
        "problem_statement": business_data.get("problem", "Growth"),
        "generated_strategy": strategy_output,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.strategy_prediction.insert_one(record)
    return True

async def update_roi_email(db, visitor_id: str, email: str):
    clean_id = safe_visitor_id(visitor_id)
    await db.roi_calculations.update_many(
        {"visitor_id": clean_id},
        {"$set": {"email": email}}
    )
    return True

async def update_strategy_email(db, visitor_id: str, email: str):
    clean_id = safe_visitor_id(visitor_id)
    await db.strategy_prediction.update_many(
        {"visitor_id": clean_id},
        {"$set": {"email": email}}
    )
    return True



# ==========================================
# Task 2: Atomic "Single-Token" Visitor Logic
# ==========================================
PULSE_PROCESS_SCRIPT = """
local key = KEYS[1]
local increment_time = tonumber(ARGV[1])
local score = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local freq_map = ARGV[4]
local section_freq_map = ARGV[5]
local scroll_memory = ARGV[6]
local actions_taken = ARGV[7]
local mt_page = ARGV[8]
local mt_section = ARGV[9]

local burst = 5
local rate = 1

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1] or burst)
local last_refill = tonumber(bucket[2] or now)

local time_passed = math.max(0, now - last_refill)
tokens = math.min(burst, tokens + time_passed * rate)

if tokens <= 0 then
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    return 0
end

tokens = tokens - 1
-- Update state and reset TTL in the same call
redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now, 'total_time', tonumber(redis.call('HGET', key, 'total_time') or 0) + increment_time, 'score', math.max(tonumber(redis.call('HGET', key, 'score') or 0), score), 'last_pulse', now, 'freq_map', freq_map, 'section_freq_map', section_freq_map, 'scroll_memory', scroll_memory, 'actions_taken', actions_taken, 'most_time_spent_page', mt_page, 'most_time_spent_section', mt_section)
redis.call('EXPIRE', key, 3600)
return 1
"""

async def process_pulse_atomic(redis_client, visitor_id: str, increment_time: float, score: int, now: int, state_json_args: list) -> bool:
    """Executes the single-token atomic pulse logic via Lua.
    
    Security: Fail-CLOSED design. If Redis/Lua fails, returns False (blocks the pulse)
    to prevent rate limiting bypass during backend outages.
    """
    if hasattr(redis_client, 'data'):
        # MockRedis — only allow in explicit dev mode
        from app.config import settings
        if settings.ALLOW_MOCK_FALLBACK:
            return True
        # In production, mock should never be active. Fail closed.
        print("[SHIELD] CRITICAL: MockRedis detected in non-dev mode. Failing closed.")
        return False
        
    key = f"visitor:state:{visitor_id}"
    try:
        if redis_client.__class__.__module__.startswith('upstash_redis'):
            result = await redis_client.eval(PULSE_PROCESS_SCRIPT, keys=[key], args=[increment_time, score, now] + state_json_args)
        else:
            result = await redis_client.eval(PULSE_PROCESS_SCRIPT, 1, key, increment_time, score, now, *state_json_args)
        return bool(result)
    except Exception as e:
        print(f"[SHIELD] Lua Execution Error (FAIL-CLOSED): {e}")
        return False  # Fail-CLOSED: block the pulse to prevent rate limiting bypass
