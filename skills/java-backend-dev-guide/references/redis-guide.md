# Redis Integration Development Standards

---

## 1. General Development Standards

### 1.1. Key-Value Conventions

#### 1.1.1. [Mandatory] Key Naming Conventions

Key naming follows `{business-module}:{object-type}:{unique-id}[:{additional-dimension}]`, using colon `:` as separator.

Examples: `article:detail:12345`, `author:info:67890`

#### 1.1.2. [Mandatory] Prohibit BigKeys

String type Value >10KB or Hash/List/Set/ZSet collection elements >5000 is considered a BigKey. Value >1MB must be compressed or split.

#### 1.1.3. [Mandatory] Keys Must Have Expiration Time

Except for persistent storage scenarios, all cache keys must set TTL. Long-lived keys adopt "extend expiration time on each access" strategy.

#### 1.1.4. [Recommended] Choose Appropriate Data Structures

| Data structure | Applicable scenarios |
|---------------|---------------------|
| `String` | Plain KV, counters, distributed locks |
| `Hash` | Store object properties, field count ≤100 |
| `List` | Message queues, latest lists |
| `Set` | Deduplication, intersection/union operations |
| `ZSet` | Leaderboards, delayed queues |
| `Bitmap` | Statistics, user check-ins |
| `HyperLogLog` | Deduplication counting |

> Hash fields >100 need to be split into multiple Hashes or use String serialized storage instead.

---

### 1.2. Cache Conventions

#### 1.2.1. [Mandatory] Data Sync Uses Cache Aside Pattern

When updating data, update database first, then delete cache after success. Prohibit "delete cache first then update DB" or "dual-write" patterns.

For extremely high consistency requirements, use Canal to listen to Binlog for async cache deletion or use distributed locks.

#### 1.2.2. [Recommended] Cache Avalanche Mitigation

1. Randomized expiration times: TTL adds random jitter (1%-5%)
2. Multi-level cache: Local cache + Redis two-level structure
3. Circuit breaker degradation: Degrade to direct database queries when cache cluster unavailable

#### 1.2.3. [Recommended] Cache Penetration Mitigation

1. Cache null/default values: Set short TTL for results not found (e.g. 5 minutes)
2. Bloom filters: Judge whether key possibly exists before accessing cache

#### 1.2.4. [Recommended] Cache Breakdown Mitigation

1. Mutex Lock: When cache misses, use distributed lock to ensure single-thread loading
2. Logical expiration: Store logical expiration time when caching data, update asynchronously after expiration

#### 1.2.5. [Recommended] Hot Key Mitigation

- Local cache (Guava/Caffeine) + Redis multi-level cache
- Hot key splitting (e.g. `key_1`, `key_2`)
- Optimize data type (leaderboards switch to String+incr)

---

### 1.3. Command Conventions

#### 1.3.1. [Mandatory] Prohibit KEYS Command in Production

Prohibit using `KEYS` command. Use `SCAN` command for gradual traversal, recommend executing on replica.

#### 1.3.2. [Mandatory] Careful Use of Full Retrieval Commands

Prohibit using `HGETALL`, `SMEMBERS`, `LRANGE 0 -1` on large collections. Use `HSCAN`, `SSCAN` for paginated retrieval.

#### 1.3.3. [Recommended] Prefer Lua Scripts for Atomicity

When involving multi-step logic (such as check+update), prefer Lua scripts. In Cluster mode, all keys must map to the same shard through Hashtag `{}`.

#### 1.3.4. [Recommended] Pipeline Batch Operation Optimization

Prefer `MGET`, `MSET`, `HMGET` and other batch commands or Pipeline. Batch key count ≤500. In Cluster mode, Pipeline involving multiple shards cannot guarantee atomicity, should split into single-shard Pipeline.

#### 1.3.5. [Mandatory] Careful Use of Redis Transactions

Avoid `MULTI/EXEC` as much as possible. Use Lua scripts instead in high-concurrency scenarios.

---

### 1.4. Client Conventions

#### 1.4.1. [Mandatory] Reasonable Connection Pool Configuration

Configure `maxTotal`, `maxIdle`, `minIdle`, `maxWaitMillis` according to business QPS. `maxTotal` reference formula: `(QPS × average response time) / 1000 + buffer`. Read timeout recommended 2s-5s.

#### 1.4.2. [Recommended] Careful Use of Hashtag

Unless there is a need for cross-key atomic operations, avoid manually constructing Hashtags with `{}`.

#### 1.4.3. [Recommended] Cluster Retry Configuration

`maxRedirections` defaults to 5 times is sufficient. Frequent redirection exceptions should investigate cluster stability rather than increasing retries.

---

### 1.5. Architecture Conventions

#### 1.5.1. [Mandatory] Single Instance Memory Limit

Single Redis instance maximum memory does not exceed 70%-80% of physical memory, not recommended to exceed 10GB. Must set `maxmemory` and `maxmemory-policy`.

#### 1.5.2. [Mandatory] Hot/Cold Data Separation

Only store high-frequency hot data (QPS > 5000) in Redis, cold data stored in MySQL/ES/MongoDB.

#### 1.5.3. [Mandatory] Business Isolation

Different business data stored in independent Redis clusters, to avoid mutual impact.

#### 1.5.4. [Recommended] Compressed Storage

Text data exceeding 500 Bytes compressed at application end (GZIP/Snappy/LZ4) before storing in Redis.

#### 1.5.5. [Recommended] Reasonable Eviction Policy Selection

Production environment must configure `maxmemory-policy`, `noeviction` not recommended. Common: `allkeys-lru` (mixed read/write), `volatile-lru` (only evict keys with TTL), `volatile-ttl` (prefer evicting about-to-expire), `allkeys-lfu` (Redis ≥4.0).

---

### 1.6. High Availability Conventions

#### 1.6.1. [Mandatory] Prohibit FLUSHALL/FLUSHDB

Strictly prohibit executing database clear commands in production environment.

#### 1.6.2. [Recommended] Add Exception Handling for Critical Operations

Core business data writes should capture Redis client exceptions and perform retry or degradation.

#### 1.6.3. [Recommended] Reliable Message Queue Implementation

When using Redis List for message queues, use `RPOPLPUSH` for consumption acknowledgement. Production environment message queues recommended to use RocketMQ/Kafka.

#### 1.6.4. [Recommended] Data Backup and Recovery

- Cache scenarios can enable RDB only
- Persistent data scenarios enable both RDB and AOF
- Hybrid persistence (Redis ≥4.0): `aof-use-rdb-preamble yes`
- At least one snapshot backup daily

#### 1.6.5. [Recommended] Cluster Deployment and Node Monitoring

Production instances must choose master-replica or cluster instances. Redis Cluster shards data across multiple nodes, each key maps to one of 16384 hash slots. Must monitor the memory usage ratio, connection count, evicted key count, slow query log.
