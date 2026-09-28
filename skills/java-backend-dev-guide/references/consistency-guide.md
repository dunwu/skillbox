# 跨存储数据一致性模式指南

> **摘要**
>
> - **核心约束**：多存储写入 MUST 采用"先 MySQL 后异步入步"模式；MySQL → ES 同步 MUST 通过 Canal/MQ 异步，MUST NOT 同步双写；缓存更新遵循 Cache Aside（先更库再删缓存）；多步写入部分失败 MUST 有补偿机制
> - **关键阈值**：异步同步延迟容忍 ≤5s；补偿重试最多 3 次；最终一致性收敛时间 ≤30s
> - **常见违规**：同步双写 MySQL+ES、先删缓存再更库、事务内发 MQ、忽略 Canal 断流后的数据缺口

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 一致性模型选型

| 一致性级别           | 适用场景           | 实现方式                         | 典型存储组合         |
| -------------------- | ------------------ | -------------------------------- | -------------------- |
| 强一致性             | 资金、库存扣减     | 分布式事务 / 本地事务 + 同步调用 | MySQL 单库 / 分库    |
| 最终一致性           | 内容发布、索引同步 | 异步消息 + 补偿                  | MySQL → ES / MongoDB |
| 弱一致性（容忍丢失） | 计数器、PV 统计    | 尽力写入 + 定期对账              | MySQL → Redis        |

**选型原则**：

- **MUST** 优先选择最终一致性，避免引入分布式事务
- 仅当业务语义要求"要么全成功要么全失败"时使用强一致性
- 弱一致性场景 MUST 有定期对账机制

---

## 2. MySQL → ES 同步模式

### 2.1. 推荐模式：Canal 监听 Binlog

```
MySQL ──Binlog──→ Canal ──→ MQ ──→ 消费者 ──→ ES
```

**优势**：解耦业务代码、保证 Binlog 顺序、断流可回溯。

**MUST**：

- Canal 实例 MUST 监控延迟，延迟 > 5s 触发告警
- 消费者 MUST 实现幂等（以 `binlog position + row primary key` 去重）
- Canal 断流恢复后 MUST 从断点续读，MUST NOT 丢弃断流期间的变更
- ES 批量写入使用 BulkProcessor（→ es-guide.md §2）

### 2.2. 备选模式：事务提交后发 MQ

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

**MUST NOT** 在事务内发 MQ（事务回滚但消息已发，造成数据不一致）。

### 2.3. 同步模式选择

| 场景             | 推荐模式                 | 原因           |
| ---------------- | ------------------------ | -------------- |
| 全量索引同步     | Canal                    | 解耦、顺序保证 |
| 单条记录索引更新 | 事务后 MQ                | 简单、延迟低   |
| 索引重建         | 全量导出 + BulkProcessor | 批量高效       |

---

## 3. MySQL → Redis 缓存一致性

### 3.1. Cache Aside Pattern（推荐）

```
读：先读缓存 → 未命中则读库 → 写入缓存（设 TTL）
写：先更库 → 再删缓存
```

**MUST NOT** 使用"先删缓存再更库"（并发读会将旧值回写缓存）。

### 3.2. 延迟双删（极高一致性场景）

```java
public void updateArticle(Article article) {
    articleDao.updateById(article);
    cacheClient.del(cacheKey);
    scheduler.schedule(() -> cacheClient.del(cacheKey), 500, TimeUnit.MILLISECONDS);
}
```

### 3.3. Canal 异步删缓存

适用于对一致性要求极高且写频率低的场景：

```
MySQL ──Binlog──→ Canal ──→ 消费者 ──→ 删除 Redis 缓存
```

### 3.4. 缓存一致性策略选择

| 一致性要求             | 推荐策略         | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| 一般（容忍短暂不一致） | Cache Aside      | 先更库再删缓存，实现简单   |
| 较高                   | 延迟双删         | 额外延迟删除，覆盖并发回写 |
| 极高                   | Canal 异步删缓存 | 基于 Binlog 保证最终一致   |

---

## 4. MySQL → MongoDB 同步模式

### 4.1. 异步消息模式

```
MySQL ──事务后 MQ──→ 消费者 ──→ MongoDB
```

**适用场景**：MySQL 存结构化元数据，MongoDB 存半结构化内容文档。

**MUST**：

- 消费者 MUST 实现幂等（以业务 ID 去重）
- MongoDB 写入 MUST 处理 `DuplicateKeyException`

### 4.2. 双写 + 补偿模式

```java
@Transactional(rollbackFor = Exception.class)
public void createArticle(CreateArticleCMD cmd) {
    articleDao.save(articleDO);
    mongoTemplate.save(articleContentDO);
}
```

**注意**：此模式依赖 MongoDB 参与分布式事务（需 MongoDB 4.0+ 副本集），低版本不支持多文档事务时，**MUST 使用异步消息模式**。

---

## 5. MySQL → HBase 同步模式

### 5.1. 异步归档模式

```
MySQL ──Binlog──→ Canal/MQ ──→ 消费者 ──→ HBase
```

**适用场景**：热数据存 MySQL，冷数据归档 HBase。

**MUST**：

- HBase RowKey MUST 包含散列前缀（→ hbase-guide.md §2）
- 批量写入使用 `batchPut`，每批 ≤ 1000 条
- 归档任务 MUST 有数据校验（对比 MySQL 源数据与 HBase 归档数据的一致性）

---

## 6. 多存储部分失败补偿

### 6.1. 补偿模式

当多步写入中某一步失败时，**MUST** 按以下优先级处理：

| 策略     | 适用场景                     | 实现方式                           |
| -------- | ---------------------------- | ---------------------------------- |
| 自动重试 | 临时性故障（网络抖动、超时） | 指数退避，最多 3 次，间隔 1s/2s/4s |
| 补偿回滚 | 永久性失败且已有部分写入成功 | 记录补偿日志，异步执行反向操作     |
| 人工介入 | 补偿失败或数据已暴露         | 告警 + 运维工单                    |

### 6.2. 补偿日志规范

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

### 6.3. 禁止行为

- **MUST NOT** 忽略异步写入失败（必须记录补偿日志）
- **MUST NOT** 在补偿重试中使用固定间隔（必须指数退避）
- **MUST NOT** 补偿重试超过 3 次后仍静默（必须告警 + 升级为人工处理）

---

## 7. 数据对账机制

### 7.1. 定期对账

对于最终一致性场景，**MUST** 建立定期对账机制：

| 对账类型      | 频率   | 实现方式                                 |
| ------------- | ------ | ---------------------------------------- |
| MySQL ↔ ES    | 每日   | 对比文档数和最新更新时间，差异超阈值告警 |
| MySQL ↔ Redis | 每小时 | 抽样热 Key 验证缓存与库数据一致性        |
| MySQL ↔ HBase | 每日   | 对比归档数据行数与 MySQL 已归档记录数    |

### 7.2. 对账差异处理

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

## Checklist 与反模式

### Checklist

新增跨存储操作时：

- [ ] 明确一致性要求（强一致 / 最终一致 / 弱一致）
- [ ] 选择对应的同步模式（Canal / MQ / Cache Aside）
- [ ] 异步写入失败有补偿机制（补偿日志 + 重试）
- [ ] 消费者已实现幂等
- [ ] 缓存更新遵循 Cache Aside（先更库再删缓存）
- [ ] 已建立对账机制（频率 + 告警阈值）
- [ ] 事务内未发 MQ（MUST 在事务提交后发送）

### 常见反模式（禁止）

```
❌ 同步双写 MySQL + ES（性能差 + 部分失败无补偿）
❌ 先删缓存再更库（并发读回写脏数据）
❌ 事务内发 MQ（事务回滚但消息已发）
❌ 忽略 Canal 断流后的数据缺口
❌ 异步写入失败不记录补偿日志
❌ 补偿重试使用固定间隔（应指数退避）
❌ 无对账机制（数据漂移无法发现）
```

---

## 变更记录

| 版本 | 日期       | 变更     | Review |
| ---- | ---------- | -------- | ------ |
| v1.0 | 2026-06-09 | 初始版本 | —      |
