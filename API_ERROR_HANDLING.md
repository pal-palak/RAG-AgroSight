# API ERROR HANDLING - Complete Guide

## Table of Contents
1. [Error Handling Architecture](#error-handling-architecture)
2. [Retry Mechanism (Tenacity)](#retry-mechanism-tenacity)
3. [Exception Types & Handling](#exception-types--handling)
4. [Graceful Degradation](#graceful-degradation)
5. [Error Response Formats](#error-response-formats)
6. [Tool-by-Tool Error Handling](#tool-by-tool-error-handling)
7. [Logging Strategy](#logging-strategy)
8. [Recovery Techniques](#recovery-techniques)

---

## Error Handling Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              API Call Attempt                               │
│  (weather_tool / mandi_price_tool / fertiliser_tool)        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   @retry Decorator          │
        │  (Tenacity Library)         │
        │                             │
        │ ┌──────────────────────┐    │
        │ │ Attempt 1 (try)      │    │
        │ └────────┬─────────────┘    │
        │          │ Fails?           │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ Wait (exponential)   │    │
        │ │ 1s + jitter          │    │
        │ └────────┬─────────────┘    │
        │          │                  │
        │ ┌────────▼──────────────┐   │
        │ │ Attempt 2 (retry)     │   │
        │ └────────┬──────────────┘   │
        │          │ Fails?           │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ Wait 2s + jitter     │    │
        │ └────────┬─────────────┘    │
        │          │                  │
        │ ┌────────▼──────────────┐   │
        │ │ Attempt 3 (final)     │   │
        │ └────────┬──────────────┘   │
        │          │ Fails?           │
        │          ▼                  │
        │    Max Retries Reached!     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   Try-Except Blocks         │
        │  (Specific Exception Types) │
        │                             │
        │ ┌──────────────────────┐    │
        │ │ HTTPStatusError?      │    │
        │ │ (Bad status codes)    │    │
        │ └────────┬─────────────┘    │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ TimeoutError?        │    │
        │ │ (Request timeout)    │    │
        │ └────────┬─────────────┘    │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ ConnectionError?     │    │
        │ │ (Network issue)      │    │
        │ └────────┬─────────────┘    │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ KeyError/ValueError? │    │
        │ │ (Response parse)     │    │
        │ └────────┬─────────────┘    │
        │          ↓                  │
        │ ┌──────────────────────┐    │
        │ │ Generic Exception    │    │
        │ │ (Unknown errors)     │    │
        │ └────────┬─────────────┘    │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────┐
        │  Primary Source Failed  │
        │  Try Secondary Source   │
        │  (Fallback Mechanism)   │
        └──────────┬──────────────┘
                   │
        ┌──────────▼──────────────┐
        │  All Sources Failed?    │
        ├──────────┬──────────────┤
        │ YES      │ NO           │
        ↓          ↓
    Error Dict   Return Data
```

---

## Retry Mechanism (Tenacity)

### What is @retry?

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),                    # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=1, max=8)  # Exponential backoff
)
async def get_weather_advisory(location: str):
    # Will retry up to 3 times with exponential backoff
    pass
```

### Retry Flow

```
ATTEMPT 1: Try immediately
├─ Success → Return result
└─ Failure → Wait and retry

WAIT: Exponential backoff
├─ Base: 1 second
├─ Formula: min(1 * 2^(attempt-1), 8)
├─ Attempt 1 wait: 1s * 2^0 = 1s
├─ Attempt 2 wait: 1s * 2^1 = 2s
└─ Attempt 3 wait: 1s * 2^2 = 4s (capped at 8s max)

ATTEMPT 2: After 1s wait
├─ Success → Return result
└─ Failure → Wait and retry

ATTEMPT 3: After 2s wait
├─ Success → Return result
└─ Failure → Raise exception (max attempts reached)
```

### Retry Configuration

```python
# Configuration used in AgroSight
@retry(
    stop=stop_after_attempt(3),                # Attempt up to 3 times
    wait=wait_exponential(
        multiplier=1,                          # Base multiplier
        min=1,                                 # Minimum wait: 1 second
        max=8                                  # Maximum wait: 8 seconds
    )
)
```

**Timing breakdown:**
```
Attempt 1: 0s (immediate)
  ↓ Fails
Wait: ~1 second
Attempt 2: 1s
  ↓ Fails
Wait: ~2 seconds
Attempt 3: 3s
  ↓ Fails
Raise: Stop after 3 attempts (total ~3-6 seconds elapsed)
```

### WHY Retry?

```
Transient Failures (retry helps):
├─ Network hiccup → Retry works
├─ Temporary server overload → Retry works
├─ DNS resolution delay → Retry works
└─ Brief connection drop → Retry works

Permanent Failures (retry doesn't help):
├─ Invalid API key → Failed all 3 times
├─ Wrong endpoint → Failed all 3 times
├─ Service permanently down → Failed all 3 times
└─ Invalid credentials → Failed all 3 times
```

---

## Exception Types & Handling

### 1. HTTPStatusError (HTTP Error Codes)

```python
try:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()  # ← Raises HTTPStatusError on 4xx/5xx
        data = resp.json()
except httpx.HTTPStatusError as exc:
    # Specific handling for HTTP errors
    error_msg = f"OpenWeatherMap API error (HTTP {exc.response.status_code}): {exc.response.text}"
    logger.error(error_msg)
    return {
        "error": error_msg,
        "location": location,
        "status": "api_error",
    }
```

**Common HTTP Status Codes:**

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check parameters |
| 401 | Unauthorized | Invalid API key |
| 403 | Forbidden | No permission |
| 404 | Not Found | Endpoint wrong |
| 429 | Too Many Requests | Rate limited (retry helps) |
| 500 | Server Error | Try again (retry helps) |
| 502 | Bad Gateway | Service down |
| 503 | Service Unavailable | Temporary downtime |
| 504 | Gateway Timeout | Timeout (retry helps) |

---

### 2. TimeoutError (Request Timeout)

```python
try:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        # If request takes > 10 seconds, raises TimeoutError
        resp = await client.get(url, params=params)
except httpx.TimeoutError as exc:
    error_msg = f"Request timeout: {exc}"
    logger.error(error_msg)
    return {"error": error_msg, "status": "timeout"}
```

**Timeout Settings:**
```python
settings.request_timeout = 10  # seconds
# If API doesn't respond in 10 seconds, give up and retry
```

---

### 3. ConnectionError (Network Issues)

```python
try:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
except httpx.ConnectError as exc:
    # Network unreachable, DNS failure, etc.
    error_msg = f"Connection failed: {exc}"
    logger.error(error_msg)
    return {"error": error_msg, "status": "connection_error"}
```

---

### 4. KeyError/ValueError (Response Parsing)

```python
try:
    data = resp.json()
    temp = data["main"]["temp"]      # KeyError if "main" missing
    humidity = data["main"]["humidity"]
except KeyError as exc:
    error_msg = f"Invalid response format: missing key {exc}"
    logger.error(error_msg)
    return {"error": error_msg, "status": "invalid_response"}
except ValueError as exc:
    # JSON parsing failed
    error_msg = f"Response not valid JSON: {exc}"
    logger.error(error_msg)
    return {"error": error_msg, "status": "invalid_json"}
```

---

### 5. Generic Exception (Catch-all)

```python
except Exception as exc:
    # Unknown error - catch all to prevent crash
    error_msg = f"Failed to fetch weather for {location}: {exc}"
    logger.error(error_msg)
    return {
        "error": error_msg,
        "location": location,
        "status": "unavailable",
    }
```

**Why catch-all?**
- Unexpected exceptions don't crash the system
- Always return graceful error dict
- LLM can still provide helpful advice

---

## Graceful Degradation

### Strategy 1: Fallback Sources

```python
async def get_mandi_price(commodity: str, market: str, state: str):
    """Try multiple sources in priority order."""
    
    # Primary source
    result = await _fetch_from_data_gov_in(commodity, market, state)
    if result:
        return result
    
    # Secondary source (fallback)
    result = await _fetch_from_agmarknet(commodity, market, state)
    if result:
        return result
    
    # All sources failed
    return {
        "error": "All price sources unavailable",
        "available_sources": ["data.gov.in", "agmarknet.gov.in"],
        "status": "unavailable"
    }
```

**Flow:**
```
Try data.gov.in Resource 1
  ↓ Fails
Try data.gov.in Resource 2
  ↓ Fails
Try agmarknet.gov.in
  ↓ Fails
Return: Error dict (don't crash)
```

---

### Strategy 2: Cached/Historical Data

```python
# NOT IMPLEMENTED in current version
# But could be added:

try:
    real_time_price = await get_mandi_price()
except:
    logger.warning("Real-time price unavailable, using cache")
    cached_price = redis.get(f"price:{commodity}:{market}")
    if cached_price:
        return {
            **cached_price,
            "freshness": "cached (5 days old)",
            "warning": "Real-time data unavailable"
        }
    else:
        return {"error": "No data available"}
```

**Current approach:** No fallback to stale data (design choice)
- Ensures accuracy for agricultural decisions
- Better to say "unavailable" than give old price

---

### Strategy 3: LLM Fallback

```
API Call Result:
├─ Success: Use real data in prompt
└─ Failure: LLM uses training knowledge
  
LLM still provides answer:
├─ "APIs are currently unavailable, but based on seasonal patterns..."
├─ User gets something helpful
└─ Not "error occurred"
```

---

## Error Response Formats

### Format 1: Weather Tool Error

```python
{
    "error": "OpenWeatherMap API error (HTTP 401): Unauthorized",
    "location": "Rajkot",
    "status": "api_error",  # ← Status key
}
```

**Status values:**
- `"unavailable"` - Service/API down
- `"api_error"` - HTTP error (4xx/5xx)
- `"timeout"` - Request too slow
- `"connection_error"` - Network issue
- `"invalid_response"` - Bad format

---

### Format 2: Mandi Price Error

```python
{
    "error": "Unable to fetch real-time price for wheat in Rajkot, Gujarat. All price sources are temporarily unavailable. Please try again in a few moments.",
    "commodity": "wheat",
    "market": "Rajkot",
    "state": "Gujarat",
    "status": "unavailable",
    "available_sources": ["data.gov.in", "agmarknet.gov.in"],  # ← Which sources tried
}
```

---

### Format 3: Fertilizer Error

```python
{
    "error": "Crop 'sugarcane' not in database. Please consult local ICAR advisory.",
    "available_crops": ["wheat", "rice", "cotton", "maize", ...],  # ← Helpful list
}
```

---

## Tool-by-Tool Error Handling

### Tool 1: Weather Advisory

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
async def get_weather_advisory(location: str):
    # Check 1: API key configured?
    if not settings.openweather_api_key:
        return {
            "error": "OpenWeatherMap API key not configured...",
            "status": "unavailable"
        }
    
    # Check 2: API call succeeds?
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()  # Raises on 4xx/5xx
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        # HTTP error (401, 429, 500, etc)
        return {"error": f"API error ({exc.response.status_code})", ...}
    except Exception as exc:
        # Network error, timeout, etc
        return {"error": f"Failed to fetch: {exc}", ...}
    
    # Check 3: Response has required fields?
    try:
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
    except KeyError as exc:
        return {"error": f"Invalid response format: {exc}", ...}
    
    # Success
    return {
        "location": data.get("name"),
        "temperature_c": temp,
        "humidity_pct": humidity,
        # ... more data
        "source": "OpenWeatherMap (Real-time)"
    }
```

**Error Handling Layers:**
1. Pre-check: API key configured
2. Network: HTTPStatusError, TimeoutError, ConnectError
3. Parse: KeyError, ValueError
4. Fallback: Returns error dict (doesn't crash)

---

### Tool 2: Mandi Price

```python
async def get_mandi_price(commodity: str, market: str, state: str):
    # Try primary source
    data_gov_result = await _fetch_from_data_gov_in(...)
    if data_gov_result:
        return data_gov_result
    
    # Try secondary source
    agmarknet_result = await _fetch_from_agmarknet(...)
    if agmarknet_result:
        return agmarknet_result
    
    # All sources failed
    return {
        "error": "Unable to fetch price. All sources unavailable.",
        "status": "unavailable",
        "available_sources": ["data.gov.in", "agmarknet.gov.in"]
    }


async def _fetch_from_data_gov_in(...):
    # Check: API key configured
    if not api_key:
        return None  # Skip to next source
    
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        # Check: Response has records
        records = data.get("records", [])
        if not records:
            logger.info("No records found")
            return None  # Try next source
        
        # Check: Parse fields
        latest = records[0]
        price = float(latest["modal_price"])
        
        return {
            "commodity": latest.get("commodity"),
            "market": latest.get("market"),
            "modal_price_inr": price,
            "source": "data.gov.in"
        }
    
    except Exception as exc:
        logger.debug(f"data.gov.in error: {exc}")
        return None  # Try next source
```

**Multi-Source Strategy:**
```
data.gov.in Resource 1
  ↓ (on any error)
data.gov.in Resource 2
  ↓ (on any error)
agmarknet.gov.in
  ↓ (on any error)
Return error dict
```

---

### Tool 3: Fertilizer Calculator

```python
async def fertiliser_calculator(crop: str, area_acres: float, ...):
    crop_key = crop.lower().strip()
    
    # Check 1: Crop exists in database
    crop_req = _CROP_NUTRIENT_REQ.get(crop_key)
    if crop_req is None:
        return {
            "error": f"Crop '{crop}' not in database...",
            "available_crops": list(_CROP_NUTRIENT_REQ.keys())
        }
    
    # Check 2: Fertilizer exists
    fert_comp = _FERTILISER_COMPOSITION.get(fert_key)
    if fert_comp is None:
        return {
            "error": f"Fertiliser '{fertiliser}' not in database.",
            "available_fertilisers": list(_FERTILISER_COMPOSITION.keys())
        }
    
    # Check 3: Nutrient is valid
    if nutrient not in ("N", "P", "K"):
        return {"error": "Nutrient must be N, P, or K."}
    
    # Check 4: Fertilizer contains nutrient
    nutrient_pct = fert_comp.get(nutrient, 0)
    if nutrient_pct == 0:
        return {
            "error": f"Urea contains no {nutrient}. Choose different fertiliser."
        }
    
    # All checks pass
    dose_kg = calculate_dose(crop_req, nutrient_pct, area_acres)
    return {
        "crop": crop,
        "fertiliser_dose_kg": dose_kg,
        "bags_50kg": round(dose_kg / 50),
        "source": "Local database"
    }
```

**Validation Layers:**
1. Crop exists?
2. Fertilizer exists?
3. Nutrient valid (N/P/K)?
4. Fertilizer has this nutrient?

---

## Logging Strategy

### Logger Levels

```python
logger.debug(msg)       # Detailed info (API call details)
logger.info(msg)        # General info (successful call)
logger.warning(msg)     # Warning (degraded service)
logger.error(msg)       # Error (API failed)
logger.critical(msg)    # Critical (system down)
```

### Logging Examples

```python
# Success
logger.info(f"data.gov.in R1 → wheat@Rajkot,Gujarat | latest: 29/04/2026")

# Retry
logger.debug(f"data.gov.in resource 1 error: {exc} — trying resource 2")

# Fallback
logger.debug("data.gov.in API key not configured, skipping this source")

# Failure
logger.error("OpenWeatherMap API error (HTTP 401): Unauthorized")

# No results
logger.info("No records found for wheat in Rajkot market on agmarknet.gov.in")
```

### Log Output

```
2026-04-29 14:30:45 DEBUG: Calling weather_tool("Rajkot")
2026-04-29 14:30:46 INFO:  data.gov.in R1 → wheat@Rajkot,Gujarat | latest: 29/04/2026
2026-04-29 14:30:46 INFO:  Successfully retrieved: price=2850
2026-04-29 14:30:46 DEBUG: Agent streaming tokens to frontend

[If error occurs]
2026-04-29 14:31:00 DEBUG: data.gov.in resource 1 error: HTTPStatusError(429)
2026-04-29 14:31:01 DEBUG: Retrying in 1 second...
2026-04-29 14:31:02 DEBUG: data.gov.in resource 2 error: Timeout
2026-04-29 14:31:02 ERROR: Unable to fetch price. All sources unavailable.
2026-04-29 14:31:02 WARNING: Returning error dict to LLM
```

---

## Recovery Techniques

### Technique 1: Retry with Exponential Backoff

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8)
)
```

**Best for:** Transient failures
- Network hiccups
- Temporary server overload
- Rate limiting (429 Too Many Requests)

---

### Technique 2: Fallback to Secondary Source

```python
result = await _fetch_from_data_gov_in(...)
if not result:
    result = await _fetch_from_agmarknet(...)
```

**Best for:** Multiple API sources available
- Mandi prices (2 sources)
- IP geolocation (3 sources)

---

### Technique 3: Configuration Check

```python
if not settings.openweather_api_key:
    return {"error": "API key not configured", ...}
```

**Best for:** Preventing wasted API calls
- Fail fast if not configured
- Clear error message to admin

---

### Technique 4: Circuit Breaker Pattern (Not Implemented Yet)

```python
# Could be added for high-traffic scenarios
circuit_breaker_state = "CLOSED"  # Normal
# After 5 consecutive failures:
circuit_breaker_state = "OPEN"    # Stop trying
# Wait 60 seconds, try 1 request:
circuit_breaker_state = "HALF_OPEN"
# If succeeds:
circuit_breaker_state = "CLOSED"  # Resume normal
```

---

## Complete Error Handling Example

### Real Scenario: User asks "Wheat price in Rajkot?"

```
┌─ API GATEWAY ──────────────────────────────────────────────┐
│ POST /chat                                                 │
│ {"question": "Wheat price in Rajkot?"}                    │
└─────────────────────┬──────────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │ stream_agent()          │
         └────────────┬────────────┘
                      │
      ┌───────────────▼─────────────────┐
      │ retrieve_context()              │
      │ Search Qdrant for "wheat price" │
      │ Result: OK (5 docs)             │
      └───────────────┬─────────────────┘
                      │
      ┌───────────────▼─────────────────┐
      │ Agent processes with tools      │
      │ Decides: Need mandi_price_tool  │
      └───────────────┬─────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ mandi_price_tool("wheat", "Rajkot", "Gujarat")  │
      │                                                  │
      │ @retry decorator active                         │
      │ (max 3 attempts with exponential backoff)        │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ ATTEMPT 1: data.gov.in Resource 1                │
      │ ├─ HTTP 429 (Too Many Requests)                 │
      │ ├─ Caught: HTTPStatusError                      │
      │ ├─ Logged: error level                          │
      │ └─ Returns: None (try next source)              │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ Wait: 1 second (exponential backoff)             │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ ATTEMPT 2: data.gov.in Resource 2                │
      │ ├─ HTTP 200 OK                                  │
      │ ├─ Response parsed successfully                 │
      │ ├─ Records: [] (empty list)                     │
      │ └─ Returns: None (no data for wheat)            │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ ATTEMPT 3 (final): agmarknet.gov.in              │
      │ ├─ HTTP 500 Internal Server Error               │
      │ ├─ Caught: HTTPStatusError                      │
      │ ├─ Max retries reached                          │
      │ └─ Returns: None (all sources failed)           │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ Error Result Returned                           │
      │ {                                                │
      │   "error": "Unable to fetch real-time price...", │
      │   "commodity": "wheat",                          │
      │   "market": "Rajkot",                           │
      │   "status": "unavailable",                      │
      │   "available_sources": ["data.gov.in", "..."]   │
      │ }                                                │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ Agent receives error dict                       │
      │ LLM reads: status="unavailable"                 │
      │ LLM generates fallback response:                │
      │ "Currently unable to fetch live prices.         │
      │  But based on recent trends and storage...      │
      │  Wheat is trading around ₹2,800-2,900 range."   │
      └───────────────┬──────────────────────────────────┘
                      │
      ┌───────────────▼──────────────────────────────────┐
      │ Stream to frontend                              │
      │ User sees: Helpful answer despite API failure   │
      │ No error message (LLM handled it gracefully)    │
      └───────────────────────────────────────────────────┘
```

---

## Summary Table

| Scenario | Detection | Action | Result |
|----------|-----------|--------|--------|
| API not responding | TimeoutError | Retry up to 3x | If all fail: return error dict |
| Rate limited (429) | HTTPStatusError | Retry with backoff | If all fail: try next source |
| Invalid API key | HTTPStatusError (401) | Don't retry | Return error immediately |
| Wrong endpoint | HTTPStatusError (404) | Don't retry | Return error immediately |
| Server down (500) | HTTPStatusError | Retry (transient) | If all fail: try next source |
| No results found | Empty records list | Try next source | If all fail: return error dict |
| Bad response format | KeyError/ValueError | Log and fail | Return error dict |
| Network down | ConnectError | Retry with backoff | If all fail: return error dict |
| All sources fail | Multiple exceptions | Continue with cache/LLM | LLM uses training knowledge |

---

## Key Terminology

### @retry Decorator
- Automatically retries failed function calls
- Used for: `@retry(stop=stop_after_attempt(3), wait=...)`

### HTTPStatusError
- HTTP status codes indicate error (4xx, 5xx)
- Examples: 401 (unauthorized), 429 (rate limited), 500 (server error)

### TimeoutError
- Request takes too long (> 10 seconds)
- Trigger: API not responding within timeout

### ConnectionError
- Network unreachable
- Trigger: No internet, DNS failure

### Exponential Backoff
- Wait time increases with each retry
- Formula: `wait = min(base * 2^(attempt-1), max)`
- Benefit: Reduces load on struggling services

### Circuit Breaker
- Pattern to stop retrying when service is clearly down
- States: CLOSED (normal) → OPEN (stop) → HALF_OPEN (test) → CLOSED

### Fallback
- Secondary option when primary fails
- Example: Try data.gov.in, then try agmarknet

### Graceful Degradation
- System continues working even when some parts fail
- Return error dict instead of crashing

### Status Key
- Field in error response indicating error type
- Values: "unavailable", "api_error", "timeout", "invalid_response"

---

**END OF DOCUMENT**

This guide covers how AgroSight handles all API failures gracefully!
