# Multiple Chats in Single Session - Detailed Flow

## Overview

A single `session_id` can handle **unlimited messages** (chats), but only the **last 5 user-assistant pairs** are kept in memory for context.

---

## Visual Example: Session Evolution

```
Session ID: sess_farmer_001
Created: 2026-05-04 10:00:00

TIME    USER MESSAGE                           REDIS HISTORY SIZE
────────────────────────────────────────────────────────────────

10:00   [START SESSION]
        Redis: session:sess_farmer_001 = []
        
10:05   User: "What is yellow rust?"
        ├─ Query sent to /chat endpoint
        ├─ Agent processes (no history context)
        ├─ Response streamed to browser
        └─ History appended
        Redis: [Turn 1 - 2 messages: user + assistant]  (50 KB)
        
10:10   User: "How to treat it?"
        ├─ Get history → [Turn 1 conversation]
        ├─ Include Turn 1 in prompt as context
        ├─ Agent uses this context
        ├─ Response references previous advice
        └─ History appended
        Redis: [Turn 1 + Turn 2 - 4 messages]  (100 KB)
        
10:15   User: "What fertilizer for wheat?"
        ├─ Get history → [Turn 1 + Turn 2]
        ├─ Include in prompt
        ├─ Agent processes
        └─ History appended
        Redis: [Turn 1 + Turn 2 + Turn 3 - 6 messages]  (150 KB)
        
10:20   User: "What about cotton?"
        ├─ Get history → [Turn 1 + Turn 2 + Turn 3]
        ├─ Context includes wheat discussion
        ├─ Agent compares with cotton
        └─ History appended
        Redis: [Turn 1-4 - 8 messages]  (200 KB)
        
10:25   User: "Mandi prices today?"
        ├─ Get history → [Turn 1 + Turn 2 + Turn 3 + Turn 4]
        ├─ Context includes all previous
        ├─ Agent calls mandi_price_tool
        └─ History appended
        Redis: [Turn 1-5 - 10 messages] (250 KB) ← MAX REACHED
        
10:30   User: "Best crop this season?"  ← NEW TURN (6th)
        ├─ Get history → [Turn 1-5: 10 messages]
        ├─ Process...
        ├─ History appended: [Turn 1-5 + Turn 6 = 12 messages]
        ├─ ENFORCE MAX: Keep only last 10
        ├─ Result: Delete Turn 1, Keep Turn 2-6
        └─ History updated
        Redis: [Turn 2-6 - 10 messages] (250 KB) ← MAX MAINTAINED
        
        ⚠️  Turn 1 conversation deleted from Redis!
        ⚠️  But Turn 2+ remain with all context
```

---

## Code Flow: Multiple Chats in One Session

### Session_Store.py Handling:

```python
# app/services/session_store.py

def append_turn(session_id: str, role: str, content: str) -> None:
    """Append a new turn and enforce MAX_HISTORY_TURNS"""
    
    # Step 1: Get current history
    history = get_history(session_id)
    # Example: history = [
    #   {"role": "user", "content": "What is yellow rust?"},
    #   {"role": "assistant", "content": "Yellow rust is..."},
    #   {"role": "user", "content": "How to treat it?"},
    #   {"role": "assistant", "content": "Use fungicides..."}
    # ]
    
    # Step 2: Append new message
    history.append({"role": role, "content": content})
    # Now: 5 messages (2 + 2 + 1)
    
    # Step 3: Enforce limit (MAX = 5 turns = 10 messages)
    max_turns = settings.max_history_turns * 2  # 5 * 2 = 10
    if len(history) > max_turns:
        history = history[-max_turns:]  # Keep ONLY last 10
    # If we had 11 messages, delete the oldest (Turn 1)
    
    # Step 4: Store in Redis with TTL
    r = _get_redis()
    if r is not None:
        r.setex(
            f"session:{session_id}",
            settings.session_ttl_seconds,  # 7 days = 604800 seconds
            json.dumps(history),
        )
```

---

## Detailed Example: 6 Chat Turns

### Turn 1: Yellow Rust Question

```
CLIENT REQUEST:
POST /chat
{
  "session_id": "sess_farmer_001",
  "query": "What is yellow rust?"
}

SERVER PROCESSING:
├─ Step 1: get_history("sess_farmer_001")
│  └─ Redis lookup: session:sess_farmer_001 → NOT FOUND
│  └─ Result: [] (empty)
│
├─ Step 2: retrieve_context("What is yellow rust?")
│  ├─ Encode: "What is yellow rust?"
│  ├─ Vector search: returns chunks about rust
│  └─ Rerank: top 5 results
│
├─ Step 3: Build prompt
│  System: "You are an agricultural expert..."
│  Context: [Retrieved chunks about yellow rust]
│  History: "" (empty, first turn)
│  User: "What is yellow rust?"
│
├─ Step 4: Run agent & stream response
│  "Yellow Rust caused by Puccinia striiformis..."
│
└─ Step 5: append_turn(sess_farmer_001, "user", "What is yellow rust?")
   append_turn(sess_farmer_001, "assistant", "Yellow Rust caused by...")

REDIS NOW CONTAINS:
session:sess_farmer_001 = [
  {"role": "user", "content": "What is yellow rust?"},
  {"role": "assistant", "content": "Yellow Rust caused by Puccinia striiformis..."}
]
```

### Turn 2: Treatment Question

```
CLIENT REQUEST:
POST /chat
{
  "session_id": "sess_farmer_001",
  "query": "How to treat it?"
}

SERVER PROCESSING:
├─ Step 1: get_history("sess_farmer_001")
│  └─ Redis lookup: session:sess_farmer_001
│  └─ Result: [Turn 1 messages: 2 items]
│
├─ Step 2: retrieve_context("How to treat it?")
│  ├─ Encode & search
│  └─ Returns: chunks about fungicides
│
├─ Step 3: Build prompt WITH HISTORY
│  System: "You are an agricultural expert..."
│  
│  HISTORY (From Redis):
│  User: "What is yellow rust?"
│  Assistant: "Yellow Rust caused by..."
│  
│  Context: [Fungicide treatment chunks]
│  User: "How to treat it?"
│
├─ Step 4: Agent response (uses context from Turn 1)
│  "Based on our discussion about rust, use Propiconazole..."
│
└─ Step 5: Append both messages
   history = [Turn 1 msgs (2)] + [Turn 2 msgs (2)] = 4 messages

REDIS NOW CONTAINS:
session:sess_farmer_001 = [
  {"role": "user", "content": "What is yellow rust?"},
  {"role": "assistant", "content": "Yellow Rust caused by..."},
  {"role": "user", "content": "How to treat it?"},
  {"role": "assistant", "content": "Use Propiconazole..."}
]
```

### Turn 3-5: Continue Building

```
Turn 3:
history = 4 messages + 2 new = 6 messages

Turn 4:
history = 6 messages + 2 new = 8 messages

Turn 5:
history = 8 messages + 2 new = 10 messages ✓ (AT MAX)

Turn 6: ⚠️ OVERFLOW
history = 10 messages + 2 new = 12 messages ✗ (EXCEEDS MAX)

ENFORCEMENT:
history = history[-10:]  # Keep ONLY last 10
Result: Delete Turn 1, Keep Turn 2-6
```

### Turn 6: Overflow & Cleanup

```
CLIENT REQUEST:
POST /chat
{
  "session_id": "sess_farmer_001",
  "query": "Best crop to grow?"
}

SERVER PROCESSING:
├─ Step 1: get_history()
│  └─ Result: 10 messages (Turn 1-5)
│
├─ Step 2: retrieve_context()
│  └─ Returns crop recommendations
│
├─ Step 3: Build prompt
│  HISTORY:
│  Turn 1: user "What is yellow rust?" + assistant response
│  Turn 2: user "How to treat it?" + assistant response
│  Turn 3: ...
│  Turn 4: ...
│  Turn 5: ...
│  (10 messages total)
│  
│  User: "Best crop to grow?"
│
├─ Step 4: Agent response
│  Uses context of previous 5 turns
│
└─ Step 5: Append & enforce
   history = [10 messages] + 2 new = 12 messages
   if len(12) > max(10):
       history = history[-10:]  # TRIM!
   
   RESULT: Delete Turn 1! Keep Turn 2-6

REDIS NOW CONTAINS (Turn 1 DELETED):
session:sess_farmer_001 = [
  {"role": "user", "content": "How to treat it?"},
  {"role": "assistant", "content": "Use Propiconazole..."},
  ... (Turn 2-5 complete) ...
  {"role": "user", "content": "Best crop to grow?"},
  {"role": "assistant", "content": "Based on..."}
]

⚠️ IMPLICATION:
- Turn 1 conversation about yellow rust NO LONGER in context
- If user asks about yellow rust again, no memory of Turn 1
- Must re-retrieve from vector DB
- Turn 2-6 still available for context
```

---

## Memory State at Each Turn

```
Turn   Messages   Redis Size   Max Reached?   Notes
────────────────────────────────────────────────────
1      2          ~50 KB       No             First turn
2      4          ~100 KB      No             History loaded
3      6          ~150 KB      No             Growing context
4      8          ~200 KB      No             Near limit
5      10         ~250 KB      YES ✓          At max (5 pairs)
6      12 → 10   ~250 KB      YES ✓          Turn 1 deleted
7      12 → 10   ~250 KB      YES ✓          Turn 2 deleted
8      12 → 10   ~250 KB      YES ✓          Turn 3 deleted
...
∞      10 (stable) ~250 KB    YES ✓          Always maintain 5 turns
```

---

## Frontend Handling: Multiple Chats

### Browser Session Storage (app/static/js/app.js):

```javascript
// Frontend maintains its own history in localStorage
const sessionHistory = {
  "sess_farmer_001": [
    {role: "user", text: "What is yellow rust?"},
    {role: "assistant", text: "Yellow Rust caused by..."},
    {role: "user", text: "How to treat it?"},
    {role: "assistant", text: "Use Propiconazole..."},
    {role: "user", text: "What fertilizer for wheat?"},
    {role: "assistant", text: "Nitrogen 120 kg/ha..."},
    // ... can have UNLIMITED messages in browser
    // (limited by localStorage ~5-10 MB)
  ]
};

// Function: Send message
async function submitQuery(query) {
  const sessionId = localStorage.getItem('agrosight_session_id');
  
  // Add to frontend display immediately
  appendMessage("user", query);
  
  // Send to server
  const response = await fetch('/chat', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      query: query
    })
  });
  
  // Stream response
  const stream = response.body.getReader();
  let fullResponse = "";
  
  while (true) {
    const {done, value} = await stream.read();
    if (done) break;
    
    const text = new TextDecoder().decode(value);
    fullResponse += text;
    displayChunk(text);  // Show token by token
  }
  
  // Add assistant response to frontend
  appendMessage("assistant", fullResponse);
}

// Result: Frontend shows ALL messages (unlimited)
// But server only uses last 5 turns for LLM context
```

---

## Context Window Management

### What Gets Included in LLM Prompt:

```
For Turn 6 ("Best crop?"):

SYSTEM PROMPT (fixed)
├─ "You are an agricultural expert..."
├─ Token count: ~100 tokens

RETRIEVED CONTEXT (from vector DB)
├─ Top 5 reranked chunks about crops
├─ Token count: ~500 tokens

CONVERSATION HISTORY (last 5 turns)
├─ Turn 2: user question + assistant answer
├─ Turn 3: user question + assistant answer
├─ Turn 4: user question + assistant answer
├─ Turn 5: user question + assistant answer
├─ Token count: ~400 tokens

CURRENT QUERY
├─ "Best crop to grow?"
├─ Token count: ~10 tokens

TOTAL TOKEN COUNT: ~1010 tokens (under 2000 token limit)

✓ Everything fits in context window
✓ LLM can see last 5 turns of conversation
✓ Can maintain coherent multi-turn conversation
```

---

## Scenario: User Asks Same Question Twice

### Scenario: User asks about yellow rust in Turn 1, then again in Turn 7

```
TURN 1: "What is yellow rust?"
├─ Retrieved from vector DB
├─ Stored in Redis history
└─ Response: "Yellow Rust caused by Puccinia striiformis..."

TURNS 2-6: (Various other questions)
├─ Redis history grows
├─ At Turn 6, Turn 1 gets deleted (overflow)
└─ No memory of Turn 1 conversation

TURN 7: "Tell me about yellow rust again"
├─ get_history() → [Turn 2-6 only]
├─ NO MENTION of Turn 1 in history
├─ But Vector DB still has the knowledge!
├─ retrieve_context() → [Same chunks as Turn 1]
├─ Agent responds: "Yellow Rust caused by..."
└─ Response same, but not using chat history
```

---

## Multiple Sessions Simultaneously

### Different Users, Different Sessions:

```
Browser 1 (Session: sess_user_A)
├─ Turn 1: "Wheat MSP?"
├─ Turn 2: "Cotton yield?"
└─ Redis: session:sess_user_A = [4 messages]

Browser 2 (Session: sess_user_B)
├─ Turn 1: "Yellow rust treatment?"
├─ Turn 2: "Fertilizer dose?"
└─ Redis: session:sess_user_B = [4 messages]

Browser 3 (Session: sess_user_C)
├─ Turn 1: "Mandi prices?"
└─ Redis: session:sess_user_C = [2 messages]

Redis Data:
├─ session:sess_user_A = [4 messages]
├─ session:sess_user_B = [4 messages]
└─ session:sess_user_C = [2 messages]
Total: 10 messages across 3 sessions

Each GET /chat with sess_user_A:
└─ Loads ONLY sess_user_A's history
└─ Ignores sess_user_B and sess_user_C
```

---

## Summary: Multi-Chat Flow

| Aspect | Details |
|--------|---------|
| **Session Scope** | Single session_id spans entire conversation session |
| **Message Limit** | Last 5 user-assistant pairs (10 messages) in Redis |
| **Overflow** | Oldest turn deleted when exceeds 10 messages |
| **Frontend** | Shows all messages (unlimited in browser) |
| **Backend Context** | Only uses last 5 turns for LLM prompt |
| **Vector DB** | Always searchable (not limited by history) |
| **TTL** | 7 days before Redis auto-deletes entire session |
| **Concurrent Users** | Each user has separate session_id in Redis |
| **Turn Sequence** | User message → Server processes → Assistant response → Append |

---

## Config to Adjust:

```python
# config.py

# Increase history turns (more context for LLM)
max_history_turns = 10  # Keep last 10 pairs (20 messages)

# Decrease history turns (save memory)
max_history_turns = 2   # Keep last 2 pairs (4 messages)

# Change session TTL (longer retention)
session_ttl_seconds = 2592000  # 30 days instead of 7

# Redis memory limit
# docker-compose.yml: --maxmemory 512mb (increased from 256mb)
```

---

## References

- Multiple Chats: `app/services/session_store.py` - `append_turn()` function
- History Loading: `app/services/agent.py` - `run_agent()` function
- Frontend Chat Loop: `app/static/js/app.js` - `submitQuery()` function
- Config: `app/utils/config.py` - `max_history_turns`, `session_ttl_seconds`
