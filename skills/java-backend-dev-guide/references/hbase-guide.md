# HBase 整合开发规约

> **摘要**
>
> - **核心约束**：RowKey 必须 10-100 字节且均匀散列（禁纯递增/时间戳前缀）；列族 ≤3 个；建表必须预分区；必须设 TTL 和 VERSIONS（非审计 VERSIONS=1）；禁无 StartRow/StopRow 的全表 Scan
> - **关键阈值**：batchPut ≤1000 条、Scan setCaching 50-100、单节点 shard ≤600 个
> - **常见违规**：纯递增 ID 作 RowKey 导致热点、全表 Scan 耗尽资源、忽略 TTL 导致 StoreFile 膨胀、业务高峰期触发 major_compact
> - **人工操作项**：HBase 表权限须通过管理平台申请，非 AI 编码范围

> **版本**：v1.1 | 最后更新：2026-06-08 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 通用开发规约

### 1.1. 架构与建模

#### 1.1.1. 【强制】RowKey 长度与散列性

RowKey 长度控制在 10~100 字节（最佳 10~50 字节）。必须保证均匀散列，严禁单调递增或递减设计。

- **正例**：哈希加盐 `hash(userId) + timestamp`；反转时间戳 `Long.MAX_VALUE - timestamp + userId`
- **反例**：纯递增 ID `articleId`（热点）；时间戳前缀 `timestamp + articleId`（批量写入热点）；UUID（无序、存储浪费）

#### 1.1.2. 【强制】列族数量控制

每张表列族数量不得超过 3 个，强烈建议仅使用 1 个列族。列族名应尽量简短。Flush 和 Compaction 以 Region 为单位，多列族会导致写放大。

#### 1.1.3. 【强制】预分区

建表时必须预分区，分区数量建议为 RegionServer 数量的 1.5~2 倍。可通过 `SPLITS` 参数或 `RegionSplitter` 类执行预分区。

#### 1.1.4. 【推荐】冷热数据分离建模

超过 3 个月的历史数据建议按时间维度分表；>1MB 的大对象使用 MOB 特性存储。

---

### 1.2. 存储与索引

#### 1.2.1. 【强制】TTL 与版本数控制

必须设置 TTL。非审计场景 VERSIONS 必须设为 1。过多版本导致 StoreFile 膨胀，Scan 性能指数级下降。

#### 1.2.2. 【推荐】布隆过滤器

随机读（Get）且读密集场景必须开启布隆过滤器，常用类型为 `ROW`。

#### 1.2.3. 【推荐】生产环境开启压缩

推荐使用 `SNAPPY`（兼顾性能与压缩率）或 `ZSTD`（更高压缩比）。

#### 1.2.4. 【推荐】二级索引规范

HBase 原生仅支持 RowKey 查询。多维度查询按以下优先级选择：

1. **Phoenix 全局索引**：读多写少，稳定读性能
2. **Phoenix 本地索引**：写负载较重
3. **ES/Solr 同步**：全文检索、复杂条件组合

严禁为所有列建索引，只针对高频过滤列、高选择性字段创建。

---

### 1.3. 读写与聚合

#### 1.3.1. 【强制】禁止全表扫描

严禁执行无 StartRow/StopRow 的 Scan。Scan 缓存 `setCaching` 建议设置为 50~100。单次 batchPut 不超过 1000 条，超出需分批。

#### 1.3.2. 【强制】批量操作与内存控制

写入必须使用 `Table.put(List<Put>)` 批量提交。配合关闭 `autoFlush` 并增大 `writeBufferSize`（8-32 MB）可显著提升吞吐量。

#### 1.3.3. 【强制】Scan 的分页与超时

Scan 必须设置 Start/Stop 范围，且同时设置 `setCaching`（单次 RPC 拉取行数）与 `setBatch`（限制单行返回列数），防止 Scanner 持有 Region 锁过久。

#### 1.3.4. 【推荐】聚合计算策略

HBase 不适合做复杂聚合。实时聚合使用 Redis 维护预聚合计数；离线聚合使用 Spark on HBase。

---

### 1.4. 事务与一致性

#### 1.4.1. 【强制】行级原子性边界

HBase 仅保证单行原子性。跨行操作必须在应用层实现。

#### 1.4.2. 【强制】CheckAndPut 的使用

实现分布式锁、库存扣减、状态流转时，必须使用 `checkAndPut`，保证「检查并修改」在同一行上是原子的。

---

### 1.5. 集群与运维

#### 1.5.1. 【强制】Major Compaction 调度

严禁在业务高峰期手动触发 `major_compact`。建议配置在低峰期执行。

#### 1.5.2. 【推荐】监控关键指标

- **RegionServer**：Heap Usage >80% 报警、GC Time
- **Cache**：BlockCache Hit Ratio <90% 需优化
- **请求**：Requests Per Second、Compaction Queue Size

#### 1.5.3. 【推荐】客户端连接池与重试

应用端必须复用 `Connection` 和 `Table` 对象。重试参数：`hbase.client.retries.number` 推荐 3，`hbase.client.pause` 推荐 1000ms。

#### 1.5.4. 【推荐】数据备份与恢复

核心业务表必须开启快照备份。使用 `snapshot` / `restore_snapshot` 进行备份恢复。

#### 1.5.5. 【推荐】跨集群复制

异地多活或灾备场景必须开启 HBase Replication。

---

### 1.6. 安全与合规

#### 1.6.1. 【强制】认证与授权

生产集群必须启用 Kerberos 认证，使用 ACL 进行表级、列族级权限控制。`hbase.security.authentication` 设为 `kerberos`。

#### 1.6.2. 【强制】传输加密与静态加密

RPC 通信开启 SASL 加密；静态数据加密依赖 HDFS 透明加密（KMS）。

---

### 1.7. 反模式

| 反模式                             | 问题描述                      | 正确实践                           |
| :--------------------------------- | :---------------------------- | :--------------------------------- |
| 纯递增 ID 作为 RowKey              | 热点写入，单 Region 成为瓶颈  | 使用散列前缀或反转时间戳           |
| 全表 Scan（不设 StartRow/StopRow） | 耗尽 RegionServer 资源        | 必须设置 StartRow/StopRow 限制范围 |
| 循环单条 put                       | RPC 开销大，吞吐量低          | 使用 batchPut 批量写入             |
| 列族超过 3 个                      | Compaction 性能下降，写放大   | 合并列族，最多 3 个                |
| 单次 batchPut 超过 1000 条         | 内存压力大，GC 频繁           | 分批处理，每批 ≤ 1000 条           |
| 用 UUID 作为 RowKey                | 无序读性能差，存储浪费        | 使用业务 ID + 散列前缀             |
| 未设置 TTL 和 VERSIONS             | StoreFile 膨胀，Scan 性能下降 | 必须设置 TTL，非审计 VERSIONS=1    |
| 业务高峰期手动触发 major_compact   | I/O 风暴，P99 延迟抖动        | 配置在低峰期自动执行               |
| 不复用 Connection 和 Table 对象    | 连接建立开销大，资源浪费      | 应用端复用连接对象                 |

---

## 2. 工程化规约（HBase Client + Spring Data Hadoop）

> **[FOR HUMAN REFERENCE]** 以下内容为工程化配置说明，AI 编码时通常无需加载。
>
> 本节基于 **Apache HBase Client** 标准用法编写。项目级 Skill 可覆盖为项目自定义封装（如 HbaseTemplate）。

### 2.1. 快速上手

#### 2.1.1. 添加依赖

```xml
<dependency>
    <groupId>org.apache.hbase</groupId>
    <artifactId>hbase-client</artifactId>
</dependency>
```

#### 2.1.2. 配置

```java
@Configuration
public class HbaseConfig {

    @Bean
    public Connection hbaseConnection() throws IOException {
        org.apache.hadoop.conf.Configuration config = HBaseConfiguration.create();
        config.set("hbase.zookeeper.quorum", "${HBASE_ZK_QUORUM}");
        config.set("hbase.zookeeper.property.clientPort", "${HBASE_ZK_PORT}");
        config.set("hbase.client.retries.number", "3");
        config.set("hbase.client.pause", "1000");
        return ConnectionFactory.createConnection(config);
    }
}
```

```java
@Autowired
private Connection hbaseConnection;
```

> ⚠️ **权限前置**：使用 HBase 前须通过管理平台申请目标表的读写权限。

---

### 2.2. 适用场景

| 场景                 | 推荐存储  | 说明                          |
| -------------------- | --------- | ----------------------------- |
| 海量内容正文（亿级） | **HBase** | 高吞吐随机读写，低存储成本    |
| 历史数据归档         | **HBase** | 冷数据，按时序 RowKey 扫描    |
| 用户行为时序数据     | **HBase** | 时间戳版本管理，Scan 范围查询 |
| 文章元数据（结构化） | MySQL     | 关联查询、事务                |
| 文档型内容（< 16MB） | MongoDB   | 半结构化，灵活 Schema         |

---

### 2.3. 实体与 RowKey 设计规范

#### 2.3.1. RowKey 散列前缀（必须）

```java
// ✅ 加散列前缀，数据均匀分布
String rowKey = String.format("%02d_%d", articleId % 100, articleId);

// ❌ 纯递增 ID 或时间戳前缀会导致热点
```

#### 2.3.2. 时序数据的反转时间戳

```java
long reverseTime = Long.MAX_VALUE - System.currentTimeMillis();
String rowKey = String.format("%d_%s", reverseTime, userId);
```

#### 2.3.3. RowKey 长度

建议 10~50 字节。避免使用 UUID。

---

### 2.4. 写操作规范

#### 2.4.1. 单条写入

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"))) {
    Put put = new Put(Bytes.toBytes(rowKey));
    put.addColumn(Bytes.toBytes("cf"), Bytes.toBytes("title"), Bytes.toBytes(title));
    put.addColumn(Bytes.toBytes("cf"), Bytes.toBytes("content"), Bytes.toBytes(content));
    table.put(put);
}
```

#### 2.4.2. 批量写入（必须用 batchPut）

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"))) {
    List<Put> puts = entities.stream()
        .map(entity -> {
            Put put = new Put(Bytes.toBytes(entity.getRowKey()));
            put.addColumn(Bytes.toBytes("cf"), Bytes.toBytes("title"), Bytes.toBytes(entity.getTitle()));
            put.addColumn(Bytes.toBytes("cf"), Bytes.toBytes("content"), Bytes.toBytes(entity.getRawContent()));
            return put;
        })
        .collect(Collectors.toList());
    table.put(puts);  // 批量写入
}
```

单次 `batchPut` 不超过 1000 条。

---

### 2.5. 读操作规范

#### 2.5.1. 按 RowKey 查询

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"))) {
    Get get = new Get(Bytes.toBytes(rowKey));
    get.addFamily(Bytes.toBytes("cf"));
    Result result = table.get(get);

    String title = Bytes.toString(result.getValue(Bytes.toBytes("cf"), Bytes.toBytes("title")));
    String content = Bytes.toString(result.getValue(Bytes.toBytes("cf"), Bytes.toBytes("content")));
}
```

#### 2.5.2. 批量 RowKey 查询

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"))) {
    List<Get> gets = rowKeys.stream()
        .map(key -> new Get(Bytes.toBytes(key)))
        .collect(Collectors.toList());
    Result[] results = table.get(gets);
}
```

---

### 2.6. Scan 扫描规范

#### 2.6.1. 分页查询

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"))) {
    Scan scan = new Scan();
    scan.setStartRow(Bytes.toBytes("00_" + authorId));
    scan.setStopRow(Bytes.toBytes("99_" + authorId + "z"));
    scan.setCaching(20);
    scan.addFamily(Bytes.toBytes("cf"));

    try (ResultScanner scanner = table.getScanner(scan)) {
        for (Result result : scanner) {
            // 处理每行数据
        }
    }
}
```

#### 2.6.2. 游标查询（大批量）

```java
Scan scan = new Scan();
scan.setStartRow(Bytes.toBytes(startRow));
scan.setStopRow(Bytes.toBytes(stopRow));
scan.setCaching(500);
scan.addFamily(Bytes.toBytes("cf"));

try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_content"));
     ResultScanner scanner = table.getScanner(scan)) {
    for (Result result : scanner) {
        processData(result);
    }
}
```

#### 2.6.3. Scan 规范

```
✅ 必须设置 StartRow 和 StopRow
✅ 必须设置列族过滤
✅ setCaching 设为 50-100（大扫描 500）
❌ 禁止全表扫描
❌ 禁止 Scan 不设 size 限制
```

---

### 2.7. 计数器操作

```java
try (Table table = hbaseConnection.getTable(TableName.valueOf("t_article_stats"))) {
    long newCount = table.incrementColumnValue(
        Bytes.toBytes(rowKey),
        Bytes.toBytes("stats"),
        Bytes.toBytes("view_count"),
        1L
    );
}
```

---

### 2.8. 开发 Checklist 与反模式

#### Checklist

- [ ] RowKey 设计含散列前缀，避免热点
- [ ] 列族 ≤ 3 个，列族名简短
- [ ] 写入使用批量 put，禁止循环单条写入
- [ ] Scan 查询设置 StartRow/StopRow
- [ ] 大批量扫描使用分页（setCaching + setBatch）
- [ ] 复用 Connection 对象，不复用 Table 对象

#### 常见反模式（禁止）

```
❌ 纯递增 ID 作为 RowKey
❌ 全表 Scan
❌ 循环单条 put
❌ 列族超过 3 个
❌ 单次 batchPut 超过 1000 条
❌ 用 UUID 作为 RowKey
❌ 不复用 Connection 对象
```

---

## 参考资料

- HBase 官方文档
- Apache Phoenix 官网
- HBase 权威指南
