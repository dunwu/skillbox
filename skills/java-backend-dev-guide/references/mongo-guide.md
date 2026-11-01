# MongoDB Integration Development Standards

---

## 1. General Development Standards

### 1.1. Database and Collection Standards

#### 1.1.1. [Mandatory] Naming Conventions

Database and collection names must all be lowercase, only allowing letters, numbers, and underscores `_`, prohibited from starting with numbers or `system.`. Names at most 32 characters.

#### 1.1.2. [Mandatory] Database and Collection Count Control

Single database table count ≤100, entire instance table count ≤2000.

#### 1.1.3. [Mandatory] Reasonable Assessment of Sharding and Cluster Planning

Before creating new databases, must assess data volume and throughput. Collections expected to exceed 3TB, or whose working set exceeds memory capacity, must have a sharding plan designed in advance.

#### 1.1.4. [Recommended] Use TTL Indexes for Auto-Expiration

Time-sensitive data such as logs and sessions must create TTL indexes on time fields. Field type must be Date.

#### 1.1.5. [Recommended] Reasonable Use of Capped Collections

Fixed-size, FIFO scenarios (such as latest log polling) use capped collections. Do not support regular `remove()` and size-incremental `update()`.

#### 1.1.6. [Recommended] Different Businesses Use Different Databases

Avoid issues from database-level locking, different businesses use different databases.

---

### 1.2. Document Modeling Standards

#### 1.2.1. [Recommended] Maintain Document Structure Consistency

Documents within the same collection maintain similar structure, to improve index efficiency and query predictability.

#### 1.2.2. [Mandatory] Control Document Size and Nesting Depth

Single BSON document ≤16MB, nesting depth ≤3 levels.

#### 1.2.3. [Recommended] Embedding vs Referencing

- **Embedding preferred**: Data queried together, has "contains" relationship, updated together, archived simultaneously
- **Referencing preferred**: Data exists independently, frequently updated, high write load, documents grow unboundedly

#### 1.2.4. [Recommended] Document Field Design Conventions

- Documents include `sys_ctime` (creation time) and `sys_utime` (update time)
- Keys prohibited from using special characters other than `_`, keys all lowercase, multi-word separated by underscores
- Prohibit keys starting with numbers

---

### 1.3. Index Design Standards

#### 1.3.1. [Mandatory] Follow Leftmost Prefix Principle

Composite indexes must match the leftmost prefix logic of queries. Index `{a: 1, b: 1}` supports queries on `a` or `a, b`, cannot efficiently support `b` alone.

#### 1.3.2. [Mandatory] Query and Sort Fields Must Have Indexes

All fields in `find` filter conditions and `sort` ordering conditions must have indexes.

#### 1.3.3. [Mandatory] Index Creation in Production Must Use the background Parameter

MongoDB versions before 4.2 default `createIndex()` to foreground mode which blocks all operations, must add `background: true`.

#### 1.3.4. [Mandatory] Limit Single Table Index Count

Single table indexes not to exceed 10, prohibit indexing every field.

#### 1.3.5. [Recommended] Composite Index Field Order Optimization

Follow ESR rule (Equality → Sort → Range): equality fields leftmost, sort fields next, range fields last. `$ne`, `$nin` cannot effectively utilize indexes.

#### 1.3.6. [Recommended] Prefer Covering Indexes

Include fields returned by queries in the index as well.

#### 1.3.7. [Recommended] Create Indexes on Fields with Higher Selectivity

Prefer creating indexes for high-selectivity (high cardinality) fields.

#### 1.3.8. [Recommended] Use Hidden Indexes Wisely

MongoDB 4.4+ use hidden index to first hide unused indexes, verify business is normal before deleting, to avoid accidental deletion.

#### 1.3.9. [Recommended] Index Selection Strategy

- **Single-key index**: Used when all queries are single-key queries
- **Composite index**: When queries involve multiple keys (at most 32 keys)
- **Text index**: Match specific words from large text fields

---

### 1.4. Query and Aggregation Optimization

#### 1.4.1. [Mandatory] Limit Return Count and Sort Range

Single query returns ≤2000 records. Sort fields must have indexes, sort operations ≤32MB memory.

#### 1.4.2. [Mandatory] Prohibit High-Risk Operators

Strictly prohibit using `$where` in production; use `$ne`, `$nin`, `$or` with caution, these operators easily cause index invalidation.

#### 1.4.3. [Recommended] Use Aggregation Framework and Explain Wisely

- Complex statistics prefer Aggregation Pipeline over MapReduce
- Before going live, must use `explain("executionStats")` to analyze execution plan, ensure `stage` is `IXSCAN`
- `$match` stage in aggregation pipeline placed early to filter data as soon as possible
- Create indexes on outer collection for `$lookup` join queries

#### 1.4.4. [Recommended] Projection Queries

Use Projection when querying to specify needed fields, reduce network transmission and memory usage, improve covering index hit rate.

---

### 1.5. Writes and Atomicity

#### 1.5.1. [Recommended] Batch Writes

High-frequency writes use `bulkWrite` or `insertMany`, single batch ≤1000 records or 16MB.

#### 1.5.2. [Mandatory] Understand Atomicity Boundaries

MongoDB atomicity is limited to single-document level. Business must construct related data as single documents through embedded documents and array structures.

#### 1.5.3. [Recommended] Conditional Updates Use `findAndModify`

Use `findAndModify` for atomic "find and update" operations, operations on the same document are atomic.

#### 1.5.4. [Recommended] Efficient Data Cleanup

Use `drop()` instead of `remove({})` to clear collection data.

#### 1.5.5. [Recommended] Multi-Document Transaction Usage Limits

MongoDB 4.0+ supports multi-document transactions, but use with caution, avoid frequent use in high-performance write scenarios. Prefer satisfying requirements through single-document atomic operations.

---

### 1.6. Cluster and High Availability

#### 1.6.1. [Mandatory] Replica Set Connection Mode

Must connect through Replica Set, prohibit direct single-node connection.

#### 1.6.2. [Recommended] Read-Write Separation and Read Preference Configuration

Configure `ReadPreference` according to business needs, distribute query pressure to secondary nodes. Note data delay when using secondary nodes.

#### 1.6.3. [Recommended] Monitor Key Metrics

- Slow query threshold defaults to 100ms, adjust through `db.setProfilingLevel`
- Cache hit rate monitored through `db.serverStatus().wiredTiger.cache`, <90% needs scaling
- Sharded clusters regularly run `db.stats()` and `sh.status()` to monitor health

#### 1.6.4. [Recommended] Shard Key Selection

Shard keys should have high cardinality (large number of unique values), avoid using low-cardinality shard keys. Official recommendation to use `analyzeShardKey` to assist selection.

#### 1.6.5. [Recommended] Monitoring and Optimization Tools

- `mongotop`: Analyze read/write load by collection
- `mongostat`: Periodically report server statistics
- `db.currentOp()`: Locate long-running queries
- `db.collection.stats()`: Collection detailed statistics (index size, document count, etc.)

---

### 1.7. Performance Optimization

#### 1.7.1. [Recommended] WiredTiger Cache Configuration

Set cache size through `storage.wiredTiger.engineConfig.cacheSizeGB`, recommended 50%-60% of available memory. Cache hit rate <90% needs scaling.

#### 1.7.2. [Recommended] Working Set Analysis

Ensure active data (working set) can fit in memory.

#### 1.7.3. [Recommended] Aggregation Framework Optimization

- `$match` placed early to filter data as soon as possible
- Create indexes on outer joined collections for `$lookup`
- Set `allowDiskUse: true` for large data volume aggregation

---

### 1.8. Anti-Patterns

| Anti-pattern | Problem description | Correct practice |
|:------------|:-------------------|:----------------|
| `_id` uses auto-increment sequence or random strings | B-Tree index reorganization frequent, write performance drops | Use default `ObjectId` |
| Create index for every field | Write performance severely drops, storage waste | Single table indexes not to exceed 10 |
| No TTL or no table splitting | Data grows unboundedly, performance degrades yearly | Must set TTL, split tables or shard when necessary |
| Production uses unindexed full table scans | Cluster load spikes or even crashes | All queries must have corresponding indexes |
| MongoDB 4.2 and earlier: index creation in production without background | Blocks all database operations | Must add `background: true` |
| Use array fields as primary query conditions | Array indexes are large, query efficiency low | Avoid using array fields as primary query conditions |
| Use `$where` for complex queries | Extremely poor performance, cannot utilize indexes | Use aggregation framework or application layer processing |
| Frequently create and close database connections | High connection overhead, resource waste | Use connection pool to manage connections |
