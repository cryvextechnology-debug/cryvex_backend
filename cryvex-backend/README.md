# Cryvex Lead Intelligence Engine (CLIE)

A high-performance, real-time backend predicting AI for B2B Textile/Manufacturing sites. It calculates a "Lead Quality Score" using a Weighted Behavioral Decay Model in real-time ($<50ms$ latency limits) using FastAPI, Socket.IO, Redis, and MongoDB.

## Getting Started

1. Set up a local Redis and MongoDB instance. You can use Docker:
   ```bash
   docker run -d -p 6379:6379 redis
   docker run -d -p 27017:27017 mongo
   ```

2. Install Dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Export environment variables (or rely on `.env` fallback):
   ```bash
   export MONGODB_URI=mongodb://localhost:27017
   export REDIS_URI=redis://localhost:6379/0
   ```

4. Run the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Deploying to Production

Since the CLIE engine relies on high-speed real-time loops, deploying to production requires three pieces of infrastructure:

### 1. Provision Databases (Free & Fast)
You don't need to install Docker for production; you will use managed cloud databases.
* **MongoDB**: Create a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas). Grab your connection string.
* **Redis**: Create a free Redis database on [Upstash](https://upstash.com/) or Railway. Grab the connection string.

### 2. Deploy the FastAPI Server
The easiest way to deploy this engine is using a Platform as a Service like **Render.com** or **Railway.app**.
1. Push this folder to a GitHub Repository.
2. Log into Render/Railway and click "Deploy from GitHub".
3. Add your Environment Variables:
   * Key: `MONGODB_URI`, Value: `mongodb+srv://...`
   * Key: `REDIS_URI`, Value: `rediss://...`
4. Set the Start Command: Let the platform know how to boot the server.
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Connect Your Frontend
Once deployed, Render or Railway will give you a public URL (e.g., `https://cryvex-ai-engine.onrender.com`). Give this URL to your frontend partner. They will simply change the connection string in their code:
`const socket = io("https://cryvex-ai-engine.onrender.com");`

---

## WebSocket JSON Contract

This section explains the exact payloads expected for the Socket.IO integration between the frontend and the Cryvex Intelligent Backend.

**Connection Endpoint:**
Connect your Socket.IO client directly to the host.
`ws://localhost:8000`

### 1. `heartbeat` (Client -> Server)

Emit this event from the frontend every 1 or 2 seconds to supply the latest behavioral data for the prediction engine.

**Event Name:** `heartbeat`

**Payload:**
```json
{
  "current_page": "Textile/Mfg/E-commerce Fields",
  "current_section": "AI Strategy/ROI Intro",
  "dwell_time": 25,
  "scroll_depth": 60,
  "actions": ["hover"]
}
```

*Notes on Payload:*
* **`current_page`**: The string identifier of the overall page (e.g., `Home`, `About`, `Textile/Mfg/E-commerce Fields`).
* **`current_section`**: The specific section the user is dwelling on (e.g., `Welcome`, `Case Study`, `AI Strategy/ROI Intro`, `CTA Click`).
* **`dwell_time`**: Total seconds spent on the *current_section*. If this exceeds 20s and `scroll_depth > 50`, the engine multiplies the section score by 1.5x (Deep Reading detection).
* **`scroll_depth`**: Percentage integer (0-100) indicating how far down the section/page the user has explored.
* **`actions`**: An array of detected string events. Include `"click"` when a CTA is pressed to forcefully trigger permanent MongoDB save operations.

### 2. `prediction_update` (Server -> Client)

Listen for this event to receive real-time behavioral nudges and updated intent scores. It is pushed immediately in response to a `heartbeat`.

**Event Name:** `prediction_update`

**Payload:**
```json
{
  "score": 87,
  "primary_interest": "Textile/Mfg/E-commerce Fields",
  "suggested_message": "Hot Lead / Gmail capture request"
}
```

*Notes on Response:*
* **`score`**: The calculated intent score ($0-100$).
* **`primary_interest`**: Evaluated over the course of the session, identifying the topic/page where the user spent the most cumulative time.
* **`suggested_message`**: You can render dynamic popups on the frontend directly mapping to these distinct threshold ranges:
  * `0–30`: "Welcome / General"
  * `31–60`: "Industry-specific Case Study nudge"
  * `61–85`: "ROI/Strategy nudge"
  * `86–100`: "Hot Lead / Gmail capture request"
