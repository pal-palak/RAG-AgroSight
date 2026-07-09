# AgroSight Interview Guide

## Project Positioning

AgroSight is a production-style agricultural RAG assistant built for Indian farmers. It combines a FastAPI backend, a browser-based chat UI, retrieval from a Qdrant vector database, a LangGraph ReAct agent, live tool calling for weather and mandi prices, multilingual prompting, and session-based chat history.

You can think of it as a domain-focused AI system with three major strengths:

- It answers agricultural questions using both retrieved project knowledge and LLM reasoning.
- It can call live tools when the answer depends on current data like weather or market price.
- It supports multi-turn conversations by separating chat sessions using `session_id`.

Important interview note:

- Some older repo docs mention Ollama and `qwen3.5:9b`.
- The current implementation in code uses `ChatMistralAI` with LangGraph and Mistral API settings.
- In an interview, always say: "The current code uses Mistral through LangGraph, but some architecture docs appear to reflect an earlier design stage."

---

## 1. Executive Project Summary

### Problem Statement

Farmers often need answers that are:

- domain-specific,
- easy to understand,
- sometimes based on current data,
- and available in more than one language.

A general chatbot may hallucinate, may not know local agricultural context, and may not fetch live weather or mandi price data when freshness matters. AgroSight solves that by combining retrieval, tool calling, and session-aware chat.

### Target Users

- Indian farmers
- agricultural advisors
- agri-support teams
- developers building agriculture-focused AI products

### Major Capabilities

- crop advisory
- pest and disease guidance
- fertilizer quantity estimation
- government scheme help
- mandi price lookup
- weather advisory
- multilingual response control
- multi-turn chat with session history

### One-Line Interview Answer

"AgroSight is an agricultural RAG assistant that uses FastAPI, Qdrant, `bge-m3` embeddings, reranking, and a LangGraph ReAct agent with live tools to give grounded farmer-focused answers in a session-based chat interface."

### One-Paragraph Interview Answer

AgroSight is a domain-specific AI assistant for agriculture. A user asks a question from the web UI, the backend retrieves relevant knowledge from Qdrant using hybrid dense and sparse retrieval, reranks the results, builds a prompt with conversation history, and sends it to a LangGraph ReAct agent powered by Mistral. If the query needs live weather, mandi prices, or fertilizer calculation, the agent calls dedicated tools. The answer is streamed back to the browser using SSE, and the session history is stored using Redis or an in-memory fallback.

---

## 2. Technology Stack and Why It Is Used

### FastAPI

What it does:

- Provides the API layer for chat, search, health, and session clearing.

Why it fits:

- FastAPI is strong for async Python backends, validation, and auto-generated docs.

How it works here:

- `app/main.py` defines `GET /health`, `POST /search`, `POST /chat`, and `DELETE /session/{session_id}`.
- It also serves static frontend files.

Why this instead of simpler alternatives:

- Compared to Flask, FastAPI gives cleaner request models, better async support, and built-in OpenAPI docs.

### SSE (Server-Sent Events)

What it does:

- Streams the model output token-by-token from backend to frontend.

Why it fits:

- Chat responses need progressive display, but the communication pattern is mostly server-to-client streaming.

How it works here:

- `POST /chat` returns `EventSourceResponse` when `stream=True`.
- Events used are `session`, `token`, and `done`.

Why this instead of WebSockets:

- SSE is simpler when only the server needs to push streamed text.
- It reduces complexity compared to full-duplex WebSocket infrastructure.

### Pydantic

What it does:

- Validates request and response schemas.

Why it fits:

- API inputs like chat question, search query, and top-k limits should be validated early.

How it works here:

- `SearchRequest`, `SearchResponse`, `ChatRequest`, and `ChatResponse` are defined in `app/main.py`.
- Config settings are also handled through Pydantic Settings in `app/utils/config.py`.

Why this instead of plain dictionaries:

- Stronger validation, cleaner types, fewer runtime surprises.

### LangGraph

What it does:

- Orchestrates the ReAct-style agent flow.

Why it fits:

- The system needs an LLM that can reason, decide whether tools are needed, call them, and continue.

How it works here:

- `create_react_agent(llm, TOOLS)` is used in `app/services/agent.py`.
- The agent receives a system message and a prompt containing retrieved context and history.

Why this instead of a single direct LLM call:

- A plain LLM call cannot safely handle tool invocation flow as well as an agent loop can.

### LangChain Tool Wrappers

What they do:

- Convert normal Python functions into tool-callable units for the agent.

Why they fit:

- Weather lookup, mandi price lookup, and fertilizer calculations are naturally separate tools.

How they work here:

- `@tool` wrappers are used around `weather_tool`, `mandi_price_tool`, and `fertiliser_tool` in `app/services/agent.py`.

Why this design is useful:

- It cleanly separates agent reasoning from external side-effect functions.

### Mistral API and `ChatMistralAI`

What it does:

- Serves as the current LLM backend for the agent.

Why it fits:

- The project needs a capable chat model with tool-calling support through the LangChain ecosystem.

How it works here:

- `_get_llm()` in `app/services/agent.py` creates a `ChatMistralAI` client using settings from `.env`.

Why this matters in interviews:

- Say clearly that the running code uses Mistral even if some documents mention Ollama.

### BAAI `bge-m3`

What it does:

- Generates dense multilingual embeddings and also supports sparse lexical weights.

Why it fits:

- Agriculture questions can be multilingual and retrieval quality matters a lot.
- `bge-m3` supports hybrid retrieval better than a simple dense-only model.

How it works here:

- `app/services/embedder.py` loads `BGEM3FlagModel` when `bge-m3` is configured.
- Dense vectors are used for semantic retrieval.
- Sparse lexical weights are used for BM25-style hybrid retrieval in Qdrant.

Why this instead of only MiniLM:

- Better multilingual support and hybrid retrieval support.

### Qdrant

What it does:

- Stores vectors and payload metadata for retrieval.

Why it fits:

- The project needs vector search, metadata filtering, and hybrid dense/sparse support.

How it works here:

- `app/services/vector_store.py` manages collection creation, upsert, dense search, sparse search, and hybrid search.

Why this instead of a normal SQL database:

- SQL is not built for semantic nearest-neighbor vector search.

### Redis

What it does:

- Stores session chat history.

Why it fits:

- Session history is lightweight, short-lived, and needs fast read/write access.

How it works here:

- `app/services/session_store.py` stores messages under keys like `session:{session_id}`.
- If Redis is unavailable, it falls back to an in-memory Python store.

Why not store full history only in browser:

- The backend needs history to produce multi-turn answers consistently.

### Loguru

What it does:

- Centralized structured logging.

Why it fits:

- Easier logging setup than standard library logging for many teams.

How it works here:

- `app/utils/logger.py` configures stderr logging plus file logging to `logs/agrosight.log`.

### `httpx`

What it does:

- Async HTTP client for external APIs.

Why it fits:

- Weather and mandi tools need external network calls without blocking the whole app.

How it works here:

- `app/services/agro_tools.py` and `scripts/download_data.py` use `httpx.AsyncClient`.

### Tenacity

What it does:

- Adds retry logic.

Why it fits:

- External APIs may fail temporarily.

How it works here:

- Weather and mandi fetch functions use retry decorators with exponential backoff.

### pandas

What it does:

- Handles CSV and tabular data processing.

Why it fits:

- Mandi and other tabular sources need grouping and narrative conversion before chunking.

How it works here:

- `chunker.py` turns DataFrames into retrieval-friendly text chunks.

### PDF Tooling

What it does:

- Extracts text from PDF knowledge sources.

Why it fits:

- Agricultural content often exists in PDF books and guides.

How it works here:

- `chunker.py` tries `pdfplumber`, then `pypdf`, then PyMuPDF as fallback.

Why multiple PDF libraries are used:

- PDF extraction quality varies by file, so fallback layers improve robustness.

### Docker and Docker Compose

What they do:

- Package the app and run backend plus Redis together.

Why they fit:

- Easier local setup and deployment consistency.

How they work here:

- `Dockerfile` builds the Python app image.
- `docker-compose.yml` runs the API service and Redis service.

### pytest

What it does:

- Tests chunking and selected behavior.

Why it fits:

- Retrieval systems need repeatable validation of preprocessing logic.

How it works here:

- `tests/test_agrosight.py` covers chunking strategies, prompt helpers, and some dispatch logic.

---

## 3. End-to-End Request Flow

### Full Runtime Flow

1. The user types a question in the browser UI.
2. `app/static/js/app.js` sends a `POST /chat` request with `question`, `session_id`, and `stream: true`.
3. `app/main.py` receives the request and decides whether to stream or return JSON.
4. If no `session_id` is sent, the backend generates one. Normally the frontend already sends it.
5. `stream_agent()` or `run_agent()` in `app/services/agent.py` starts processing.
6. The system loads existing conversation history from `session_store.py`.
7. It encodes the question using `embedder.py`.
8. It runs hybrid retrieval through `vector_store.py`.
9. It reranks the retrieved candidates using `reranker.py`.
10. It formats context and history using `prompts.py`.
11. It creates a LangGraph ReAct agent with Mistral and tool definitions.
12. If the model decides a live tool is required, it calls weather, mandi, or fertilizer logic from `agro_tools.py`.
13. The final answer is streamed back as SSE tokens or returned as JSON.
14. The backend appends user and assistant turns to session storage.
15. The frontend also stores session metadata and local conversation copies in `localStorage`.

### Search Flow

`POST /search` is a retrieval-only debugging endpoint:

1. accept query
2. retrieve chunks
3. rerank them
4. return top results without LLM generation

This is useful in interviews because it shows separation between retrieval quality and generation quality.

### Health Flow

`GET /health` returns:

- status
- version
- embedding model
- LLM model
- Qdrant collection name

This is useful for liveness and environment verification.

---

## 4. File-by-File Breakdown of the Real System

### `app/main.py`

Purpose:

- Main FastAPI entrypoint.

Responsibilities:

- initialize app lifecycle
- preload heavy resources
- define public API endpoints
- serve static files
- handle streaming chat responses

Important pieces:

- `lifespan()` preloads embedder, reranker, and Qdrant client.
- `chat()` handles both streaming and non-streaming modes.
- `delete_session()` clears session history.

Why separate file:

- Keeps API wiring independent from business logic.

### `app/services/agent.py`

Purpose:

- Core orchestration layer for RAG plus agent behavior.

Responsibilities:

- retrieve context
- load conversation history
- detect language
- build prompt
- create and run LangGraph ReAct agent
- stream or return final answer

Important functions:

- `retrieve_context()`
- `run_agent()`
- `run_agent_with_metadata()`
- `stream_agent()`

Advanced note:

- This file contains a monkey patch for Mistral message conversion to avoid duplicate tool call ID issues. That is powerful but also fragile because it depends on internal library behavior.

Why separate file:

- This is the brain of the system and would become too large if mixed into the API layer.

### `app/services/agro_tools.py`

Purpose:

- Implements live domain tools.

Responsibilities:

- current weather advisory
- mandi price lookup
- fertilizer calculation

Important functions:

- `get_weather_advisory()`
- `get_mandi_price()`
- `fertiliser_calculator()`

Why this file matters:

- It converts the system from a static knowledge bot into a live-action assistant.

### `app/services/embedder.py`

Purpose:

- Embedding generation and sparse weight generation.

Responsibilities:

- lazy model loading
- dense vector generation
- sparse lexical weight generation for `bge-m3`

Important functions:

- `_load_model()`
- `preload_models()`
- `encode_texts()`
- `encode_query()`
- `encode_sparse()`

Why separate file:

- Model loading and encoding logic are heavy and deserve a dedicated abstraction.

### `app/services/vector_store.py`

Purpose:

- Qdrant integration layer.

Responsibilities:

- connect to Qdrant
- create collections
- upsert chunk payloads
- dense search
- sparse search
- hybrid retrieval with Reciprocal Rank Fusion
- metadata filter building

Important functions:

- `get_client()`
- `ensure_collection()`
- `upsert_chunks()`
- `dense_search()`
- `sparse_search()`
- `hybrid_search()`

Why separate file:

- Vector database logic is a separate concern from agent logic.

### `app/services/reranker.py`

Purpose:

- Improves precision after retrieval.

Responsibilities:

- score query-chunk pairs with a cross-encoder
- reorder top candidates

Important functions:

- `_get_cross_encoder()`
- `preload_models()`
- `rerank()`

Why this file exists:

- Retrieval and reranking are different stages. Dense retrieval is fast candidate generation, reranking is precise candidate ordering.

### `app/services/prompts.py`

Purpose:

- Central prompt control.

Responsibilities:

- define system prompt
- define user prompt template
- enforce agriculture-only behavior
- enforce tool usage rules
- detect language
- format context and history

Important functions:

- `detect_language()`
- `get_language_name()`
- `format_context()`
- `format_history()`

Why separate file:

- Prompt engineering should be centralized so behavior changes stay consistent.

### `app/services/session_store.py`

Purpose:

- Conversation memory layer.

Responsibilities:

- fetch chat history
- append turns
- clear sessions
- Redis fallback to in-memory store

Important functions:

- `get_history()`
- `append_turn()`
- `clear_session()`

Why separate file:

- Session persistence is a distinct storage concern.

### `app/services/chunker.py`

Purpose:

- Converts raw source files into chunk objects suitable for embedding.

Responsibilities:

- semantic chunking
- section-based chunking
- Q&A chunking
- tabular narrative chunking
- record narrative chunking
- sliding window fallback
- PDF text extraction
- auto-dispatch by file type

Important functions:

- `semantic_chunks()`
- `section_chunks()`
- `qa_pair_chunks()`
- `table_row_chunks()`
- `record_narrative_chunks()`
- `sliding_window_chunks()`
- `chunk_file()`

Why this file matters:

- RAG quality starts here. Bad chunking causes bad retrieval even if the model is strong.

### `app/static/js/app.js`

Purpose:

- Frontend chat behavior.

Responsibilities:

- manage `session_id`
- manage local chat history
- send API requests
- parse SSE stream manually
- update the chat UI
- fetch location and weather display

Important functions:

- `init()`
- `createNewSession()`
- `loadSession()`
- `sendMessage()`
- `saveToLocalHistory()`

Why separate file:

- Keeps browser interaction logic out of HTML.

### `app/static/index.html`

Purpose:

- Main UI structure.

Responsibilities:

- sidebar
- chat area
- hero/welcome state
- input area
- quick action chips

Why this file exists:

- It defines the user-facing interface skeleton while JavaScript provides behavior and CSS provides styling.

### `app/utils/config.py`

Purpose:

- Centralized configuration.

Responsibilities:

- load app, model, API, Redis, Qdrant, and ingestion settings from environment

Why separate file:

- Central config reduces hidden constants across files.

### `app/utils/logger.py`

Purpose:

- Shared logging setup.

Responsibilities:

- configure stderr logs
- configure rotating file logs

Why separate file:

- Keeps logging consistent across services.

### `app/utils/file_utils.py`

Purpose:

- File and hashing helpers.

Responsibilities:

- SHA-256 hashing
- directory iteration
- vision file filtering
- directory creation

Why separate file:

- Small utilities are reused in ingestion and chunking.

### `scripts/ingest.py`

Purpose:

- Real ingestion entrypoint.

Responsibilities:

- collect source files
- chunk them
- embed them
- create sparse vectors if needed
- upsert into Qdrant
- track ingestion stats

Why it matters:

- This is the operational pipeline that turns raw knowledge into searchable vectors.

Important truth:

- `ingestion.py` at repo root is effectively empty and not the real active ingestion script.
- The real entrypoint is `scripts/ingest.py`.

### `scripts/download_data.py`

Purpose:

- Downloads or seeds raw knowledge sources before ingestion.

Responsibilities:

- weather download
- mandi data download
- USDA data download
- SoilGrids download
- static JSON knowledge seeding

Why separate file:

- Data acquisition is different from data ingestion.

### `Dockerfile`

Purpose:

- Container build definition.

Responsibilities:

- install dependencies
- include OCR and PDF system packages
- package app runtime
- run `uvicorn`

Why important:

- Shows how the system is expected to run in a production-like environment.

### `docker-compose.yml`

Purpose:

- Multi-service local deployment.

Responsibilities:

- run API container
- run Redis container
- wire health checks and volumes

Why useful:

- Makes the project easier to run end-to-end.

### `Makefile`

Purpose:

- Developer command shortcuts.

Responsibilities:

- install
- run server
- download data
- ingest
- test
- evaluate
- Docker commands

Why it matters:

- It improves developer experience and standardizes workflows.

### `tests/test_agrosight.py`

Purpose:

- Primary test suite in this repo.

Responsibilities:

- validates chunking behavior
- validates chunk dispatch
- validates prompt helper functions

Why it matters:

- It protects the most important preprocessing layer of the RAG pipeline.

---

## 5. Data Ingestion and Knowledge Pipeline

### Step 1: Raw Data Sources

The project uses knowledge from sources like:

- JSON FAQs
- scheme records
- disease knowledge
- soil data
- weather advisory JSON
- CSV market data
- PDF books and guides

### Step 2: File Discovery

`scripts/ingest.py` uses `iter_data_files()` from `file_utils.py` to find supported files under:

- `data/raw`
- `data/books`

Image files are skipped because they are considered part of a future or separate vision pipeline.

### Step 3: Chunking

`chunk_file()` in `chunker.py` decides the best strategy based on file type and content pattern.

Different chunking strategies are used because different source structures need different retrieval shapes:

- semantic chunking for flowing text
- section chunking for structured guides
- Q&A chunking for FAQs
- table row chunking for CSV/tabular data
- record narrative chunking for JSON object records
- sliding window as fallback

Why this matters:

- If you chunk every file the same way, retrieval quality drops.
- A FAQ works better as one question-answer chunk.
- A market CSV works better as grouped tabular narrative.
- A PDF guide works better as sections or semantic chunks.

### Step 4: Hashing and Deduplication

Every chunk gets a SHA-256 hash using:

- chunk text
- source file
- chunk index

Why deduplication is used:

- re-running ingestion should not keep inserting the same content
- idempotent ingestion is important in production pipelines

### Step 5: Dense and Sparse Embeddings

`embedder.py` generates:

- dense embeddings for semantic meaning
- sparse lexical weights for hybrid retrieval when using `bge-m3`

Why both are useful:

- dense retrieval catches semantic similarity
- sparse retrieval catches keyword matches
- hybrid retrieval reduces miss rate on mixed query types

### Step 6: Qdrant Upsert

Each chunk is stored with:

- vector data
- optional sparse vector
- text
- source file
- chunk type
- crop category
- language
- metadata

### Step 7: Retrieval Time

When a user asks a question:

1. query embedding is created
2. sparse weights may also be created
3. Qdrant performs dense and sparse searches
4. results are merged using Reciprocal Rank Fusion
5. top candidates are reranked by cross-encoder
6. the final context goes into the agent prompt

---

## 6. Interview Questions and Answers

## A. Project Overview

### Q1. What problem does AgroSight solve?

Short answer:

It gives farmers a domain-specific AI assistant that can answer agricultural questions using retrieved knowledge plus live tools.

Medium answer:

AgroSight solves the problem of unreliable generic AI advice in agriculture by combining a curated agricultural knowledge base, hybrid retrieval, reranking, and live tools for weather and mandi prices. This helps produce more grounded and useful farmer-facing answers.

Advanced answer:

The core problem is trust and relevance in agriculture-focused AI. A pure LLM may hallucinate or miss current operational facts. AgroSight addresses this with a RAG pipeline for static knowledge, tool calling for real-time facts, and session memory for multi-turn continuity. The design separates retrieval, reranking, generation, and session persistence into different layers so each can be improved independently.

### Q2. Why did you not build this as only a normal chatbot?

Because agriculture answers often need grounding, citations, and live data. A plain chatbot is weaker for domain reliability and current conditions.

### Q3. What makes this project production-style?

- layered architecture
- config-driven setup
- health endpoint
- session storage
- retry logic
- Docker support
- test coverage for chunking
- dedicated ingestion pipeline

## B. Backend and API

### Q4. What are the public APIs in this system?

- `GET /health`
- `POST /search`
- `POST /chat`
- `DELETE /session/{session_id}`

### Q5. Why is `/search` useful if `/chat` already exists?

`/search` isolates retrieval from generation. It helps debug whether the problem is in retrieval quality or in the LLM answer layer.

### Q6. How does streaming work?

The backend uses SSE through `EventSourceResponse`, and the frontend reads the response body stream manually, parsing `event:` and `data:` lines for `session`, `token`, and `done`.

## C. RAG Pipeline

### Q7. What happens after the user asks a question?

The system loads history, retrieves relevant chunks using hybrid search, reranks them, formats a prompt, runs the LangGraph ReAct agent, optionally calls tools, and returns the answer.

### Q8. Why is retrieval needed before generation?

Retrieval provides grounded context from domain data so the model does not rely only on parametric memory.

### Q9. Why rerank after retrieval?

Initial retrieval is optimized for recall. Reranking improves precision by re-scoring query-document pairs more deeply.

## D. Embeddings

### Q10. Why use `bge-m3`?

Because it supports multilingual embeddings and sparse lexical weights, which make it a strong fit for hybrid search in this project.

### Q11. What is the difference between dense and sparse retrieval?

Dense retrieval uses semantic vectors and finds meaning-level similarity. Sparse retrieval uses lexical weights and finds keyword overlap. Hybrid search combines both.

## E. Vector Database

### Q12. Why use Qdrant?

Because the project needs vector similarity search, hybrid retrieval support, metadata payloads, and filtering.

### Q13. What metadata do you store with each chunk?

- text
- chunk hash
- source file
- chunk type
- chunk index
- crop category
- language
- optional extra metadata

## F. Reranking

### Q14. Which reranker is used and why?

The project uses `cross-encoder/ms-marco-MiniLM-L-6-v2`. It adds extra compute cost but improves the ordering of top retrieved candidates.

### Q15. Why not let Qdrant ranking alone decide the final chunks?

Because nearest-neighbor search is a fast approximation stage. A cross-encoder looks at the full query-document pair and often gives better final relevance.

## G. Agent and Tool Calling

### Q16. Why use a ReAct agent here?

Because some answers require reasoning plus conditional tool use. For example, current weather must come from the weather tool, not from model memory.

### Q17. What tools are available?

- weather tool
- mandi price tool
- fertilizer calculator tool

### Q18. Why make tool usage mandatory for some question types?

Because current weather and current prices are freshness-sensitive. The prompt explicitly instructs the agent not to guess those from internal knowledge.

## H. Frontend and Session Management

### Q19. How are multiple chats separated?

By `session_id`. One session ID represents one conversation.

### Q20. Where is session state stored?

- frontend stores current session and local copies of conversation in `localStorage`
- backend stores server-side history in Redis or in-memory fallback

### Q21. Why keep both browser history and backend history?

Browser history helps UI restoration and recent-chat display. Backend history helps answer multi-turn questions consistently. This is practical but also duplicates state, which is a design tradeoff.

## I. Deployment

### Q22. How do you deploy this system locally?

Use Docker Compose to run the API and Redis together, or use the Makefile for local development commands.

### Q23. Why include OCR and PDF packages in Docker?

Because the ingestion layer may need robust PDF extraction and related document tooling.

## J. Testing

### Q24. What is tested well in this repo?

Chunking strategies and some prompt/helper behavior are tested better than the full live API stack.

### Q25. What is missing from testing?

- more end-to-end chat tests
- more retrieval correctness tests
- tool integration tests against mocked external APIs
- session behavior tests

## K. Failure Handling

### Q26. What happens if Redis is down?

The system falls back to an in-memory session store. That keeps the app usable, but history is no longer shared across processes or preserved across restarts.

### Q27. What happens if external APIs fail?

Tool functions retry with exponential backoff and eventually return structured error information instead of crashing the whole system.

## L. Tradeoffs

### Q28. What are the main tradeoffs in this architecture?

- better retrieval quality at the cost of more latency
- live tools add freshness but also add external dependency risk
- browser and backend state both improve UX but duplicate responsibility
- monkey patching the Mistral adapter solves a real bug but increases maintenance risk

---

## 7. Advanced Discussion Topics

### Hybrid Retrieval

This system combines dense and sparse search. Dense search is good for semantic similarity. Sparse search is good for exact words and domain-specific terms. The project merges both using Reciprocal Rank Fusion, which is a practical way to combine ranked lists without overfitting to one score scale.

### Why Reranking Helps

Vector search is strong at finding good candidates quickly, but the top few results are not always in the best order. A cross-encoder reads the query and candidate chunk together and produces a stronger relevance score. That improves final context quality before generation.

### Why Session State Is Split

Frontend state exists for UI convenience, recent chats, and browser persistence. Backend state exists for actual conversational grounding during answer generation. This split is common, but it creates consistency questions if frontend and backend histories diverge.

### Why SSE Instead of WebSockets

SSE is simpler for one-way token streaming, easier to wire into a standard HTTP request flow, and enough for this chat pattern. WebSockets would be more useful if the project needed bi-directional low-latency event exchange or richer live collaboration behavior.

### Redis Fallback Behavior

The in-memory fallback keeps the app from fully failing when Redis is unavailable. However, it is not durable, not shared across multiple workers or replicas, and not suitable for long-term production scale.

### External API Failure Handling

The tool layer uses retries and returns structured error payloads. That is good because it keeps tool failures isolated, but the final user experience still depends on how well the model explains those failures in natural language.

### Scalability Bottlenecks

Likely bottlenecks include:

- embedding latency
- reranking cost
- LLM latency
- external tool latency
- session inconsistency across processes if Redis is unavailable

---

## 8. Weaknesses and Improvement Ideas

### 1. Frontend weather API key exposure

The frontend JavaScript contains an OpenWeatherMap API key directly in the client-side code. That is a security and quota risk. A safer design would proxy this through the backend.

### 2. Broad CORS configuration

`allow_origins=["*"]` is convenient for development but too open for stricter production environments.

### 3. Duplicated state across browser and backend

The system stores chat data in both `localStorage` and backend session storage. This is helpful for UX but can lead to mismatch or debugging complexity.

### 4. Older docs may be stale

Some repo docs describe Ollama and `qwen3.5:9b`, while the code uses Mistral. Interview answers should prioritize code truth over old design notes.

### 5. Simple language detection

Language detection is based on Unicode ranges for Hindi and Gujarati. That is lightweight and fast, but not robust for mixed-language or transliterated input.

### 6. In-memory fallback is not persistent

If Redis is unavailable, sessions exist only in process memory. That is acceptable as resilience fallback but not ideal for distributed systems.

### 7. Custom Mistral patch risk

The monkey patch in `agent.py` fixes a real issue, but it depends on internal behavior of `langchain_mistralai`. Future package updates could break it.

### 8. Retrieval and evaluation could be stronger

The project has strong chunking tests, but it could benefit from benchmarked retrieval evaluation, answer-quality evaluation, and more end-to-end automated tests.

### 9. Frontend and backend weather logic are separate

The frontend fetches weather display data independently while the backend also has a weather tool. That means weather-related logic is split across layers instead of being fully centralized.

### 10. Session storage is limited to recent turns

Only the last few conversation turns are stored. This improves efficiency, but it may reduce continuity in longer conversations.

---

## 9. Rapid Revision Section

### 1-Minute Answer

AgroSight is an agricultural RAG chatbot for Indian farmers. The frontend sends a question and session ID to a FastAPI backend. The backend retrieves relevant agricultural content from Qdrant using `bge-m3` embeddings and hybrid retrieval, reranks the results, builds a prompt with session history, and runs a LangGraph ReAct agent using Mistral. If the question needs live weather, mandi prices, or fertilizer calculation, the agent calls dedicated tools. The response is streamed back with SSE and session history is stored in Redis.

### 5-Minute Architecture Answer

The system has four main parts. First is the frontend in `app/static`, which manages session IDs, local chat history, and SSE rendering. Second is the FastAPI API layer in `app/main.py`, which exposes health, search, chat, and session endpoints and preloads heavy resources at startup. Third is the service layer, where `agent.py` orchestrates retrieval, reranking, prompt construction, agent execution, and streaming; `agro_tools.py` handles live data tools; `session_store.py` manages history; and `prompts.py` centralizes behavior control. Fourth is the retrieval layer, where `chunker.py` processes source files, `embedder.py` creates dense and sparse representations, `vector_store.py` manages Qdrant search and upsert, and `reranker.py` improves final relevance. The project is supported by Docker, Redis, Make targets, and test coverage around chunking and preprocessing.

### Top 20 Likely Interview Questions

- What problem does AgroSight solve?
- Why is this better than a normal chatbot?
- Why use RAG in this project?
- Why use FastAPI?
- Why use SSE instead of WebSockets?
- Why use `bge-m3` embeddings?
- Why use Qdrant?
- What is hybrid retrieval?
- Why rerank results after retrieval?
- Why use LangGraph instead of one plain LLM call?
- What tools does the agent have?
- How does session management work?
- What is stored in Redis?
- What is stored in browser `localStorage`?
- How does the ingestion pipeline work?
- Why use different chunking strategies?
- What happens if Redis fails?
- What happens if weather or mandi APIs fail?
- What are the main weaknesses of the current implementation?
- If you had more time, what would you improve first?

### Top 10 Tricky Follow-Up Questions

- Why did you choose a hybrid dense+sparse design instead of dense-only retrieval?
- What are the risks of keeping session data in both frontend and backend?
- Why is reranking worth the extra latency?
- What would break if the Mistral adapter patch stopped working?
- How would you make this multi-tenant or user-aware instead of only session-aware?
- How would you secure the exposed frontend weather key?
- How would you evaluate retrieval quality independently from answer quality?
- How would this architecture change if you added image-based disease diagnosis?
- What problems can happen when Redis falls back to process memory in a multi-worker setup?
- How would you reduce hallucinations further without making responses too rigid?

---

## 10. Best Practices for Explaining This Project in Interviews

- Start with the business problem first, then architecture.
- Say "domain-specific RAG assistant with live tools" early.
- Mention current code truth when docs and code differ.
- Explain retrieval, reranking, and tool calling as separate layers.
- Show that you understand tradeoffs, not only happy-path behavior.
- Point out improvement ideas confidently. That makes your explanation stronger, not weaker.

---

## 11. Final Interview-Ready Closing

If an interviewer asks, "How would you summarize your contribution or understanding of this project?" a strong answer is:

"I understand AgroSight as a layered agricultural AI system rather than just a chatbot. The frontend manages chat sessions and streaming UI, the FastAPI layer exposes clean endpoints, the retrieval layer uses chunking plus hybrid vector search in Qdrant, a cross-encoder improves precision, and a LangGraph ReAct agent powered by Mistral decides whether to answer from retrieved context or call live tools like weather, mandi price, and fertilizer calculation. I also understand the limitations, such as duplicated session state, exposed frontend weather key, and the maintenance risk of the custom Mistral patch, and I can explain how I would improve those areas."
