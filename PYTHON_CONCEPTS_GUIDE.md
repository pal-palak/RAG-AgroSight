# Python Concepts Guide – AgroSight System

This document provides a detailed explanation of all Python concepts, patterns, and features used in the AgroSight agricultural AI system, with reasons for their usage.

---

## 1. Async/Await & Concurrency

### **Concept**: Asynchronous Programming
```python
# From main.py
async def lifespan(app: FastAPI):
    """Lifespan events: preload heavy models on startup."""
    loop = asyncio.get_event_loop()
    await asyncio.gather(
        loop.run_in_executor(None, embedder.preload_models),
        loop.run_in_executor(None, reranker.preload_models),
        loop.run_in_executor(None, get_client),
    )
```

### **Why Used**:
- **Non-blocking I/O**: FastAPI is async-first. Multiple requests can be processed concurrently without blocking threads
- **Efficient Resource Use**: Heavy model loading (embedder, reranker, vector store) happens in parallel during startup, reducing boot time
- **Scalability**: Can handle many concurrent user requests with minimal thread overhead

### **Key Components**:
- `async def`: Defines coroutine functions that can be paused/resumed
- `await`: Waits for async operations to complete
- `asyncio.gather()`: Runs multiple async tasks concurrently
- `loop.run_in_executor()`: Runs blocking CPU operations in thread pool without blocking event loop

---

## 2. Type Hints & Static Typing

### **Concept**: Python Type Annotations
```python
# From config.py
from typing import Literal, Any, AsyncGenerator

def retrieve_context(query: str, filters: dict | None = None) -> list[dict[str, Any]]:
    """Return list of dictionaries containing retrieved context."""
    ...

async def stream_agent(question: str, session_id: str = "default") -> AsyncGenerator[str, None]:
    """Yield response tokens as they arrive."""
    ...
```

### **Why Used**:
- **IDE Support**: Enable autocomplete, refactoring, and code navigation in VS Code/PyCharm
- **Error Detection**: Catch type mismatches before runtime (via Pylance, mypy)
- **Documentation**: Types serve as inline documentation for function contracts
- **Union Types** (`dict | None`): Modern Python 3.10+ syntax for optional parameters
- **Generic Types** (`list[dict[str, Any]]`): Specify container element types

### **Key Components**:
- `str`, `int`, `float`, `bool`: Basic types
- `List[T]`, `Dict[K, V]`, `Tuple[T, ...]`: Collection types
- `Optional[T]` / `T | None`: Optional values
- `AsyncGenerator[YieldType, SendType]`: Async generator type
- `Literal["option1", "option2"]`: Restrict to specific string values
- `Any`: Flexible type when needed

---

## 3. Decorators

### **Concept A**: Built-in Decorators
```python
# From config.py
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
```

### **Why Used - LRU Cache**:
- **Performance**: Avoids re-parsing `.env` file on every request
- **Singleton Pattern**: Ensures only one Settings object exists application-wide
- **Memoization**: Caches function result based on arguments (here: no args, so always returns same object)

### **Concept B**: Framework Decorators
```python
# From agent.py
from langchain_core.tools import tool

@tool
async def weather_tool(location: str) -> str:
    """Get current weather and agronomy advisory for a location."""
    result = await get_weather_advisory(location)
    return str(result)

# From main.py
@app.get("/", tags=["UI"])
async def read_root():
    """Serve the premium chatbot UI."""
    return FileResponse("app/static/index.html")
```

### **Why Used - Framework Decorators**:
- **Tool Registration**: `@tool` makes functions callable by LangGraph ReAct agent
- **Route Definition**: `@app.get()` registers HTTP endpoint with FastAPI
- **Automatic Documentation**: FastAPI generates OpenAPI schema from decorated functions

---

## 4. Context Managers & Lifespan

### **Concept**: Context Manager Pattern
```python
# From main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: preload heavy models and connections on startup.
    """
    logger.info("Initializing heavy resources...")
    # Setup code runs here
    await asyncio.gather(...)
    yield  # Application runs here
    # Cleanup code runs here after shutdown
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
```

### **Why Used**:
- **Resource Management**: Ensures embedder, reranker, vector DB client are loaded before first request
- **Guaranteed Cleanup**: Resources are properly closed on shutdown (prevents resource leaks)
- **Startup/Shutdown Hooks**: Runs initialization code once per app lifecycle
- **Error Safe**: Even if app crashes, cleanup code runs

### **Key Components**:
- `@asynccontextmanager`: Decorator for async context managers
- `yield`: Separates setup from teardown
- Works with `with`/`async with` statements (and FastAPI's lifespan)

---

## 5. Pydantic Models & Data Validation

### **Concept**: Declarative Data Validation
```python
# From config.py
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    mistral_api_key: str = Field(..., env="MISTRAL_API_KEY")
    mistral_model: str = "mistral-large-latest"
    llm_temperature: float = 0.2
    retrieval_top_k: int = 8
    
    @field_validator("log_level", mode="before")
    @classmethod
    def normalise_log_level(cls, v: str) -> str:
        return v.upper()
```

### **Why Used**:
- **Auto Validation**: Checks types, ranges, formats automatically on instantiation
- **Environment Variables**: `Field(..., env="NAME")` loads from `.env` files
- **Type Coercion**: `"0.2"` string auto-converts to `float` type
- **Custom Validators**: `@field_validator` applies custom transformation rules (e.g., `.upper()`)
- **Self-Documenting**: Config is the source of truth; no separate schema needed
- **Error Messages**: Clear validation errors on misconfiguration

### **Key Components**:
- `BaseSettings`: Extends `BaseModel` to read from environment
- `Field(...)`: Provide defaults, descriptions, environment variable names
- `SettingsConfigDict`: Control how settings are loaded
- `@field_validator`: Custom validation logic per field

---

## 6. Singleton Pattern & Global State Management

### **Concept**: Lazy-Loading Singletons
```python
# From vector_store.py
_client: QdrantClient | None = None

def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.request_timeout,
        )
        logger.info(f"Qdrant client connected: {settings.qdrant_url}")
    return _client

# From embedder.py
_model = None
_model_name: str = ""

def _load_model(model_name: str):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model  # Already loaded, return cached version
    # Load model only once per process
    _model = SentenceTransformer(model_name)
    _model_name = model_name
    return _model
```

### **Why Used**:
- **One Instance Only**: Embedding models (100MB+), vector DB clients expensive to create—create once, reuse always
- **Lazy Loading**: Models loaded only when first needed (not at import time)
- **Efficient Memory**: Avoid duplicate model copies across threads/tasks
- **Thread-Safe**: Python's GIL ensures `_model is None` check is atomic

### **Advantages**:
- ✅ Lower memory footprint
- ✅ Faster subsequent requests
- ✅ Predictable startup time

---

## 7. Exception Handling & Retry Logic

### **Concept**: Decorated Retry Pattern
```python
# From agro_tools.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def get_weather_advisory(location: str) -> dict[str, Any]:
    """Fetch current weather with automatic retry on failure."""
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        error_msg = f"OpenWeatherMap API error (HTTP {exc.response.status_code}): {exc.response.text}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "api_error",
        }
    except Exception as exc:
        error_msg = f"Failed to fetch weather for {location}: {exc}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "unavailable",
        }
```

### **Why Used**:
- **Resilience**: External APIs (OpenWeather, data.gov.in) can temporarily fail; retry with backoff
- **Exponential Backoff**: `wait_exponential(multiplier=1, min=1, max=8)` prevents hammering failed service
- **Stop Condition**: `stop_after_attempt(3)` gives up after 3 tries
- **Graceful Degradation**: Caught exceptions return error responses instead of crashing

### **Key Components**:
- `@retry`: Automatic retry decorator from tenacity library
- `stop_after_attempt(N)`: Max retry attempts
- `wait_exponential()`: Backoff strategy (1s, 2s, 4s, 8s, ...)
- Multiple `except` blocks: Handle different error types differently

---

## 8. Async Context Managers for HTTP Clients

### **Concept**: Async Context Manager for Resource Management
```python
# From agro_tools.py
async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
```

### **Why Used**:
- **Connection Pooling**: Reuses TCP connections across multiple requests
- **Automatic Cleanup**: Closes connection gracefully even if exception occurs
- **Timeout Control**: `timeout=30s` prevents hanging on slow networks
- **Non-blocking**: Uses async I/O, doesn't block event loop

### **Control Flow**:
1. `async with httpx.AsyncClient() as client:` → Setup (create client, connect pool)
2. `await client.get()` → Make request (non-blocking)
3. Exit `with` block → Cleanup (close connection)

---

## 9. Data Structures & Collections

### **Concept A**: Default Dictionary for Session Management
```python
# From session_store.py
from collections import defaultdict

_memory_store: dict[str, list[dict]] = defaultdict(list)

def append_turn(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)  # Auto-creates empty list if key missing
    history.append({"role": role, "content": content})
```

### **Why Used**:
- **Auto-Initialization**: No need for `if session_id not in _memory_store` checks
- **Cleaner Code**: Fewer defensive coding patterns
- **Key Type**: `dict[str, list[dict]]` means session_id → list of message dicts

### **Concept B**: JSON Serialization
```python
# From session_store.py
import json

def append_turn(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)
    history.append({"role": role, "content": content})
    
    r = _get_redis()
    if r is not None:
        r.setex(
            f"session:{session_id}",
            settings.session_ttl_seconds,
            json.dumps(history),  # Convert to JSON string for Redis storage
        )
```

### **Why Used**:
- **Redis Storage**: Redis stores strings; JSON is the universal format
- **Cross-Language**: JSON can be read by other services (Node.js, Go, etc.)
- **Human Readable**: Logs are debuggable

---

## 10. Logging & Structured Output

### **Concept**: Centralized Structured Logger
```python
# From logger.py
from loguru import logger

def configure_logger() -> None:
    """Configure loguru based on settings."""
    settings = get_settings()
    logger.remove()  # Remove default handler
    
    # Console output with colors
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | ..."
    )
    
    # File output with rotation & compression
    logger.add(
        "logs/agrosight.log",
        level="DEBUG",
        rotation="50 MB",        # Create new file every 50MB
        retention="30 days",     # Keep logs for 30 days
        compression="gz",        # Compress old logs
        enqueue=True,            # Non-blocking I/O
    )

# Usage everywhere
logger.info("Starting...")
logger.error(f"Failed: {exc}")
logger.success("Operation completed")
```

### **Why Used**:
- **Centralized Config**: One place to configure all logging (stdout, file, level, format)
- **Structured Format**: Consistent, machine-parsable log format with timestamps
- **Log Rotation**: Prevents disk space from filling up
- **Debug Mode**: File logs at DEBUG level; console shows only INFO+
- **Performance**: `enqueue=True` uses async logging (doesn't block app)
- **Rich Info**: Colors, line numbers, function names aid debugging

---

## 11. Type Aliases & Forward References

### **Concept**: Type Aliases for Readability
```python
# From agent.py
from typing import Any, AsyncGenerator

def stream_agent(question: str, session_id: str = "default") -> AsyncGenerator[str, None]:
    """Yield response tokens one at a time."""
    ...

def retrieve_context(query: str, filters: dict | None = None) -> list[dict[str, Any]]:
    """Retrieve ranked documents."""
    ...
```

### **Why Used**:
- **Semantic Clarity**: `AsyncGenerator[str, None]` is self-documenting (yields strings)
- **Generic Types**: `list[dict[str, Any]]` describes data structure precisely
- **IDE Hints**: Helps tools understand what functions return

---

## 12. Module Organization & Imports

### **Concept**: Package Structure with `__init__.py`
```
app/
  __init__.py          # Empty or re-exports public API
  main.py              # FastAPI app factory
  services/
    __init__.py
    agent.py           # ReAct agent orchestration
    embedder.py        # Model loading & encoding
    vector_store.py    # Qdrant operations
    session_store.py   # Redis session management
  utils/
    __init__.py
    config.py          # Settings from environment
    logger.py          # Centralized logger
```

### **Why Used**:
- **Namespacing**: `from app.services.agent import run_agent` is clear and unambiguous
- **Lazy Imports**: Services imported only when needed
- **Circular Dependency Prevention**: Clear dependency hierarchy
- **Type Hints**: `from typing import ...` imports type hints for static analysis

---

## 13. File & I/O Operations

### **Concept**: Serving Static Files
```python
# From main.py
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticMount

app.mount("/css", StaticFiles(directory="app/static/css"), name="css")
app.mount("/js", StaticFiles(directory="app/static/js"), name="js")

@app.get("/", tags=["UI"])
async def read_root():
    """Serve the premium chatbot UI."""
    return FileResponse("app/static/index.html")
```

### **Why Used**:
- **Efficient Serving**: FastAPI's `StaticFiles` handles caching headers, compression
- **Single Endpoint**: `/` serves HTML; `/css/*` and `/js/*` serve assets
- **No Extra Server**: Nginx/Apache not needed for static content in development

---

## 14. Environment Configuration & Secrets

### **Concept**: Environment Variables for Secrets
```python
# From config.py & .env file
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    mistral_api_key: str = Field(..., env="MISTRAL_API_KEY")
    qdrant_api_key: str = Field(..., env="QDRANT_API_KEY")
    openweather_api_key: str = ""

# .env file (not in version control)
MISTRAL_API_KEY="sk-..."
QDRANT_API_KEY="ey..."
```

### **Why Used**:
- **Security**: API keys never hardcoded in source
- **Environment-Specific**: Different keys for dev/staging/production
- **12-Factor App**: Follows industry best practice
- **Easy Deployment**: Container just needs `.env` mounted

---

## 15. Union Types & Optional Parameters

### **Concept**: Modern Python 3.10+ Union Syntax
```python
# From vector_store.py & agent.py
def retrieve_context(
    query: str, 
    filters: dict | None = None  # Union: either dict or None
) -> list[dict[str, Any]]:
    ...

def get_client() -> QdrantClient:
    global _client: QdrantClient | None  # Type annotation for global
    ...
```

### **Why Used**:
- **Concise Syntax**: `dict | None` is cleaner than `Optional[dict]` or `Union[dict, None]`
- **Optional Parameters**: `None` as default means "use default behavior"
- **Type Safety**: IDE catches `None` dereferences (`if filters is not None:`)

---

## 16. Function Composition & Higher-Order Functions

### **Concept**: Functions Returning Functions
```python
# From main.py & config.py
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Factory function returns cached Settings singleton."""
    return Settings()

# Usage everywhere
settings = get_settings()
```

### **Why Used**:
- **Factory Pattern**: Centralized object creation
- **Lazy Initialization**: Object created on first call, then cached
- **Dependency Injection**: App passes `settings` to all services

---

## 17. Language Detection & Multilingual Support

### **Concept**: String Processing & Conditionals
```python
# From prompts.py (inferred from usage)
def detect_language(question: str) -> str:
    """Detect language from text (e.g., 'en', 'hi', 'gu')."""
    # Uses fasttext or textblob to detect language
    ...

def get_language_name(lang_code: str) -> str:
    """Map language code to full name."""
    lang_map = {
        "en": "English",
        "hi": "Hindi",
        "gu": "Gujarati",
    }
    return lang_map.get(lang_code, "English")
```

### **Why Used**:
- **Multilingual Farmers**: India has diverse languages; detect and respond in user's language
- **Dynamic Prompts**: System prompt adjusts based on detected language
- **Accessibility**: Non-English speakers get native language responses

---

## 18. Streaming Responses (Server-Sent Events)

### **Concept**: Async Generator for Streaming
```python
# From agent.py & main.py (conceptually)
async def stream_agent(question: str) -> AsyncGenerator[str, None]:
    """Yield tokens as they arrive from LLM."""
    # First yield retrieved chunks
    yield json.dumps({"type": "chunks", "data": chunks})
    
    # Then yield token stream
    async for token in llm.stream(prompt):
        yield token

# From main.py
@app.post("/chat", tags=["Chat"])
async def chat(req: ChatRequest):
    """Stream response via Server-Sent Events."""
    def event_generator():
        async for token in stream_agent(req.question, req.session_id):
            yield f"data: {token}\n\n"
    
    return EventSourceResponse(event_generator())
```

### **Why Used**:
- **Real-Time Feel**: User sees response appearing token-by-token (not wait for full response)
- **Large Responses**: Token streaming reduces perceived latency
- **Browser Compatible**: SSE (Server-Sent Events) works in all browsers
- **Memory Efficient**: Stream doesn't buffer entire response

---

## 19. Dataclass-Like Behavior

### **Concept**: Pydantic Models (Dataclass Alternative)
```python
# From main.py (inferred)
from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    filters: dict | None = None

class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[str]
    chunks: list[dict]
```

### **Why Used**:
- **JSON Serialization**: FastAPI auto-converts to/from JSON
- **Validation**: Request data is validated on receive
- **Documentation**: OpenAPI schema auto-generated
- **Type Safety**: Better than `dict` with string keys

---

## 20. Error Handling Strategies

### **Concept**: Layered Error Handling
```python
# From main.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, log, return error response."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# From services (pattern)
try:
    result = await external_api_call()
except httpx.HTTPStatusError as exc:
    logger.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
    return {"error": "API error", "status": "api_error"}
except Exception as exc:
    logger.error(f"Unexpected error: {exc}")
    return {"error": "Unavailable", "status": "unavailable"}
```

### **Why Used**:
- **User Experience**: Clear error messages instead of 500 page
- **Debugging**: Logged errors include stack traces and context
- **Graceful Degradation**: Fallback responses when services unavailable
- **Production Ready**: Catches edge cases that slip through unit tests

---

## Summary Table

| Concept | Location | Purpose |
|---------|----------|---------|
| **Async/Await** | main.py, agent.py | Non-blocking I/O, concurrency |
| **Type Hints** | All files | IDE support, static analysis |
| **Decorators** | config.py, agent.py, main.py | Caching, tool registration, routing |
| **Context Managers** | main.py, agro_tools.py | Resource management, cleanup |
| **Pydantic Models** | config.py, main.py | Data validation, serialization |
| **Singletons** | vector_store.py, embedder.py | One instance, lazy load |
| **Retry Logic** | agro_tools.py | External API resilience |
| **Logging** | logger.py | Structured observability |
| **Streaming** | agent.py, main.py | Real-time token delivery |
| **Environment Config** | config.py | Secrets management |
| **Package Structure** | app/ | Clean namespacing |
| **Error Handling** | All services | Graceful degradation |

---

## Architecture Flow

```
User Request
    ↓
FastAPI Route (@app.post("/chat"))
    ↓
Async Request Handler (async def chat)
    ↓
LangGraph ReAct Agent Pipeline:
    1. Encode query (Embedder singleton)
    2. Hybrid search in Qdrant (Singleton client)
    3. Rerank with cross-encoder
    4. Run LLM with tools
    ↓
Response Streamer (AsyncGenerator)
    ↓
Server-Sent Events
    ↓
Browser (JavaScript) consumes token stream in real-time
```

Each layer uses Python concepts for efficiency, readability, and maintainability:
- **Concurrency**: Handle multiple requests simultaneously
- **Type Safety**: Catch errors early
- **Singleton Pattern**: Efficient resource usage
- **Structured Logging**: Production observability
- **Error Resilience**: External API failures don't crash app

---

This system is a **production-grade Python application** demonstrating modern best practices for building scalable, maintainable AI services.
