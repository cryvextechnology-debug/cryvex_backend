import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from upstash_redis.asyncio import Redis as UpstashRedis

load_dotenv()

async def check_connections():
    print("--- 🔍 Cryvex Cloud Connectivity Check (REST Mode) ---")
    
    # 1. Check MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    print(f"\n[1] Testing MongoDB Atlas...")
    try:
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        info = await client.server_info()
        print(f"    ✅ SUCCESS: Connected to MongoDB (Version: {info.get('version')})")
    except Exception as e:
        print(f"    ❌ FAILED: MongoDB Connection Error: {e}")

    # 2. Check Redis (Upstash REST)
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    print(f"\n[2] Testing Upstash Redis (REST API)...")
    try:
        redis = UpstashRedis(url=url, token=token)
        await redis.set("foo", "bar")
        val = await redis.get("foo")
        if val == "bar":
            print(f"    ✅ SUCCESS: Connected to Upstash Redis REST API")
            print(f"    ✅ SUCCESS: Write/Read test passed (Value: {val})")
    except Exception as e:
        print(f"    ❌ FAILED: Redis REST Connection Error: {e}")

    print("\n--- 🏁 Check Complete ---")

if __name__ == "__main__":
    asyncio.run(check_connections())
