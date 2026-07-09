aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaasssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss# Multiple Chats and New Chat Flow

## Purpose

This document explains, in simple but detailed language:

1. What a chat session is
2. Why multiple chats work
3. How one single user can create many chats
4. What happens when the user clicks `New Chat`
5. What is stored in frontend vs backend
6. Why old chat context is not mixed into a new chat

---

## Short Answer

In this project, a chat is identified by `session_id`.

- One `session_id` = one conversation
- A new `session_id` = a new conversation
- The backend does not really know a logged-in user
- The backend only knows: "which `session_id` sent this question?"

So if the same person creates 3 chats, the system treats them like:

- Chat A -> `session_abc`
- Chat B -> `session_xyz`
- Chat C -> `session_pqr`

These are three separate conversations.

---

## Main Idea

The app separates conversations by `session_id`, not by username.

That means:

- If the same `session_id` is used again, the backend continues the same chat
- If a different `session_id` is used, the backend starts a different chat

This is the core reason multiple chats work.

---

## What Is a Session?

A session is just a unique ID used to group messages of one conversation.

Example:

```text
session_k8f3m2x9a
```

When the frontend sends a question like:

```json
{
  "question": "What is yellow rust?",
  "session_id": "session_k8f3m2x9a",
  "stream": true
}
```

the backend uses `session_k8f3m2x9a` to find old messages for that same chat.

---

## Where the Session ID Comes From

### Frontend

The frontend creates the session ID in `app/static/js/app.js`.

Important logic:

- On page load, it checks `localStorage` for `agrosight_session_id`
- If none exists, it creates a new one
- On `New Chat`, it creates another new one

Conceptually:

```javascript
let currentSessionId = localStorage.getItem('agrosight_session_id') || '';

if (!currentSessionId) {
    createNewSession();
}
```

And:

```javascript
function createNewSession() {
    currentSessionId = 'session_' + randomValue;
    localStorage.setItem('agrosight_session_id', currentSessionId);
}
```

### Backend

The backend also supports auto-generating a session ID if the request does not include one.

That happens in `app/main.py`:

```python
session_id = req.session_id or str(uuid.uuid4())
```

In your current UI flow, the frontend usually sends the session ID itself, so the backend mostly reuses that value.

---

## Why Multiple Chats Work

Multiple chats work because each chat gets a different `session_id`.

Imagine one user creates three chats:

### Chat 1

```text
session_wheat_111
```

Messages stored under:

```text
session:session_wheat_111
```

### Chat 2

```text
session_cotton_222
```

Messages stored under:

```text
session:session_cotton_222
```

### Chat 3

```text
session_prices_333
```

Messages stored under:

```text
session:session_prices_333
```

So Redis sees them as three different keys, not one mixed conversation.

---

## How the Backend Stores Chat History

The backend session store is in `app/services/session_store.py`.

It has three main functions:

- `get_history(session_id)`
- `append_turn(session_id, role, content)`
- `clear_session(session_id)`

### 1. `get_history(session_id)`

This reads old conversation for one session.

If Redis has:

```text
session:session_wheat_111
```

then `get_history("session_wheat_111")` returns:

```python
[
  {"role": "user", "content": "What is yellow rust?"},
  {"role": "assistant", "content": "Yellow rust is a fungal disease."}
]
```

If Redis has no such key, it returns:

```python
[]
```

That empty list means: this is a fresh conversation.

### 2. `append_turn(session_id, role, content)`

This adds a new message into that session history.

Example:

```python
append_turn("session_wheat_111", "user", "How to treat it?")
append_turn("session_wheat_111", "assistant", "Use recommended fungicide...")
```

Now the same session has more messages.

### 3. `clear_session(session_id)`

This deletes chat history for one session.

Example:

```python
clear_session("session_wheat_111")
```

After that, backend memory for that chat is gone.

---

## What Happens When One User Starts a New Chat

This is the part that usually causes confusion.

Suppose one person already has an old chat:

- Current chat session: `session_old_123`
- Old history already exists in Redis

Then the user clicks `New Chat`.

### Step-by-step flow

1. Frontend runs `createNewSession()`
2. A brand-new session ID is created
3. Example: `session_new_456`
4. Frontend stores that new ID in `localStorage`
5. Frontend clears the visible chat area
6. User sends first message in the new chat
7. Request goes to `/chat` with `session_id = session_new_456`
8. Backend runs `get_history("session_new_456")`
9. Redis does not find old messages for this new key
10. Backend gets `[]`
11. Agent answers without old chat history
12. Backend stores the new user and assistant messages under `session:session_new_456`

So the old chat is not reused because the key changed.

---

## Visual Flow for New Chat

```text
OLD CHAT
User is talking in: session_old_123

Redis:
session:session_old_123 -> [
  user msg 1,
  assistant msg 1,
  user msg 2,
  assistant msg 2
]

USER CLICKS "NEW CHAT"
    |
    v
Frontend creates: session_new_456
    |
    v
Next question sent with session_new_456
    |
    v
Backend checks Redis:
session:session_new_456 -> not found
    |
    v
History = []
    |
    v
Fresh conversation starts
```

---

## Important: One User Is Not the Same as One Session

In this system:

- one user can have many sessions
- one session belongs to one conversation

So:

```text
User A
  -> session_1
  -> session_2
  -> session_3
```

This means one person can maintain many independent chats.

But the backend does not store:

```text
user_id -> all sessions
```

It only stores:

```text
session_id -> messages
```

That is a very important design detail.

---

## Frontend Storage vs Backend Storage

This project actually stores chat-related data in two places.

## 1. Backend storage

Backend stores chat context in Redis.

Purpose:

- give the agent previous conversation context
- let the model answer follow-up questions

Stored as:

```text
session:<session_id> -> JSON history
```

Example:

```text
session:session_abc123
```

## 2. Frontend storage

Frontend stores chat list and rendered conversation in browser `localStorage`.

Keys used:

- `agrosight_session_id`
- `agrosight_history`
- `agrosight_sessions`

Purpose:

- remember which chat is currently open
- show chat history in sidebar
- redraw old conversation in the browser UI

This means:

- Redis is used by the AI/backend
- `localStorage` is used by the browser UI

---

## Why Both Frontend and Backend Store History

They store history for different reasons.

### Backend history

Used for AI context.

Example:

- User asks: "What is yellow rust?"
- Then asks: "How to treat it?"

The backend uses previous messages from Redis so the model understands what "it" means.

### Frontend history

Used for screen display.

Example:

- User refreshes the page
- Browser reads `agrosight_sessions`
- Old messages are shown again in the UI

So even if the UI can show old messages, the AI context still depends on backend session history.

---

## Complete Flow of One Existing Chat

Suppose current session is:

```text
session_111
```

### First message

User sends:

```text
What is wheat rust?
```

Flow:

1. Frontend sends `session_111`
2. Backend checks Redis
3. No history found
4. Retrieval runs
5. LLM generates answer
6. Backend saves:

```python
[
  {"role": "user", "content": "What is wheat rust?"},
  {"role": "assistant", "content": "...answer..."}
]
```

### Second message in same chat

User sends:

```text
How to control it?
```

Flow:

1. Frontend again sends `session_111`
2. Backend loads old history for `session_111`
3. Prompt includes old messages
4. LLM understands "`it`" means wheat rust
5. New answer is generated
6. Backend appends new turn

That is how continuity works.

---

## Complete Flow of a New Chat by the Same User

Now the same user clicks `New Chat`.

Frontend creates:

```text
session_222
```

Then user asks:

```text
Tell me cotton fertilizer
```

Flow:

1. Frontend sends `session_222`
2. Backend checks Redis for `session:session_222`
3. Not found
4. History is empty
5. Prompt has no old conversation
6. Answer is generated as a new independent conversation
7. Backend saves messages under `session:session_222`

So the same user now has:

- one old wheat chat in `session_111`
- one new cotton chat in `session_222`

They are separate.

---

## Why Old Chat Context Does Not Mix Into New Chat

Because the lookup key is different.

Old chat:

```text
session:session_111
```

New chat:

```text
session:session_222
```

When the backend does:

```python
history = get_history(session_id)
```

it only reads one key, not all chats of that browser.

That is why chat isolation works.

---

## History Limit: Only Last 5 Turns

The backend does not keep unlimited context per chat.

In `append_turn()`:

```python
max_turns = settings.max_history_turns * 2
if len(history) > max_turns:
    history = history[-max_turns:]
```

Meaning:

- `max_history_turns` is 5
- each turn means user + assistant
- total kept messages = 10

So even if one chat continues for 30 messages, only the latest 10 messages are kept for AI context.

### Why this is done

Reasons:

- lower memory use
- smaller prompts
- faster model input building
- cheaper inference
- prevents very old context from bloating the request

---

## Session Expiry

Redis stores each session with TTL.

That means after some time, old chat history expires automatically.

In `append_turn()`:

```python
r.setex(
    f"session:{session_id}",
    settings.session_ttl_seconds,
    json.dumps(history),
)
```

Meaning:

- key is stored with expiry time
- if no one uses it long enough, Redis deletes it

### Why TTL is useful

- avoids keeping useless old sessions forever
- saves memory
- lets the system clean itself automatically

---

## What If Redis Is Down?

The code has a fallback:

```python
_memory_store: dict[str, list[dict]] = defaultdict(list)
```

If Redis connection fails:

- session history is stored in Python memory
- app can still work temporarily

But there are limits:

- data is lost on server restart
- not shared across multiple app instances
- weaker than Redis for production

So Redis is the real primary store.

---

## What the User Sees vs What the System Knows

This is another important difference.

### What the user sees

The sidebar and visible chat messages come from browser `localStorage`.

### What the AI system knows

The model gets previous context from Redis or memory fallback.

So there can be edge cases like:

- browser still shows old messages from `localStorage`
- but Redis history expired
- user sees chat on screen
- backend thinks this is a conversation with no history

That can create mismatch between UI and AI memory.

---

## Real Behavior Summary

### Same chat continues when

- same `session_id` is sent again

### New chat starts when

- frontend creates a different `session_id`

### Multiple chats work because

- each chat uses a different session key

### Old history is remembered because

- backend loads messages by that session key

### Old history is forgotten because

- only last 5 turns are kept
- session can expire by TTL
- memory fallback resets on restart

---

## Example With One User and Three Chats

```text
Same user in one browser

Chat 1:
  session_a1
  topic: wheat disease

Chat 2:
  session_b2
  topic: cotton fertilizer

Chat 3:
  session_c3
  topic: mandi prices
```

Backend storage:

```text
session:session_a1 -> wheat messages
session:session_b2 -> cotton messages
session:session_c3 -> mandi messages
```

Frontend storage:

```text
agrosight_history -> list of chat cards in sidebar
agrosight_sessions -> local copy of rendered conversations
agrosight_session_id -> currently selected chat
```

So one user can have many chats without mixing them.

---

## One Limitation of Current Design

This is not true multi-user account-based chat management yet.

Current design supports:

- many sessions
- many chats in one browser
- session-based isolation

Current design does not fully support:

- authenticated user ownership
- syncing all chats across devices automatically
- backend query like "show all chats for user 42"

To support that, you would need something like:

```text
user_id -> [session_1, session_2, session_3]
```

plus database storage for chat metadata.

---

## Final Mental Model

Use this simple rule:

```text
Same session_id = same chat
New session_id = new chat
```

And this second rule:

```text
Backend remembers by session_id
Frontend displays by localStorage
```

If you remember these two rules, the full flow becomes much easier to understand.
