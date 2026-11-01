# MySQL Integration Development Standards

---

## 1. General Development Standards

### 1.1. Table Creation Standards

#### 1.1.1. [Recommended] Denormalization and Redundancy Sync Mechanism

For high-frequency read and low-frequency update scenarios, moderate redundancy of core fields is allowed (such as redundantly storing product names in order table) to reduce `JOIN`, but must establish reliable data sync mechanism (Canal listening to Binlog or MQ async notification) to guarantee eventual consistency.

Redundancy is allowed when:

1. Not frequently modified fields
2. Not unique index fields
3. Not overly long `varchar` fields, and definitely not `text` fields

#### 1.1.2. [Mandatory] JSON Field Performance Boundaries

Only use `JSON` type when data structure is extremely flexible and internal fields do not need complex indexing. Core search fields must be split into independent columns.

#### 1.1.3. [Recommended] Partition Table Usage Standards

When single table data exceeds 5 million rows, can partition by time (RANGE), hash (HASH), list (LIST), etc. RANGE partition by month or year is preferred.

---

### 1.2. Index Standards

#### 1.2.1. [Mandatory] Composite Index "Equality - Range" Ordering Principle

When creating composite indexes, equality query (`=` / `IN`) fields must be placed first, range query (`>` / `<` / `BETWEEN`) fields placed after.

Example: `WHERE a = 1 AND b > 10 ORDER BY c`, index should be created as `(a, b, c)`.

#### 1.2.2. [Recommended] Prefix Index Selectivity Quantification

When using prefix indexes for long strings (such as URLs, summaries), must ensure selectivity ≥ 90%. Can evaluate through `SELECT COUNT(DISTINCT LEFT(col, N)) / COUNT(*)`.

#### 1.2.3. [Recommended] Index Condition Pushdown Utilization

Confirm ICP takes effect through `EXPLAIN` `Extra` column showing `Using index condition`.

#### 1.2.4. [Recommended] Index Length Control

When creating indexes on `VARCHAR` fields, specify appropriate index length, no need to index the entire field.

---

### 1.3. SQL Statement Standards

#### 1.3.1. [Mandatory] Deep Pagination Performance Optimization

Direct use of `LIMIT offset, size` for deep pagination over millions of records is prohibited. Select based on scenario:

- **Cursor pagination (Keyset Pagination)**: Applicable to continuous paging or infinite scrolling. `WHERE id > last_id LIMIT size`.
- **Deferred join**: Applicable to random jumps. Subquery first locates primary key IDs, then `JOIN` original table to get details.

```sql
-- ❌ 慢：offset 10万时需扫描 100010 行
SELECT * FROM t_article WHERE status=2 LIMIT 100000, 20;

-- ✅ 快：先用覆盖索引定位 id，再关联取数据
SELECT a.* FROM t_article a
                  INNER JOIN (SELECT id FROM t_article WHERE status=2 LIMIT 100000, 20) b
ON a.id = b.id;
```

#### 1.3.2. [Mandatory] Implicit Conversion Deep Investigation

Besides parameter type consistency, also pay attention to character set (Charset) and collation consistency. `characterEncoding` in JDBC URL must match database definition.

---

### 1.4. Transaction and Lock Standards

#### 1.4.1. [Mandatory] Deadlock Prevention and Retry Mechanism

When accessing the same group of resources in concurrent environments, must maintain consistent locking order. Business layer must have deadlock (Error Code 1213) auto-retry mechanism, using exponential backoff strategy.

#### 1.4.2. [Recommended] Gap Lock Risk Avoidance

Under RR isolation level, try to avoid range updates or deletes on non-unique indexes.

#### 1.4.3. [Recommended] Avoid Large Transactions

- Move log recording, message sending, cache updating, and other non-core operations out of transaction blocks
- Do not perform RPC / HTTP calls and other time-consuming operations inside transactions
- Pay attention to cache rollback, search engine rollback, and other compensation plans

---

### 1.5. Cluster and High Availability Standards

#### 1.5.1. [Mandatory] Online DDL Change Process

For table structure changes on tables exceeding 1 million rows in production, direct `ALTER TABLE` is strictly prohibited, must use lock-free tools such as `gh-ost` or `pt-online-schema-change`.

#### 1.5.2. [Mandatory] Read-Write Separation Strategy for Master-Slave Delay

Scenarios that read immediately after writing (such as querying order after successful payment), must be forcibly routed to the master database.

---

### 1.6. Partition Table Management Standards

#### 1.6.1. [Recommended] Partition Strategy Selection

Prefer RANGE partition (by time range), avoid using HASH partition for data cleanup.

---

### 1.7. Data Archive Governance Standards

#### 1.7.1. [Recommended] Hot/Cold Data Separation

Historical data older than 6 months should be archived from main business tables to archive tables or data warehouse ODS layer, keeping main business tables ≤5 million rows. Recommended to use partition tables + `EXCHANGE PARTITION` for quick splitting.

---

### 1.8. Operations Monitoring Standards

#### 1.8.1. [Recommended] Slow Log Automated Analysis and Alerting

Should integrate with slow log analysis platform, auto-alert for SQL with `Query_time > 1s` and `Rows_examined > 10000`. Enable `slow_query_log=ON`, `long_query_time≥1.0`; analyze with `pt-query-digest`.

#### 1.8.2. [Recommended] Backup and Recovery Drills

Core business tables must enable Binlog and perform regular full backups. At least one data recovery drill per half year.

---

### 1.9. SQL Audit and Cost Standards

#### 1.9.1. [Recommended] Development Stage SQL Review

Before going live, all SQL must pass through review platform scanning, `SELECT *` and unindexed conditional queries are prohibited from going live.
