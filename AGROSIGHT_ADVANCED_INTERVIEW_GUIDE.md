# 🌾 AgroSight – Advanced Technical Interview Guide & System Architecture Companion

**A Comprehensive File-by-File Review with Technology Explanations, Interview Questions & Concept Guides**

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Technology Stack Explained](#technology-stack-explained)
4. [File-by-File Detailed Analysis](#file-by-file-detailed-analysis)
5. [Core Concepts & How They Work](#core-concepts--how-they-work)
6. [Interview Questions & Answer Guidance](#interview-questions--answer-guidance)

---

## Project Overview

### What is AgroSight?

**AgroSight** is a **Production-Grade Retrieval-Augmented Generation (RAG) System** designed specifically for Indian farmers. It provides expert agricultural advice through a conversational AI interface supporting English, Hindi, and Gujarati.

### Key Features
- 🌱 **Crop Advisory & Disease Diagnosis** – Knowledge from 113 agricultural PDFs (1 GB)
- 💰 **Mandi Price Updates** – Real-time market prices via data.gov.in API
- 🌦️ **Weather Advisory** – Current conditions + agronomy recommendations (OpenWeatherMap)
- 🧮 **Fertilizer Calculator** – Nutrient requirement calculations per crop & area
- 🔄 **Multi-turn Conversations** – 5-turn history in Redis (or in-memory fallback)
- 🌐 **Multilingual Support** – English, Hindi, Gujarati with Unicode handling
- ⚡ **Production Ready** – Docker containerized, async/await, SSE streaming

### Why Build This?

**Problem:** Indian farmers struggle to access reliable agricultural information quickly, in their native language.

**Solution:** A RAG system that:
1. Encodes farmer queries into dense embeddings (BAAI/bge-m3)
2. Retrieves relevant chunks from Qdrant (vector DB)
3. Reranks with cross-encoder for precision
4. Feeds into a ReAct agent with 3 specialized tools
5. Streams responses in real-time

---

## Architecture Deep Dive

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   AgroSight RAG Data Pipeline                    │
└─────────────────────────────────────────────────────────────────┘

DATA INGESTION LAYER
├─ Data Sources
│  ├─ 113 PDFs (1 GB agricultural books)
│  ├─ Mandi CSV (USDA/FAO market data)
│  ├─ Scheme FAQs (JSON)
│  ├─ Disease Knowledge Base (JSON)
│  └─ Soil Classification (JSON)
│
├─ Hybrid Auto-Select Chunker
│  ├─ Semantic chunking (flowing text)
│  ├─ Section-based (structured PDFs)
│  ├─ Q&A pair extraction (FAQ JSON)
│  ├─ Table/Record narrative (CSV/JSON)
│  └─ Sliding window fallback
│
├─ Batch Embedding (bge-m3: 1024-dim)
│  ├─ Dense vectors (cosine similarity)
│  └─ Sparse BM25 weights (hybrid search)
│
└─ Qdrant Vector DB (agricultural_knowledge_v2)
   └─ Stores 100K+ chunks with metadata

QUERY PROCESSING LAYER
├─ User Query (Frontend)
│
├─ Encode Query (bge-m3 dense + BM25 sparse)
│
├─ Hybrid Retrieval (Qdrant)
│  └─ Top 16 candidates (dense + sparse fusion)
│
├─ Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)
│  └─ Top 5 reranked by relevance
│
├─ Context Assembly
│  └─ Formatted prompt with history + guidelines
│
└─ LangGraph ReAct Agent
   ├─ LLM (Mistral API, qwen3.5:9b local option)
   ├─ Tools:
   │  ├─ 🌦️ weather_tool → OpenWeatherMap
   │  ├─ 💰 mandi_price_tool → data.gov.in
   │  └─ 🧮 fertiliser_tool → Nutrient calculator
   │
   └─ Agent Loop (max 6 iterations)
      └─ Think → Act → Observe → Repeat

OUTPUT LAYER
├─ FastAPI Server (async/await)
├─ Server-Sent Events (SSE) Streaming
├─ Session Store (Redis with in-memory fallback)
└─ Static UI (HTML + CSS + JS)
```

### Why This Architecture?

1. **Separation of Concerns**: Each layer (ingestion, retrieval, generation) is modular
2. **Scalability**: Vector DB (Qdrant) scales to millions of chunks
3. **Precision**: Hybrid search (dense + sparse) + reranking maximizes relevance
4. **Reliability**: Falls back gracefully (e.g., Redis → in-memory, bge-m3 → MiniLM)
5. **Production Ready**: Async endpoints, streaming responses, containerization

---

## Technology Stack Explained

### Core Technologies & Why They Were Chosen

| **Component** | **Technology** | **Why This?** |
|---|---|---|
| **Web Framework** | FastAPI | Async-native, auto OpenAPI docs, production-proven |
| **LLM Framework** | LangChain + LangGraph | Agent orchestration, tool integration, ReAct pattern |
| **LLM Provider** | Mistral AI API (with Ollama fallback) | Low-latency, multilingual capability, cost-effective |
| **Embeddings** | BAAI/bge-m3 (1024-dim) | Multilingual, hybrid dense+sparse, SOTA performance |
| **Vector DB** | Qdrant | Cloud-native, sparse vector support, semantic search |
| **Reranker** | ms-marco-MiniLM-L-6-v2 | Cross-encoder, ~50ms, boosts precision 15-20% |
| **Session Store** | Redis | Sub-millisecond retrieval, 5-turn history, TTL support |
| **Chunker** | Custom hybrid algorithm | Domain-specific (PDFs, tables, FAQs), 6 strategies |
| **PDF Processing** | pdfplumber + PyMuPDF + pypdf | Table extraction, OCR (tesseract), flexible parsing |
| **Async I/O** | httpx + asyncio | Non-blocking API calls, concurrent tool execution |
| **Logging** | loguru | Structured logs, color output, file rotation |
| **Frontend** | HTML5 + Vanilla JS + Lucide Icons | Lightweight, SSE integration, responsive design |
| **Containerization** | Docker (multi-stage) | Reproducible builds, optimized image size (bge-m3 + deps) |

---

## File-by-File Detailed Analysis

### 📁 Root Level Files

#### `README.md`
**Purpose**: Project documentation, quick-start guide, architecture overview.

**Key Sections**:
- Architecture diagram (ASCII art)
- Quick-start (Prerequisites, Install, Seed data, Ingest)
- API endpoint reference (/health, /search, /chat, /session/{id})

**Why This File Matters**: 
- Onboarding new developers
- Understanding the full pipeline at a glance
- Reproducible setup instructions

**Tech Concepts Used**:
- Markdown formatting with code blocks
- ASCII architecture diagrams

---

#### `requirements.txt`
**Purpose**: Declares all Python dependencies with pinned versions.

**Key Dependencies**:
```
fastapi==0.115.6              # Web server
langchain>=0.3.0              # AI framework
sentence-transformers         # Embeddings & reranking
qdrant-client==1.12.2         # Vector DB client
pdfplumber==0.11.4            # PDF extraction
redis                         # Session store
torch                         # Deep learning (GPU support)
```

**Why Each Dependency?**
- **fastapi**: Async HTTP server with automatic documentation
- **langchain**: Unified interface for LLMs, embeddings, tools
- **sentence-transformers**: Efficient model loading (GPU/CPU) + batching
- **qdrant-client**: Hybrid search (dense + sparse vectors)
- **pdfplumber**: Extracts tables from PDFs accurately
- **torch**: Enables GPU acceleration for embeddings & cross-encoder

**Version Strategy**: 
- Pinned versions (e.g., `fastapi==0.115.6`) for reproducibility
- Loose ranges for frameworks (e.g., `langchain>=0.3.0`) for compatibility

---

#### `pyproject.toml`
**Purpose**: Python project metadata, testing configuration.

**Key Sections**:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Why Use pyproject.toml?**
- Unified config file (PEP 517/518 standard)
- Pytest auto-discovery of async tests
- Ignored warnings (DeprecationWarning, UserWarning)

---

#### `Dockerfile`
**Purpose**: Multi-stage Docker build for production deployment.

**Build Stages**:
1. **Builder Stage**: Installs heavy deps (torch, transformers)
2. **Runtime Stage**: Minimal Python 3.11-slim with only runtime deps

**Why Multi-Stage?**
- Reduces final image size (excludes build tools, gcc, headers)
- Builder: ~2 GB (with build tools) → Runtime: ~800 MB

**System Deps Included**:
- `tesseract-ocr` (Hindi & Gujarati language packs) – OCR for scanned PDFs
- `poppler-utils` – PDF to image conversion
- `libssl-dev`, `libpq-dev` – Security & database libs

---

#### `docker-compose.yml`
**Purpose**: Orchestrates AgroSight services locally.

**Services**:
- `redis:7.2-alpine` – Session store
- `qdrant:v1.8.0` – Vector DB
- `app` – FastAPI server (builds from Dockerfile)

**Environment**: 
- Mounts `.env` for API keys
- Exposes ports 8000 (API), 6379 (Redis), 6333 (Qdrant)

---

#### `Makefile`
**Purpose**: Common commands for development & deployment.

**Common Targets**:
- `make build` – Build Docker image
- `make up` – Start docker-compose services
- `make ingest` – Run full data ingestion
- `make test` – Run pytest
- `make lint` – Run black + isort

---

### 📂 app/ (Core Application)

#### `app/main.py`
**Purpose**: FastAPI application factory, endpoint definitions, lifespan events.

**Key Concepts**:

1. **Lifespan Events**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: preload heavy models in parallel
    await asyncio.gather(
        embedder.preload_models(),
        reranker.preload_models(),
        get_client()
    )
    yield
    # Cleanup goes here
```

**Why?**: Ensures models (embedder: 2 GB, reranker: 400 MB) load once at startup, not per-request.

2. **CORS Middleware**
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

**Why?**: Allows browser (frontend) to call API from any origin (localhost, production domain).

3. **Endpoints**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve static HTML UI |
| `/health` | GET | Liveness probe (for Kubernetes) |
| `/search` | POST | Raw retrieval (no LLM, just chunks) |
| `/chat` | POST | Full RAG with agent (SSE streaming) |
| `/session/{id}` | DELETE | Clear conversation history |

**Why SSE (Server-Sent Events)?**
- Client-initiated connection (no polling needed)
- Server pushes response tokens as they're generated
- Browser can display tokens in real-time (streaming effect)

---

#### `app/services/agent.py`
**Purpose**: Orchestrates the full RAG pipeline via LangGraph ReAct agent.

**The RAG Pipeline** (step-by-step):

```python
async def stream_agent(query: str, session_id: str):
    # Step 1: Detect language (en, hi, gu)
    language = detect_language(query)
    
    # Step 2: Encode query (dense + sparse vectors)
    dense_vec = encode_query(query)      # 1024 dimensions
    sparse_vec = encode_sparse(query)    # BM25 weights
    
    # Step 3: Hybrid retrieve from Qdrant (top 16)
    candidates = hybrid_search(dense_vec, sparse_vec, top_k=16)
    
    # Step 4: Rerank to top 5 with cross-encoder
    reranked = rerank(query, candidates, top_k=5)
    
    # Step 5: Format context + history for prompt
    context_str = format_context(reranked)
    history_str = format_history(get_history(session_id))
    
    # Step 6: Assemble RAG prompt
    system_prompt = RAG_SYSTEM_PROMPT
    user_message = RAG_USER_TEMPLATE.format(
        context=context_str,
        history=history_str,
        question=query,
        language=get_language_name(language)
    )
    
    # Step 7: Run ReAct agent (max 6 iterations)
    agent = create_react_agent(llm, tools=[weather_tool, mandi_price_tool, fertiliser_tool])
    async for token in agent.stream(user_message):
        yield token
    
    # Step 8: Store turn in Redis history
    append_turn(session_id, "user", query)
    append_turn(session_id, "assistant", response)
```

**Key Design Patterns**:

1. **Tool Integration**
```python
@tool
async def weather_tool(location: str) -> str:
    """Get current weather and agronomy advisory for a location."""
    result = await get_weather_advisory(location)
    return str(result)
```
- LangChain `@tool` decorator makes function callable by agent
- Agent decides when to call tools (ReAct: Reasoning → Acting)

2. **Agent Loop** (ReAct Pattern)
```
Iteration 1:
  LLM Thinks: "User asked about wheat prices in Rajkot. I should use mandi_price_tool."
  Agent Acts: Calls mandi_price_tool("wheat", market="Rajkot")
  Observes: {"price": 2150, "unit": "per quintal"}

Iteration 2:
  LLM Thinks: "I got the price. Now I should provide context from knowledge base."
  Agent Acts: Uses context from RAG retrieval
  Responds: Final answer to farmer
```

**Why ReAct?**
- Transparent reasoning (farmer sees why tool was called)
- Multi-step problem solving (e.g., "calculate dose for wheat, then find which fertilizer is cheapest")
- Reduces hallucination (facts come from tools, not made up)

**Why Mistral API?**
- Lower latency than GPT-4
- Good at instruction following (tool use)
- Cost-effective (~$2/M input tokens)

---

#### `app/services/chunker.py`
**Purpose**: Splits documents into chunks using 6 strategies (hybrid auto-select).

**The 6 Chunking Strategies**:

1. **Semantic Chunking** (for flowing text)
```python
def semantic_chunks(text, chunk_size=512):
    """Split at sentence boundaries to ~512 words."""
    sentences = _split_sentences(text)
    chunks = []
    for sent in sentences:
        if len(current) + len(sent) > chunk_size:
            chunks.append(ChunkResult(text=" ".join(current)))
            current = [sent]
        else:
            current.append(sent)
    return chunks
```

**Why?**: Preserves semantic meaning (sentences are complete thoughts).

2. **Section-Based Chunking** (for structured PDFs)
```python
def section_chunks(pdf_path):
    """Extract text under each heading (H1, H2) as a chunk."""
    # Detect headers: "Chapter 5. Disease Management"
    # Group text until next header
    # Return each section as one chunk
```

**Why?**: Headers are natural boundaries (chapters, subsections).

3. **Q&A Pair Extraction** (for FAQ JSONs)
```python
def qa_chunks(json_data):
    """Each FAQ entry → one chunk with format 'Q: ... A: ...'"""
    for entry in json_data:
        chunk = f"Q: {entry['question']}\nA: {entry['answer']}"
        yield ChunkResult(chunk, chunk_type="qa")
```

**Why?**: Preserves question-context (queries often resemble questions).

4. **Table/Record Narrative** (for CSVs & mandi data)
```python
def table_chunks(csv_path):
    """Each row → 'Commodity: wheat, Market: Rajkot, Price: 2150'"""
    df = pd.read_csv(csv_path)
    for idx, row in df.iterrows():
        narrative = " | ".join([f"{col}: {row[col]}" for col in df.columns])
        yield ChunkResult(narrative, chunk_type="record")
```

**Why?**: Converts structured data to searchable narratives (BM25 loves keywords).

5. **Sliding Window** (fallback for unstructured text)
```python
def sliding_window_chunks(text, window=512, stride=256):
    """Overlapping chunks (512 words, 256 word stride)."""
    words = text.split()
    for i in range(0, len(words) - window, stride):
        chunk = " ".join(words[i:i+window])
        yield ChunkResult(chunk)
```

**Why?**: Simple fallback when no structure detected. Overlap (stride < window) preserves context across chunks.

6. **Hybrid Auto-Select**
```python
def chunk_file(file_path):
    """Automatically route file to right strategy."""
    if file_path.endswith(".pdf"):
        if has_structure(pdf):
            return section_chunks(pdf)
        else:
            return semantic_chunks(text)
    elif file_path.endswith(".json"):
        if is_faq(json_data):
            return qa_chunks(json_data)
        else:
            return record_chunks(json_data)
    elif file_path.endswith(".csv"):
        return table_chunks(csv_path)
    else:
        return sliding_window_chunks(text)
```

**Why?**: One file might need multiple strategies (e.g., PDF with both prose + tables → use both).

**The ChunkResult Dataclass**:
```python
@dataclass
class ChunkResult:
    text: str                          # The chunk text
    chunk_hash: str                    # SHA-256 (for deduplication)
    source_file: str                   # Where it came from
    chunk_type: str                    # "text", "qa", "record", "table"
    chunk_index: int                   # Order in file
    crop_category: str                 # "wheat", "cotton", etc. (metadata)
    language: str                      # "en", "hi", "gu"
    metadata: dict                     # Extensible key-value pairs
```

**Why This Design?**
- `chunk_hash`: Deduplicates identical chunks across re-ingestions
- `chunk_type`: Helps with filtering (e.g., "only show Q&A chunks")
- `crop_category`: Enables crop-specific retrieval ("wheat" queries → wheat chunks)
- `language`: Multilingual filtering

**Token Counting**:
```python
chunk_size = chunk_size or settings.default_chunk_tokens  # 512
overlap = overlap or settings.default_overlap_tokens       # 64
```

**Why 512 tokens?**
- ~1.3 words per token (average)
- ~670 words per chunk
- Good balance: detailed enough for context, small enough for Qdrant to index millions

---

#### `app/services/embedder.py`
**Purpose**: Encodes text into dense vectors (embeddings) using BAAI/bge-m3.

**Embedding Model Comparison**:

| Model | Dim | Multilingual | BM25 Sparse | Speed | Use Case |
|-------|-----|--------------|-------------|-------|----------|
| all-MiniLM-L6-v2 | 384 | ❌ | ❌ | 300 chunks/sec | English only |
| paraphrase-multilingual-MiniLM | 384 | ✅ | ❌ | 250 chunks/sec | Basic multi-lang |
| **BAAI/bge-m3** | **1024** | **✅** | **✅** | **50 chunks/sec** | **Best overall (SOTA)** |

**Why bge-m3?**
- **1024 dimensions**: More discriminative power (denser vector space)
- **Multilingual**: Trained on 111 languages (Hindi, Gujarati included)
- **Sparse vectors**: Built-in BM25 weights for hybrid search (dense + keyword)
- **SOTA performance**: Ranked #1 on MTEB leaderboard for semantic search

**Encoding Workflow**:

```python
def encode_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Batch encode texts → normalized vectors (shape: [N, 1024])."""
    model = _load_model(settings.embedding_model)
    
    embeddings = []
    for batch in tqdm(chunks(texts, batch_size)):
        if "bge-m3" in settings.embedding_model:
            # FlagEmbedding API: encode() returns dict with 'dense_vecs'
            output = model.encode(batch, return_dense=True, return_sparse=False)
            embeddings.append(output['dense_vecs'])
        else:
            # sentence-transformers API: encode() returns np.ndarray directly
            embeddings.append(model.encode(batch))
    
    vectors = np.vstack(embeddings)
    
    # Normalize (L2 norm) for cosine similarity
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    
    return vectors
```

**Why Normalization?**
- Cosine similarity = dot product of normalized vectors
- `similarity(A, B) = A·B / (|A| × |B|)` simplifies to `A·B` when both are unit vectors

**Sparse Vector Encoding** (for bge-m3):
```python
def encode_sparse(text: str) -> dict:
    """Return {'token_id': weight, ...} for BM25-like search."""
    model = _get_model()  # bge-m3
    output = model.encode([text], return_dense=False, return_sparse=True)
    # Returns: {12345: 0.5, 67890: 0.3, ...}  (token IDs → TF-IDF weights)
    return output['sparse_vecs'][0]
```

**Why Sparse Vectors?**
- Dense vectors capture semantic meaning ("disease" ≈ "pest")
- Sparse vectors capture exact keywords ("wheat" must match)
- Hybrid = best of both worlds

**Lazy Singleton Pattern**:
```python
_model = None

def _load_model(model_name: str):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model  # Reuse cached model
    # Load once, reuse forever
    _model = BGEM3FlagModel(model_name)
    return _model
```

**Why?**
- Model loading is expensive (2-3 seconds, memory allocation)
- Singleton ensures only one instance per process
- Thread-safe (GIL protects Python objects)

---

#### `app/services/vector_store.py`
**Purpose**: Manages Qdrant vector database (create, upsert, search).

**Qdrant Concepts**:

1. **Collection** = Table in SQL, but for vectors
   - Collection "agricultural_knowledge_v2" stores 100K+ chunks
   - Each chunk = vector (1024-dim) + payload (metadata)

2. **Vector Config**
```python
def ensure_collection(collection_name, dim=1024):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=dim,                                  # 1024 dimensions
            distance=models.Distance.COSINE,           # Similarity metric
            on_disk=False,                             # RAM for speed
        ),
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(...)     # Hybrid search
        }
    )
```

**Why Cosine Distance?**
- Normalized vectors: `dist = 1 - similarity` (0 = identical, 1 = opposite)
- Popular for semantic search (ignores magnitude, only direction)

3. **Upsert (Insert/Update)**
```python
def upsert_chunks(chunks: list[ChunkResult], batch_size: int = 100):
    """Add/update chunks in Qdrant."""
    for batch in chunks_iter(chunks, batch_size):
        points = []
        for chunk in batch:
            point = models.PointStruct(
                id=uuid.uuid4(),
                vector=chunk.embedding,            # 1024-dim dense vector
                payload={
                    'text': chunk.text,
                    'source_file': chunk.source_file,
                    'chunk_type': chunk.chunk_type,
                    'chunk_hash': chunk.chunk_hash, # Deduplication key
                    'crop_category': chunk.crop_category,
                    'language': chunk.language,
                    **chunk.metadata
                },
                sparse_vectors={'bm25': chunk.sparse_vector}  # {token: weight}
            )
            points.append(point)
        
        # Upsert = "insert or overwrite"
        client.upsert(settings.qdrant_collection, points=points)
```

**Deduplication Strategy**:
```python
# Before upsert, check: does this chunk_hash already exist?
chunk_hash = sha256(f"{text}|{source_file}|{chunk_index}")
existing = client.scroll(
    collection_name,
    limit=1,
    scroll_filter=models.HasIdFilter(
        has_id=[chunk_hash]
    )
)
if existing:
    return  # Skip duplicate
```

**Why?**: Re-ingesting files would create duplicates. SHA-256 ensures idempotency.

4. **Hybrid Search** (Dense + Sparse)
```python
def hybrid_search(dense_vec, sparse_vec, top_k=16):
    """Retrieve using both semantic (dense) and keyword (sparse) signals."""
    
    # Dense search (cosine similarity)
    dense_results = client.search(
        collection_name,
        query_vector=dense_vec,
        limit=top_k * 2  # Get extra candidates for reranking
    )
    
    # Sparse search (BM25-like keyword matching)
    sparse_results = client.search(
        collection_name,
        query_vector=sparse_vec,
        vector_name="bm25",           # Use sparse vector config
        limit=top_k * 2
    )
    
    # Reciprocal Rank Fusion (RRF): merge dense + sparse scores
    merged = _rrf_fusion([dense_results, sparse_results])
    
    return merged[:top_k]
```

**Reciprocal Rank Fusion (RRF)** Formula:
```
RRF_score = 1 / (k + rank_dense) + 1 / (k + rank_sparse)
```
- `k=60` (typical value)
- Example: if dense ranked chunk at position 1, sparse at position 3:
  - `RRF = 1/(60+1) + 1/(60+3) ≈ 0.0179`
- Combines both signals without weighting bias

**Why Hybrid?**
- Dense: Semantically similar chunks (farmer asks "disease" → finds "pest" chunks)
- Sparse: Exact keywords (farmer asks "wheat prices" → finds chunks with "wheat" and "price")
- Together: Best recall + precision

---

#### `app/services/reranker.py`
**Purpose**: Re-ranks top-K candidates using cross-encoder for precision.

**Cross-Encoder vs. Bi-Encoder**:

| Type | Input | Output | Use Case |
|------|-------|--------|----------|
| **Bi-Encoder** (embedding model) | Text separately | Vector for each text | Fast retrieval (million chunks) |
| **Cross-Encoder** (reranker) | (Query, Chunk) pair | Score (0-1) | Precise ranking (top-K) |

**Cross-Encoder: ms-marco-MiniLM-L-6-v2**

```python
def rerank(query: str, candidates: list[dict], top_k: int = 5):
    """Rerank candidates by (query, candidate) relevance."""
    cross_encoder = _get_cross_encoder()  # Load model
    
    # Prepare pairs: [(query, chunk1), (query, chunk2), ...]
    pairs = [(query, c.get('text', '')) for c in candidates]
    
    # Score each pair (takes ~1ms per pair with GPU)
    scores = cross_encoder.predict(pairs)  # Returns [0.8, 0.5, 0.9, ...]
    
    # Rank by score
    ranked = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True
    )[:top_k]
    
    return [doc for score, doc in ranked]
```

**Why ms-marco-MiniLM-L-6-v2?**
- Trained on MS MARCO (500K real search queries + judgments)
- Small (22 MB, 6 layers) yet powerful
- ~50ms per 16 candidates (acceptable latency)
- Improves retrieval precision by 15-20%

**Workflow**:
```
Hybrid Search: top 16 candidates → [chunk1, chunk2, ..., chunk16]
Cross-Encoder Rerank: top 5 by relevance → [chunk3, chunk7, chunk2, chunk1, chunk15]
```

**Example**: Query = "wheat disease"
| Rank | Candidate | Dense Score | Hybrid Score | Cross-Encoder Score |
|------|-----------|-------------|--------------|---------------------|
| 1 | "Wheat leaf rust" | 0.89 | 0.75 | 0.92 |
| 2 | "Rice blast disease" | 0.85 | 0.70 | 0.45 |
| 3 | "Wheat fertilizer guide" | 0.80 | 0.68 | 0.50 |

**Result**: Reranker moves "Rice blast" down (low cross-encoder score), boosts "Leaf rust" (high score).

---

#### `app/services/session_store.py`
**Purpose**: Manages 5-turn conversation history per session_id.

**Session Store Strategy**:

```python
def get_history(session_id: str) -> list[dict]:
    """Fetch conversation history."""
    r = _get_redis()
    if r is not None:
        # Try Redis first
        raw = r.get(f"session:{session_id}")
        if raw:
            return json.loads(raw)
    
    # Fallback: in-memory dict
    return list(_memory_store[session_id])
```

**Why Redis?**
- **Sub-millisecond retrieval** (compared to database queries)
- **TTL support**: Automatically expire sessions after 24h
- **Distributed**: Works across multiple API servers

**Fallback (In-Memory)**:
- Works offline (development without Redis)
- Lost on server restart (acceptable for dev)

**History Management**:

```python
def append_turn(session_id: str, role: str, content: str):
    """Add turn and enforce max history."""
    history = get_history(session_id)
    history.append({"role": role, "content": content})
    
    # Keep only last 5 turns (user + assistant pairs)
    max_turns = settings.max_history_turns * 2
    if len(history) > max_turns:
        history = history[-max_turns:]
    
    # Store back
    if r := _get_redis():
        r.setex(
            f"session:{session_id}",
            settings.session_ttl_seconds,  # 24h
            json.dumps(history)
        )
```

**Format**:
```json
[
  {"role": "user", "content": "What is wheat rust?"},
  {"role": "assistant", "content": "Wheat rust is a fungal disease..."},
  {"role": "user", "content": "How to control it?"},
  {"role": "assistant", "content": "Apply sulfur spray..."}
]
```

**Why 5 turns (10 messages)?**
- Enough context for agent to understand conversation flow
- Not too much (keeps token count < 2000 for LLM context)
- Reduces token usage cost

---

#### `app/services/prompts.py`
**Purpose**: Centralized prompt templates for system & user messages.

**System Prompt** (Embedded in Agent):

```
You are AgroSight, a highly helpful expert agricultural assistant serving Indian farmers.
You provide authoritative, practical, and expert advice.

DOMAIN FOCUS & GUARDRAILS:
- You are a STRICTLY AGRICULTURAL assistant. Your expertise is limited to farming, crops, livestock, mandi prices, weather, and government schemes for farmers.
- If the user asks about unrelated topics (e.g., sports results, movie news, politics), politely decline by saying you are an agricultural assistant and redirect them to a farming-related topic.

CORE OPERATING PRINCIPLE:
- You are an expert agronomist. Use BOTH the provided CONTEXT samples and your OWN INTERNAL KNOWLEDGE to give the best possible answer.
- TOOL USAGE (MANDATORY): You have specialized tools for certain tasks. You MUST use them.
    1. For current/upcoming weather: Always call `weather_tool`. DO NOT guess weather.
    2. For current mandi/market prices: Always call `mandi_price_tool`. DO NOT provide "estimated" or "average" prices from internal knowledge if the tool is available.
    3. For fertilizer calculations: Always use `fertiliser_tool`.
- Answer in the EXACT same language as the user's question (e.g., 100% English or 100% Hindi).
- CRITICAL: Never mix languages in a single response unless the user specifically asks for it.
- CRITICAL HINDI/GUJARATI RULE: Always provide cohesive, well-formed text. Never insert spaces or breaks inside words (e.g., use "सिंचाई" not "स िंचाई").
- Cite source file names if a specific fact comes from the context, e.g. [Source: wheat_guide.pdf].
```

**Why These Rules?**

1. **Domain Focus**: Prevents off-topic responses (reduces hallucination risk)
2. **Tool Mandate**: Forces exact, current data (prices, weather change hourly)
3. **Multilingual**: Detects query language, responds in same language (no confusion)
4. **Hindi/Gujarati Rules**: These languages have complex scripts; breaking words kills meaning

**User Prompt Template**:

```
RETRIEVED CONTEXT:
{context}  ← Top 5 reranked chunks from Qdrant

CONVERSATION HISTORY:
{history}  ← Last 5 turns from Redis

FARMER'S QUESTION:
{question}  ← User's raw query

TARGET RESPONSE LANGUAGE:
{language}  ← "English", "Hindi", or "Gujarati"

INSTRUCTIONS:
1. Provide a comprehensive answer. Use the RETRIEVED CONTEXT to back your points with [Source: filename] citations.
2. If context is missing, use your expert internal knowledge to fill in the gaps for the user.
3. You MUST respond exclusively in {language}. All headings, bullet points, and the final disclaimer must be in this language.
```

**Language Detection**:

```python
import re

_HINDI_RANGE = re.compile(r'[\u0900-\u097F]')     # Devanagari script
_GUJARATI_RANGE = re.compile(r'[\u0A80-\u0AFF]')  # Gujarati script

def detect_language(text: str) -> str:
    """Return 'hi', 'gu', or 'en' based on Unicode character ranges."""
    if _HINDI_RANGE.search(text):
        return "hi"
    if _GUJARATI_RANGE.search(text):
        return "gu"
    return "en"
```

**Why Unicode Ranges?**
- Hindi (Devanagari): U+0900 to U+097F (e.g., "सिंचाई" = U+0938 U+0902 U+0902 ...)
- Gujarati: U+0A80 to U+0AFF (e.g., "ખેતર" = U+0A96 U+0AC7 U+0AA4 ...)
- Simple regex check (no ML model needed)

---

#### `app/services/agro_tools.py`
**Purpose**: Three LangGraph-compatible tools for specialized tasks.

**Tool 1: Weather Advisory**

```python
async def get_weather_advisory(location: str) -> dict:
    """
    Fetch current weather from OpenWeatherMap.
    Generate agronomy advisory based on conditions.
    """
    if not settings.openweather_api_key:
        return {"error": "API key not configured"}
    
    url = f"{settings.openweather_base_url}/weather"
    params = {
        "appid": settings.openweather_api_key,
        "q": location,
        "units": "metric"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    
    temp_c = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    wind_kmh = data["wind"]["speed"] * 3.6
    condition = data["weather"][0]["description"]
    
    # Generate rule-based advisory
    advisory = _generate_advisory(temp_c, humidity, wind_kmh, condition)
    
    return {
        "location": data.get("name", location),
        "temperature_c": temp_c,
        "humidity_pct": humidity,
        "wind_kmh": wind_kmh,
        "condition": condition,
        "advisory": advisory,
        "source": "OpenWeatherMap (Real-time)"
    }
```

**Advisory Rules**:
```python
def _generate_advisory(temp_c, humidity, wind_kmh, condition, rain_mm) -> str:
    tips = []
    
    if rain_mm > 10:
        tips.append("Heavy rainfall — avoid irrigation and field operations today.")
    elif humidity < 40 and temp_c > 35:
        tips.append("Hot and dry conditions — irrigate crops early morning or evening.")
    
    if wind_kmh > 40:
        tips.append("High winds — postpone pesticide/fertiliser spraying to avoid drift.")
    
    if temp_c > 40:
        tips.append("Extreme heat — protect nurseries with shade netting.")
    elif temp_c < 5:
        tips.append("Near-frost temperatures — protect sensitive crops.")
    
    return "\n".join(tips) if tips else "Conditions are favourable for farming operations."
```

**Why Rule-Based?**
- Transparent (farmer understands why advice is given)
- Fast (no ML model, just if-else)
- Deterministic (same input = same output)

**Tool 2: Mandi Price Lookup**

```python
async def get_mandi_price(
    commodity: str,
    market: str = "",
    state: str = "Gujarat"
) -> dict:
    """
    Fetch latest mandi price from data.gov.in API.
    Falls back to cached CSV if API unavailable.
    """
    url = f"{settings.data_gov_base_url}/resource/{settings.data_gov_mandi_resource_id}"
    
    params = {
        "limit": 100,
        "api-key": settings.data_gov_api_key_1,
        "filters": [
            ("commodity", commodity),
            ("state", state)
        ]
    }
    
    if market:
        params["filters"].append(("market", market))
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(url, params=params)
            data = resp.json()
            
            records = data.get("records", [])
            if records:
                latest = records[0]  # Most recent
                return {
                    "commodity": latest["commodity"],
                    "market": latest.get("market", market),
                    "state": latest.get("state", state),
                    "price": float(latest["price"]),
                    "unit": latest.get("unit", "per quintal"),
                    "date": latest.get("date", "today"),
                    "source": "data.gov.in (Government of India)"
                }
        except Exception as e:
            logger.warning(f"data.gov.in unavailable: {e}. Using fallback CSV.")
    
    # Fallback: read from cached CSV
    return _get_mandi_price_from_csv(commodity, market, state)
```

**Why Fallback?**
- APIs are unreliable (rate limits, downtime)
- Cached CSV (mandi_prices_2026-04-29.csv) still provides value
- Graceful degradation (less fresh, but still working)

**Tool 3: Fertilizer Calculator**

```python
async def fertiliser_calculator(
    crop: str,
    area_acres: float,
    fertiliser: str = "urea",
    nutrient: str = "N"
) -> dict:
    """
    Calculate fertiliser dose based on crop, area, and nutrient.
    Uses standard Indian agricultural guidelines (ICAR).
    """
    # Nutrient requirements (kg/hectare) per crop
    REQUIREMENTS = {
        "wheat": {"N": 120, "P": 60, "K": 40},
        "rice": {"N": 150, "P": 75, "K": 40},
        "cotton": {"N": 200, "P": 100, "K": 60},
        "sugarcane": {"N": 250, "P": 100, "K": 100},
        # ... more crops
    }
    
    if crop.lower() not in REQUIREMENTS:
        return {"error": f"Crop '{crop}' not in database. Contact admin to add."}
    
    # Get requirement
    requirement_kg_per_ha = REQUIREMENTS[crop.lower()][nutrient]
    
    # Convert acres to hectares (1 acre = 0.4047 hectares)
    area_ha = area_acres * 0.4047
    
    # Calculate total nutrient needed
    total_nutrient_kg = requirement_kg_per_ha * area_ha
    
    # Fertiliser nutrient content (%)
    NUTRIENT_CONTENT = {
        "urea": {"N": 46},
        "dap": {"P": 18, "N": 18},
        "mop": {"K": 60},
        # ... more fertilisers
    }
    
    if fertiliser.lower() not in NUTRIENT_CONTENT:
        return {"error": f"Fertiliser '{fertiliser}' not found."}
    
    # Calculate fertiliser needed
    nutrient_pct = NUTRIENT_CONTENT[fertiliser.lower()].get(nutrient, 0)
    if nutrient_pct == 0:
        return {"error": f"'{fertiliser}' doesn't contain nutrient '{nutrient}'."}
    
    fertiliser_kg = (total_nutrient_kg * 100) / nutrient_pct
    
    # Standard bag size
    BAG_SIZE = 50  # kg
    bags_needed = math.ceil(fertiliser_kg / BAG_SIZE)
    
    return {
        "crop": crop,
        "area_acres": area_acres,
        "area_hectares": round(area_ha, 2),
        "nutrient_required": f"{nutrient} {requirement_kg_per_ha} kg/ha",
        "total_nutrient_kg": round(total_nutrient_kg, 2),
        "fertiliser": fertiliser,
        "fertiliser_kg": round(fertiliser_kg, 2),
        "bags_needed": bags_needed,
        "bag_size_kg": BAG_SIZE,
        "source": "ICAR (Indian Council of Agricultural Research)"
    }
```

**Example Calculation**:
```
Crop: Wheat, Area: 2 acres, Nutrient: N, Fertiliser: Urea

1. Requirement: 120 kg N per hectare
2. Area: 2 acres = 0.8094 hectares
3. Total N needed: 120 × 0.8094 = 97.13 kg
4. Urea contains 46% N, so: (97.13 × 100) / 46 = 211.2 kg urea
5. Standard bag: 50 kg, so: ceil(211.2 / 50) = 5 bags
6. Result: "Use 5 bags of urea (211 kg total)"
```

---

### 📂 app/utils/ (Configuration & Helpers)

#### `app/utils/config.py`
**Purpose**: Centralized configuration (Pydantic BaseSettings).

**Design Pattern** (12-Factor App):

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Load from .env or environment variables
    mistral_api_key: str = Field(..., env="MISTRAL_API_KEY")
    qdrant_url: str = Field(..., env="QDRANT_URL")
    redis_url: str = "redis://localhost:6379/0"  # Default if not set
```

**Why Pydantic Settings?**
- **Type validation**: Ensures config values are correct type (int, str, URL)
- **Default values**: Provides sensible defaults (e.g., redis_url fallback)
- **Environment-aware**: Reads from .env file or OS environment
- **Lazy loading**: Settings loaded once per app instance (singleton via `@lru_cache`)

**Key Settings**:

| Setting | Default | Purpose |
|---------|---------|---------|
| `embedding_model` | BAAI/bge-m3 | Dense+sparse embeddings |
| `embedding_dim` | 1024 | Vector dimensionality |
| `retrieval_top_k` | 8 | Retrieve this many candidates |
| `retrieval_score_threshold` | 0.18 | Minimum relevance score |
| `default_chunk_tokens` | 512 | Target chunk size |
| `max_history_turns` | 5 | Conversation history depth |
| `session_ttl_seconds` | 86400 | 24 hours |
| `llm_temperature` | 0.2 | Low temp = deterministic responses |
| `llm_max_tokens` | 4096 | Max response length |
| `max_agent_iterations` | 6 | Max tool calls per query |

---

#### `app/utils/logger.py`
**Purpose**: Structured logging with loguru.

**Why loguru?**
- **Pretty output**: Colors, timestamps, module names (stdout)
- **File rotation**: Logs auto-rotate at 50 MB (prevents disk filling)
- **Structured**: Easy to parse logs in production (JSON format available)
- **Lazy enqueue**: Logging doesn't block main thread

**Setup**:

```python
def configure_logger() -> None:
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    logger.add(
        "logs/agrosight.log",
        level="DEBUG",
        rotation="50 MB",
        retention="30 days",
        compression="gz",
        enqueue=True,  # Non-blocking
    )
```

**Output Example**:
```
2026-05-06 14:23:45 | INFO     | agent.py:45 – Encoding query: "wheat price Rajkot"
2026-05-06 14:23:46 | DEBUG    | vector_store.py:120 – Qdrant retrieved 16 candidates
2026-05-06 14:23:46 | INFO     | reranker.py:78 – Reranked to top 5 results
2026-05-06 14:23:50 | SUCCESS  | agent.py:180 – Response generated successfully
```

---

#### `app/utils/file_utils.py`
**Purpose**: File I/O helpers (iterate files, hash chunks, load JSON/CSV).

**Key Functions**:

```python
def iter_data_files(root: Path) -> Generator[Path, None, None]:
    """Walk data directory, yield ingestible files (.pdf, .json, .csv)."""
    for file_path in root.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".pdf", ".json", ".csv"]:
            yield file_path

def sha256_of_text(text: str) -> str:
    """Hash text for deduplication."""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()

def load_json(file_path: Path) -> dict | list:
    """Load JSON with error handling."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_csv(file_path: Path) -> pd.DataFrame:
    """Load CSV with pandas."""
    return pd.read_csv(file_path, encoding="utf-8")
```

---

### 📂 app/static/ (Frontend)

#### `app/static/index.html`
**Purpose**: Chatbot UI (HTML structure).

**Key Sections**:

1. **Sidebar** (Brand + History)
   - Logo + "AgroSight" brand
   - Recent activity (session history)
   - "New Conversation" button

2. **Main Content** (Chat Area)
   - Welcome screen (hero + suggestion chips)
   - Chat messages container
   - Input form (text + send button)

3. **Lucide Icons** (SVG icons)
   - `sprout` – Brand icon
   - `message-square` – Chat icon
   - `trending-up` – Mandi prices
   - `calculator` – Fertilizer calc
   - `cloud-sun` – Weather

**Why This Structure?**
- **Responsive**: Works on mobile + desktop
- **Semantic HTML**: Proper `<aside>`, `<main>`, `<nav>` tags
- **Accessibility**: ARIA labels (not shown in snippet)

---

#### `app/static/js/app.js`
**Purpose**: Frontend logic (SSE streaming, session management, UI state).

**Key Functions**:

1. **Session Management**
```javascript
let currentSessionId = localStorage.getItem('agrosight_session_id') || '';

function createNewSession() {
    currentSessionId = 'session_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('agrosight_session_id', currentSessionId);
    // Clear chat, show welcome screen
}

function loadSession(sessionId) {
    currentSessionId = sessionId;
    // Fetch messages for this session from localStorage
    const sessions = JSON.parse(localStorage.getItem('agrosight_sessions') || '{}');
    const conversation = sessions[currentSessionId] || [];
    // Render messages
}
```

**Why localStorage?**
- Client-side persistence (no backend needed)
- Works offline
- Keeps user conversations private (not sent to server)

2. **SSE Streaming**
```javascript
async function sendMessage(message) {
    isGenerating = true;
    elements.sendBtn.disabled = true;
    
    appendMessage("user", message);
    
    // Server-Sent Events: Open stream to /chat endpoint
    const eventSource = new EventSource(
        `/chat?session_id=${currentSessionId}&query=${encodeURIComponent(message)}`
    );
    
    let fullResponse = "";
    
    eventSource.onmessage = (event) => {
        const token = event.data;
        fullResponse += token;
        
        // Append token to last message (streaming effect)
        const lastMsg = elements.chatMessages.lastElementChild;
        lastMsg.textContent += token;
        
        // Scroll to bottom
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    };
    
    eventSource.onerror = () => {
        eventSource.close();
        isGenerating = false;
        elements.sendBtn.disabled = false;
    };
    
    eventSource.addEventListener("done", () => {
        eventSource.close();
        
        // Save conversation
        appendMessage("assistant", fullResponse);
        saveConversation();
        
        isGenerating = false;
        elements.sendBtn.disabled = false;
    });
}
```

**Why SSE?**
- Real-time token streaming (farmer sees response appearing live)
- Client-initiated (no polling needed)
- Works with proxies/firewalls (HTTP protocol)

3. **Message Rendering**
```javascript
function appendMessage(role, content) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}-message`;
    msgDiv.innerHTML = `<p>${escapeHtml(content)}</p>`;
    elements.chatMessages.appendChild(msgDiv);
}
```

**Why `escapeHtml()`?**
- Prevents XSS attacks (if content has `<script>` tags)
- Converts `<` → `&lt;`, `>` → `&gt;`, etc.

---

#### `app/static/css/style.css`
**Purpose**: Responsive styling for premium UI.

**Key Styles**:
- **Colors**: Brand green (#2D5016), accent orange (#D97706)
- **Typography**: Google Fonts "Outfit" (modern, readable)
- **Layout**: CSS Grid (sidebar + main), Flexbox (messages)
- **Animations**: Smooth transitions, typing effect for streaming

---

### 📂 scripts/ (Data Processing & Ingestion)

#### `scripts/ingest.py`
**Purpose**: End-to-end pipeline: chunk files → embed → upsert to Qdrant.

**Workflow**:

```python
def run_ingestion(data_root, books_dir, batch_size=50, recreate_collection=False):
    """Full ingestion pipeline."""
    
    # 1. Ensure Qdrant collection exists
    ensure_collection(recreate=recreate_collection)
    
    # 2. Collect all ingestible files
    all_files = []
    for root in [Path(data_root), Path(books_dir)]:
        all_files.extend(iter_data_files(root))
    
    # 3. Process files in batches
    pending_chunks = []
    for file_path in tqdm(all_files):
        chunks = chunk_file(file_path)  # Hybrid auto-select
        pending_chunks.extend(chunks)
        
        if len(pending_chunks) >= batch_size:
            upserted, skipped = _embed_and_upsert(pending_chunks)
            pending_chunks = []
    
    # 4. Flush remainder
    if pending_chunks:
        _embed_and_upsert(pending_chunks)
```

**Embedding & Upsert**:

```python
def _embed_and_upsert(chunks: list[ChunkResult]) -> tuple[int, int]:
    """
    Embed chunks in batches, deduplicate, upsert to Qdrant.
    Returns (upserted_count, skipped_count).
    """
    # Extract texts
    texts = [c.text for c in chunks]
    
    # Batch encode with bge-m3
    embeddings = encode_texts(texts, batch_size=32)
    
    # Get sparse vectors for hybrid search
    sparse_vecs = [encode_sparse(text) for text in texts]
    
    # Check for duplicates (by chunk_hash)
    existing_hashes = _get_existing_hashes()  # Query Qdrant
    
    # Filter out duplicates
    to_upsert = [
        (chunk, emb, sparse)
        for chunk, emb, sparse in zip(chunks, embeddings, sparse_vecs)
        if chunk.chunk_hash not in existing_hashes
    ]
    
    # Upsert to Qdrant
    if to_upsert:
        upsert_chunks([c for c, _, _ in to_upsert], embeddings=[e for _, e, _ in to_upsert])
    
    skipped = len(chunks) - len(to_upsert)
    return len(to_upsert), skipped
```

**Deduplication Strategy**:
- Before upsert, check if `chunk_hash` already exists
- If yes, skip (idempotent: re-running doesn't duplicate data)

---

### 📂 tests/ (Test Suite)

#### `tests/test_agrosight.py`
**Purpose**: Unit & integration tests.

**Typical Tests** (inferred from structure):
```python
def test_embedder_encode_query():
    """Test bge-m3 encoding."""
    query = "wheat disease"
    embedding = encode_query(query)
    assert embedding.shape == (1024,)
    assert np.linalg.norm(embedding) ≈ 1.0  # Normalized

def test_chunker_semantic():
    """Test semantic chunking."""
    text = "Sentence one. Sentence two. Sentence three."
    chunks = semantic_chunks(text, chunk_size=10)
    assert len(chunks) > 0

def test_reranker_ranks():
    """Test cross-encoder reranking."""
    query = "wheat price"
    candidates = [
        {"text": "Wheat is expensive"},
        {"text": "Rice cultivation guide"}
    ]
    ranked = rerank(query, candidates, top_k=2)
    assert ranked[0]["text"] == "Wheat is expensive"  # Higher relevance

def test_vector_store_upsert():
    """Test Qdrant upsert & retrieval."""
    chunk = ChunkResult(text="Test chunk")
    upsert_chunks([chunk])
    results = hybrid_search(embedding, top_k=1)
    assert len(results) == 1
```

**Why Tests?**
- Catch regressions (code changes break something)
- Document expected behavior
- Enable confident refactoring

---

## Core Concepts & How They Work

### 1. **Retrieval-Augmented Generation (RAG)**

**Problem**: LLMs have knowledge cutoff. They can hallucinate (make up facts).

**Solution**: Retrieve relevant documents first, then generate from them.

```
Query → Retrieve Context → Augment LLM Prompt → Generate Response
```

**AgroSight RAG Pipeline**:

```python
# Step 1: User asks about wheat
query = "How to prevent wheat rust?"

# Step 2: Retrieve relevant chunks from knowledge base
context = retrieve_context(query)
# Returns: [
#     {"text": "Wheat rust is caused by fungus Puccinia. Prevention: ..."},
#     {"text": "Spray sulfur 0.5% or triadimefon 0.1% at boot stage..."}
# ]

# Step 3: Augment prompt with context + history
prompt = f"""
CONTEXT:
{format_context(context)}

HISTORY:
{format_history(history)}

QUESTION:
{query}

Please answer using the context above.
"""

# Step 4: LLM generates from augmented prompt
response = llm.generate(prompt)
# Output: "To prevent wheat rust, apply fungicide..."
```

**Why RAG?**
- **Factuality**: Facts come from documents, not LLM's training data
- **Freshness**: Can include new documents (weather, mandi prices)
- **Citability**: Can point to source document
- **Cost**: Smaller model needed (augmented with retrieval)

---

### 2. **Hybrid Search (Dense + Sparse)**

**Dense Search** (Semantic):
- Query → Embedding (1024-dim vector)
- Candidate chunks → Embeddings
- Similarity = Cosine(Query, Chunk)
- **Strength**: Understands meaning ("disease" ≈ "pest")
- **Weakness**: Exact keywords might not matter ("wheat" = "rice" if semantically close)

**Sparse Search** (Keyword):
- Query → BM25 weights (bag of words with TF-IDF)
- Candidate chunks → BM25 weights
- Relevance = BM25(Query, Chunk)
- **Strength**: Exact keywords required ("wheat" must appear)
- **Weakness**: Doesn't understand meaning

**Hybrid** (Dense + Sparse):
```python
# Retrieve with dense
dense_results = dense_search(query_embedding, top_k=16)

# Retrieve with sparse
sparse_results = sparse_search(query_bm25, top_k=16)

# Merge using Reciprocal Rank Fusion
merged = rrf_fusion([dense_results, sparse_results])
```

**Example**: Query = "wheat prices in Gujarat"
| Chunk | Dense Score | Reason | Sparse Score | Reason |
|-------|-------------|--------|--------------|--------|
| "Mandi price: wheat 2150 Gujarat" | 0.92 | Exact match | 0.98 | All keywords |
| "Rice prices in Gujarat" | 0.75 | Similar structure | 0.45 | Missing "wheat" |
| "Wheat cultivation is expensive" | 0.70 | Contains "wheat" | 0.62 | Missing "price" |

**Ranking After RRF**: Chunk 1 wins (both dense + sparse high).

---

### 3. **Cross-Encoder Reranking**

**Problem**: Hybrid search returns 16 candidates, but maybe top 3 are mediocre.

**Solution**: Use cross-encoder to fine-tune ranking.

**Bi-Encoder vs. Cross-Encoder**:
```
BI-ENCODER (used for retrieval):
  Query → Embedding → Compare with Chunk Embeddings
  Efficient (embed chunks once, then quick dot product)
  Less accurate (ignores interaction between query and chunk)

CROSS-ENCODER (used for reranking):
  (Query, Chunk) → Score (0-1)
  Slower (compute interaction between query and chunk)
  More accurate (sees full picture)
```

**Workflow**:
```python
# Hybrid search: 16 candidates
candidates = hybrid_search(query, top_k=16)

# Cross-encoder: Score each (query, candidate) pair
for candidate in candidates:
    pair = (query, candidate['text'])
    score = cross_encoder.predict(pair)  # 0-1
    candidate['rerank_score'] = score

# Rerank by score
candidates.sort(key=lambda x: x['rerank_score'], reverse=True)

# Return top 5
return candidates[:5]
```

**Why Reranking?**
- Improves precision (top 5 are truly relevant)
- Small latency cost (~50ms for 16 candidates with GPU)
- Standard in production RAG systems

---

### 4. **LangGraph ReAct Agent**

**ReAct** = Reasoning + Acting

**Concept**: LLM alternates between thinking and calling tools.

**Agent Loop**:
```
Iteration 1:
  LLM.Reason: "User asked for wheat mandi price. I should use mandi_price_tool."
  Agent.Act: Call mandi_price_tool("wheat", state="Gujarat")
  Tool.Observe: Returns {"price": 2150, "market": "Rajkot"}

Iteration 2:
  LLM.Reason: "I got the price. Now I have enough context. I should respond."
  Agent.Act: Return final response to farmer
```

**vs. Chain-of-Thought**:
```
Chain-of-Thought: "Let me think about wheat prices... Based on my training data, prices are around 2000-2500."
(No tool call, likely hallucination if prices changed)

ReAct: "I need current prices. Let me call the tool." → Tool returns fresh data
(Factual, transparent, verifiable)
```

**LangGraph Implementation**:
```python
from langgraph.prebuilt import create_react_agent

llm = ChatMistralAI(model="mistral-large-latest")
tools = [weather_tool, mandi_price_tool, fertiliser_tool]

agent = create_react_agent(llm, tools)

# Agent automatically:
# 1. Calls LLM with tools in system prompt
# 2. Detects tool calls in LLM output
# 3. Executes tools (handles async)
# 4. Feeds results back to LLM
# 5. Repeats until LLM says "done"
```

**Max Iterations**: 6 (prevent infinite loops)

---

### 5. **Server-Sent Events (SSE) Streaming**

**Problem**: User has to wait 5 seconds for full response before seeing anything.

**Solution**: Stream response token-by-token.

**HTTP Request/Response**:
```
Client                           Server
  │                               │
  ├─── POST /chat ────────────────>│
  │                               │
  │<─── 200 OK, Content-Type: text/event-stream ───│
  │<─── data: "To\n" ─────────────│
  │<─── data: " prevent\n" ───────│
  │<─── data: " wheat\n" ─────────│
  │<─── data: " rust,\n" ─────────│
  │      ...
  │<─── event: done \n\n ─────────│
```

**Frontend**:
```javascript
const eventSource = new EventSource('/chat?query=...');

eventSource.onmessage = (event) => {
    const token = event.data;
    displayDiv.textContent += token;  // Append token
};
```

**Why SSE?**
- **User Experience**: See response appearing in real-time
- **Protocol**: Standard HTTP (works with proxies, firewalls)
- **Simple**: No websockets, no polling

---

### 6. **Vector Database (Qdrant)**

**Concept**: Database optimized for similarity search.

**Traditional Database** (SQL):
```sql
SELECT * FROM chunks WHERE source_file = 'wheat_guide.pdf';
-- Returns exact matches (WHERE conditions)
```

**Vector Database** (Qdrant):
```python
results = client.search(
    collection_name="agricultural_knowledge_v2",
    query_vector=embedding,  # 1024-dim query vector
    limit=10
)
# Returns 10 most similar chunks (by cosine distance)
```

**Internal Structure**:
```
Chunks → Embeddings → HNSW Index → Fast Retrieval

HNSW (Hierarchical Navigable Small World):
  - Approximation of KNN (K-Nearest Neighbors)
  - Fast (~1ms for 1M vectors) vs exact (~100ms)
  - Trade-off: Small accuracy loss (~1-2%)
```

**Payload** (Metadata):
```python
point = models.PointStruct(
    id=uuid.uuid4(),
    vector=chunk_embedding,
    payload={
        'text': chunk.text,
        'source_file': 'wheat_guide.pdf',
        'crop_category': 'wheat',
        'language': 'en',
        'chunk_type': 'text'
    }
)
```

**Filtering**:
```python
# Retrieve only wheat chunks
client.search(
    query_vector=embedding,
    limit=10,
    query_filter=models.HasPayloadFilter(
        key="crop_category",
        value="wheat"
    )
)
```

---

### 7. **Session Management & History**

**Problem**: Each query should remember previous context (multi-turn chat).

**Solution**: Store last 5 turns in Redis.

**Flow**:
```
User Turn 1: "What is wheat rust?"
  Agent retrieves context, generates response
  Store in Redis:
    session:abc123 = [
      {"role": "user", "content": "What is wheat rust?"},
      {"role": "assistant", "content": "Wheat rust is a fungal disease..."}
    ]

User Turn 2: "How to control it?"
  Agent retrieves history from Redis
  Augment prompt with history (full context)
  LLM can reference Turn 1: "As I mentioned, wheat rust is caused by fungus. Here's how to control it:"
```

**Why History?**
- **Context**: LLM understands conversation flow
- **Reduced Token Waste**: Don't repeat explanations
- **Natural Conversation**: Feels like talking to a person

**Limitations**:
- 5 turns = ~1000-2000 tokens (LLM token limit is 4096)
- Trade-off between history depth and new response space

---

## Interview Questions & Answer Guidance

### **Architecture & Design**

#### Q1: Why use a vector database instead of traditional SQL database for agricultural knowledge?

**Expected Answer Structure**:

1. **Problem with SQL**:
   - SQL searches by exact match (WHERE clauses)
   - "wheat rust" ≠ "pest control" even if semantically related
   - Need to index every possible keyword combination

2. **Solution with Vector DB**:
   - Query → Dense embedding (1024-dim)
   - Candidates → Dense embeddings
   - Cosine similarity finds semantically related chunks
   - One index for all queries

3. **Trade-offs**:
   - **Advantage**: Semantic search, multilingual, no schema changes
   - **Disadvantage**: Approximate (not exact), slow cold starts (model loading)

**Depth**: Explain HNSW indexing, why cosine similarity, comparison with BM25.

---

#### Q2: What is RAG and why is it better than fine-tuning for this use case?

**Expected Answer**:

1. **What is RAG**:
   - Retrieve relevant docs → Augment prompt with retrieved context → Generate response

2. **Why RAG > Fine-tuning**:
   - **Speed**: Days to fine-tune, minutes to ingest new docs
   - **Cost**: Fine-tuning expensive (GPU, data labeling), RAG just adds retrieval cost
   - **Freshness**: New mandi prices, weather data without retraining
   - **Citability**: Can point to source document

3. **Trade-off**:
   - Fine-tuning: Model "knows" facts (better for closed knowledge)
   - RAG: Model references external docs (better for open/changing knowledge)

**Depth**: When would you choose fine-tuning? (Answer: When knowledge is stable & proprietary).

---

#### Q3: Why use both dense embeddings (bge-m3) and sparse BM25 weights for retrieval?

**Expected Answer**:

1. **Dense Embeddings**:
   - Capture semantic meaning ("disease" ≈ "pest")
   - Work across languages (multilingual bge-m3)
   - **Weakness**: Miss exact keywords

2. **Sparse BM25**:
   - Match exact keywords ("wheat" must appear)
   - Work with uncommon terms (unusual crop names)
   - **Weakness**: Don't understand meaning

3. **Hybrid Strategy**:
   - Dense: Find semantically similar chunks
   - Sparse: Ensure keywords present
   - Together: Best recall + precision

**Example**:
- Query: "wheat prices in Rajkot"
- Dense alone: Returns "rice prices in Gujarat" (similar structure)
- Sparse alone: Returns nothing (exact phrase not in DB)
- Hybrid: Returns "wheat prices Rajkot" (dense + sparse both high)

---

#### Q4: How does the LangGraph ReAct agent decide when to use tools?

**Expected Answer**:

1. **Tool Integration**:
   - System prompt includes tool descriptions
   - LLM sees: "You have these tools: weather_tool, mandi_price_tool, fertiliser_tool"

2. **Decision Process**:
   - LLM thinks: "User asked about weather → need weather_tool"
   - LLM outputs special token: `<tool_call>weather_tool(location="Rajkot")</tool_call>`
   - Agent parses this, calls the tool
   - Tool returns result
   - Agent feeds result back to LLM

3. **Termination**:
   - LLM says "I have enough context, here's the response"
   - Agent stops looping, returns response

**Depth**: Explain why LLM is better than hardcoded rules for tool selection.

---

### **Data & Retrieval**

#### Q5: Explain the chunking strategies. Why 6 different strategies instead of one?

**Expected Answer**:

1. **Problem**: Different document types need different splits
   - PDF book: Natural sections/chapters
   - FAQ JSON: Question-answer pairs
   - Mandi CSV: Rows with commodity + price + market

2. **Solution**: 6 Strategies
   - **Semantic**: Sentence boundaries (flowing text)
   - **Section-based**: Detect headers (structured docs)
   - **Q&A**: {"Q": "...", "A": "..."} format
   - **Table/Record**: Narrative from CSV rows
   - **Sliding Window**: Overlap (fallback)
   - **Hybrid Auto-select**: Route to right strategy

3. **Why Not One?**
   - One strategy (e.g., sentence splitting) breaks tables & Q&As
   - Hybrid ensures each doc is chunked optimally

**Example**:
- Wheat guide PDF → Semantic (prose) + Section-based (chapters)
- FAQ JSON → Q&A chunks
- Mandi CSV → Record narrative

---

#### Q6: How does deduplication work during ingestion?

**Expected Answer**:

1. **Problem**: Re-ingesting same files creates duplicate chunks
   - Vector DB size grows
   - Retrieval returns duplicates (confuses user)

2. **Solution**: SHA-256 Hash Deduplication
   ```
   chunk_hash = SHA256(f"{text}|{source_file}|{chunk_index}")
   ```
   - Before upsert, check if hash exists in Qdrant
   - If yes, skip (already ingested)
   - If no, insert

3. **Idempotency**:
   - Run ingestion twice → same result
   - Safe to re-ingest (no duplicates created)

4. **Why SHA-256?**
   - 256-bit (negligible collision risk)
   - Deterministic (same input → same hash)
   - Fast (~microseconds)

**Depth**: When would duplicate removal fail? (Answer: If text is edited slightly).

---

#### Q7: How does the cross-encoder reranker improve precision?

**Expected Answer**:

1. **Hybrid Search Results** (top 16):
   - Mixture of highly relevant + somewhat relevant chunks
   - Ranked by dense+sparse fusion, not semantic relevance

2. **Cross-Encoder Reranking**:
   - Score each (query, chunk) pair
   - Trained on MS MARCO (500K relevance judgments)
   - Understands what "relevance" means for a query

3. **Improvement**:
   - Precision increases 15-20%
   - Example: Hybrid returns 16, reranker picks 5 best

4. **Trade-off**:
   - +50ms latency (acceptable for chat)
   - Significantly better relevance

**Depth**: Why is cross-encoder better than bi-encoder for reranking? (Answer: Sees interaction between query and document).

---

### **API & Frontend**

#### Q8: How does Server-Sent Events (SSE) streaming work in the frontend?

**Expected Answer**:

1. **Protocol**:
   - Client: `POST /chat?query=...`
   - Server: `200 OK, Content-Type: text/event-stream`
   - Server streams: `data: "To\n"`, `data: " prevent\n"`, ...
   - Client: `eventSource.onmessage = (e) => display(e.data)`

2. **Flow**:
   ```
   User types query → Send to server
   Server:
     - Retrieves context
     - Runs LLM
     - LLM returns tokens one by one
     - Send each token via SSE
   Client:
     - Receives tokens
     - Appends to message div
     - User sees response appearing live
   ```

3. **vs. Polling**:
   - Polling: Client asks "Is response ready?" every 100ms (wasteful)
   - SSE: Server pushes tokens (real-time, efficient)

4. **vs. WebSocket**:
   - WebSocket: Bidirectional (overkill for response streaming)
   - SSE: Unidirectional (simpler, standard HTTP)

---

#### Q9: Why does the frontend store session history in localStorage instead of the server?

**Expected Answer**:

1. **Advantages of localStorage**:
   - **Privacy**: User conversations stay on device
   - **Offline**: Works without internet
   - **Performance**: No server request for history
   - **Simplicity**: No session management code needed

2. **Disadvantages**:
   - **Lost on clear cache**: User loses history
   - **Single device**: History not synced across devices
   - **Limited size**: ~5 MB per domain

3. **Server Alternative**:
   - **Advantage**: Persistent, synced, backed-up
   - **Disadvantage**: Privacy concerns, costs server storage

4. **AgroSight Design Choice**:
   - localStorage for UI state (fast, private)
   - Redis for RAG context (last 5 turns, for LLM)
   - Trade-off: Accept history loss on cache clear

**Depth**: When would you switch to server-side history? (Answer: Multi-device support, analytics).

---

### **Tools & Integrations**

#### Q10: How does the fertilizer calculator work? Why hardcode nutrient requirements?

**Expected Answer**:

1. **Workflow**:
   ```
   Input: Crop, Area, Fertiliser, Nutrient
   
   Step 1: Lookup requirement (kg/hectare) from database
     - Wheat + N → 120 kg/ha
   
   Step 2: Convert area (acres → hectares)
     - 2 acres = 0.8094 ha
   
   Step 3: Calculate total nutrient needed
     - 120 × 0.8094 = 97.13 kg N
   
   Step 4: Convert to fertiliser amount
     - Urea contains 46% N
     - (97.13 × 100) / 46 = 211 kg urea
   
   Step 5: Calculate bags needed
     - 1 bag = 50 kg
     - 211 / 50 = 4.22 → 5 bags
   ```

2. **Why Hardcode Nutrients?**
   - **Accuracy**: Based on ICAR (Indian Council of Agricultural Research) standards
   - **Simplicity**: No ML model needed (deterministic)
   - **Trustworthiness**: Farmer can verify in government publications

3. **Extensibility**:
   - Add new crops by adding to `REQUIREMENTS` dict
   - Add new fertilisers by adding to `NUTRIENT_CONTENT` dict

**Depth**: What if nutrient requirements vary by soil, rainfall? (Answer: Could enhance with soil testing data).

---

#### Q11: How does the weather tool work? Why retry on API failure?

**Expected Answer**:

1. **Workflow**:
   ```python
   @retry(stop=stop_after_attempt(3), wait=wait_exponential())
   async def get_weather_advisory(location):
       # Call OpenWeatherMap API
       # On failure: Wait 1s, retry
       # On failure: Wait 2s, retry
       # On failure: Wait 4s, retry
       # If all fail: Return error message
   ```

2. **Why Retry?**
   - APIs occasionally timeout (network blip)
   - Exponential backoff (don't hammer server)
   - 3 attempts = 99% success rate

3. **Advisory Generation**:
   - Rule-based (not ML)
   - If humidity < 40% AND temp > 35°C: "Irrigate early morning"
   - If wind > 40 km/h: "Don't spray pesticides"
   - **Advantage**: Transparent, farmer understands advice

4. **Fallback**:
   - If API unavailable: Return error with explanation
   - User can manually check weather app

**Depth**: Why exponential backoff instead of linear? (Answer: Prevents server overload).

---

#### Q12: How is the mandi price tool connected to government APIs?

**Expected Answer**:

1. **Data Source**: data.gov.in
   - Official Indian government portal
   - Resource: Agricultural commodity prices
   - Updated daily by data.gov.in

2. **Integration**:
   ```python
   url = f"{settings.data_gov_base_url}/resource/{settings.data_gov_mandi_resource_id}"
   params = {
       "api-key": settings.data_gov_api_key_1,
       "filters": [("commodity", "wheat"), ("state", "Gujarat")]
   }
   response = client.get(url, params=params)
   records = response.json()["records"]
   latest_price = records[0]["price"]  # Most recent
   ```

3. **Fallback**:
   - If API down: Read from cached CSV (mandi_prices_2026-04-29.csv)
   - Less fresh, but still functional

4. **User Benefit**:
   - Real-time prices (not estimated)
   - Farmer can make selling decisions confidently

**Depth**: How often should prices be cached/refreshed? (Answer: Daily, aligned with mandi closing times).

---

### **Production & Deployment**

#### Q13: How is the application containerized? Why multi-stage Docker?

**Expected Answer**:

1. **Single-Stage Dockerfile**:
   ```dockerfile
   FROM python:3.11
   RUN apt-get install gcc, build-essential, ...
   RUN pip install -r requirements.txt
   COPY app .
   CMD ["uvicorn", "app.main:app"]
   ```
   - Image size: ~3 GB (includes build tools)

2. **Multi-Stage Dockerfile**:
   - **Stage 1 (Builder)**: Install heavy deps, build wheels
   - **Stage 2 (Runtime)**: Copy only wheels, skip build tools
   - Image size: ~800 MB

3. **Multi-Stage Workflow**:
   ```dockerfile
   FROM python:3.11-slim AS builder
   RUN apt-get install build-essential, ...
   RUN pip install --prefix=/install -r requirements.txt
   
   FROM python:3.11-slim AS runtime
   COPY --from=builder /install /usr/local
   COPY app .
   CMD ["uvicorn", ...]
   ```

4. **Benefits**:
   - **Speed**: Smaller images deploy faster
   - **Security**: No build tools in production (smaller attack surface)
   - **Cost**: Smaller images → cheaper storage & transfer

**Depth**: What's included in the runtime image? (Answer: Python 3.11-slim + tesseract OCR + poppler utils).

---

#### Q14: How does the lifespan event improve startup performance?

**Expected Answer**:

1. **Problem**:
   - Models are heavy (bge-m3: 2 GB, cross-encoder: 400 MB)
   - If loaded per-request: 2-3 second delay for first request
   - Affects user experience (cold start)

2. **Solution: Lifespan Events**:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup: Preload models in parallel
       await asyncio.gather(
           embedder.preload_models(),      # 3 sec
           reranker.preload_models(),      # 2 sec
           get_client()                    # 1 sec
       )
       # Total: ~3 sec (parallel, not sequential 6 sec)
       yield
       # Cleanup (if needed)
   ```

3. **How It Works**:
   - FastAPI calls `lifespan()` on startup
   - Models loaded before first request
   - `yield` keeps server running
   - Cleanup code runs on shutdown

4. **Impact**:
   - First request: < 100ms (models already in memory)
   - vs. Without: 2-3 seconds (model loading)

**Depth**: How do you measure startup time? (Answer: `time docker run ...` or Kubernetes readiness probes).

---

#### Q15: How is session management handled for concurrent users?

**Expected Answer**:

1. **Session ID**:
   - User gets unique `session_id` (UUID or random string)
   - Stored in browser localStorage
   - Sent with every request

2. **Redis Storage**:
   ```python
   # User A (session_abc123)
   redis.setex("session:abc123", 86400, json.dumps([...]))  # 24h TTL
   
   # User B (session_def456)
   redis.setex("session:def456", 86400, json.dumps([...]))  # 24h TTL
   ```

3. **Concurrency**:
   - Multiple users → Multiple session_ids
   - Redis handles concurrent reads/writes (atomic)
   - No data leakage (each user's data isolated)

4. **Isolation**:
   ```python
   # User A's history (private)
   append_turn("session:abc123", "user", "What is wheat?")
   
   # User B's history (private)
   append_turn("session:def456", "user", "How to grow rice?")
   
   # No mixing of conversations
   ```

5. **Cleanup**:
   - TTL = 24h: Session auto-expires
   - Can also DELETE /session/{id} manually

**Depth**: What if Redis goes down? (Answer: Falls back to in-memory store, loses on restart).

---

### **Multilingual Support**

#### Q16: How does AgroSight handle Hindi and Gujarati?

**Expected Answer**:

1. **Language Detection**:
   ```python
   import re
   _HINDI_RANGE = re.compile(r'[\u0900-\u097F]')
   _GUJARATI_RANGE = re.compile(r'[\u0A80-\u0AFF]')
   
   def detect_language(text: str) -> str:
       if _HINDI_RANGE.search(text):
           return "hi"
       if _GUJARATI_RANGE.search(text):
           return "gu"
       return "en"
   ```
   - Hindi: Unicode Devanagari (U+0900-U+097F)
   - Gujarati: Unicode Gujarati (U+0A80-U+0AFF)

2. **Why Unicode Ranges?**
   - No language detection model needed (fast)
   - Deterministic (same script = same language)
   - Handles mixed scripts (Hindi + English)

3. **Embeddings**:
   - BAAI/bge-m3: Trained on 111 languages
   - Natively supports Hindi, Gujarati
   - No translation needed

4. **Response Format**:
   - Detect user's query language
   - Respond in same language
   - Prompt template specifies target language

5. **Challenges**:
   ```
   Problem: "सिंचाई" (irrigation) is broken as "स िंचाई"
   Cause: Careless string splitting (splits Unicode combining characters)
   Solution: Use Unicode-aware text processing, test with Hindi/Gujarati text
   ```

**Depth**: How would you add a 4th language (Tamil)? (Answer: Add Unicode range, train embeddings if not already).

---

### **Error Handling & Reliability**

#### Q17: How does the system handle API failures gracefully?

**Expected Answer**:

1. **OpenWeatherMap API Down**:
   - Retry logic with exponential backoff
   - If all retries fail: Return error message
   - User informed: "Weather data unavailable. Please check weather.com"

2. **Qdrant Down**:
   - FastAPI startup fails (lifespan fails)
   - Container health check fails
   - Kubernetes restarts container
   - Try again when Qdrant is up

3. **Redis Down**:
   - Session store falls back to in-memory dict
   - Feature still works (history kept in memory)
   - On server restart: History lost (acceptable)

4. **Embedding Model Load Failure**:
   - Try bge-m3 (preferred)
   - Fallback to all-MiniLM-L6-v2 (smaller, English only)
   - Log warning: "bge-m3 unavailable, using MiniLM"

5. **LLM API Timeout**:
   - Timeout = 30 seconds
   - Return partial response + error message
   - Log: "LLM timeout after 30s"

**Depth**: How would you add circuit breakers? (Answer: Use `pybreaker` library to auto-disable flaky APIs).

---

#### Q18: How does logging help in production debugging?

**Expected Answer**:

1. **Log Levels**:
   - **DEBUG**: Detailed info (embedding vectors, retrieval scores)
   - **INFO**: Important events ("Qdrant collection created", "Session 123 deleted")
   - **WARNING**: Potential issues ("API timeout, using fallback")
   - **ERROR**: Failures ("Chunking failed for file.pdf")

2. **Log Output**:
   - **Stdout**: Colorized (dev environment)
   - **File** (logs/agrosight.log): Structured, rotated (production)

3. **Example Debug Scenario**:
   ```
   Farmer reports: "System returns irrelevant results"
   Engineer enables DEBUG logging, re-runs query:
   
   2026-05-06 14:23:45 | INFO     | Encoding query: "wheat disease"
   2026-05-06 14:23:46 | DEBUG    | Query embedding: [0.12, -0.05, ..., 0.44]
   2026-05-06 14:23:46 | DEBUG    | Retrieved 16 candidates with scores: [0.89, 0.85, 0.78, ...]
   2026-05-06 14:23:46 | DEBUG    | After reranking: [0.92, 0.50, 0.45, ...]
   2026-05-06 14:23:47 | INFO     | Response generated
   
   Engineer sees: Cross-encoder reranked incorrectly (chunk 2 & 3 too low)
   → Investigate cross-encoder model or reranking logic
   ```

4. **Log Rotation**:
   - Rotate at 50 MB
   - Keep 30 days of logs
   - Compress to .gz (save storage)

**Depth**: How would you centralize logs from multiple servers? (Answer: Use ELK stack or cloud logging services).

---

### **Performance & Optimization**

#### Q19: What are the bottlenecks in the RAG pipeline?

**Expected Answer**:

1. **Profiling the Pipeline**:
   ```
   Query received
   ├─ Encode query (bge-m3): 100ms
   ├─ Retrieve from Qdrant: 50ms
   ├─ Rerank with cross-encoder: 50ms
   ├─ Format context & history: 10ms
   └─ Run LLM: 3000ms ← BOTTLENECK
       └─ Tool calls: 500ms (weather API, etc.)
   
   Total: ~3700ms
   ```

2. **Bottleneck Analysis**:
   - **LLM generation**: Accounts for 80% of latency
   - **Tool calls**: 13% (external APIs)
   - **Retrieval & reranking**: 6%

3. **Optimization Options**:
   - **Use faster LLM**: Mistral vs. GPT-4 (already done)
   - **Smaller LLM**: qwen3.5:9b locally (lower quality)
   - **Parallel tool calls**: If multiple tools needed, call in parallel
   - **Cache results**: Common queries (mandi prices don't change hourly)

4. **Acceptable Latency**:
   - < 100ms: Instant (feel instant)
   - < 1s: Fast (user doesn't notice delay)
   - < 5s: Acceptable (user waits patiently)
   - > 5s: Slow (user frustrated)
   
   AgroSight: ~3-4s (acceptable, can be improved to <2s with caching).

**Depth**: How would you measure latency in production? (Answer: APM tools like New Relic, Datadog).

---

#### Q20: How can you scale AgroSight to 10,000 concurrent users?

**Expected Answer**:

1. **Current Bottleneck**: Single server
   - 1 FastAPI instance = ~10-20 concurrent requests (depends on hardware)
   - 10K users = need ~500-1000 server instances (unrealistic)

2. **Horizontal Scaling**:
   ```
   Load Balancer (nginx, AWS ALB)
   ├─ FastAPI instance 1 (port 8001)
   ├─ FastAPI instance 2 (port 8002)
   └─ FastAPI instance 3 (port 8003)
   
   + Redis (shared session store)
   + Qdrant (shared vector DB)
   ```
   - Requests round-robin across instances
   - Session data shared (no duplication)

3. **Scaling Components**:
   - **FastAPI**: Stateless (easy to scale)
   - **Qdrant**: Cloud service (scales automatically) or cluster
   - **Redis**: Cloud service (AWS ElastiCache) or cluster
   - **Models** (embedder, reranker): Shared GPU server (inference scaling)

4. **GPU Scaling**:
   - Embedding & reranking run on GPU (expensive)
   - Option A: Share GPU across instances (vLLM/Ray Serve)
   - Option B: CPU-only inference (slower but cheaper)

5. **Estimated Infrastructure**:
   ```
   For 10K users (peak):
   - 100 FastAPI instances (CPU-only)
   - 5 GPU inference servers (embedder + reranker)
   - Qdrant Cloud (multi-node cluster)
   - Redis Cloud (high availability)
   - Cost: ~$5-10K/month
   ```

**Depth**: How would you handle geographic distribution? (Answer: CDN for static assets, edge inference for latency).

---

## Bonus: Advanced Concepts

### **Concept: Async/Await Mechanism**

**What is Async/Await?**

Asynchronous programming allows your code to do multiple things "at the same time" without blocking.

**Traditional Synchronous Code**:
```python
def fetch_weather(location):
    # This blocks until response comes back (~200ms)
    response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}")
    return response.json()

def process_query(query):
    print("Fetching weather...")
    weather = fetch_weather("Rajkot")      # Waits 200ms ⏳
    print("Processing results...")
    result = search_qdrant(query)           # Waits 50ms ⏳
    return f"{result} + {weather}"

# Timeline (synchronous):
# 0ms:    Start
# 200ms:  Weather API returns
# 250ms:  Qdrant returns
# 250ms:  End
# Total: 250ms (sequential)
```

**Asynchronous Code (Async/Await)**:
```python
async def fetch_weather_async(location):
    # This releases control while waiting (~200ms)
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}")
    return response.json()

async def process_query_async(query):
    print("Fetching weather and searching...")
    
    # Both tasks run concurrently (not sequentially!)
    weather_task = fetch_weather_async("Rajkot")
    search_task = search_qdrant_async(query)
    
    weather, result = await asyncio.gather(weather_task, search_task)
    return f"{result} + {weather}"

# Timeline (asynchronous):
# 0ms:    Both tasks start
# 0-50ms: While weather API is responding, Qdrant search runs
# 200ms:  Weather API returns
# 200ms:  Both results ready
# Total: 200ms (concurrent, not 250ms!)
```

**Key Concepts**:

1. **`async def`** – Declares an asynchronous function
   - Can use `await` inside
   - Returns a coroutine (not result immediately)

2. **`await`** – Pauses execution until result is ready
   - While waiting, other tasks can run
   - Like yielding control to event loop

3. **Event Loop** – Central scheduler
   ```
   While there are pending tasks:
     1. Check task A: Is it ready? Yes → run it
     2. Check task B: Is it ready? No → skip
     3. Check task C: Is it ready? Yes → run it
     4. Wait for I/O (network, disk)     4. Wait for I/O (network, disk)
                                                                      
     5. Go back to step 1
   ```

4. **`asyncio.gather()`** – Run multiple tasks concurrently
   ```python
   results = await asyncio.gather(
       fetch_weather("Rajkot"),      # Starts immediately
       fetch_mandi_price("wheat"),   # Starts immediately (doesn't wait for weather)
       search_qdrant(query)          # Starts immediately
   )
   # All 3 run "at the same time" (interleaved)
   # Returns when all finish
   ```

**AgroSight Usage Examples**:

1. **Concurrent Tool Calls** (agent.py):
```python
async def stream_agent(query, session_id):
    # All 3 tools can run concurrently if agent calls them
    weather = await weather_tool("Rajkot")
    price = await mandi_price_tool("wheat", state="Gujarat")
    dose = await fertiliser_tool("wheat", area_acres=2)
    
    # If agent calls all 3 tools:
    # Sequential: 200ms + 300ms + 100ms = 600ms
    # Concurrent: max(200, 300, 100) = 300ms
```

2. **Batch Encoding** (embedder.py):
```python
async def encode_texts_async(texts: list[str]):
    # Load model once (fast, synchronous)
    model = _load_model()
    
    # But in HTTP server context:
    # Multiple requests happen concurrently
    # Request 1: Encoding "wheat" (100ms)
    # Request 2: Encoding "rice" (100ms, runs while Request 1 waits for I/O)
    # Total: 100ms per request (not 200ms!)
```

3. **FastAPI Handlers** (main.py):
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    # FastAPI can handle 1000+ concurrent users
    # Each request is an async coroutine
    # While one waits for LLM response, others can run
    
    context = await retrieve_context(query)     # Network I/O
    history = await get_history(session_id)     # Redis I/O
    response = await stream_agent(query)        # LLM call
    
    return response
```

**Why Async/Await for AgroSight?**

| Scenario | Sync | Async |
|----------|------|-------|
| 1 user asks query | 5s | 5s (same) |
| 10 users ask queries | 50s (each waits for previous) | 5s (all concurrent) |
| Tool calls (weather + price + fertilizer) | 600ms (sequential) | 300ms (concurrent) |

**Latency Improvement**:
```
Without async: 1 request = 200ms → 10 requests = 2000ms (blocked)
With async:    1 request = 200ms → 10 requests = 200ms (concurrent)
               10x improvement in throughput!
```

**Common Pitfalls**:

1. **Forgetting `await`**:
```python
# ❌ WRONG: Task not executed, just created
result = fetch_weather("Rajkot")  # Returns coroutine, doesn't run

# ✅ CORRECT: Task executed and waits for result
result = await fetch_weather("Rajkot")
```

2. **Mixing Sync & Async**:
```python
# ❌ WRONG: Sync function blocks event loop
async def process():
    time.sleep(5)  # Blocks everything!
    return "done"

# ✅ CORRECT: Use async equivalents
async def process():
    await asyncio.sleep(5)  # Non-blocking
    return "done"
```

3. **Not Using `gather()` for Concurrency**:
```python
# ❌ SLOW: Sequential (600ms)
weather = await fetch_weather("Rajkot")
price = await mandi_price("wheat")
dose = await fertiliser_dose("wheat")

# ✅ FAST: Concurrent (300ms)
weather, price, dose = await asyncio.gather(
    fetch_weather("Rajkot"),
    mandi_price("wheat"),
    fertiliser_dose("wheat")
)
```

**In AgroSight Context**:

The system can handle 10K+ concurrent users because:
1. FastAPI is async-native (uvicorn + asyncio)
2. Each request doesn't block others (concurrent execution)
3. I/O operations (network, Redis, Qdrant) are non-blocking
4. Tool calls run concurrently via `asyncio.gather()`

**Single Server Capacity**:
```
Sync (blocking): 10 concurrent requests max (limited by threads)
Async: 1000+ concurrent requests (limited by event loop overhead)

Cost: Async is harder to debug but massive throughput gain.
```

---

### **Concept: httpx.AsyncClient Pattern**

**What is httpx?**

`httpx` is an async-friendly HTTP client library (like `requests` but for async code).

**Why httpx Over requests?**

```python
# ❌ BLOCKING (synchronous):
import requests
resp = requests.get("https://api.openweathermap.org/data/2.5/weather?q=Rajkot")
# Blocks for 200ms — nothing else happens!

# ✅ NON-BLOCKING (asynchronous):
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.openweathermap.org/data/2.5/weather?q=Rajkot")
# Awaits 200ms — other tasks can run meanwhile!
```

**Anatomy of `async with httpx.AsyncClient`**:

```python
async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
    #  ↑          ↑                  ↑
    #  |          |                  |
    # async with  Client creation    Context manager variable
    #
    # Steps:
    # 1. Create AsyncClient (open connection pool)
    # 2. Assign to 'client' variable
    # 3. Run code block
    # 4. Auto-close connection (even if error occurs)
    
    resp = await client.get(url, params=params)
    # ↑ Makes HTTP request, awaits response
    # While waiting, event loop handles other requests!
    
    data = resp.json()
    # Parse response JSON
    
    return data
    
# Auto-cleanup happens here (connection closed)
```

**Context Manager (`async with`) Benefits**:

```python
# ❌ MANUAL (you must remember to close):
client = httpx.AsyncClient()
try:
    resp = await client.get(url)
    data = resp.json()
except Exception as e:
    logger.error(e)
finally:
    await client.aclose()  # Easy to forget!

# ✅ AUTOMATIC (always closes):
async with httpx.AsyncClient() as client:
    resp = await client.get(url)
    data = resp.json()
# Auto-closes, even if error occurs above!
```

**Parameters Explained**:

```python
async with httpx.AsyncClient(
    timeout=30,                      # Seconds to wait for response
    follow_redirects=True,           # Follow 301/302/307 redirects
    http2=True,                      # Use HTTP/2 if available
    limits=httpx.Limits(              # Connection pool limits
        max_connections=100,         # Max concurrent connections
        max_keepalive_connections=20 # Reuse connections
    )
) as client:
    resp = await client.get(url)
```

**Real AgroSight Example**:

```python
async def get_weather_advisory(location: str) -> dict[str, Any]:
    """Fetch weather from OpenWeatherMap API."""
    
    url = f"{settings.openweather_base_url}/weather"
    params = {
        "appid": settings.openweather_api_key,
        "q": location,
        "units": "metric"
    }
    
    try:
        # Create async HTTP client with 30-second timeout
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            # Make GET request to OpenWeatherMap
            resp = await client.get(url, params=params)
            
            # If server doesn't respond in 30 seconds:
            #   → httpx raises TimeoutError
            #   → Caught below, returns error dict
            
            # If HTTP error (404, 500, etc.):
            #   → resp.raise_for_status() raises HTTPStatusError
            #   → Caught below, returns error dict
            
            resp.raise_for_status()
            data = resp.json()
    
    except httpx.TimeoutException:
        # Server too slow (> 30 seconds)
        logger.error(f"Weather API timeout for {location}")
        return {
            "error": "API timeout",
            "location": location,
            "status": "unavailable"
        }
    
    except httpx.HTTPStatusError as exc:
        # HTTP error: 404 (not found), 401 (unauthorized), 500 (server error)
        logger.error(f"Weather API error: {exc.response.status_code}")
        return {
            "error": f"API error (HTTP {exc.response.status_code})",
            "status": "api_error"
        }
    
    except Exception as exc:
        # Other errors: network issues, SSL errors, etc.
        logger.error(f"Failed to fetch weather: {exc}")
        return {
            "error": "Network error",
            "status": "unavailable"
        }
    
    # Success: Extract data
    return {
        "temperature_c": data["main"]["temp"],
        "humidity_pct": data["main"]["humidity"],
        "condition": data["weather"][0]["description"],
        "source": "OpenWeatherMap (Real-time)"
    }
```

**Concurrent Requests Example**:

```python
async def fetch_multiple_prices(commodities: list[str]):
    """Fetch prices for multiple commodities CONCURRENTLY."""
    
    # Create ONE client (reuse connections for efficiency)
    async with httpx.AsyncClient(timeout=30) as client:
        
        # Create coroutines for each commodity (don't await yet)
        tasks = [
            _fetch_commodity_price(client, commodity)
            for commodity in commodities
        ]
        
        # Run all tasks concurrently (NOT sequentially)
        prices = await asyncio.gather(*tasks)
        
        return prices

async def _fetch_commodity_price(client: httpx.AsyncClient, commodity: str):
    """Helper: fetch price for one commodity."""
    resp = await client.get(
        "https://api.data.gov.in/resource/...",
        params={"commodity": commodity}
    )
    resp.raise_for_status()
    return resp.json()

# Timeline:
# With 3 commodities (wheat, rice, cotton):
# 
# Sequential (wrong):
#   wheat:  0-200ms (waiting)
#   rice:   200-400ms (waiting)
#   cotton: 400-600ms (waiting)
#   Total: 600ms
#
# Concurrent (right):
#   wheat:  0-200ms (waiting)
#   rice:   0-200ms (waiting, overlapped!)
#   cotton: 0-200ms (waiting, overlapped!)
#   Total: 200ms (3x faster!)
```

---

### **Concept: Error Handling (Try/Except) in Async Code**

**Error Handling Pyramid** (most specific → most general):

```python
async def get_mandi_price(commodity: str, market: str) -> dict:
    """Fetch mandi price with comprehensive error handling."""
    
    try:
        # Try primary source: data.gov.in API
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.data.gov.in/resource/...",
                params={"commodity": commodity, "market": market}
            )
            
            # Level 1: HTTP errors (4xx, 5xx)
            resp.raise_for_status()
            # If HTTP error (404, 500, etc.) → raises HTTPStatusError
            
            data = resp.json()
            # If JSON invalid → raises json.JSONDecodeError
            
            return {
                "commodity": commodity,
                "price": data["modal_price"],
                "source": "data.gov.in"
            }
    
    # Level 1: Specific HTTP errors
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        
        if status_code == 401:
            logger.error("API key invalid or expired")
            return {"error": "Authentication failed", "status": "auth_error"}
        
        elif status_code == 404:
            logger.error(f"No price data for {commodity}/{market}")
            return {"error": "Commodity not found", "status": "not_found"}
        
        elif status_code == 429:
            logger.warning("API rate limit exceeded")
            return {"error": "Too many requests, try later", "status": "rate_limited"}
        
        elif status_code >= 500:
            logger.error(f"API server error: {status_code}")
            return {"error": "API server error", "status": "server_error"}
    
    # Level 2: Network/timeout errors
    except httpx.TimeoutException:
        logger.error(f"API timeout for {commodity}")
        return {"error": "Request timeout", "status": "timeout"}
    
    except httpx.NetworkError as exc:
        logger.error(f"Network error: {exc}")
        return {"error": "Network unreachable", "status": "network_error"}
    
    # Level 3: JSON parsing errors
    except ValueError as exc:
        logger.error(f"Invalid JSON response: {exc}")
        return {"error": "Invalid response format", "status": "parse_error"}
    
    # Level 4: Catch-all (unknown errors)
    except Exception as exc:
        logger.error(f"Unexpected error: {type(exc).__name__}: {exc}")
        return {"error": "Unexpected error occurred", "status": "unknown_error"}
    
    # No finally needed here (context manager auto-closes)
```

**Error Hierarchy in AgroSight**:

```
Exception (base)
├─ httpx.RequestError (network issues)
│  ├─ httpx.TimeoutException      → "API timeout"
│  ├─ httpx.NetworkError          → "Network unreachable"
│  └─ httpx.ProxyError            → "Proxy error"
├─ httpx.HTTPStatusError           → "HTTP 4xx/5xx errors"
│  ├─ 401 Unauthorized             → "Invalid API key"
│  ├─ 404 Not Found                → "Resource not found"
│  ├─ 429 Too Many Requests        → "Rate limited"
│  └─ 5xx Server Errors            → "Server error"
├─ ValueError (JSON decode)        → "Invalid response"
└─ Exception (everything else)     → "Unknown error"
```

**Real AgroSight Example** (from agro_tools.py):

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def get_weather_advisory(location: str) -> dict[str, Any]:
    """
    Fetch weather with retry logic + error handling.
    @retry decorator automatically retries on exceptions.
    """
    if not settings.openweather_api_key:
        # Level 0: Configuration error
        error_msg = "OpenWeatherMap API key not configured"
        logger.error(error_msg)
        return {"error": error_msg, "status": "unavailable"}
    
    url = f"{settings.openweather_base_url}/weather"
    params = {
        "appid": settings.openweather_api_key,
        "q": location,
        "units": "metric"
    }
    
    try:
        # Try to fetch weather
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(url, params=params)
            
            # Raises HTTPStatusError if 4xx/5xx
            resp.raise_for_status()
            data = resp.json()
    
    # Level 1: HTTP errors (4xx/5xx)
    except httpx.HTTPStatusError as exc:
        error_msg = f"OpenWeatherMap API error (HTTP {exc.response.status_code}): {exc.response.text}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "api_error"
        }
    
    # Level 2: Network/timeout errors
    except Exception as exc:
        error_msg = f"Failed to fetch weather for {location}: {exc}"
        logger.error(error_msg)
        # @retry decorator will retry (max 3 attempts)
        raise  # Re-raise so @retry can catch and retry
    
    # Success path
    temp_c = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    wind_kmh = data["wind"]["speed"] * 3.6
    condition = data["weather"][0]["description"]
    
    advisory = _generate_advisory(temp_c, humidity, wind_kmh, condition)
    
    return {
        "location": data.get("name", location),
        "temperature_c": temp_c,
        "humidity_pct": humidity,
        "wind_kmh": wind_kmh,
        "condition": condition,
        "advisory": advisory,
        "source": "OpenWeatherMap (Real-time)"
    }
```

**Error Handling with Retry Decorator** (`@retry`):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),  # Max 3 attempts
    wait=wait_exponential(       # Exponential backoff
        multiplier=1,            # Base multiplier
        min=1,                   # Min wait = 1 second
        max=8                    # Max wait = 8 seconds
    )
)
async def get_weather_advisory(location: str):
    """Automatically retries on failure."""
    
    # Attempt 1: Fails (network timeout)
    #   Wait 1 second
    # Attempt 2: Fails (API error)
    #   Wait 2 seconds
    # Attempt 3: Succeeds!
    #   Return result
    
    # If all 3 fail: Raise exception (caller handles)
```

**Graceful Degradation Example**:

```python
async def get_mandi_price(commodity: str, market: str, state: str):
    """Try multiple data sources, degrade gracefully."""
    
    # Try primary source
    try:
        return await _fetch_from_data_gov_in(commodity, market, state)
    except Exception as exc:
        logger.warning(f"data.gov.in failed: {exc}")
    
    # Try secondary source
    try:
        return await _fetch_from_agmarknet(commodity, market, state)
    except Exception as exc:
        logger.warning(f"agmarknet.gov.in failed: {exc}")
    
    # Try cached CSV (stale but functional)
    try:
        return _get_price_from_cached_csv(commodity, market, state)
    except Exception as exc:
        logger.error(f"All sources exhausted: {exc}")
    
    # If everything fails: Return error to user
    return {
        "error": f"Unable to fetch price for {commodity}",
        "status": "unavailable",
        "all_sources_failed": True
    }
```

**Error Handling in FastAPI Endpoints**:

```python
@app.post("/chat")
async def chat(request: ChatRequest):
    """HTTP endpoint with error handling."""
    session_id = request.session_id
    query = request.query
    
    try:
        # Step 1: Retrieve context (might fail)
        context = await retrieve_context(query)
        
        # Step 2: Get session history (might fail)
        history = await get_history(session_id)
        
        # Step 3: Run agent (might fail)
        response = await stream_agent(query, history)
        
        # Step 4: Store turn in history (might fail)
        await append_turn(session_id, "user", query)
        await append_turn(session_id, "assistant", response)
        
        return {"response": response}
    
    except ValueError as exc:
        # Bad input (e.g., session_id invalid)
        logger.warning(f"Bad request: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    
    except TimeoutError as exc:
        # Request took too long
        logger.error(f"Request timeout: {exc}")
        raise HTTPException(status_code=504, detail="Gateway Timeout")
    
    except Exception as exc:
        # Unexpected error
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
```

**Best Practices**:

| Practice | Why |
|----------|-----|
| **Specific exceptions first** | Catch exact errors, not blanket `Exception` |
| **Log with context** | Include variable values in error messages |
| **Don't silently fail** | Always return error status/message to user |
| **Distinguish user errors** | 400 (bad input) vs 500 (server error) |
| **Retry transient errors** | Use `@retry` for network/timeout issues |
| **Fallback gracefully** | data.gov.in down? Try CSV backup |
| **Monitor errors** | Log errors for debugging in production |

---

### **Concept: Reciprocal Rank Fusion (RRF)**

Problem: How to merge dense search (ranked 1,2,3) and sparse search (ranked 3,1,2) fairly?

**RRF Formula**:
```
RRF_score(doc) = 1 / (k + rank_dense) + 1 / (k + rank_sparse)
```
where `k=60` (typical value).

**Example**:
```
Dense ranking:  [A, B, C] (scores: 0.9, 0.8, 0.7)
Sparse ranking: [C, A, B] (scores: 0.95, 0.85, 0.75)

RRF scores:
  A: 1/(60+1) + 1/(60+1) = 0.0164 + 0.0164 = 0.0329
  B: 1/(60+2) + 1/(60+3) = 0.0159 + 0.0156 = 0.0315
  C: 1/(60+3) + 1/(60+1) = 0.0156 + 0.0164 = 0.0320

Merged ranking: [A, C, B]
```

**Why RRF?**
- No need to weight dense vs. sparse (equal importance)
- Simple, interpretable
- Works with any ranking algorithms

---

### **Concept: Lazy Singleton Pattern**

Problem: Loading models is expensive (2-3 seconds). Don't want to load multiple times.

**Pattern**:
```python
_model = None
_model_name = ""

def _load_model(model_name: str):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model  # Reuse cached
    
    # Load fresh
    _model = BGEM3FlagModel(model_name)
    _model_name = model_name
    return _model
```

**Why Not a Class?**
- Module-level singleton simpler than class-based
- Only one instance per process (Python GIL)
- Thread-safe (GIL protects object references)

---

### **Concept: Exponential Backoff Retry**

Problem: API timeouts happen. Retrying immediately often fails again.

**Solution**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8)
)
async def fetch_api():
    # Call API
```

**Timeline**:
```
Attempt 1: Fail immediately
Wait 1 second
Attempt 2: Fail
Wait 2 seconds (exponential: 2^1)
Attempt 3: Fail
Wait 4 seconds (exponential: 2^2)
Attempt 4 (not tried): Would wait 8 seconds (capped at max=8)

All failed: Raise exception
```

**Why Exponential?**
- Prevents hammering server (gives time to recover)
- Common in distributed systems
- Standard practice (HTTP 429, 503 responses recommend this)

---

## Summary: Key Takeaways

1. **RAG Architecture**: Retrieval + Augmentation + Generation for factual, citable responses
2. **Hybrid Search**: Dense (semantic) + Sparse (keyword) for best recall
3. **Reranking**: Cross-encoder improves precision, small latency cost
4. **Multilinguality**: Unicode ranges for language detection, bge-m3 for embeddings
5. **Tools**: LangGraph agents decide when to call weather, prices, fertilizer tools
6. **Streaming**: SSE for real-time response display
7. **Session Management**: Redis for multi-turn conversation context
8. **Reliability**: Fallbacks (in-memory if Redis down, CSV if API down)
9. **Production Ready**: Docker, logging, monitoring, horizontal scaling capability
10. **Performance**: Lazy loading, parallel startup, profile before optimizing

---

**Document Created**: May 6, 2026  
**Version**: 1.0 (Advanced Technical Interview Guide)

For updates or clarifications, refer to individual file documentation or reach out to the development team.
