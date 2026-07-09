# Distributed Caching Systems: In-Depth Comparison

## Executive Summary

| Aspect | Redis Cluster | Hazelcast | Valkey | Memcached |
|--------|---------------|-----------|--------|-----------|
| **Language** | C | Java | C | C |
| **Persistence** | ✓ RDB/AOF | ✓ Snapshots | ✓ RDB/AOF | ✗ None |
| **Clustering** | ✓ Native | ✓ Native | ✓ Native | Requires external tools |
| **High Availability** | Sentinel/Cluster | Built-in | Sentinel | None |
| **Memory Efficiency** | Excellent | Good | Excellent | Excellent |
| **Throughput** | Very High | High | Very High | Highest |
| **Latency** | Ultra-low | Low | Ultra-low | Ultra-low |
| **Learning Curve** | Moderate | Steep | Easy (Redis compatible) | Very Easy |
| **Community** | Largest | Mid | Growing | Large |

---

## 1. REDIS CLUSTER (Most Popular)

### Architecture

```
┌─────────────────────────────────────────────────────┐
│           Redis Cluster (3-7+ nodes)                │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Slot 0-5460      Slot 5461-10922    Slot 10923+   │
│  ┌──────────┐     ┌──────────┐      ┌──────────┐   │
│  │ Node 1   │     │ Node 2   │      │ Node 3   │   │
│  │ Primary  │     │ Primary  │      │ Primary  │   │
│  └────┬─────┘     └────┬─────┘      └────┬─────┘   │
│       │                │                  │         │
│  ┌────▼─────┐     ┌────▼─────┐      ┌────▼─────┐   │
│  │ Node 1R  │     │ Node 2R  │      │ Node 3R  │   │
│  │ Replica  │     │ Replica  │      │ Replica  │   │
│  └──────────┘     └──────────┘      └──────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Key Features

**Data Partitioning:**
```
Hash Slot = CRC16(key) % 16384

Example:
- Key "user:123" → Slot 8000 → Node 2
- Key "session:abc" → Slot 12500 → Node 3
- Keys automatically distributed
```

**Replication (Master-Slave):**
```
Primary Node (Write)
    ↓ (replicates)
Replica Node (Read-only copy)
```

### Configuration Example

```yaml
# redis-cluster.conf
port 6379
cluster-enabled yes
cluster-node-timeout 15000
cluster-replica-validity-factor 10
appendonly yes              # Persistence: AOF (Append-Only File)
appendfsync everysec        # Fsync every second

# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict LRU keys when full

# Replication
repl-diskless-sync no       # Disk-based replication
min-replicas-to-write 1     # Wait for 1 replica before ACK
```

### Initialization

```python
import redis
from redis.cluster import RedisCluster

# Connect to cluster
startup_nodes = [
    {"host": "127.0.0.1", "port": "7000"},
    {"host": "127.0.0.1", "port": "7001"},
    {"host": "127.0.0.1", "port": "7002"}
]

rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

# Usage (same as single Redis)
rc.set("session:user123", json.dumps({"turns": 5}), ex=86400)
history = json.loads(rc.get("session:user123"))

# Cluster-aware operations
info = rc.cluster_info()
nodes = rc.cluster_nodes()
```

### Cluster Topology

```bash
# Create cluster with 6 nodes (3 primary + 3 replica)
redis-cli --cluster create \
  127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
  127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1

# Check cluster status
redis-cli cluster info

# Reshard data
redis-cli --cluster reshard 127.0.0.1:7000
```

### Advantages

✅ **Horizontal Scaling** – Add nodes, auto-rebalance slots  
✅ **High Availability** – Automatic failover if primary dies  
✅ **Persistence** – RDB snapshots + AOF (Append-Only Files)  
✅ **Rich Data Types** – Strings, Lists, Sets, Hashes, Sorted Sets, Streams  
✅ **Transactions** – MULTI/EXEC for atomic operations  
✅ **Pub/Sub** – Messaging between services  
✅ **TTL/Expiration** – Automatic key expiration  
✅ **Modules** – Extend with custom functionality  

### Disadvantages

❌ **Operational Complexity** – Cluster management requires expertise  
❌ **Network Overhead** – Inter-node gossip protocol (bandwidth)  
❌ **Slot Movement Cost** – Resharding is expensive  
❌ **Limited Transactions** – Can't span multiple slots easily  
❌ **Memory as Bottleneck** – All data must fit in RAM  

### Performance

```
Throughput:  100,000+ ops/sec per node
Latency:     <1ms p50, <5ms p99
Memory:      Efficient (1-2 bytes overhead per key)
Bandwidth:   Gossip protocol adds ~1% overhead
```

### Best For

- Session management ✓
- Cache with persistence required
- High-throughput applications
- Multi-node deployments
- Real-time analytics

---

## 2. HAZELCAST (Enterprise Grade)

### Architecture

```
┌─────────────────────────────────────────────────────┐
│    Hazelcast Distributed Cluster (In-Memory Grid)   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐    ┌──────────────────┐      │
│  │ Member Node 1    │    │ Member Node 2    │      │
│  │ ┌──────────────┐ │    │ ┌──────────────┐ │      │
│  │ │ Partition 0-1│ │◄──►│ │ Partition 2-3│ │      │
│  │ │ Backup 8-9   │ │    │ │ Backup 10-11 │ │      │
│  │ └──────────────┘ │    │ └──────────────┘ │      │
│  │                  │    │                  │      │
│  │ Hazelcast Map    │    │ Hazelcast Map    │      │
│  │ Hazelcast Queue  │    │ Hazelcast Queue  │      │
│  │ Hazelcast Locks  │    │ Hazelcast Locks  │      │
│  └──────────────────┘    └──────────────────┘      │
│                                                      │
└─────────────────────────────────────────────────────┘
         ▲                           ▲
         │ Partition Aware Client    │
    ┌────┴───────────────────────────┴────┐
    │     Client Application (Java/.NET)   │
    └─────────────────────────────────────┘
```

### Key Features

**Partitioned Data Grid:**
```
IMap (Distributed Map) = Partitioned HashMap
- Each partition has primary + replica
- Automatic replication
- Partition-aware routing from client

Example:
IMap<String, String> sessions = hazelcast.getMap("sessions");
sessions.put("user:123", jsonString);  // Auto-partitioned
sessions.get("user:123");              // Direct partition access
```

**Rich Distributed Data Structures:**
```java
IMap<K, V>           // Partitioned hashmap with TTL
IQueue<E>            // Distributed queue
ISet<E>              // Distributed set
ITopic<E>            // Pub/Sub topic
ILock                // Distributed lock
ICountDownLatch      // Distributed latch
ISemaphore           // Distributed semaphore
```

### Configuration Example

```xml
<!-- hazelcast.xml -->
<hazelcast xmlns="http://www.hazelcast.com/schema/config">
    <cluster-name>agrosight-cluster</cluster-name>
    
    <network>
        <port>5701</port>
        <port-count>100</port-count>
        
        <!-- Auto-discovery -->
        <join>
            <multicast enabled="false"/>
            <tcp-ip enabled="true">
                <member>127.0.0.1:5701</member>
                <member>127.0.0.1:5702</member>
                <member>127.0.0.1:5703</member>
            </tcp-ip>
        </join>
    </network>
    
    <!-- Map configuration -->
    <map name="sessions">
        <time-to-live-seconds>604800</time-to-live-seconds>
        <max-idle-seconds>3600</max-idle-seconds>
        <eviction-policy>LRU</eviction-policy>
        <max-size policy="per-node">1000000</max-size>
        <backup-count>1</backup-count>
        <async-backup-count>0</async-backup-count>
        
        <!-- Persistence -->
        <map-store enabled="true">
            <class-name>com.example.SessionMapStore</class-name>
            <write-delay-seconds>0</write-delay-seconds>
        </map-store>
    </map>
    
    <!-- Memory management -->
    <properties>
        <property name="hazelcast.memory.max-native.memory.size">2G</property>
    </properties>
</hazelcast>
```

### Java/Python Usage

```java
// Java (native)
HazelcastInstance hz = Hazelcast.newHazelcastInstance();
IMap<String, String> sessionMap = hz.getMap("sessions");

// Put with TTL
sessionMap.put("user:123", jsonData, 7, TimeUnit.DAYS);

// Get
String data = sessionMap.get("user:123");

// Distributed lock
ILock lock = hz.getLock("user:123");
lock.lock();
try {
    // Critical section
} finally {
    lock.unlock();
}

// Pub/Sub
ITopic<String> topic = hz.getTopic("notifications");
topic.addMessageListener((msg) -> {
    System.out.println("Received: " + msg.getMessageObject());
});
topic.publish("Order placed!");
```

```python
# Python (client library)
from hazelcast import HazelcastClient
from hazelcast.config import Config

config = Config()
config.network.addresses.append("127.0.0.1:5701")
client = HazelcastClient(config=config)

sessions = client.get_map("sessions").blocking()
sessions.put("user:123", json_data, ttl=604800)
data = sessions.get("user:123")
```

### Advantages

✅ **Rich Distributed Data Structures** – Maps, Queues, Topics, Locks, Latches  
✅ **Enterprise Features** – Security, auditing, monitoring built-in  
✅ **Persistence Options** – SQL, NoSQL, custom MapStore implementations  
✅ **Compute Grid** – Distributed processing with MapReduce, Aggregations  
✅ **Multi-language** – Java, .NET, Node.js, Python clients  
✅ **Transaction Support** – ACID transactions across distributed data  
✅ **Replication with Backup** – Configurable backup counts  
✅ **Hot Restart** – Persist and restore entire cluster state  

### Disadvantages

❌ **Requires Java** – Heavy JVM footprint (500MB+ per node)  yt
❌ **Steep Learning Curve** – Complex configuration  
❌ **Higher Memory Overhead** – ~10-20 bytes per entry  
❌ **Licensing** – Free version (open-source) vs paid (enterprise features)  
❌ **Less Throughput than Redis** – ~50k ops/sec vs Redis 100k+  
❌ **Operational Complexity** – More moving parts  

### Performance

```
Throughput:  50,000-70,000 ops/sec
Latency:     <2ms p50, <10ms p99
Memory:      Higher overhead (10-20 bytes per entry)
CPU:         Higher (Java GC pauses possible)
```

### Best For

- Enterprise systems requiring ACID transactions
- Complex distributed data structures
- Applications needing distributed compute
- Systems requiring hot restart
- Multi-language clusters (.NET + Java)

---

## 3. VALKEY (Redis Fork - Open Source)

### Architecture

```
Valkey = Redis codebase without Redis enterprise restrictions
├─ Same architecture as Redis Cluster
├─ Open source (BSD license)
├─ Maintained by Linux Foundation
├─ Community-driven development
└─ Identical API to Redis
```

### Background

```
Timeline:
2006: Redis created by Salvatore Sanfilippo
2022: Redis Labs changes to dual licensing (source + commercial)
2024: Linux Foundation forks Redis → Valkey
      All previous Redis features, now truly open source
```

### Configuration (Identical to Redis)

```yaml
# valkey.conf - Same as redis.conf
port 6379
cluster-enabled yes
cluster-node-timeout 15000
appendonly yes
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Python Client

```python
import valkey  # Drop-in replacement for redis

# Connect (same API as redis)
v = valkey.Valkey(host='localhost', port=6379)

# Usage (100% identical)
v.set('session:user123', json.dumps(data), ex=86400)
session_data = json.loads(v.get('session:user123'))

# Cluster
from valkey.cluster import ValkeyCluster
vc = ValkeyCluster(startup_nodes=[...])
vc.set('key', 'value')
```

### Advantages

✅ **100% Redis Compatible** – Drop-in replacement, no code changes  
✅ **Truly Open Source** – No licensing restrictions  
✅ **Active Community** – Linux Foundation backing  
✅ **Future-proof** – Long-term stability commitment  
✅ **Lower Cost** – No enterprise license fees  
✅ **Same Performance** – Identical to Redis (same C codebase)  

### Disadvantages

❌ **Younger Project** – Valkey 1.0 released 2024  
❌ **Smaller Community** – Fewer resources/integrations than Redis  
❌ **Learning Resources** – Most tutorials still reference Redis  
❌ **Enterprise Support** – Limited compared to Redis Labs offerings  

### Migration from Redis

```bash
# Just change package name - no other changes needed
pip uninstall redis
pip install valkey

# Docker
# FROM redis:7  →  FROM valkey:latest
```

### Performance (Identical to Redis)

```
Throughput:  100,000+ ops/sec
Latency:     <1ms p50
Memory:      Efficient
Cost:        Lower (no licensing)
```

### Best For

- Drop-in Redis replacement
- Cost-conscious deployments
- Organizations requiring truly open-source solutions
- Future-proofing (no vendor lock-in)

---

## 4. MEMCACHED (Simple, Fast)

### Architecture

```
┌────────────────────────────────────────────────────┐
│         Memcached Distributed Cache                │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ Memcached #1 │  │ Memcached #2 │               │
│  │ Hash Table   │  │ Hash Table   │               │
│  │ LRU Eviction │  │ LRU Eviction │               │
│  └──────────────┘  └──────────────┘               │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ Memcached #3 │  │ Memcached #4 │               │
│  │ Hash Table   │  │ Hash Table   │               │
│  │ LRU Eviction │  │ LRU Eviction │               │
│  └──────────────┘  └──────────────┘               │
│                                                    │
└────────────────────────────────────────────────────┘
         ▲
         │ Client-side Consistent Hashing
    ┌────┴──────────────────────┐
    │   Application Layer       │
    │  (kettle, pymemcache)     │
    └──────────────────────────┘
```

### Key Characteristics

**No Built-in Clustering:**
```
Client → Key hash → Choose server → Store/Retrieve

Example Consistent Hashing:
Key "session:123" 
  → Hash("session:123") = 8729
  → 8729 % 4 = 1 
  → Use Memcached #1

Problem: Add/remove server → rehash many keys
Solution: Consistent hashing library (client-side)
```

**Simple Protocol:**
```
SET <key> <flags> <expiry> <bytes>
<data>
CTRL+Z

GET <key>
CTRL+Z

DELETE <key>
CTRL+Z
```

### Configuration Example

```
# /etc/memcached.conf
-p 11211           # Port
-m 512             # Memory (MB)
-c 1024            # Max connections
-t 4               # Threads
-u memcache        # Run as user
-vv                # Very verbose logging

# No persistence options (intentional)
# No replication (stateless)
# No clustering (client handles it)
```

### Python Usage

```python
import pymemcache

# Single server
from pymemcache.client.base import PooledClient
client = PooledClient(('localhost', 11211), max_pool_size=4)

# Set and get
client.set(b'session:user123', json.dumps(data).encode(), expire=86400)
session_data = json.loads(client.get(b'session:user123').decode())

# Delete
client.delete(b'session:user123')

# Distributed (client-side consistent hashing)
from pymemcache.client.hash import HashClient

client = HashClient([
    ('localhost', 11211),
    ('localhost', 11212),
    ('localhost', 11213)
])

# Client automatically hashes and routes
client.set(b'key', b'value', expire=3600)
value = client.get(b'key')
```

### Advantages

✅ **Ultra-fast** – Simplest implementation, ~1M ops/sec per node  
✅ **Low Latency** – <1ms p99  
✅ **Minimal Memory Overhead** – ~100 bytes per key  
✅ **Easy to Deploy** – No configuration needed  
✅ **Horizontal Scaling** – Just add more instances  
✅ **Mature/Stable** – 20+ years, battle-tested  
✅ **Multi-language** – Clients for every language  

### Disadvantages

❌ **No Persistence** – All data lost on restart  
❌ **No Built-in Clustering** – Client manages distribution  
❌ **Simple Key-Value Only** – No rich data types  
❌ **No Replication** – No HA unless external layer  
❌ **LRU Eviction Only** – Can't control eviction policy easily  
❌ **Stateless Design** – Not suitable for state management alone  
❌ **No TTL Precision** – Nearest second only  

### Performance

```
Throughput:  1,000,000+ ops/sec per node (Highest!)
Latency:     <0.5ms p50, <1ms p99
Memory:      Most efficient (100 bytes overhead)
CPU:         Minimal (single-threaded core logic)
```

### Best For

- Session caching (with backup storage)
- Database query caching
- Leaderboards, counters
- High-throughput read-heavy workloads
- Applications where data loss is acceptable

---

## 5. DETAILED COMPARISON TABLE

### Performance Metrics

| Metric | Redis Cluster | Hazelcast | Valkey | Memcached |
|--------|---------------|-----------|--------|-----------|
| **Throughput (ops/sec)** | 100,000 | 50,000 | 100,000 | 1,000,000 |
| **P50 Latency** | <1ms | <2ms | <1ms | <0.5ms |
| **P99 Latency** | <5ms | <10ms | <5ms | <1ms |
| **Memory/Key** | 1-2 bytes | 10-20 bytes | 1-2 bytes | ~100 bytes |
| **Max Cluster Size** | 1000+ nodes | 500+ nodes | 1000+ nodes | Unlimited* |

*Client-side management

### Features Comparison

| Feature | Redis Cluster | Hazelcast | Valkey | Memcached |
|---------|---------------|-----------|--------|-----------|
| **Persistence** | ✅ RDB/AOF | ✅ Snapshots | ✅ RDB/AOF | ❌ None |
| **Replication** | ✅ Built-in | ✅ Built-in | ✅ Built-in | ❌ None |
| **High Availability** | ✅ Sentinel | ✅ Built-in | ✅ Sentinel | ❌ None |
| **Data Types** | 10+ | Limited | 10+ | 1 (binary) |
| **Transactions** | ✅ Limited | ✅ ACID | ✅ Limited | ❌ No |
| **Pub/Sub** | ✅ Yes | ✅ Topics | ✅ Yes | ❌ No |
| **Distributed Locks** | ✅ Redlock | ✅ Native | ✅ Redlock | ❌ No |
| **TTL Support** | ✅ Millisecond | ✅ Millisecond | ✅ Millisecond | ✅ Second |
| **Scripting** | ✅ Lua | ❌ No | ✅ Lua | ❌ No |
| **Monitoring** | Good | Excellent | Good | Basic |

### Operational Complexity

| Aspect | Redis Cluster | Hazelcast | Valkey | Memcached |
|--------|---------------|-----------|--------|-----------|
| **Startup Time** | Seconds | Minutes | Seconds | Seconds |
| **Memory Footprint** | 50-100MB | 300-500MB | 50-100MB | 10-50MB |
| **CPU Usage** | Low | Medium | Low | Very Low |
| **Operational Overhead** | Medium | High | Medium | Low |
| **Learning Curve** | Moderate | Steep | Easy | Very Easy |

### Cost Analysis (1 Year, 3 Nodes)

| System | License | Infra | Total |
|--------|---------|-------|-------|
| **Redis Cluster** | Free (OSS) | $500/mo | $6000 |
| **Redis Enterprise** | $10k+/mo | Included | $120k+ |
| **Hazelcast Open Source** | Free | $500/mo | $6000 |
| **Hazelcast Enterprise** | $20k+/mo | Included | $240k+ |
| **Valkey** | Free | $500/mo | $6000 |
| **Memcached** | Free | $500/mo | $6000 |

---

## 6. USE CASE MATRIX

### AgroSight Session Management

```
REQUIREMENT: Store chat history, TTL-based expiry, 5-turn max

┌──────────────────────────────────────────────────┐
│ BEST: Redis Cluster or Valkey                    │
├──────────────────────────────────────────────────┤
│ ✅ TTL support (millisecond precision)           │
│ ✅ String/JSON storage                           │
│ ✅ Automatic expiry                              │
│ ✅ Easy Python integration                       │
│ ✅ Lower operational cost                        │
│ ✅ Horizontal scaling                            │
│ ✅ Persistence optional                          │
└──────────────────────────────────────────────────┘
```

### Comparison for Your Use Case

```
Sessions: {"user:123": [{"role":"user","content":"..."}], "exp": 604800}
Volume: ~1000 sessions/day, max 10k concurrent
Throughput: ~100 requests/sec
Uptime: 99.9%
```

**Winner: Redis Cluster or Valkey**

| Criterion | Score |
|-----------|-------|
| TTL Support | Redis 10/10, Memcached 8/10 |
| Scalability | Redis Cluster 10/10 |
| Cost | Valkey 10/10 |
| Operational Complexity | Memcached 10/10 |
| **Overall** | **Redis/Valkey 9/10** |

---

## 7. MIGRATION STRATEGIES

### From Redis → Valkey

```bash
# Step 1: Install Valkey
docker run -d -p 6379:6379 valkey:latest

# Step 2: No code changes needed
pip install valkey
# Already using pymemcache? No changes!

# Step 3: Migrate data
valkey-cli --pipe < /tmp/redis-backup.rdb

# Completely transparent to application
```

### From Memcached → Redis Cluster

```python
# Before (Memcached)
from pymemcache.client.hash import HashClient
cache = HashClient([...])
cache.set(b'key', b'value', expire=3600)

# After (Redis Cluster)
from redis.cluster import RedisCluster
cache = RedisCluster(startup_nodes=[...])
cache.set('key', 'value', ex=3600)

# Logic is identical, just different backend
```

### From Redis Standalone → Redis Cluster

```python
# Before
import redis
r = redis.Redis(host='localhost', port=6379)

# After (cluster mode)
from redis.cluster import RedisCluster
r = RedisCluster(startup_nodes=[
    {'host': 'localhost', 'port': 6379},
    {'host': 'localhost', 'port': 6380},
])

# 99% code compatibility
# Some limitations: 
#   - KEYS command (use SCAN)
#   - Transactions across keys (impossible in cluster)
#   - Watch command (no cluster support)
```

---

## 8. RECOMMENDATION FOR AGROSIGHT

### Current Setup
```
Single Redis instance
- Session storage
- TTL-based cleanup
- Fallback to in-memory dict
```

### Recommended Upgrade Path

**Phase 1 (Now):** Keep current Redis
- ✅ Meets all requirements
- ✅ Simple to operate
- ✅ Easy debugging

**Phase 2 (If scaling):** Add Redis Sentinel
```
Master (writes)
    ├── Slave 1 (reads)
    └── Slave 2 (reads)

Sentinel (monitors)
    └── Auto-failover if master down
```

**Phase 3 (If massive scale):** Redis Cluster
```
Multiple hash slot ranges
- Geographic distribution
- Horizontal scaling
- But: increased complexity
```

### Do NOT Use (for your case)
- ❌ Memcached – No TTL for 7 days, data loss unacceptable
- ❌ Hazelcast – Overkill, Java overhead not justified
- ✅ Valkey – Use if you want Redis without licensing concerns

### Final Recommendation

```
For AgroSight:
├─ Use: Redis Cluster or Valkey Cluster
├─ Why: Perfect fit for session management
├─ Cost: Minimal (~$500/month infrastructure)
├─ Complexity: Moderate (manageable)
├─ Alternative: Memcached + Persistent DB backup
└─ Never: Hazelcast (unless distributed compute needed)
```

---

## 9. QUICK DECISION TREE

```
START: "Which caching system should I use?"
│
├─ "Do I need persistence?"
│  ├─ YES → Redis/Valkey ✓
│  └─ NO  → Next question
│
├─ "Throughput > 500k ops/sec required?"
│  ├─ YES → Memcached ✓
│  └─ NO  → Next question
│
├─ "Need distributed compute/complex data structures?"
│  ├─ YES → Hazelcast ✓
│  └─ NO  → Next question
│
├─ "Need TTL/expiration?"
│  ├─ YES → Redis/Valkey ✓
│  └─ NO  → Memcached ✓
│
└─ "Java/polyglot environment?"
   ├─ YES → Hazelcast ✓
   └─ NO  → Redis/Valkey ✓

AGROSIGHT: TTL required (7 days) → Redis/Valkey ✓
```

---

## 10. MONITORING & OPERATIONS

### Redis Cluster Monitoring

```bash
# Check cluster health
redis-cli cluster info
redis-cli cluster nodes

# Monitor throughput
redis-cli --stat

# Check memory usage
redis-cli info memory

# Backup
redis-cli BGSAVE
```

### Hazelcast Monitoring

```java
// Built-in monitoring
HazelcastInstance hz = Hazelcast.getAllHazelcastInstances().get(0);
IExecutorService executor = hz.getExecutorService("default");
Cluster cluster = hz.getCluster();

System.out.println("Members: " + cluster.getMembers().size());
System.out.println("Partitions: " + hz.getPartitionService().getPartitions().size());
```

### Memcached Monitoring

```bash
# Using memcached-tool
memcached-tool localhost:11211

# Statistics
echo "stats" | nc localhost 11211
echo "stats slabs" | nc localhost 11211
```

### Valkey Monitoring

```bash
# Same as Redis
valkey-cli info
valkey-cli monitor
valkey-cli slowlog get
```

---

## Summary

| System | Best For | Verdict |
|--------|----------|---------|
| **Redis Cluster** | Session management, general caching, persistence | ⭐⭐⭐⭐⭐ |
| **Valkey** | Drop-in Redis replacement, open-source focus | ⭐⭐⭐⭐⭐ |
| **Hazelcast** | Enterprise distributed systems, transactions | ⭐⭐⭐ (Overkill for most) |
| **Memcached** | Ultra-high throughput, ephemeral data | ⭐⭐⭐⭐ (Needs backup) |

**For AgroSight: Use Redis Cluster or Valkey Cluster** ✓

