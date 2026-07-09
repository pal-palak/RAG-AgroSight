# AgroSight: Complete Chat & Session Architecture

## Overview
This document explains how **session management**, **chat history**, **memory management**, and **chat functionality** work together in AgroSight.

---

## 1. SESSION MANAGEMENT (Redis/In-Memory)

### Location: `app/services/session_store.py`

```
User Session
    ↓
Redis (Primary) or In-Memory Dict (Fallback)
    ↓
Store/Retrieve Chat History
```

### Flow:

```python
# Session starts
session_id = "user_123_abc"  # Generated from frontend

# Append user message
append_turn(session_id, "user", "What is wheat rust?")

# Store in Redis with TTL (Time To Live)
{
  "session:user_123_abc": [
    {"role": "user", "content": "What is wheat rust?"},
    {"role": "assistant", "content": "Yellow Rust is caused by..."}
  ]
}

# Redis automatically deletes after session_ttl_seconds (default: 7 days)
```

### Key Functions:

```python
get_history(session_id)
  └─ Returns: list[{"role": "user|assistant", "content": "..."}]
  └─ Max 5 turns enforced (10 messages total)
  
append_turn(session_id, role, content)
  └─ Adds new message
  └─ Enforces MAX_HISTORY_TURNS (keeps only last 5 exchanges)
  
clear_session(session_id)
  └─ Deletes all history for session (on logout/delete)
```

---

## 2. MEMORY MANAGEMENT

### Storage Strategy:

```
Redis (Distributed, Persistent)
├── session:user_123 = JSON serialized history (TTL: 7 days)
└── Max 256MB (Docker redis limit)

In-Memory Fallback
├── _memory_store: dict[session_id] → history list
├── Only used if Redis unavailable
└── Lost on app restart
```

### Memory Limits:

```yaml
# docker-compose.yml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
  # When > 256MB: removes LEAST RECENTLY USED keys
```

### Python Memory:

```python
# Models loaded ONCE at startup (lifespan)
embedder.preload_models()      # ~2GB (BGE-M3)
reranker.preload_models()      # ~500MB (cross-encoder)

# Per-request cleanup
async def run_agent(question):
    chunks = retrieve_context(question)  # ~10-50MB
    result = run_agent(...)
    # chunks garbage collected when function ends
    # Reference count → 0 → Memory freed
```

---

## 3. CHAT HISTORY & CONVERSATION FLOW

### Frontend → Backend:

```
User Types Message
    ↓
JavaScript (index.html)
    ↓
POST /chat with {
    "session_id": "user_123",
    "query": "Tell me about mandi prices",
    "filters": {}
}
    ↓
FastAPI Server (main.py)
```

### Request Handler: `POST /chat`

```python
# app/main.py: ChatRequest
@dataclass
class ChatRequest:
    session_id: str              # Browser session
    query: str                   # User question
    filters: dict | None = None  # Optional crop filters

# Handler
@app.post("/chat")
async def chat_endpoint(req: ChatRequest) -> EventSourceResponse:
    """
    Full flow:
    1. Get conversation history from Redis
    2. Run RAG retrieval
    3. Stream agent response
    4. Append to history
    """
    # Step 1: Get history
    history = get_history(req.session_id)
    # history = [
    #   {"role": "user", "content": "What is..."},
    #   {"role": "assistant", "content": "..."}
    # ]
    
    # Step 2: Run agent (with context + history)
    async for chunk in stream_agent(req.query, req.session_id, req.filters):
        yield chunk  # Stream to frontend
    
    # Step 3: Append to history
    append_turn(req.session_id, "user", req.query)
    append_turn(req.session_id, "assistant", full_response)
```

---

## 4. COMPLETE REQUEST-RESPONSE CYCLE

### Example: User asks about wheat fertilizer

```
STEP 1: USER SUBMITS QUESTION
────────────────────────────
Browser sends:
{
  "session_id": "sess_abc123",
  "query": "Calculate fertilizer for 5 acres of wheat"
}

STEP 2: SERVER RETRIEVES SESSION HISTORY
────────────────────────────────────────
Redis GET session:sess_abc123
→ [
    {"role": "user", "content": "What is yellow rust?"},
    {"role": "assistant", "content": "Yellow rust is..."},
    {"role": "user", "content": "How to treat it?"},
    {"role": "assistant", "content": "Use fungicides..."}
  ]

STEP 3: ENCODE QUERY
──────────────────
embedder.encode_query("Calculate fertilizer for 5 acres of wheat")
→ vector: [0.23, -0.15, 0.88, ...] (1024 dimensions for BGE-M3)

STEP 4: HYBRID SEARCH IN QDRANT
───────────────────────────────
Search for:
- Dense vector similarity
- Sparse term matches
→ Returns top 20 candidates:
  [
    {"text": "Nitrogen dose for wheat: 120kg/ha", "score": 0.94},
    {"text": "Urea application method", "score": 0.87},
    ...
  ]

STEP 5: RERANK WITH CROSS-ENCODER
─────────────────────────────────
Rerank candidates with ms-marco-MiniLM-L-6-v2
→ Keep top 5:
  [
    {"text": "Nitrogen dose for wheat: 120kg/ha", "score": 0.99},
    {"text": "Urea fertilizer guide", "score": 0.97},
    ...
  ]

STEP 6: BUILD PROMPT WITH HISTORY + CONTEXT
──────────────────────────────────────────
System prompt: "You are an expert agricultural advisor..."

Context (from chunks):
"Nitrogen dose for wheat: 120 kg N/ha in 3 splits"

History (last 2 turns):
User: "How to treat yellow rust?"
Assistant: "Use Propiconazole or Tebuconazole..."

New Query: "Calculate fertilizer for 5 acres of wheat"

Full Prompt to LLM:
"""
You are an expert...
[CONTEXT from retrieved chunks]
[HISTORY of previous messages]
User: Calculate fertilizer for 5 acres of wheat
Assistant: (STREAM THIS)
"""

STEP 7: RUN REACT AGENT WITH TOOLS
──────────────────────────────────
Agent has 3 tools:
- weather_tool(location) → get weather advisory
- mandi_price_tool(commodity) → get prices
- fertiliser_tool(crop, acres, nutrient) → calculate dose

Agent decides: "I need fertiliser_tool"
→ Call: fertiliser_tool("wheat", 5, "urea", "N")
→ Returns: "For 5 acres, use 600kg urea (120kg N/ha × 5 acres)"

STEP 8: STREAM RESPONSE TO CLIENT
────────────────────────────────
SSE (Server-Sent Events):
data: {"token": "For"}
data: {"token": " 5"}
data: {"token": " acres"}
data: {"token": " of"}
data: {"token": " wheat"}
data: {"token": ","}
...
data: {"done": true, "chunks": [...]}

STEP 9: APPEND TO SESSION HISTORY
────────────────────────────────
Redis SET session:sess_abc123 = [
  {"role": "user", "content": "What is yellow rust?"},
  {"role": "assistant", "content": "Yellow rust is..."},
  {"role": "user", "content": "How to treat it?"},
  {"role": "assistant", "content": "Use fungicides..."},
  {"role": "user", "content": "Calculate fertilizer for 5 acres of wheat"},
  {"role": "assistant", "content": "For 5 acres, use 600kg urea..."}
]

STEP 10: BROWSER DISPLAYS RESPONSE
─────────────────────────────────
Frontend JavaScript:
- Shows streamed tokens in real-time
- Updates history sidebar
- Saves to localStorage for offline access
```

---

## 5. MEMORY LIFECYCLE

### Per-Request Memory Usage:

```
Request Start
  ├── Load History (~50KB)
  ├── Encode Query (~1MB)
  ├── Vector Search (~10MB)
  ├── Reranking (~50MB)
  ├── LLM Inference (~200MB)
  └── Stream Response (~10MB)
      TOTAL: ~270MB per request

After Response
  ├── History appended to Redis
  ├── Temporary variables freed
  ├── Memory back to baseline
```

### Persistent Memory:

```
At Startup (loaded ONCE):
  ├── BGE-M3 model: 2000 MB
  ├── Cross-encoder: 500 MB
  ├── Qdrant vector DB: 100 MB
  └── Redis connection: 10 MB
      BASELINE: ~2600 MB

Per Active Session (stored in Redis):
  ├── Session history: ~10-50 KB
  └── TTL: 7 days
```

---

## 6. CHAT HISTORY STRUCTURE

### JSON Format in Redis:

```json
{
  "session:user_123_abc": [
    {
      "role": "user",
      "content": "What is wheat rust?"
    },
    {
      "role": "assistant",
      "content": "Yellow Rust caused by Puccinia striiformis is a major wheat disease. It appears as stripe-like yellow pustules on leaves. Recommended treatment: Apply Propiconazole or Tebuconazole at first appearance."
    },
    {
      "role": "user",
      "content": "What's the mandi price of wheat?"
    },
    {
      "role": "assistant",
      "content": "The MSP (Minimum Support Price) for wheat in 2026 is ₹2,500/quintal. Current market prices in Gujarat: Rajkot: ₹2,480/q, Ahmedabad: ₹2,495/q"
    }
  ]
}
```

### Enforcement:

```python
# Max history enforcement in session_store.py
max_turns = settings.max_history_turns * 2  # 5 turns × 2 = 10 messages
if len(history) > max_turns:
    history = history[-max_turns:]  # Keep only last 10 messages

# Why? Prevent:
# 1. Redis memory bloat
# 2. LLM context explosion
# 3. Slow history loading
```

---

## 7. CHAT SYSTEM ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                       BROWSER (Frontend)                     │
│  • index.html + app.js                                       │
│  • Displays chat messages in real-time                       │
│  • localStorage for offline fallback                         │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket / SSE
                         │ POST /chat
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI SERVER                            │
│  main.py: /chat endpoint                                     │
│  ├─ Receives: {session_id, query, filters}                 │
│  └─ Returns: EventSourceResponse (streaming)                │
└────────────┬──────────────────────┬──────────────────────────┘
             │                      │
             ↓                      ↓
    ┌────────────────┐    ┌─────────────────────┐
    │  SESSION_STORE │    │    AGENT PIPELINE   │
    ├────────────────┤    ├─────────────────────┤
    │ Redis (Primary)│    │ 1. Encode query     │
    │ Memory (backup)│    │ 2. Hybrid search    │
    │                │    │ 3. Rerank           │
    │ get_history()  │    │ 4. Build prompt     │
    │ append_turn()  │    │ 5. Run ReAct agent  │
    │ clear_session()│    │ 6. Stream response  │
    └────────────────┘    └─────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ↓            ↓            ↓
            ┌──────────────┐ ┌─────────┐ ┌────────┐
            │   EMBEDDER   │ │RERANKER │ │ TOOLS  │
            ├──────────────┤ ├─────────┤ ├────────┤
            │ BGE-M3 (2GB) │ │ms-marco │ │Weather │
            │              │ │ (500MB) │ │Mandi   │
            │ encode_query │ │ rerank()│ │Fertiliz│
            │ encode_sparse│ │         │ │        │
            └──────────────┘ └─────────┘ └────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ↓
                    ┌──────────────────────┐
                    │   VECTOR DATABASE    │
                    ├──────────────────────┤
                    │    Qdrant Cloud      │
                    │  • 50,000+ chunks    │
                    │  • 1024-dim vectors  │
                    │  • Sparse search     │
                    └──────────────────────┘
```

---

## 8. CONFIGURATION

### Key Settings (config.py):

```python
# Session management
max_history_turns = 5              # Keep last 5 user-assistant pairs (10 messages)
session_ttl_seconds = 604800       # 7 days

# Memory
redis_url = "redis://localhost:6380/0"  # Or Cloud Qdrant Redis

# LLM
mistral_model = "mistral-large-latest"
llm_temperature = 0.7
llm_max_tokens = 1024

# Retrieval
retrieval_top_k = 20               # Retrieve 20 candidates
```

---

## 9. EXAMPLE: Multi-Turn Conversation

### Turn 1:
```
User: "What is the MSP of wheat in Gujarat?"
├─ Query encoded
├─ Search vector DB
├─ Return: "MSP wheat 2026 is ₹2,500/quintal"
└─ Append to history: {user, assistant}
```

### Turn 2:
```
User: "Compare with cotton prices"
├─ History = [Turn 1 messages]
├─ Build prompt with context + Turn 1 history
├─ Query encodes: "Compare with cotton prices"
├─ Search: "cotton MSP price"
├─ Agent retrieves cotton price
└─ Append to history
```

### Turn 3:
```
User: "Which crop is more profitable?"
├─ History = [Turn 1, Turn 2]
├─ Agent uses memory of previous prices
├─ Makes comparison
└─ Updated history has all 3 turns (6 messages total)
```

---

## 10. CLEANUP & MEMORY FREEING

### Automatic:
```python
# Redis TTL (7 days)
redis.setex(f"session:{session_id}", 604800, data)
# After 604800 seconds, Redis auto-deletes

# Python garbage collection
def run_agent(query):
    chunks = retrieve_context()  # Allocated
    ...
    # Function ends
    # chunks reference count → 0
    # Memory freed by Python GC
```

### Manual:
```python
# User logout / session delete
DELETE /session/{session_id}
  └─ clear_session(session_id)
  └─ Redis: DELETE session:user_123
  └─ Memory immediately freed
```

---

## Summary Table

| Component | Storage | Size | TTL | Purpose |
|-----------|---------|------|-----|---------|
| Chat History | Redis | 10-50 KB | 7 days | Store conversation |
| Embeddings (cache) | RAM | 2 GB | ∞ (app lifetime) | Fast encoding |
| Reranker (cache) | RAM | 500 MB | ∞ (app lifetime) | Fast ranking |
| Vector DB | Qdrant Cloud | 5+ GB | ∞ | Search corpus |
| Session Context | RAM | ~270 MB/req | <1s | Current request |

---

## Performance Metrics

```
User Message → Response:
├─ History retrieval: 10-50ms
├─ Query encoding: 100-200ms
├─ Vector search: 100-300ms
├─ Reranking: 200-500ms
├─ LLM inference: 2-5s
└─ Total: 2.5-6 seconds

Memory per request: ~270 MB (freed after response)
Concurrent users: Limited by LLM queue (usually 5-10)
```

---

## References

- Session Store: `app/services/session_store.py`
- Agent Logic: `app/services/agent.py`
- FastAPI Routes: `app/main.py`
- Frontend Chat: `app/static/js/app.js`
- Vector Store: `app/services/vector_store.py`
