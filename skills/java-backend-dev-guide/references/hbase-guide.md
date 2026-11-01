# HBase Integration Development Standards

---

## 1. General Development Standards

### 1.1. Architecture and Modeling

#### 1.1.1. [Mandatory] RowKey Length and Hash Distribution

RowKey length controlled to 10–100 bytes (optimal 10–50 bytes). Must ensure uniform hash distribution, monotonically increasing or decreasing designs are strictly prohibited.

- **Correct example**: Hash salt `hash(userId) + timestamp`; reversed timestamp `Long.MAX_VALUE - timestamp + userId`
- **Anti-example**: Pure incrementing ID `articleId` (hotspot); timestamp prefix `timestamp + articleId` (batch write hotspot); UUID (unordered, storage waste)

#### 1.1.2. [Mandatory] Column Family Count Control

Each table must not exceed 3 column families, strongly recommend using only 1 column family. Column family names should be as concise as possible.

#### 1.1.3. [Mandatory] Pre-splitting

Tables must be pre-split when created, recommended partition count is 1.5–2x the RegionServer count. Pre-splitting can be performed via `SPLITS` parameter or `RegionSplitter` class.

#### 1.1.4. [Recommended] Hot/Cold Data Separation Modeling

Historical data older than 3 months is recommended to be split into separate tables by time dimension; large objects >1MB use MOB feature for storage.

---

### 1.2. Storage and Indexing

#### 1.2.1. [Mandatory] TTL and Version Count Control

TTL must be set. For non-audit scenarios, VERSIONS must be set to 1.

#### 1.2.2. [Recommended] Bloom Filter

Random read (Get) in read-intensive scenarios should enable the bloom filter (HBase enables it by default; do not explicitly disable it in the table definition), common type is `ROW`. Scan-dominated scenarios need not enable it.

#### 1.2.3. [Recommended] Enable Compression in Production

Recommended to use `SNAPPY` (balances performance and compression ratio) or `ZSTD` (higher compression ratio).

#### 1.2.4. [Recommended] Secondary Index Standards

HBase natively only supports RowKey queries. For multi-dimensional queries, select by the following priority:

1. **Phoenix global index**: Read-heavy, write-light, stable read performance
2. **Phoenix local index**: Write load is relatively heavy
3. **ES/Solr sync**: Full-text search, complex condition combinations

Strictly prohibit indexing all columns, only create indexes for high-frequency filter columns and high-selectivity fields.

---

### 1.3. Read/Write and Aggregation

#### 1.3.1. [Mandatory] Prohibit Full Table Scan

Strictly prohibit Scan without StartRow/StopRow. Scan cache `setCaching` recommended set to 50–100. Single batchPut ≤ 1000 records, must batch if exceeding.

#### 1.3.2. [Mandatory] Batch Operations and Memory Control

Writes must use `Table.put(List<Put>)` for batch submission. Disable `autoFlush`, set `writeBufferSize` to 8-32 MB.

#### 1.3.3. [Mandatory] Scan Pagination and Timeout

Scan must set Start/Stop range, and simultaneously set `setCaching` (rows fetched per RPC) and `setBatch` (limit columns returned per row).

#### 1.3.4. [Recommended] Aggregation Strategy

HBase is not suitable for complex aggregations. Real-time aggregation uses Redis to maintain pre-aggregated counts; offline aggregation uses Spark on HBase.

---

### 1.4. Transactions and Consistency

#### 1.4.1. [Mandatory] Row-level Atomicity Boundary

HBase only guarantees single-row atomicity. Cross-row operations must be implemented at the application layer.

#### 1.4.2. [Mandatory] CheckAndPut Usage

When implementing distributed locks, inventory deduction, state transitions, must use `checkAndPut` to ensure "check and modify" is atomic on the same row.

---

### 1.5. Cluster and Operations

#### 1.5.1. [Mandatory] Major Compaction Scheduling

Strictly prohibit manually triggering `major_compact` during business peak hours. Recommended to configure execution during off-peak hours.

#### 1.5.2. [Recommended] Monitor Key Metrics

- **RegionServer**: Heap Usage >80% alert, GC Time
- **Cache**: BlockCache Hit Ratio <90% needs optimization
- **Requests**: Requests Per Second, Compaction Queue Size

#### 1.5.3. [Recommended] Client Connection Pool and Retry

Application must reuse `Connection` and `Table` objects. Retry parameters: `hbase.client.retries.number` recommended 3, `hbase.client.pause` recommended 1000ms.

#### 1.5.4. [Recommended] Data Backup and Recovery

Core business tables must enable snapshot backup. Use `snapshot` / `restore_snapshot` for backup and recovery.

#### 1.5.5. [Recommended] Cross-cluster Replication

Multi-active or disaster recovery scenarios across regions must enable HBase Replication.

---

### 1.6. Security and Compliance

#### 1.6.1. [Mandatory] Authentication and Authorization

Production clusters must enable Kerberos authentication, use ACL for table-level and column-family-level permission control. Set `hbase.security.authentication` to `kerberos`.

#### 1.6.2. [Mandatory] Transport Encryption and Encryption at Rest

RPC communication enables SASL encryption; at-rest data encryption relies on HDFS transparent encryption (KMS).

---

### 1.7. Anti-Patterns

| Anti-pattern | Problem description | Correct practice |
|:------------|:-------------------|:----------------|
| Pure incrementing ID as RowKey | Hotspot writes, single Region becomes bottleneck | Use hash prefix or reversed timestamp |
| Full table Scan (no StartRow/StopRow) | Exhausts RegionServer resources | Must set StartRow/StopRow to limit range |
| Loop single put | High RPC overhead, low throughput | Use batchPut for batch writes |
| More than 3 column families | Compaction performance drops, write amplification | Merge column families, max 3 |
| Single batchPut exceeding 1000 records | High memory pressure, frequent GC | Batch processing, each batch ≤ 1000 records |
| Using UUID as RowKey | Unordered, poor read performance, storage waste | Use business ID + hash prefix |
| Not setting TTL and VERSIONS | StoreFile bloat, Scan performance drops | Must set TTL, non-audit VERSIONS=1 |
| Manual major_compact during business peak | I/O storm, P99 latency jitter | Configure automatic execution during off-peak |
| Not reusing Connection and Table objects | High connection establishment overhead, resource waste | Application reuses connection objects |
