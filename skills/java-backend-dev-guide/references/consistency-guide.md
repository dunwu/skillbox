# Cross-Storage Data Consistency Pattern Guide

> **Summary**
>
> - **Core constraint**: Multi-storage writes MUST adopt "MySQL first, then async writes to other stores" pattern; MySQL → ES sync MUST use Canal/MQ async, MUST NOT use synchronous dual-write; cache updates follow Cache Aside (update DB first, then delete cache); partial failure in multi-step writes MUST have compensation mechanism
> - **Key thresholds**: Async sync latency tolerance ≤5s; compensation retries max 3; eventual consistency convergence time ≤30s
> - **Common violations**: Synchronous dual-write MySQL+ES, delete cache before updating DB, send MQ inside transaction, ignore data gaps after Canal stream interruption

---

## 1. Consistency Model Selection

| Consistency level | Applicable scenarios | Implementation | Typical storage combinations |
|------------------|---------------------|---------------|----------------------------|
| Strong consistency | Funds, inventory deduction | Distributed transaction / local transaction + synchronous call | MySQL single database / sharded database |
| Eventual consistency | Content publishing, index sync | Async message + compensation | MySQL → ES / MongoDB |
| Weak consistency (tolerate loss) | Counters, PV statistics | Best-effort write + periodic reconciliation | MySQL → Redis |

**Selection principles**:

- **MUST** prefer eventual consistency, avoid introducing distributed transactions
- Only use strong consistency when business semantics require "all succeed or all fail"
- Weak consistency scenarios MUST have periodic reconciliation mechanism

---

## 2. MySQL → ES Sync Pattern

### 2.1. Recommended Pattern: Canal Listening to Binlog

```
MySQL ──Binlog──→ Canal ──→ MQ ──→ 消费者 ──→ ES
```

**Advantages**: Decouples business code, guarantees Binlog ordering, interrupted streams can be replayed from the break point.

**MUST**:

- Canal instances MUST monitor latency, latency > 5s triggers alert
- Consumers MUST implement idempotency (deduplicate by `binlog position + row primary key`)
- After Canal stream interruption recovery, MUST resume from breakpoint, MUST NOT discard changes during interruption
- ES batch writes use BulkProcessor (→ es-guide.md §1.4)

### 2.2. Alternative Pattern: Send MQ After Transaction Commit

```java
// ✅ 事务提交后再发 MQ
@Transactional(rollbackFor = Exception.class)
public void createArticle(CreateArticleCMD cmd) {
    articleDao.save(article);
    TransactionSynchronizationManager.registerSynchronization(
        new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                articleEventPublisher.publishCreated(event);
            }
        }
    );
}
```

**MUST NOT** send MQ inside transaction (transaction rolls back but message already sent, causing data inconsistency).

### 2.3. Sync Pattern Selection

| Scenario | Recommended pattern | Reason |
|----------|-------------------|--------|
| Full index sync | Canal | Decoupled, ordering guaranteed |
| Single record index update | Post-transaction MQ | Simple, low latency |
| Index rebuild | Full export + BulkProcessor | Batch efficient |

---

## 3. MySQL → Redis Cache Consistency

### 3.1. Cache Aside Pattern (Recommended)

```
读：先读缓存 → 未命中则读库 → 写入缓存（设 TTL）
写：先更库 → 再删缓存
```

**MUST NOT** use "delete cache first, then update DB" (concurrent reads will write stale values back to cache).

### 3.2. Delayed Double Delete (Extremely High Consistency Scenarios)

```java
public void updateArticle(Article article) {
    articleDao.updateById(article);
    cacheClient.del(cacheKey);
    scheduler.schedule(() -> cacheClient.del(cacheKey), 500, TimeUnit.MILLISECONDS);
}
```

### 3.3. Canal Async Cache Deletion

Applicable to scenarios with extremely high consistency requirements and low write frequency:

```
MySQL ──Binlog──→ Canal ──→ 消费者 ──→ 删除 Redis 缓存
```

### 3.4. Cache Consistency Strategy Selection

| Consistency requirement | Recommended strategy | Notes |
|------------------------|---------------------|-------|
| General (tolerate brief inconsistency) | Cache Aside | Update DB first then delete cache, simple implementation |
| Relatively high | Delayed double delete | Additional delayed deletion, covers concurrent write-back |
| Extremely high | Canal async cache deletion | Binlog-based to guarantee eventual consistency |

---

## 4. MySQL → MongoDB Sync Pattern

### 4.1. Async Message Pattern

```
MySQL ──事务后 MQ──→ 消费者 ──→ MongoDB
```

**Applicable scenarios**: MySQL stores structured metadata, MongoDB stores semi-structured content documents.

**MUST**:

- Consumers MUST implement idempotency (deduplicate by business ID)
- MongoDB writes MUST handle `DuplicateKeyException`

### 4.2. Dual-write + Compensation Pattern

```java
@Transactional(rollbackFor = Exception.class)
public void createArticle(CreateArticleCMD cmd) {
    articleDao.save(articleDO);
    mongoTemplate.save(articleContentDO);
}
```

**Note**: This pattern relies on MongoDB participating in distributed transactions (requires MongoDB 4.0+ replica set). When lower versions do not support multi-document transactions, **MUST use async message pattern**.

---

## 5. MySQL → HBase Sync Pattern

### 5.1. Async Archive Pattern

```
MySQL ──Binlog──→ Canal/MQ ──→ 消费者 ──→ HBase
```

**Applicable scenarios**: Hot data in MySQL, cold data archived to HBase.

**MUST**:

- HBase RowKey MUST contain hash prefix (→ hbase-guide.md §1.1.1)
- Batch writes use `batchPut`, each batch ≤ 1000 records
- Archive tasks MUST have data verification (compare MySQL source data with HBase archived data consistency)

---

## 6. Multi-Storage Partial Failure Compensation

### 6.1. Compensation Pattern

When one step in multi-step writes fails, **MUST** handle according to the following priority:

| Strategy | Applicable scenarios | Implementation |
|----------|---------------------|---------------|
| Auto retry | Transient failures (network jitter, timeout) | Exponential backoff, max 3 times, intervals 1s/2s/4s |
| Compensation rollback | Permanent failure with partial writes already succeeded | Record compensation log, async execute reverse operation |
| Manual intervention | Compensation failed or data already exposed | Alert + operations ticket |

### 6.2. Compensation Log Specification

```sql
-- ✅ 补偿日志表结构
CREATE TABLE t_compensation_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    biz_type        VARCHAR(64)  NOT NULL COMMENT '业务类型',
    biz_id          VARCHAR(128) NOT NULL COMMENT '业务ID',
    action          VARCHAR(32)  NOT NULL COMMENT '操作：CREATE/UPDATE/DELETE',
    target_storage  VARCHAR(32)  NOT NULL COMMENT '目标存储：ES/REDIS/MONGO/HBASE',
    payload         TEXT         NOT NULL COMMENT '操作数据（JSON）',
    status          TINYINT      NOT NULL DEFAULT 1 COMMENT '1=待补偿 2=补偿中 3=已补偿 4=补偿失败',
    retry_count     TINYINT      NOT NULL DEFAULT 0 COMMENT '重试次数',
    max_retry       TINYINT      NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    next_retry_time DATETIME     NOT NULL COMMENT '下次重试时间',
    create_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status_next (status, next_retry_time),
    INDEX idx_biz (biz_type, biz_id)
) COMMENT '补偿日志表';
```

### 6.3. Prohibited Behaviors

- **MUST NOT** ignore async write failures (must record compensation log)
- **MUST NOT** use fixed intervals in compensation retries (must use exponential backoff)
- **MUST NOT** remain silent after compensation retries exceed 3 times (must alert + escalate to manual handling)

---

## 7. Data Reconciliation Mechanism

### 7.1. Periodic Reconciliation

For eventual consistency scenarios, **MUST** establish periodic reconciliation mechanism:

| Reconciliation type | Frequency | Implementation |
|--------------------|-----------|---------------|
| MySQL ↔ ES | Daily | Compare document count and latest update time, alert when difference exceeds threshold |
| MySQL ↔ Redis | Hourly | Sample hot keys to verify cache and DB data consistency |
| MySQL ↔ HBase | Daily | Compare archived data row count with MySQL archived record count |

### 7.2. Reconciliation Difference Handling

```
发现差异
  │
  ├─ 缺失数据 → 触发增量同步（从 MySQL 重新写入目标存储）
  │
  ├─ 多余数据 → 标记为待清理，人工确认后删除
  │
  └─ 数据不一致 → 以 MySQL 为准，覆盖目标存储
```

---

## Checklist and Anti-Patterns

### Checklist

When adding cross-storage operations:

- [ ] Consistency requirements clarified (strong / eventual / weak)
- [ ] Corresponding sync pattern selected (Canal / MQ / Cache Aside)
- [ ] Async write failure has compensation mechanism (compensation log + retry)
- [ ] Consumer has implemented idempotency
- [ ] Cache updates follow Cache Aside (update DB first then delete cache)
- [ ] Reconciliation mechanism established (frequency + alert threshold)
- [ ] No MQ sent inside transaction (MUST send after transaction commits)

### Common Anti-Patterns (Prohibited)

```
❌ 同步双写 MySQL + ES（性能差 + 部分失败无补偿）
❌ 先删缓存再更库（并发读回写脏数据）
❌ 事务内发 MQ（事务回滚但消息已发）
❌ 忽略 Canal 断流后的数据缺口
❌ 异步写入失败不记录补偿日志
❌ 补偿重试使用固定间隔（应指数退避）
❌ 无对账机制（数据漂移无法发现）
```
