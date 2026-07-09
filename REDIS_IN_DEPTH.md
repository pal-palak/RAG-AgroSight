# Redis: Complete In-Depth Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Data Structures](#data-structures)
4. [Memory Management](#memory-management)
5. [Persistence](#persistence)
6. [Replication & Clustering](#replication--clustering)
7. [Commands & Operations](#commands--operations)
8. [Performance Optimization](#performance-optimization)
9. [Use Cases in AgroSight](#use-cases-in-agrosight)
10. [Best Practices](#best-practices)

---

## Introduction

### What is Redis?

Redis (Remote Dictionary Server) is an in-memory data structure store that functions as:
- **Cache layer** – Ultra-fast data access
- **Message broker** – Pub/Sub messaging
- **Real-time analytics** – Stream processing
- **Session store** – User session management
- **Rate limiter** – Request throttling

**Key Characteristics:**
- **In-memory storage** – Data lives in RAM for microsecond latency
- **Persistent** – Can save to disk (RDB snapshots or AOF logs)
- **Single-threaded** – Atomic operations, no race conditions
- **Networked** – TCP-based client-server protocol
- **Versatile** – Supports 8+ data types natively

### Why Redis?

| Feature | Redis | SQL DB | Memcached |
|---------|-------|--------|-----------|
| Latency | <1ms | 10-100ms | <1ms |
| Data Types | 8+ types | Tables | Key-value only |
| Persistence | RDB + AOF | ✅ Native | ✗ Memory only |
| Pub/Sub | ✅ Built-in | ✗ | ✗ |
| Transactions | ✅ ACID-like | ✅ ACID | ✗ |
| Scripting | Lua | SQL | ✗ |

**Performance Numbers (Intel Xeon):**
```
SET operations:     ~110,000 ops/sec
GET operations:     ~95,000 ops/sec
LPUSH operations:   ~110,000 ops/sec
LPOP operations:    ~100,000 ops/sec
```

---

## Core Concepts

### 1. In-Memory Architecture

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (FastAPI, Django, Node.js, etc.)       │
└────────────────┬────────────────────────┘
                 │ TCP (Port 6379)
┌────────────────▼────────────────────────┐
│       Redis Server (Single Process)     │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    Event Loop (Libuv)           │   │
│  │  - Handles concurrent clients   │   │
│  │  - I/O multiplexing             │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    Command Processor            │   │
│  │  - Single-threaded (atomic)     │   │
│  │  - No locks needed              │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    In-Memory Data Store         │   │
│  │  - Hash tables (main DB)        │   │
│  │  - Multiple databases (0-15)    │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    Persistence Layer            │   │
│  │  - RDB snapshots                │   │
│  │  - AOF (Append-Only File)       │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 2. Single-Threaded Model

**How atomicity is guaranteed:**

```python
# In Redis, this is atomic (thread-safe):
INCR counter     # Increment counter by 1
LPUSH list val   # Push value to list
HSET hash k v    # Set hash field

# In SQL, this needs locks:
BEGIN TRANSACTION;
  SELECT value FROM counter;
  UPDATE counter SET value = value + 1;  -- Race condition without lock!
COMMIT;
```

**Why single-threaded is powerful:**
- No context switching overhead
- No deadlocks
- Predictable latency
- Easier to reason about

**Limitation:** Can only use 1 CPU core (Redis 7.0+ adds multithreading for I/O)

### 3. Key-Value Model

Every piece of data in Redis is stored as a key-value pair:

```redis
SET user:1000:name "Raj Patel"           // String key
SET user:1000:age 32                     // String key
HSET user:1000 email "raj@example.com"   // Hash key
LPUSH user:1000:activities "logged_in"   // List key
SADD user:1000:tags "farmer" "premium"   // Set key
ZADD user:1000:scores 95 "wheat_yields"  // Sorted set key
```

**Key Naming Convention (Best Practice):**
```
object_type:object_id:field
user:1000:name          → User object, ID 1000, name field
session:abc123xyz       → Session with ID abc123xyz
cache:weather:delhi     → Weather cache for Delhi
queue:notifications     → Notification queue
```

### 4. Expiration & TTL

Redis keys can expire automatically:

```redis
SET api_token "xyz789" EX 3600        // Expires in 3600 seconds (1 hour)
SET session "data" PX 1800000         // Expires in 1800000 milliseconds
EXPIRE key_name 600                    // Set expiration to 600 seconds
TTL key_name                           // Get remaining seconds (-1 = no expiry)
PTTL key_name                          // Get remaining milliseconds
PERSIST key_name                       // Remove expiration
```

**Use Cases:**
- Session tokens (auto-cleanup without code)
- Rate limiting buckets
- Cache invalidation
- Temporary locks

---

## Data Structures

### 1. Strings

**Definition:** Simple binary-safe strings (can store text, numbers, serialized JSON)

**Memory Layout:**
```
Key: "user:1000:name"
Value: "Raj Patel" (9 bytes)
Internal: SDS (Simple Dynamic String) - tracks length, capacity
```

**Operations:**

```redis
SET key value                 // Set key to value
GET key                       // Get value of key
MSET k1 v1 k2 v2 k3 v3      // Set multiple keys (atomic)
MGET k1 k2 k3                // Get multiple keys

APPEND key " Extended"       // Append to string
STRLEN key                   // Get length

INCR counter                 // Increment by 1 (for numbers)
INCRBY counter 5             // Increment by N
DECR counter                 // Decrement by 1
DECRBY counter 3             // Decrement by N
INCRBYFLOAT price 2.5        // Increment by float

GETSET key "new_value"       // Set and return old value
GETRANGE key 0 4             // Get substring (chars 0-4)
SETRANGE key 6 "new"         // Replace substring
```

**Performance:**
- Time complexity: O(1) for most operations
- Memory: ~45 bytes overhead per key + string data

**Use Cases in AgroSight:**
```redis
SET weather:delhi:temp 28.5         // Current temperature
SET crop:wheat:price 2450           // Commodity price cache
INCR user:1000:api_calls           // Rate limiting counter
SET session:user123 '{"id":123}'   // Session serialization
```

---

### 2. Lists

**Definition:** Ordered collections of strings (doubly-linked list internally)

**Memory Layout:**
```
Key: "notifications:user:1000"
[
  "irrigation_alert",      // Most recent (head)
  "fertilizer_reminder",
  "pest_disease_warning",
  "weather_forecast"       // Oldest (tail)
]
```

**Operations:**

```redis
LPUSH key val1 val2 val3  // Push values to LEFT (head) - returns length
RPUSH key val1 val2        // Push values to RIGHT (tail)
LPOP key                   // Remove and return LEFT element
RPOP key                   // Remove and return RIGHT element
LPOP key 2                 // Remove 2 elements (Redis 6.2+)

LLEN key                   // Get list length
LINDEX key 0               // Get element at index
LRANGE key 0 -1            // Get all elements (0 to end)
LRANGE key 0 9             // Get first 10 elements
LSET key 2 "new_val"       // Set element at index

LTRIM key 0 99             // Keep only first 100 elements (trim rest)
LINSERT key BEFORE "pivot" "new_val"  // Insert before pivot element
RPOPLPUSH src dst          // Pop from src, push to dst (atomic)
LPOS key "value"           // Find first index of value
```

**Performance:**
- Time complexity: O(1) for head/tail operations, O(N) for index access
- Internal: Doubly-linked list for large lists, ziplist for small lists

**Use Cases in AgroSight:**
```redis
LPUSH alerts:user:1000 '{"type":"pest_alert","crop":"wheat"}'
LPUSH activity_log "logged_in"
RPUSH job_queue '{"task":"process_mandi_prices"}'

// Get recent N alerts
LRANGE alerts:user:1000 0 4

// Trim old data (keep last 1000 alerts)
LTRIM alerts:user:1000 0 999
```

---

### 3. Hashes

**Definition:** Maps of field-value pairs (like objects/dictionaries)

**Memory Layout:**
```
Key: "user:1000"
{
  "name": "Raj Patel",
  "email": "raj@example.com",
  "age": "32",
  "state": "Gujarat",
  "crops": "wheat,cotton"
}
```

**Operations:**

```redis
HSET key field value               // Set single field
HSET key f1 v1 f2 v2 f3 v3        // Set multiple fields (atomic)
HGET key field                     // Get field value
HMGET key f1 f2 f3                // Get multiple fields
HGETALL key                        // Get all fields and values
HKEYS key                          // Get all field names
HVALS key                          // Get all values
HLEN key                           // Count of fields
HEXISTS key field                  // Check if field exists

HINCRBY key field 1                // Increment field (numeric)
HINCRBYFLOAT key field 2.5        // Increment by float

HDEL key field1 field2             // Delete fields
HSETNX key field value             // Set only if not exists
HSTRLEN key field                  // Get field value length
```

**Performance:**
- Time complexity: O(1) for single operations, O(N) for full hash operations
- Memory: More efficient than storing multiple string keys for related data

**Example in AgroSight:**

```redis
// Instead of:
SET user:1000:name "Raj Patel"
SET user:1000:email "raj@example.com"
SET user:1000:state "Gujarat"

// Use:
HSET user:1000 name "Raj Patel" email "raj@example.com" state "Gujarat"

// Access:
HGET user:1000 name           // "Raj Patel"
HGETALL user:1000             // All user data at once
```

**Real Example:**

```redis
HSET mandi_market:delhi name "Safal Produce Market"
HSET mandi_market:delhi state "Delhi"
HSET mandi_market:delhi price_wheat "2450"
HSET mandi_market:delhi price_rice "3200"
HSET mandi_market:delhi updated_at "2026-05-06T14:30:00Z"

// Get all market info
HGETALL mandi_market:delhi
// Returns: ["name", "Safal Produce Market", "state", "Delhi", ...]
```

---

### 4. Sets

**Definition:** Unordered collections of unique strings

**Memory Layout:**
```
Key: "user:1000:tags"
{
  "farmer",
  "premium_member",
  "wheat_crop",
  "fertilizer_buyer"
}
```

**Operations:**

```redis
SADD key member1 member2       // Add members
SREM key member1 member2       // Remove members
SCARD key                      // Count of members
SMEMBERS key                   // Get all members
SISMEMBER key member           // Check if member exists
SRANDMEMBER key                // Get random member
SRANDMEMBER key 3              // Get 3 random members
SPOP key                       // Remove and return random member

// Set operations
SUNION set1 set2               // Union (members in either)
SINTER set1 set2               // Intersection (members in both)
SDIFF set1 set2                // Difference (in set1, not in set2)
SUNIONSTORE dst s1 s2          // Union and store in dst
SINTERSTORE dst s1 s2          // Intersection and store

SMOVE src dst member           // Move member from src to dst
```

**Performance:**
- Time complexity: O(1) for add/remove/check, O(N) for full set operations
- Internal: Hash table (fast uniqueness checking)


---

### 5. Sorted Sets (ZSets)

**Definition:** Sets with scores (members ranked by score, 0-based index)

**Memory Layout:**
```
Key: "leaderboard:farmers"
{
  "farmer_1": 9500 points,      // Rank 1
  "farmer_2": 8300 points,      // Rank 2
  "farmer_3": 7100 points,      // Rank 3
  "farmer_4": 6200 points       // Rank 4
}
```

**Operations:**

```redis
ZADD key score member              // Add member with score
ZADD key 100 member1 200 member2   // Add multiple

ZCARD key                          // Count of members
ZCOUNT key min max                 // Count members in score range
ZRANGE key 0 -1                    // Get all members (low to high score)
ZRANGE key 0 -1 WITHSCORES         // Include scores
ZREVRANGE key 0 -1                 // Get all members (high to low)
ZREVRANGE key 0 -1 WITHSCORES      // Reverse with scores

ZRANK key member                   // Get rank (0-based, low to high)
ZREVRANK key member                // Get reverse rank (high to low)
ZSCORE key member                  // Get score of member
ZREM key member1 member2           // Remove members

ZINCRBY key amount member          // Increment score
ZPOPMIN key                        // Remove and return member with lowest score
ZPOPMAX key                        // Remove and return member with highest score

// Range by score
ZRANGEBYSCORE key 100 500          // Get members with score 100-500
ZRANGEBYSCORE key -inf +inf        // All members (no score bounds)
ZRANGEBYSCORE key (100 (500        // Score 100 < score < 500 (exclusive)

// Count in range
ZCOUNT key 100 500                 // Count members with score 100-500

// Remove by rank
ZREMRANGEBYRANK key 0 10           // Remove first 11 members
ZREMRANGEBYSCORE key 0 100         // Remove members with score 0-100
```

**Performance:**
- Time complexity: O(log N) for add/remove, O(N log N) for range ops
- Internal: Skip list (like balanced tree)

**Use Cases in AgroSight:**

```redis
// Leaderboard (top farmers by yield)
ZADD crop_yields:wheat 2500 "farmer_001"
ZADD crop_yields:wheat 2800 "farmer_002"
ZADD crop_yields:wheat 2600 "farmer_003"

// Get top 10 farmers
ZREVRANGE crop_yields:wheat 0 9 WITHSCORES

// Get farmers with yield > 2500
ZRANGEBYSCORE crop_yields:wheat 2500 +inf WITHSCORES

// Increment yield
ZINCRBY crop_yields:wheat 100 "farmer_001"

// Rate limiting (timestamp-based)
ZADD rate_limit:api:user_1000 1609459200 "request_1"
ZADD rate_limit:api:user_1000 1609459201 "request_2"

// Count requests in last 60 seconds
ZCOUNT rate_limit:api:user_1000 (1609459200-60 +inf

// Time-based events
ZADD events:scheduled (current_time + delay) event_id
ZRANGEBYSCORE events:scheduled 0 current_time  // Get due events
```

---

## Memory Management

### 1. Memory Usage Analysis

```redis
// Check memory stats
INFO memory
```

**Output:**
```
used_memory: 1048576              // 1 MB in bytes
used_memory_human: 1M             // Human readable
used_memory_rss: 2097152          // Physical memory from OS
used_memory_peak: 2097152         // Peak memory
used_memory_overhead: 524288      // Redis internals overhead
used_memory_dataset: 524288       // Actual data
used_memory_dataset_perc: 50%     // Data % of used memory
mem_fragmentation_ratio: 1.5      // RSS / used memory (>1.5 = fragmentation)
```

### 2. Eviction Policies

When Redis reaches `maxmemory`, it evicts keys based on policy:

**Configuration:**
```redis
maxmemory 268435456               // 256 MB limit
maxmemory-policy allkeys-lru      // Eviction policy
```

**Available Policies:**

| Policy | Behavior |
|--------|----------|
| `noeviction` | Return error when full (default) |
| `allkeys-lru` | Evict least-recently-used keys |
| `volatile-lru` | Evict LRU keys with expiration |
| `allkeys-lfu` | Evict least-frequently-used keys |
| `volatile-lfu` | Evict LFU keys with expiration |
| `allkeys-random` | Evict random key |
| `volatile-random` | Evict random key with expiration |
| `volatile-ttl` | Evict key with shortest TTL |

**Recommendation for AgroSight:**
```redis
maxmemory 2gb                  // Adjust to server capacity
maxmemory-policy allkeys-lru   // Keep recently-used sessions
```

### 3. Memory Optimization Tips

**Before:**
```redis
SET user:1000:name "Raj Patel"     // 50+ bytes (key + value overhead)
SET user:1000:email "raj@..."      // 50+ bytes
SET user:1000:state "Gujarat"      // 50+ bytes
TOTAL: 150+ bytes for 3 fields
```

**After:**
```redis
HSET user:1000 name "Raj Patel" email "raj@..." state "Gujarat"
TOTAL: 130 bytes for 3 fields (13% savings)
```

**More optimizations:**

```python
# Use shorter key names in production
# NOT: user:user_id:user_profile:first_name
# YES: u:1000:fn

# Serialize complex objects
import json
data = {"name": "Raj", "crops": ["wheat", "cotton"]}
redis.set("user:1000:data", json.dumps(data))  # Smaller than individual keys

# Use compression for large values
import zlib
compressed = zlib.compress(large_string.encode())
redis.set("cache:key", compressed)
```

---

## Persistence

### 1. RDB (Snapshot)

**What:** Point-in-time snapshot of entire dataset, binary format

**How it works:**
```
Time 0s:  Data in memory
Time 60s: SAVE command triggered
          └─→ Fork child process
              └─→ Child writes snapshot to disk (dump.rdb)
              └─→ Main process continues accepting commands
Time 120s: Snapshot complete
```

**Configuration:**
```redis
# Save snapshot if conditions met (any one is enough)
save 900 1        // Save if 1 key changed in 900 seconds
save 300 10       // Save if 10 keys changed in 300 seconds
save 60 10000     // Save if 10000 keys changed in 60 seconds

# Or disable automatic saves
# save ""

# Save on shutdown
stop-writes-on-bgsave-error yes
```

**Performance Impact:**
```
save (synchronous):
  └─→ BLOCKS all commands until complete
  └─→ NEVER use in production

bgsave (background):
  └─→ Forks child process
  └─→ Main process continues
  └─→ Memory: Doubles during snapshot (copy-on-write)
  └─→ Disk I/O: Medium impact

lastsave               // Last save timestamp
BGSAVE                 // Trigger background save
```

**Advantages:**
✅ Fast restore (load dump.rdb is quick)
✅ Compact format (good for backups)
✅ Low overhead when done in background

**Disadvantages:**
✗ Data loss possible (if server crashes between saves)
✗ Memory overhead (copy-on-write during fork)

### 2. AOF (Append-Only File)

**What:** Log of every write command, text format

**How it works:**
```
Command 1: SET user:1000:name "Raj Patel"
           └─→ Appended to appendonly.aof
           └─→ fsync to disk (configurable)

Command 2: LPUSH notifications "alert_1"
           └─→ Appended to appendonly.aof
           └─→ fsync to disk

On restart:
  └─→ Replay all commands in order
  └─→ Reconstruct exact state
```

**Configuration:**
```redis
appendonly yes                    // Enable AOF

appendfsync always                // fsync after EVERY command (safest, slowest)
appendfsync everysec              // fsync every 1 second (default, balanced)
appendfsync no                    // OS decides fsync (fastest, risky)

# AOF rewrite settings
auto-aof-rewrite-percentage 100   // Rewrite if size > 100% of last rewrite
auto-aof-rewrite-min-size 67108864 // Only rewrite if > 64MB
```

**AOF Rewrite (compaction):**
```
Original appendonly.aof:
  SET key val1
  SET key val2
  SET key val3
  DEL key
  SET key val4
  (2000 commands, 5 MB)

After BGREWRITEAOF:
  SET key val4
  (1 command, 50 bytes - optimized!)
```

**Commands:**
```redis
BGREWRITEAOF              // Trigger rewrite in background
```

**Advantages:**
✅ Very safe (can fsync after every command)
✅ Human-readable format
✅ Automatic compaction (rewrite)

**Disadvantages:**
✗ Slower restore (replay all commands)
✗ Larger file size (than RDB)
✗ More CPU during writes (if appendfsync always)

### 3. Hybrid Persistence (RDB + AOF)

**Recommended Setup:**
```redis
save 900 1                        // RDB snapshot every 15 min
save 300 10                       // RDB snapshot every 5 min (10 changes)

appendonly yes                    // AOF enabled
appendfsync everysec              // Balance safety and speed

# Enable mixed RDB-AOF format (Redis 4.0+)
aof-use-rdb-preamble yes          // Use RDB as base, then AOF for recent changes
```

**How it works:**
```
RDB + AOF Hybrid:
  dump.rdb (base snapshot)
  + appendonly.aof (recent commands)
  = Faster startup + High safety
```

---

## Replication & Clustering

### 1. Master-Replica Replication

**Architecture:**
```
┌─────────────────┐
│  Master Server  │
│  (Primary)      │
└────────┬────────┘
         │ Replication stream
         │ Commands replicated
         │ in real-time
┌────────▼─────────┐     ┌──────────────────┐
│ Replica Server 1 │     │ Replica Server 2 │
│ (Read-only)      │     │ (Read-only)      │
└──────────────────┘     └──────────────────┘
```

**Setup Master:**
```redis
# Master configuration
port 6379
bind 0.0.0.0
requirepass "master_password"     // Optional password
```

**Setup Replica:**
```redis
# Replica configuration
port 6380
replicaof 192.168.1.100 6379      // Connect to master
masterauth "master_password"       // Master password

# Allow reads on replica (writes go to master)
replica-read-only yes
```

**Commands:**
```redis
# On replica
INFO replication              // Check replication status
ROLE                         // Check if master/replica/sentinel

# On master
SLAVEOF NO ONE               // Promote replica to master (Older syntax)
REPLICAOF NO ONE             // Promote replica to master (New syntax)
```

**Use Cases in AgroSight:**
```
Master Server: Production writes (price updates, alerts)
Replica 1: Read-heavy operations (analytics, reports)
Replica 2: Backup/standby (failover)

Read-write split:
  ├─→ Writes → Master (127.0.0.1:6379)
  ├─→ Reads → Replica (127.0.0.1:6380)
  └─→ High availability → Auto-failover with Sentinel
```

### 2. Redis Sentinel

**Purpose:** Auto-failover, monitoring, notifications

**Architecture:**
```
┌──────────────────────────────────────┐
│       Redis Sentinel Cluster         │
│ (minimum 3 sentinels for quorum)     │
├──────────────────────────────────────┤
│  Sentinel 1  │  Sentinel 2  │ Sent 3 │
│  (Monitor)   │  (Monitor)   │(Monit) │
└──────────┬───────────┬───────────────┘
           │           │
      ┌────▼──┐    ┌───▼────┐
      │Master │    │Replica 1│  (If master fails)
      └────┬──┘    └────┬────┘   (Sentinel promotes
           │            │          replica to master)
           └─ Syncing ──┘
```

**Configuration (sentinel.conf):**
```redis
port 26379
sentinel monitor mymaster 127.0.0.1 6379 2    // Master info + quorum
sentinel down-after-milliseconds mymaster 5000 // Timeout detection
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
```

**Behavior:**
- Detects master failure (no heartbeat in 5 seconds)
- Votes for failover (quorum = 2/3 sentinels agree)
- Promotes replica to master (< 30 seconds)
- Updates clients (redirects to new master)

---

### 3. Redis Cluster

**Purpose:** Horizontal scaling, sharding, high availability

**Architecture:**
```
┌─────────────────────────────────────┐
│      Redis Cluster (6 nodes)        │
├─────────────────────────────────────┤
│  Master 1   │  Master 2  │ Master 3 │
│ (Slots 0-5) │ (Slots 6-10)(Slots ...) │
├─────────────────────────────────────┤
│ Replica 1   │  Replica 2 │ Replica 3 │
│(Backup 1)   │ (Backup 2) │(Backup 3) │
└─────────────────────────────────────┘

16,384 hash slots total
Each key hashes to a slot
Each master owns range of slots
```

**Setup:**
```bash
# 1. Create 6 nodes (3 masters, 3 replicas)
redis-server --port 7000 --cluster-enabled yes --cluster-config-file nodes-7000.conf
redis-server --port 7001 --cluster-enabled yes --cluster-config-file nodes-7001.conf
# ... 6 times total

# 2. Create cluster
redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 \
  127.0.0.1:7002 127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1

# 3. Verify
redis-cli -c -p 7000   # -c = cluster mode
```

**Key Point:**
```
CRC16(key) mod 16384 = slot number

Example:
  key = "user:1000"
  slot = CRC16("user:1000") % 16384 = 5000
  → Goes to master owning slot 5000
```

**When to use:**
- Dataset > 100 GB
- Need horizontal scaling
- Can tolerate multi-key operation limitations
- High throughput (millions ops/sec)

---

## Commands & Operations

### 1. Key Management

```redis
// Basic operations
DEL key1 key2 key3           // Delete keys, returns count
UNLINK key1 key2             // Async delete (faster, cleaner)
DUMP key                     // Serialize key to string (restore elsewhere)
EXISTS key1 key2             // Check if keys exist, returns count

EXPIRE key 600               // Set expiration (seconds)
PEXPIRE key 600000           // Set expiration (milliseconds)
EXPIREAT key 1609459200      // Expiration at Unix timestamp
TTL key                      // Get remaining seconds (-1 no exp, -2 no key)
PTTL key                     // Get remaining milliseconds
PERSIST key                  // Remove expiration

// Scanning (non-blocking iteration)
KEYS pattern                 // ⚠️ BLOCKS server, never use in production
SCAN cursor [MATCH pat] [COUNT n]  // Iterating (non-blocking)

// Scanning example
SCAN 0              // Returns: cursor + keys
SCAN "0"            // Iterate keys

// Get key type
TYPE key            // Returns: "string", "list", "hash", "set", "zset", "stream", "none"

// Rename
RENAME oldkey newkey           // Rename key
RENAMENX oldkey newkey         // Rename only if newkey doesn't exist

// Random key
RANDOMKEY                      // Get random key from DB
```

### 2. Bit Operations

```redis
// Set/get individual bits
SETBIT bits 0 1               // Set bit at offset 0 to 1
GETBIT bits 0                 // Get bit at offset 0

// Bit field operations
BITCOUNT key                  // Count set bits (1s)
BITCOUNT key 0 1              // Count bits in byte 0-1
BITPOS key 1                  // Find first bit set to 1
BITPOS key 0 2 2              // Find first 0 in byte 2

// Bit operations between keys
BITOP AND destkey key1 key2   // AND operation, store in destkey
BITOP OR destkey key1 key2    // OR operation
BITOP XOR destkey key1 key2   // XOR operation
BITOP NOT destkey key         // NOT operation

// Use case: user active status
SETBIT active:2026-05-06 1000 1  // User 1000 active today
GETBIT active:2026-05-06 1000    // 1 (yes active)
```

### 3. HyperLogLog

**Purpose:** Approximate count of unique elements (very memory efficient)

```redis
// Add elements
PFADD hll a b c d e          // Add to HyperLogLog
PFCOUNT hll                  // Approximate count of unique (~5 elements)

// Merge
PFMERGE destkey hll1 hll2    // Union of two HyperLogLogs

// Use case: unique visitors per day
PFADD visitors:2026-05-06 user1 user2 user3 user4
PFADD visitors:2026-05-07 user2 user3 user4 user5
PFCOUNT visitors:2026-05-06              // ~4 users
PFMERGE week_visitors visitors:2026-05-* // Merge all days
PFCOUNT week_visitors                    // ~5 unique users in week
```

### 4. Transactions

```redis
MULTI                        // Start transaction
  SET key1 val1
  INCR counter
  LPUSH list item
EXEC                         // Execute all (atomic)

// Discard transaction
MULTI
  SET key val
DISCARD                      // Cancel, don't execute

// WATCH (optimistic lock)
WATCH user:1000              // Watch key for changes
MULTI
  HSET user:1000 balance 1000
EXEC                         // Fails if user:1000 changed by another client

// Use case: transfer money atomically
WATCH sender:balance
WATCH recipient:balance
balance_sender = GET sender:balance
MULTI
  DECRBY sender:balance 100
  INCRBY recipient:balance 100
EXEC
```

### 5. Publish-Subscribe (Pub/Sub)

```redis
// Subscriber
SUBSCRIBE channel1 channel2  // Listen to channels
PSUBSCRIBE chan:*           // Pattern subscribe

// Publisher
PUBLISH channel1 "message"   // Send message, returns subscriber count

// Unsubscribe
UNSUBSCRIBE channel1         // Unsubscribe
PUNSUBSCRIBE chan:*          // Pattern unsubscribe

// Query
PUBSUB CHANNELS              // List active channels
PUBSUB NUMSUB ch1 ch2        // Subscriber count per channel

// Use case: real-time alerts in AgroSight
# Subscriber (Python)
pubsub = redis.pubsub()
pubsub.subscribe("alerts:weather")
for message in pubsub.listen():
    if message["type"] == "message":
        alert = json.loads(message["data"])
        notify_user(alert)

# Publisher
redis.publish("alerts:weather", json.dumps({
    "type": "heavy_rain",
    "location": "Delhi",
    "severity": "high"
}))
```

### 6. Streams (Redis 5.0+)

```redis
// Add to stream
XADD mystream * field1 value1 field2 value2
// Returns: stream-id (e.g., "1609459200000-0")

// Read from stream
XREAD COUNT 2 STREAMS mystream 0  // Read 2 messages from start
XREAD BLOCK 1000 STREAMS mystream \$  // Wait 1s for new messages

// Stream consumer groups
XGROUP CREATE mystream mygroup \$  // Create consumer group
XREADGROUP GROUP mygroup consumer1 COUNT 2 STREAMS mystream >  // Read as consumer
XACK mystream mygroup stream-id     // Acknowledge message processing

// Use case: event log, sensor data
XADD soil:readings * moisture 65 temp 28 location "Field-1"
XADD soil:readings * moisture 64 temp 29 location "Field-2"

// Process readings in batches
XREAD COUNT 100 STREAMS soil:readings 0
```

---

## Performance Optimization

### 1. Benchmarking

```bash
# Redis built-in benchmark
redis-benchmark -h 127.0.0.1 -p 6379 -n 100000 -c 50

# Results show ops/sec for each command type
# SET: ~95,000 ops/sec
# GET: ~100,000 ops/sec
# LPUSH: ~110,000 ops/sec
```

### 2. Pipeline Operations

```python
# Without pipeline (N round-trips)
redis.set("key1", "val1")   # Network round-trip 1
redis.set("key2", "val2")   # Network round-trip 2
redis.set("key3", "val3")   # Network round-trip 3
# Total time: 3 × (network latency) = ~3ms

# With pipeline (1 round-trip)
pipe = redis.pipeline()
pipe.set("key1", "val1")
pipe.set("key2", "val2")
pipe.set("key3", "val3")
pipe.execute()              # Single network round-trip
# Total time: ~1ms (3× faster)
```

### 3. Connection Pooling

```python
from redis import ConnectionPool, Redis

# Create pool (recommended)
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    decode_responses=True
)
redis = Redis(connection_pool=pool)

# Each client gets connection from pool
# Connection reused, not recreated
```

### 4. Lua Scripting

```redis
// Atomic script execution (no race conditions)
EVAL "return redis.call('incr', KEYS[1])" 1 counter

// Complex operation
SCRIPT LOAD "script code"
EVALSHA sha1 1 key1

// Use case: atomic increment with max limit
script = """
if redis.call('get', KEYS[1]) < ARGV[1] then
  return redis.call('incr', KEYS[1])
else
  return 0
end
"""
redis.eval(script, 1, "rate:user:1000", 100)  // Max 100
```

### 5. Key Design for Performance

```redis
// ✗ BAD: Deep nesting, long keys
GET "user:profile:personal:details:contact:email"  // Slow

// ✓ GOOD: Flat, short keys
GET "u:1000:em"    // Fast, less memory

// ✗ BAD: Complex values, need parsing
GET "user:data"    // Returns {"name":"...", "email":"...", ...}
// Requires deserialization

// ✓ GOOD: Separate concerns
HSET user:1000 name "Raj" email "raj@..."  // Hash is faster
```

---

## Use Cases in AgroSight

### 1. Session Management

```python
# FastAPI + Redis session
from fastapi import Request, HTTPException
import json
import uuid

app = FastAPI()
redis = Redis.from_url("redis://localhost:6379/0")

@app.post("/login")
async def login(user_id: str, password: str):
    # Authenticate user
    user = await authenticate(user_id, password)
    if not user:
        raise HTTPException(status_code=401)
    
    # Create session
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_id,
        "name": user["name"],
        "state": user["state"],
        "timestamp": datetime.now().isoformat()
    }
    
    # Store in Redis with 24-hour expiration
    redis.setex(
        f"session:{session_id}",
        86400,  # 24 hours
        json.dumps(session_data)
    )
    
    return {"session_id": session_id}

@app.get("/profile")
async def get_profile(session_id: str):
    # Retrieve session from Redis
    session_data = redis.get(f"session:{session_id}")
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired")
    
    session = json.loads(session_data)
    return {"user_id": session["user_id"], "name": session["name"]}
```

### 2. Real-Time Mandi Price Cache

```redis
// Store latest prices for quick access
HSET mandi:prices:delhi wheat 2450 rice 3200 cotton 5800
HSET mandi:prices:mumbai wheat 2500 rice 3250 cotton 5900

// Expire after 4 hours (stale data not served)
EXPIRE mandi:prices:delhi 14400

// High-frequency updates
HINCRBY mandi:prices:delhi wheat 50  // Price increased by 50

// Real-time leaderboard
ZADD price_trends:daily 1609459200 "wheat:up:150"
ZREVRANGE price_trends:daily 0 4  // Top 5 trending commodities
```

**Python Implementation:**

```python
import redis
import json
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_mandi_price(market, commodity, price):
    """Cache commodity price for market"""
    key = f"mandi:price:{market}:{commodity}"
    redis_client.setex(
        key,
        3600,  # 1 hour expiration
        json.dumps({
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "source": "agmarknet"
        })
    )

def get_cached_price(market, commodity):
    """Get cached price if available"""
    key = f"mandi:price:{market}:{commodity}"
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None

def update_price_leaderboard():
    """Update trending prices"""
    prices = {
        "wheat": {"up": 150, "down": 50},
        "rice": {"up": 200, "down": 75},
        "cotton": {"up": 300, "down": 100}
    }
    
    for commodity, trends in prices.items():
        timestamp = int(datetime.now().timestamp())
        if trends["up"] > trends["down"]:
            redis_client.zadd(
                "trending:prices",
                {f"{commodity}:up": timestamp}
            )
```

### 3. Rate Limiting (Sliding Window)

```python
def is_rate_limited(user_id, limit=100, window=3600):
    """Check if user exceeded rate limit"""
    key = f"rate_limit:{user_id}"
    
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    
    return current > limit

# In FastAPI
from fastapi import Request, HTTPException

@app.post("/api/mandi-price")
async def get_price(request: Request):
    user_id = request.headers.get("X-User-ID")
    
    if is_rate_limited(user_id, limit=100, window=3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Process request
    return {...}
```

### 4. Activity Logging (List + Expiration)

```redis
// User activity log
LPUSH activity:user:1000 "viewed_prices:2026-05-06"
LPUSH activity:user:1000 "searched:wheat"
LPUSH activity:user:1000 "added_alert:drought"
EXPIRE activity:user:1000 604800  // 7 days

// Get recent activities
LRANGE activity:user:1000 0 9  // Last 10 activities
```

### 5. Notification Queue

```python
def enqueue_notification(user_id, message_type, data):
    """Add notification to queue"""
    notification = {
        "type": message_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "read": False
    }
    
    redis_client.lpush(
        f"notifications:queue:{user_id}",
        json.dumps(notification)
    )
    
    # Trim to last 100 notifications
    redis_client.ltrim(f"notifications:queue:{user_id}", 0, 99)

def get_unread_notifications(user_id):
    """Get unread notifications for user"""
    notifications = redis_client.lrange(
        f"notifications:queue:{user_id}",
        0,
        -1
    )
    return [json.loads(n) for n in notifications]
```

---

## Best Practices

### 1. Key Naming Convention

```redis
// Hierarchical structure with colons
object_type:object_id:field_name:subfield

Examples:
user:1000:profile:email
user:1000:settings:notifications
crop:wheat:prices:daily
weather:delhi:temp:current
session:abc123xyz:data
cache:api:mandi:prices
queue:notifications:pending
```

### 2. Expiration & Cleanup

```redis
// Always set expiration for temporary data
SET temp_data "value" EX 3600      // Expires in 1 hour

// Use EXPIRE for cache
SET price "2450"
EXPIRE price 14400                 // Expires in 4 hours

// Avoid accumulating old keys
// ✗ BAD
SET activity:user:1000:2026-01-01 "data"  // Never expires
SET activity:user:1000:2026-01-02 "data"  // Accumulates

// ✓ GOOD
LPUSH activity:user:1000 "data"           // List with trim
EXPIRE activity:user:1000 604800           // Expires in 7 days
LTRIM activity:user:1000 0 999             // Keep last 1000 items
```

### 3. Error Handling

```python
import redis
from redis.exceptions import ConnectionError, TimeoutError

try:
    redis_client.ping()
except ConnectionError:
    logger.error("Redis connection failed")
    # Fallback to database
    use_database_instead()
except TimeoutError:
    logger.error("Redis timeout")
    # Retry with exponential backoff
    retry_with_backoff()
```

### 4. Monitoring & Debugging

```bash
# Monitor all commands in real-time
redis-cli MONITOR

# Get server info
redis-cli INFO server
redis-cli INFO memory
redis-cli INFO stats
redis-cli INFO replication

# Slow log
redis-cli SLOWLOG GET 10

# Client list
redis-cli CLIENT LIST

# Memory analysis
redis-cli --bigkeys    # Find largest keys
redis-cli --hotkeys    # Find most accessed keys
```

### 5. Security

```redis
// Require password
requirepass "strong_password_here"

// ACL (Redis 6.0+)
ACL SETUSER default on >password +@all ~*
ACL SETUSER api_user on >api_password +@read ~*

// Network security
bind 127.0.0.1         // Only local connections
```

### 6. Production Checklist

```
✓ Enable persistence (RDB + AOF)
✓ Set up replication for high availability
✓ Configure Sentinel for auto-failover
✓ Set maxmemory and eviction policy
✓ Enable password authentication
✓ Set up monitoring and alerting
✓ Regular backup strategy
✓ Connection pooling in client
✓ Pipeline operations for bulk loads
✓ Implement circuit breaker for failover
```

---

## Integration with AgroSight (docker-compose.yml)

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - qdrant
    environment:
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333

  redis:
    image: redis:7-alpine
    container_name: agrosight-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: [ "CMD", "redis-cli", "ping" ]
      interval: 5s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    container_name: agrosight-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage

volumes:
  redis-data:
  qdrant-data:
```

---

## Summary

| Aspect | Key Point |
|--------|-----------|
| **What** | In-memory data store with 8+ data types |
| **Speed** | <1ms latency, 100K+ ops/sec |
| **Use** | Caching, sessions, queues, real-time analytics |
| **Persistence** | RDB snapshots + AOF logs |
| **Scaling** | Master-replica replication, Redis Cluster |
| **Safety** | Transactions, Lua scripting, expiration |
| **Memory** | Smart eviction, compression, optimization |

**For AgroSight:** Redis provides:
- Fast session storage (user login management)
- Price cache (mandi prices from data.gov.in)
- Real-time alerts (Pub/Sub notifications)
- Rate limiting (API calls per user)
- Activity logging (user actions)
- Background job queues (data processing)
