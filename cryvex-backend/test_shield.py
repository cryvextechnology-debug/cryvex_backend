import asyncio
from app.main import handle_heartbeat, sio, redis_client
from app.utils import circuit_breaker
from app import db as custom_db
import json

async def test_heartbeat():
    # Setup mock data
    await redis_client.set("sid:test_sid", "vid_test123")
    await redis_client.set("ip:test_sid", "127.0.0.1")
    await redis_client.hset("session:vid_test123", values={
        "status": "connected",
        "freq_map": json.dumps({"Home": 0}),
        "section_freq_map": json.dumps({"Entry Section": 0}),
        "scroll_memory": json.dumps({}),
        "actions_taken": json.dumps([])
    })
    
    pulse = {
        "current_page": "Home",
        "current_section": "section-hero",
        "scroll_depth": 0,
        "actions": []
    }
    
    # We must patch sio.emit to see what happens
    emitted = []
    async def mock_emit(event, data, to=None):
        emitted.append((event, data))
    sio.emit = mock_emit
    
    await handle_heartbeat("test_sid", pulse)
    print("Emitted:", emitted)

if __name__ == "__main__":
    asyncio.run(test_heartbeat())
