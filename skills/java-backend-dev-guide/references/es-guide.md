# Elasticsearch Integration Development Standards

---

## 1. General Development Standards

### 1.1. Index and Shard Standards

#### 1.1.1. [Mandatory] Reasonable Shard Capacity and Count

Non-log indexes: 10GB–30GB per shard; log indexes: 30GB–50GB per shard. Single shard document count must not exceed 2.1 billion. Single shard ≤50GB, single node shard count ≤600. Replica count defaults to 1, core search indexes can configure 2 replicas.

#### 1.1.2. [Mandatory] Prohibit Wildcard Queries Across All Indexes

Production environments are strictly prohibited from using `indexName-*` or `_all` for full index queries. Use Aliases or explicitly specify index names.

#### 1.1.3. [Recommended] Use Index Aliases for Lifecycle Management

Business layer must access indexes through Aliases, hardcoding index names is prohibited. Indexes under an Alias ≤20, to avoid read amplification.

#### 1.1.4. [Recommended] Large Index Splitting Strategy

- Log indexes split by time: `index_2024_01`, `index_2024_02`
- Large business indexes rotate by date: `article_content_{$date}`
- Use Alias to uniformly expose the externally-facing access entry point

#### 1.1.5. [Recommended] Hot/Cold Data Tiering

Use ILM to allocate hot data to SSD nodes, cold data migrated to HDD nodes. Hot data within 3 months stored on SSD.

#### 1.1.6. [Mandatory] Pre-define Mapping, Prohibit Dynamic Mapping

Must explicitly define Index Mapping, and set `dynamic` to `strict` (writes of unknown fields fail) or `false` (unknown fields are not mapped, kept only in `_source`).

#### 1.1.7. [Recommended] Use Index Templates to Standardize New Indexes

Create Index Templates for similar indexes, unify settings and mappings, ensure new indexes automatically inherit the same configuration.

---

### 1.2. Field and Modeling Standards

#### 1.2.1. [Mandatory] Distinguish Text and Keyword Types

| Type | Characteristics | Applicable scenarios |
|------|----------------|---------------------|
| `text` | Analyzed, used for full-text search | Article content, product descriptions |
| `keyword` | Not analyzed, exact match | Status codes, category tags, IDs |

Fields requiring full-text search use text; fields requiring sorting, aggregation, exact match use keyword. Prohibit fuzzy search or regex matching on text fields.

#### 1.2.2. [Recommended] Selectively Enable Doc Values and Disable Norms

Fields not requiring aggregation or sorting set `"doc_values": false`; text fields not requiring document weight calculation set `"norms": false`.

#### 1.2.3. [Mandatory] Avoid Wide Tables and Excessive Nesting

Single index field count ≤100 (strictly prohibited to exceed 1000). `nested` or `parent-child` queries have significant performance overhead, use with caution.

#### 1.2.4. [Recommended] Field Naming Conventions and Case Unification

Field names uniformly use snake_case (e.g. `user_name`, `order_id`).

#### 1.2.5. [Recommended] Use Runtime Fields for Unknown Fields

For fields where Mapping cannot be pre-defined and high-performance queries are not needed, use runtime fields instead of dynamic mapping.

---

### 1.3. Search Optimization

#### 1.3.1. [Mandatory] Prohibit Deep Pagination

Prohibit `from + size > 10000` (ES default `max_result_window = 10000`). Single query returns ≤2000 records.

- Shallow pagination uses `from+size`
- Deep pagination / real-time scrolling uses `search_after` (requires unique sort field)
- Full export >10000 hits uses PIT + search_after or scroll API

#### 1.3.2. [Mandatory] Prohibit Inefficient Wildcard Queries

Strictly prohibit wildcard or regexp queries starting with `*`. For prefix or middle matching, recommend using ngram tokenizer instead.

#### 1.3.3. [Mandatory] Use Filter Instead of Query for Filtering

Conditions that are not full-text search and only need to determine match must use filter context.

```java
builder.query(QueryBuilders.boolQuery()
        .must(QueryBuilders.matchQuery("title", keyword))      // 全文检索用 must
        .filter(QueryBuilders.termQuery("status", 1))          // 精确过滤用 filter
        .filter(QueryBuilders.termQuery("authorId", authorId)));
```

#### 1.3.4. [Recommended] Optimize Aggregations and Sorting

- Aggregation field types should be keyword or numeric, avoid text type aggregation
- Sort fields must have doc_values enabled, text field sorting is prohibited
- Avoid excessive nesting in aggregations
- High-cardinality field aggregation uses terms + size to limit bucket count

#### 1.3.5. [Recommended] Control Return Fields

`_source` only returns business-required fields, avoid returning all fields.

```java
builder.fetchSource(new String[]{"title", "summary", "authorName", "publishTime"}, null);
```

---

### 1.4. Write Optimization

#### 1.4.1. [Recommended] Reasonable Use of Bulk Batch Writes

Production environments must use Bulk API, single Bulk 5MB–15MB or 500–5000 documents. Small batches ≤1000 use synchronous batch, large batches >1000 use async BulkProcessor.

**BulkProcessor trigger conditions** (any one triggers): accumulated 1000 documents / accumulated 5MB / elapsed >1000ms since last flush.

#### 1.4.2. [Mandatory] Careful Use of Refresh Strategy

Default `refresh_interval` 1s. High-throughput write scenarios can increase to 30–120s, restore to default after completion. Prohibit `wait_for_refresh=true` during writes. Do not proactively trigger refresh during writes.

#### 1.4.3. [Recommended] Replica Downgrade During Import

Set replica count to 0 temporarily during index initialization or full import, restore to 1 after completion.

#### 1.4.4. [Mandatory] Avoid Using Update/Delete By Query

Strictly prohibit high-frequency use of `update_by_query` / `delete_by_query`. For large data volume deletion, use TTL (ILM) or index-level deletion.

---

### 1.5. Cluster and High Availability

#### 1.5.1. [Mandatory] Cluster Connection Mode

Clients must be configured with multiple cluster node addresses; configuring only a single node is prohibited. Domain name connection recommended.

#### 1.5.2. [Mandatory] Master Node Count and Split Brain Prevention

Cluster must configure at least 3 candidate master nodes, `discovery.zen.minimum_master_nodes` set to `N/2+1` (applicable for ES <7.0; ES 7.0+ managed automatically by cluster).

#### 1.5.3. [Recommended] Use Rolling Restart

Cluster maintenance upgrades must use Rolling Restart to restart nodes one by one, wait for cluster to recover to green before continuing.

#### 1.5.4. [Recommended] Monitor Key Metrics

- **Nodes**: JVM Heap usage, GC, disk usage, Segment Memory
- **Indexes**: Docs Count, Deleted Docs, Store Size, Query/Index latency
- **Cluster**: Health Status, Pending Tasks, Unassigned Shards
- **Performance**: Search/Index thread pool backlog, Bulk Rejection, query circuit breaker count
- **Slow queries**: Configure `index.search.slowlog.threshold.query.warn: 10s` etc. in index template

#### 1.5.5. [Recommended] Use Circuit Breakers to Prevent OOM

```json
PUT /_cluster/settings
{
  "persistent": {
    "indices.breaker.total.limit": "60%",
    "indices.breaker.fielddata.limit": "40%",
    "indices.breaker.request.limit": "10%"
  }
}
```

Text aggregations that have not disabled fielddata must be paired with circuit breakers.

#### 1.5.6. [Recommended] Use Snapshot Backups

Core business data must have regular snapshot backups to HDFS/S3, recommended at least once daily.

#### 1.5.7. [Recommended] Read-Write Separation and Query Routing

When read load is high, achieve read scaling by increasing replica count.

---

### 1.6. Performance Optimization

#### 1.6.1. [Recommended] JVM and Operating System Configuration

JVM heap memory configured to half of physical memory and not exceeding 32GB (recommended 28GB). Disable swap partition (swap off).

#### 1.6.2. [Recommended] Reasonable Shard Configuration

Shard capacity 10-50 GB, shard count is a multiple of node count. Estimate data volume for the next 3–6 months before designing shards.

#### 1.6.3. [Recommended] Use Sliced Scroll to Accelerate Large Data Export

When using Scroll API to export large amounts of data, enable sliced scroll for parallel fetching.

#### 1.6.4. [Recommended] Node Role Separation

Production environments configure dedicated master nodes, dedicated coordinating nodes, data nodes (Hot/Warm/Cold tiering).

---

### 1.7. Anti-Patterns

| Anti-pattern | Problem | Correct practice |
|:------------|:--------|:----------------|
| Dynamic mapping | Field types uncontrollable | Must explicitly define Mapping |
| from + size exceeding 10000 | Memory consumption explosion | Use SearchAfter or Scroll |
| Unreleased Scroll cursor | ES memory leak | Must call clearScroll after query |
| indexName-* wildcard query | Scans all matching indexes | Use Alias or explicitly specify index name |
| script / update_by_query / delete_by_query | High version conflict risk | Use Bulk API or update by ID |
| Regex match query | O(N) full index scan | Use ngram tokenizer instead |
| Wide table (fields exceeding 100) | Column storage efficiency drops | Split index or assemble at application layer |
| Text field aggregation | Requires enabling fielddata, extremely high memory | Use keyword or multi-field mapping instead |
| Loop single-document writes | High network RTT overhead | Use Bulk API or BulkProcessor |
| wait_for_refresh=true | Write performance drops sharply | Rely on default 1s refresh interval |
| Not specifying fetchSource | Returns all fields, wastes bandwidth | Only return business-required fields |
| Ignoring BulkProcessor afterBulk failure callback | Batch write failure undetectable | Must handle failure callback and record logs |
