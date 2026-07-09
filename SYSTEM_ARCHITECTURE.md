# AGROSIGHT - Complete System Architecture

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Component Breakdown](#component-breakdown)
4. [Complete Request Flow](#complete-request-flow)
5. [Technology Stack](#technology-stack)
6. [Data Models](#data-models)
7. [Integration Points](#integration-points)
8. [Deployment Overview](#deployment-overview)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AgroSight System Architecture                        │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FRONTEND LAYER                              │   │
│  │  (Browser: HTML5 + CSS3 + JavaScript + Lucide Icons)           │   │
│  │  - Real-time SSE streaming                                     │   │
│  │  - Geolocation detection                                       │   │
│  │  - Session management (localStorage)                           │   │
│  └────────────────────┬────────────────────────────────────────────┘   │
│                       │ HTTP/HTTPS                                      │
│                       │ JSON requests                                   │
│                       ↓                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │               API GATEWAY / FASTAPI SERVER                      │   │
│  │  - Health checks (/health)                                     │   │
│  │  - Search endpoint (/search)                                   │   │
│  │  - Chat with streaming (/chat)                                 │   │
│  │  - Session management (/session)                               │   │
│  └────────────────────┬────────────────────────────────────────────┘   │
│                       │                                                  │
│     ┌─────────────────┼──────────────────┐                             │
│     ↓                 ↓                  ↓                             │
│  ┌──────────┐    ┌──────────────┐   ┌─────────────┐                  │
│  │RETRIEVAL │    │ LANGGRAPH    │   │  SESSION    │                  │
│  │PIPELINE  │    │  REACT       │   │   STORE     │                  │
│  │          │    │  AGENT       │   │  (Redis)    │                  │
│  │• Embed   │    │              │   │             │                  │
│  │• Search  │    │• Reasoning   │   │• History    │                  │
│  │• Rerank  │    │• Tool calling│   │• Context    │                  │
│  │          │    │• Streaming   │   │             │                  │
│  └────┬─────┘    └──────┬───────┘   └─────────────┘                  │
│       │                 │                                              │
│       ↓                 ↓                                              │
│  ┌────────────────┐ ┌──────────────┐                                 │
│  │ VECTOR DB      │ │  EXTERNAL    │                                 │
│  │ (Qdrant)       │ │  APIs        │                                 │
│  │                │ │              │                                 │
│  │• Knowledge     │ │• OpenWeather │                                 │
│  │• Embeddings    │ │• Agmarknet   │                                 │
│  │• Hybrid search │ │• data.gov.in │                                 │
│  └────────────────┘ │• Mistral LLM │                                 │
│                     │• ip-api.com  │                                 │
│                     │• geojs.io    │                                 │
│                     │• nominatim   │                                 │
│                     └──────────────┘                                 │
│                                                                       │
│  DATA STORAGE:                                                       │
│  ├─ Knowledge Base: /data/raw/ (JSON/CSV files)                     │
│  ├─ Vector DB: Qdrant (1024-dim bge-m3 embeddings)                  │
│  ├─ Sessions: Redis (conversation history)                          │
│  └─ Logs: /logs/ (application logs)                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### Layer 1: Presentation Layer (Frontend)

**Location:** `/app/static/`

```
INDEX.HTML (UI Template)
├─ HTML structure
├─ Sidebar (brand, chat history)
├─ Main content (header, chat messages, input)
└─ Script references

STYLE.CSS (Styling)
├─ Responsive design
├─ Color scheme (dark/light mode)
├─ Animations (smooth transitions)
└─ Mobile optimization

APP.JS (Frontend Logic)
├─ DOM elements selection
├─ Session management
├─ SSE streaming handler
├─ Geolocation detection
├─ Message formatting
└─ Real-time UI updates
```

**Responsibilities:**
- Render chat UI
- Handle user input
- Stream responses in real-time
- Display weather/location info
- Persist session locally
- Format markdown responses

---

### Layer 2: API Gateway (FastAPI)

**Location:** `/app/main.py`

```python
FastAPI Application
├─ Middleware (CORS, security)
├─ Lifespan management (startup/shutdown)
├─ Static files serving
└─ Endpoints:
   ├─ GET /              → Serve index.html
   ├─ GET /health        → Liveness check
   ├─ POST /search       → Raw retrieval (no LLM)
   ├─ POST /chat         → Streaming chat (RAG + Agent)
   └─ DELETE /session/{id} → Clear history
```

**Key Features:**
- Async-first design (concurrent requests)
- Streaming support (Server-Sent Events)
- Resource preloading (embedder, reranker, Qdrant)
- CORS for cross-origin requests
- JSON request/response handling

---

### Layer 3: Service Layer (Business Logic)

**Location:** `/app/services/`

```
agent.py (Orchestration)
├─ retrieve_context()      → RAG retrieval
├─ run_agent()             → Non-streaming execution
├─ stream_agent()          → Streaming execution
└─ LangGraph ReAct loop    → Tool calling orchestration

agro_tools.py (External Integrations)
├─ get_weather_advisory()  → OpenWeatherMap API
├─ get_mandi_price()       → data.gov.in API
└─ fertiliser_calculator() → Nutrient calculations

embedder.py (Embeddings)
├─ encode_query()          → Query to vector
├─ encode_sparse()         → Query to sparse weights
└─ preload_models()        → Load bge-m3 model

vector_store.py (Qdrant)
├─ hybrid_search()         → Dense + sparse search
└─ get_client()            → Qdrant connection

reranker.py (Ranking)
├─ rerank()                → Cross-encoder reranking
└─ preload_models()        → Load reranker model

session_store.py (Redis)
├─ get_history()           → Load conversation
├─ append_turn()           → Save message
└─ clear_session()         → Delete session

prompts.py (Prompt Engineering)
├─ RAG_SYSTEM_PROMPT       → System instructions
├─ RAG_USER_TEMPLATE       → User prompt template
├─ detect_language()       → Multi-language support
└─ format_context()        → Context formatting

chunker.py (Document Processing)
├─ chunk_text()            → Split documents
└─ manage_token_windows()  → Chunk sizing

logger.py (Logging)
├─ configure_logger()      → Log setup
└─ Log levels: DEBUG, INFO, WARNING, ERROR
```

---

### Layer 4: Data Layer

```
VECTOR DATABASE (Qdrant)
├─ Collection: agricultural_knowledge_v8
├─ Vectors: 1024-dim (bge-m3)
├─ Documents:
│  ├─ Soil classification
│  ├─ Crop cultivation guides
│  ├─ Pest disease knowledge
│  ├─ Fertilizer recommendations
│  ├─ Government schemes
│  ├─ Weather advisories
│  └─ Market prices
└─ Query methods: Dense + Sparse (Hybrid)

REDIS (Session Store)
├─ Key format: session:{session_id}
├─ Structure: List of turns
├─ TTL: 86400 seconds (24 hours)
├─ Per-turn data:
│  ├─ Role (user/assistant)
│  ├─ Content (message text)
│  └─ Timestamp
└─ Use cases:
   ├─ Multi-turn context
   ├─ Conversation history
   └─ User state tracking

LOCAL FILE STORAGE (/data/raw/)
├─ fertilizer/
│  └─ fertilizer_faqs.json
├─ government/
│  └─ scheme_faqs.json
├─ pest_disease/
│  └─ disease_knowledge.json
├─ soil/
│  └─ indian_soil_classification.json
└─ weather/
   └─ openweather/
      └─ agro_advisories.json
```

---

## Component Breakdown

### 1. Retrieval Pipeline (`retrieve_context()`)

```
Query: "What's wheat price in Rajkot?"

STEP 1: ENCODING
├─ Query → bge-m3 embedder
├─ Output: 1024-dim dense vector
└─ Also: Sparse weights (keywords)

STEP 2: HYBRID SEARCH (Qdrant)
├─ Dense search:
│  └─ Cosine similarity with stored embeddings
├─ Sparse search:
│  └─ BM25 keyword matching
└─ Combine results (weighted merge)

STEP 3: CANDIDATE RETRIEVAL
├─ Input: Top 8 from hybrid search
├─ Chunk metadata:
│  ├─ Text content
│  ├─ Source document
│  ├─ Chunk ID
│  └─ Similarity scores
└─ Output: 8 candidate documents

STEP 4: RERANKING (Cross-Encoder)
├─ Input: 8 candidates + original query
├─ Cross-encoder processes each:
│  └─ Relevance score (0-100)
├─ Sort by relevance
└─ Output: Top 5 reranked documents

STEP 5: FORMATTING
├─ Combine 5 chunks
├─ Add source citations
└─ Format as context string for LLM
```

**Code Flow:**
```python
def retrieve_context(query: str, filters: dict | None = None):
    # 1. Encode
    query_vec = encode_query(query)
    sparse_weights = encode_sparse([query])[0]
    
    # 2. Search
    candidates = hybrid_search(
        query_vector=query_vec,
        sparse_weights=sparse_weights,
        top_k=8
    )
    
    # 3. Rerank
    reranked = rerank(query, candidates, top_k=5)
    
    # 4. Return
    return reranked
```

---

### 2. ReAct Agent Loop (`agent.ainvoke()`)

```
INPUT: messages = [SystemMessage, HumanMessage]

TURN 1: INITIAL REASONING
├─ LLM receives:
│  ├─ System prompt (guardrails)
│  ├─ Context (5 documents)
│  ├─ History (past turns)
│  └─ User question
├─ LLM thinks: "What do I need to do?"
└─ LLM outputs:
   ├─ Reasoning text
   └─ Tool call decision

TURN 1 OUTCOME OPTIONS:
A) Tool call needed:
   ├─ Tool name: "mandi_price_tool"
   ├─ Args: {"commodity": "wheat", "market": "Rajkot"}
   └─ LangGraph executes tool
B) Direct answer:
   ├─ No tool needed
   └─ Skip to final synthesis

TURN 2 (if tool called): TOOL EXECUTION
├─ LangGraph intercepts tool call
├─ Executes: await mandi_price_tool("wheat", "Rajkot")
├─ Result: {"price": 2850, "quality": "Grade A"}
└─ Adds ToolMessage to messages

TURN 2 (if tool called): RE-REASONING
├─ LLM receives:
│  ├─ Previous messages
│  ├─ ToolMessage(result)
│  └─ Original question
├─ LLM thinks: "I have the tool result. Any more tools needed?"
└─ Decision: Tool call or final answer?

TURN 3: FINAL SYNTHESIS
├─ LLM sees all data
├─ Generates complete answer
├─ No more tool calls
└─ LangGraph returns result

OUTPUT: result["messages"] contains full conversation
```

**Configuration:**
```python
config = {"recursion_limit": 20}
# Max tool calls allowed (prevents infinite loops)
```

---

### 3. Streaming Pipeline (`stream_agent()`)

```
REQUEST: POST /chat with stream=true

STEP 1: RETRIEVAL (thread pool)
├─ retrieve_context() runs in executor
├─ Reason: Embedding is CPU-bound
└─ Event loop stays responsive

STEP 2: AGENT SETUP
├─ Create LLM
├─ Create ReAct agent
├─ Build messages
└─ Ready for streaming

STEP 3: STREAMING LOOP
├─ agent.astream(stream_mode="messages")
├─ Yields each AIMessageChunk
└─ Continue until done

STEP 4: TOKEN BUFFERING
├─ Collect tokens in buffer
├─ Buffering rules:
│  ├─ Yield on newline (\n)
│  ├─ Yield when buffer > 40 chars
│  └─ Otherwise accumulate
└─ Benefits:
   ├─ Smooth UI updates
   ├─ Fewer network packets
   └─ Better performance

STEP 5: SSE FORMATTING
├─ Each token wrapped as:
│  └─ "event: token\ndata: {token}\n\n"
└─ Browser receives in real-time

STEP 6: PERSISTENCE
├─ After streaming completes
├─ Save to Redis:
│  ├─ append_turn(session_id, "user", question)
│  └─ append_turn(session_id, "assistant", answer)
└─ Future turns use this context

RESPONSE: Stream of tokens → UI updates live
```

---

### 4. Tool Integration

#### Weather Tool
```python
get_weather_advisory(location: str)
├─ API: OpenWeatherMap
├─ Input: City name or coordinates
├─ Returns:
│  ├─ Current conditions
│  ├─ Temperature
│  ├─ Humidity
│  ├─ Wind speed
│  ├─ Rainfall
│  └─ Agricultural advisory
└─ Retry: Up to 3 attempts with exponential backoff
```

#### Mandi Price Tool
```python
get_mandi_price(commodity: str, market: str, state: str)
├─ API: data.gov.in + Agmarknet
├─ Input: 
│  ├─ Commodity (wheat, cotton, rice, etc)
│  ├─ Market (Rajkot, Mumbai, etc)
│  └─ State (Gujarat, Maharashtra, etc)
├─ Returns:
│  ├─ Current price
│  ├─ Previous price
│  ├─ Quality grade
│  ├─ Trading volume
│  └─ Market trend
└─ Real-time data (updated daily)
```

#### Fertilizer Calculator Tool
```python
fertiliser_calculator(crop: str, area_acres: float, 
                      fertiliser: str, nutrient: str)
├─ Database: Local knowledge base
├─ Input:
│  ├─ Crop type
│  ├─ Area in acres
│  ├─ Fertilizer type (urea, DAP, MOP, etc)
│  └─ Nutrient (N, P, K)
├─ Returns:
│  ├─ Required dose (kg)
│  ├─ Bag count
│  ├─ Application timing
│  └─ Cost estimate
└─ Based on: Soil type, crop stage, weather
```

---

## Complete Request Flow

### Scenario: User asks "Wheat price in Rajkot?"

```
┌─ BROWSER (Frontend) ──────────────────────────────────────┐
│                                                             │
│ User types: "Wheat price in Rajkot?"                      │
│       ↓                                                    │
│ Clicks send button                                        │
│       ↓                                                    │
│ JavaScript: sendMessage("Wheat price in Rajkot?")         │
│       ↓                                                    │
│ appendMessage("user", question)  [Show user message]      │
│       ↓                                                    │
│ POST /chat:                                               │
│ {                                                         │
│   "question": "Wheat price in Rajkot?",                 │
│   "session_id": "session_abc123",                        │
│   "stream": true                                         │
│ }                                                        │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ FASTAPI SERVER (app/main.py) ────────────────────────────┐
│                                                             │
│ @app.post("/chat")                                        │
│ async def chat_endpoint(request: ChatRequest):            │
│       ↓                                                    │
│ EventSourceResponse(event_generator())                    │
│       ↓                                                    │
│ Call: stream_agent(question, session_id)                  │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ RETRIEVAL PIPELINE (agent.py) ──────────────────────────┐
│                                                             │
│ retrieve_context("Wheat price in Rajkot?")                │
│       ↓                                                    │
│ query_vec = encode_query(question)                        │
│ • Input: "Wheat price in Rajkot?"                        │
│ • Model: bge-m3 (1024-dim)                               │
│ • Output: Dense vector                                    │
│       ↓                                                    │
│ hybrid_search(query_vec, sparse_weights)                  │
│ • Qdrant DB search                                       │
│ • Dense + keyword search                                  │
│ • Top 8 candidates returned                              │
│       ↓                                                    │
│ rerank(question, candidates)                              │
│ • Cross-encoder scoring                                  │
│ • Sort by relevance                                      │
│ • Top 5 returned                                         │
│       ↓                                                    │
│ chunks = [                                                │
│   {"text": "Rajkot APMC: ₹2,850 Grade A", ...},        │
│   {"text": "MSP: ₹2,350", ...},                         │
│   ...                                                     │
│ ]                                                         │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ SESSION & HISTORY (session_store.py) ────────────────────┐
│                                                             │
│ get_history("session_abc123")  [From Redis]               │
│       ↓                                                    │
│ history = [                                               │
│   {"role": "user", "content": "What's cotton price?"},   │
│   {"role": "assistant", "content": "Cotton ₹5,200..."}   │
│ ]                                                         │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ PROMPT BUILDING (prompts.py) ────────────────────────────┐
│                                                             │
│ RAG_USER_TEMPLATE.format(                                │
│   context=chunks_text,                                    │
│   history=formatted_history,                             │
│   question="Wheat price in Rajkot?",                    │
│   language="English"                                     │
│ )                                                         │
│       ↓                                                    │
│ user_msg = """                                           │
│ RETRIEVED CONTEXT:                                       │
│ Rajkot APMC: ₹2,850 Grade A...                          │
│ MSP: ₹2,350...                                          │
│                                                          │
│ CONVERSATION HISTORY:                                    │
│ Q: What's cotton price?                                 │
│ A: Cotton ₹5,200...                                    │
│                                                          │
│ FARMER'S QUESTION:                                      │
│ Wheat price in Rajkot?                                 │
│                                                          │
│ TARGET RESPONSE LANGUAGE:                               │
│ English                                                 │
│ """                                                      │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ LANGGRAPH REACT AGENT ──────────────────────────────────┐
│                                                             │
│ messages = [                                              │
│   SystemMessage(RAG_SYSTEM_PROMPT),                      │
│   HumanMessage(user_msg)                                 │
│ ]                                                         │
│       ↓                                                    │
│ agent = create_react_agent(llm, TOOLS)                   │
│       ↓                                                    │
│ async for msg, metadata in agent.astream():              │
│       ↓                                                    │
│ TURN 1: LLM REASONING                                    │
│ ├─ Sees: context + history + question                    │
│ ├─ Thinks: "I need current mandi prices"                │
│ └─ Decides: Call mandi_price_tool                        │
│       ↓                                                    │
│ mandi_price_tool("wheat", "Rajkot", "Gujarat")           │
│ • Calls data.gov.in API                                 │
│ • Gets real-time prices                                 │
│ • Returns: {"price": 2850, "quality": "Grade A"}        │
│       ↓                                                    │
│ TURN 2: SYNTHESIS                                        │
│ ├─ LLM sees tool result + context                        │
│ ├─ Generates answer:                                     │
│ │  "Current wheat price in Rajkot APMC: ₹2,850          │
│ │   per quintal (Grade A).                              │
│ │   This is ₹500 above MSP of ₹2,350.                   │
│ │   Good time to sell."                                 │
│ └─ Yields tokens one by one                             │
│       ↓                                                    │
│ STREAMING: Token by token                               │
│ "Current" → " wheat" → " price" → ...                  │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ EVENT SOURCE RESPONSE (SSE) ─────────────────────────────┐
│                                                             │
│ for each token in stream:                                │
│   yield f"event: token\ndata: {token}\n\n"              │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ BROWSER (Real-time Display) ────────────────────────────┐
│                                                             │
│ EventSource listener:                                    │
│ addEventListener('token', (event) => {                  │
│   fullAnswer += event.data                              │
│   aiMessageDiv.innerHTML = formatMarkdown(fullAnswer)   │
│ })                                                        │
│       ↓                                                    │
│ User sees text appearing in real-time:                  │
│ "Current" ... "Current wheat" ... "Current wheat price" │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ PERSISTENCE (Redis) ─────────────────────────────────────┐
│                                                             │
│ append_turn(session_id, "user", question)                │
│ append_turn(session_id, "assistant", full_answer)        │
│       ↓                                                    │
│ Redis stores:                                            │
│ session:session_abc123 = [                               │
│   {"role": "user", "content": "What's cotton price?"},  │
│   {"role": "assistant", "content": "Cotton ₹5,200..."},│
│   {"role": "user", "content": "Wheat price in Rajkot?"}, │
│   {"role": "assistant", "content": "Current wheat..."}  │
│ ]                                                         │
│ TTL: 86400 seconds (24 hours)                           │
│       ↓                                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─ NEXT TURN (Context Carried Forward) ──────────────────┐
│                                                           │
│ User: "Should I sell now?"                              │
│       ↓                                                  │
│ get_history() retrieves ALL previous turns              │
│       ↓                                                  │
│ LLM now knows:                                          │
│ • Previous: "Wheat price in Rajkot?"                    │
│ • Previous answer: "₹2,850 per quintal"                 │
│ • Current: "Should I sell now?"                         │
│       ↓                                                  │
│ LLM can reason:                                         │
│ "At ₹2,850 which is above MSP of ₹2,350,               │
│  yes, the user should sell now."                        │
│       ↓                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
```
HTML5              → Semantic structure
CSS3               → Responsive design
JavaScript (ES6+)  → Dynamic behavior
Lucide Icons       → Icon library
Font: Outfit       → Google Fonts
localStorage       → Client-side session persistence
Fetch API          → HTTP requests
EventSource API    → SSE streaming
Geolocation API    → Browser geolocation
```

### Backend
```
FastAPI            → Web framework (Python)
Pydantic           → Request validation
starlette.SSE      → Server-Sent Events
asyncio            → Async execution
uvicorn            → ASGI server
CORS middleware    → Cross-origin requests
```

### AI/ML
```
LangChain          → LLM orchestration
LangGraph          → Agent framework
langchain-mistralai → Mistral integration
Mistral API        → Large language model
```

### Data & Search
```
Qdrant             → Vector database
FAISS              → Vector indexing
bge-m3             → Dense embeddings (1024-dim)
Cross-encoder      → Reranking
Hybrid search      → Dense + sparse
```

### External APIs
```
OpenWeatherMap     → Real-time weather
data.gov.in        → Mandi prices
Agmarknet          → Market data
ip-api.com         → IP geolocation
ipapi.co           → IP geolocation (backup)
geojs.io           → IP geolocation (backup)
Nominatim          → Reverse geocoding
```

### Database & Caching
```
Redis              → Session store
JSON files         → Knowledge base
CSV files          → Mandi prices
```

### DevOps & Infrastructure
```
Docker             → Containerization
docker-compose.yml → Multi-container setup
Makefile           → Build automation
Python 3.13        → Runtime
pip/venv           → Package management
```

### Monitoring & Logging
```
Python logging     → Application logs
Logger utilities   → Custom logging
Sentry (optional)  → Error tracking
```

---

## Data Models

### Request Model
```python
class ChatRequest(BaseModel):
    question: str           # User's question
    session_id: str         # Conversation ID
    stream: bool = True     # Enable streaming
    filters: dict = None    # Optional search filters
```

### Session Model
```python
# Redis Key: session:{session_id}
# Redis Value: JSON list
[
  {
    "role": "user" | "assistant",
    "content": str,
    "timestamp": int (unix)
  },
  ...
]
```

### Document Model (Qdrant)
```python
{
  "id": "doc_unique_id",
  "text": str,
  "source": str,
  "category": str,
  "metadata": {
    "chunk_index": int,
    "total_chunks": int,
    "language": str
  },
  "embedding": [1024-dim vector],
  "sparse_weights": {
    "token_id": weight,
    ...
  }
}
```

### Tool Call Model
```python
{
  "name": "weather_tool" | "mandi_price_tool" | "fertiliser_tool",
  "args": {
    "param1": value1,
    "param2": value2,
    ...
  },
  "result": str,
  "timestamp": int
}
```

---

## Integration Points

### External APIs

#### 1. OpenWeatherMap
```
Endpoint: https://api.openweathermap.org/data/2.5/weather
Query params:
├─ lat, lon (or q=city)
├─ units=metric
└─ appid=API_KEY

Response:
├─ Temperature
├─ Humidity
├─ Wind
├─ Weather conditions
└─ Sunrise/sunset
```

#### 2. data.gov.in
```
Endpoint: https://api.data.gov.in/resource/...
Query params:
├─ api-key
├─ limit
└─ filters (resource_id, state, market)

Response:
├─ Commodity prices
├─ Market names
├─ Dates
└─ Trading volume
```

#### 3. Mistral LLM
```
Endpoint: https://api.mistral.ai/v1/chat/completions
Authentication: Bearer token (API key)
Features:
├─ Function calling (tool use)
├─ Streaming support
├─ Temperature control
└─ Max tokens
```

#### 4. IP Geolocation
```
Primary: ip-api.com
Secondary: ipapi.co
Tertiary: geojs.io

Response: City, lat, lon
Purpose: Fallback location detection
```

---

## Deployment Overview

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.13

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  agrosight:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - QDRANT_URL=${QDRANT_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - qdrant
    
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
```

### Running

```bash
# Development
uvicorn app.main:app --reload

# Production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app

# Docker
docker-compose up --build
```

---

## Real-World Data Flow: Multi-turn Conversation

### Turn 1: User asks about cotton
```
Q: "When should I plant cotton in Gujarat?"
     ↓
Context: 5 cotton plantation guides retrieved
     ↓
Agent decides: Need current weather data
     ↓
Calls: weather_tool("Gujarat")
     ↓
Gets: Current conditions + forecast
     ↓
A: "Based on current weather and soil conditions,
    plant cotton after April 15 when frost risk is gone.
    Current temperature in Gujarat is suitable."
     ↓
Saved to Redis with full context
```

### Turn 2: Follow-up question
```
Q: "How much fertilizer do I need for 2 acres?"
     ↓
History loaded: "User is planning to plant cotton"
     ↓
Context: Cotton + 2 acres + Gujarat combined
     ↓
Agent decides: Call fertiliser_tool
     ↓
Calls: fertiliser_tool("cotton", 2, "urea", "N")
     ↓
Gets: Specific dose for 2 acres
     ↓
A: "For 2 acres of cotton, apply 240 kg of urea
    (nitrogen). This equals 5 bags of 50kg or 10 bags of 25kg.
    Apply at 4 leaf stage and 60 days after planting.
    Cost estimate: ₹2,400."
     ↓
Saved to Redis, conversation grows
```

### Turn 3: Connected reasoning
```
Q: "What's the total cost of cotton farming?"
     ↓
History loaded:
├─ Plant cotton after April 15
├─ Need 240 kg urea (₹2,400)
└─ (Any previous cost data)
     ↓
Context: Cotton cultivation costs + fertilizer
     ↓
Agent synthesizes ALL information:
├─ Seeds cost
├─ Fertilizer cost (from turn 2)
├─ Labor cost
├─ Irrigation (from weather data in turn 1)
└─ Market rates
     ↓
A: "Total estimated cost for 2 acres:
    - Seeds: ₹1,200
    - Fertilizer: ₹2,400
    - Labor: ₹4,000
    - Irrigation: ₹2,000
    - Pesticides: ₹1,500
    - Total: ₹11,100
    Current market price: ₹5,800/quintal
    Expected yield: 15 quintals/acre
    Expected revenue: ₹174,000
    Profit margin: Good opportunity!"
     ↓
Saved to Redis for future reference
```

---

## Performance Considerations

### Caching Strategy
```
Layer 1: Browser localStorage
├─ Session ID
├─ Chat history (client-side)
└─ User preferences

Layer 2: Redis (Server)
├─ Conversation history (24h TTL)
├─ Session state
└─ Frequently accessed data

Layer 3: Qdrant Vector DB
├─ Cached embeddings
├─ Pre-computed vectors
└─ Persisted knowledge
```

### Optimization
```
Parallel Processing:
├─ Retrieval in thread pool (CPU-bound)
├─ LLM inference async (I/O-bound)
└─ Tool calls concurrent

Buffering:
├─ Token buffering for smoother streaming
├─ Aggregate small responses
└─ Reduce network overhead

Lazy Loading:
├─ Models loaded on startup
├─ Qdrant connection pooled
└─ LLM reused per request
```

---

## Error Handling

### Graceful Fallbacks
```
Weather API fails
├─ Try next IP geolocation service
├─ Fall back to cached data
└─ Return available information

Mandi Price API fails
├─ Use cached prices
├─ Use historical trends
└─ Inform user of stale data

Tool execution fails
├─ LLM uses context knowledge
├─ Agent continues without tool
└─ Provides best-effort answer
```

### Retry Logic
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8)
)
async def call_external_api():
    # Retries with exponential backoff
    pass
```

---

## Summary

AgroSight is a **multi-layered RAG + ReAct Agent system** where:

1. **Frontend** streams questions and displays responses in real-time
2. **API Gateway** handles requests asynchronously
3. **Retrieval** combines dense + sparse search with reranking
4. **Agent** decides which tools to use based on semantic understanding
5. **Tools** fetch real-time data from external APIs
6. **LLM** synthesizes information and streams response tokens
7. **Session Store** maintains multi-turn context
8. **Database** persists vectors and conversation history

The entire flow is **async-first**, **streaming-optimized**, and **production-ready**.

---

**END OF DOCUMENT**
