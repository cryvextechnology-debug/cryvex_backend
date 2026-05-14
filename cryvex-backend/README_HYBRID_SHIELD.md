# Cryvex Hybrid Shield: DDoS Protection & Token Optimization

This document outlines the architecture of the **Cryvex Hybrid Shield**, a cost-optimized, multi-layer security model designed to protect the Lead Intelligence Engine from IP-rotation and Session-spoofing attacks without exhausting Upstash Redis tokens.

## Architecture Strategy

The shield is composed of two primary layers:

### 1. The Fast-Path (Local RAM)
**Component**: `IPSentryTracker` & `IPSentryMiddleware` (`app/middleware.py`)
- **Cost**: $0 (Zero Redis tokens consumed)
- **Logic**: A local Python `defaultdict` maintains a sliding window of request counts per IP.
- **Action**: If an IP exceeds 5 requests within a 1-second window, the IP is instantly marked as "Suspicious" and blocked for 60 seconds.
- **Protection**: 
  - Protects HTTP endpoints via FastAPI middleware.
  - Protects WebSocket connections via inline checks within `sio.on("connect")` and `sio.on("heartbeat")`.
- **Database Safety**: Traffic blocked by the IP Sentry is dropped in RAM, guaranteeing it never hits MongoDB, preventing database bloat during an attack.

### 2. The Deep-Path (Atomic Redis Lua Script)
**Component**: `process_pulse_atomic` (`app/db.py`)
- **Cost**: 1 Token per Heartbeat
- **Logic**: The legacy system performed multiple `HSET` calls and separate Token Bucket checks, costing 3-5 tokens per heartbeat. The new Hybrid Shield delegates all session state updates and token validation to a single, highly efficient Lua script.
- **Action**: In one atomic execution, the script:
  1. Validates remaining tokens in the `visitor:state:{visitor_id}` hash.
  2. Refills tokens based on time elapsed since `last_refill`.
  3. If tokens > 0, decrements the token count.
  4. Applies updates to the visitor's `score`, `total_time`, and structural maps (`freq_map`, `scroll_memory`, etc.).
  5. Extends the hash TTL to exactly 1 hour (3600s).
- **Result**: A strict Token Bucket rate limiter that simultaneously acts as a state synchronizer, mathematically minimizing billing.

### Security Hardening
- **Visitor ID Verification**: To prevent spoofing, the application enforces the `cryvex_enc_{uuid}` prefix for all visitor IDs. Any connection or pulse utilizing a malformed visitor ID is immediately disconnected.
- **Global Guard**: A rolling bucket (`global_pulse_bucket:{current_sec}`) enforces an absolute ceiling of 10,000 pulses per second globally across all visitors. The keys possess an aggressive 2-second TTL to ensure they do not accumulate in Redis.

## Conclusion
By dropping anomalous high-frequency traffic directly in local memory and condensing legitimate state tracking into atomic Lua commands, the Cryvex Hybrid Shield survives volumetric DDoS assaults while maintaining a strictly predictable, low-cost baseline for Upstash Redis operations.
