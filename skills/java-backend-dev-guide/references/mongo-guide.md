# MongoDB 整合开发规约

> **摘要**
>
> - **核心约束**：\_id 用默认 ObjectId 禁无序内容；文档 ≤16MB 嵌套 ≤3 层；复合索引遵循 ESR 规则（Equality→Sort→Range）；查询字段必须有索引；禁 $where 和 $ne/$nin 高危操作符
> - **关键阈值**：单表索引 ≤10 个、单次返回 ≤2000 条、排序内存限制 32MB、bulkWrite ≤1000 条/16MB
> - **常见违规**：\_id 写随机字符串导致写入性能断崖、对每个字段建索引、排序字段无索引导致内存溢出、$or 拆分多次查询性能差

> **版本**：v1.0 | 最后更新：2026-06-08 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 通用开发规约

### 1.1. 库与集合规约

#### 1.1.1. 【强制】命名规约

数据库和集合名称必须全部小写，仅允许字母、数字和下划线 `_`，禁止以数字或 `system.` 开头。名称最多 32 个字符。

#### 1.1.2. 【强制】数据库与集合数量控制

单个数据库表个数 ≤100，整个实例表数量 ≤2000。WiredTiger 中每个集合创建多个文件，过多小文件导致性能下降。

#### 1.1.3. 【强制】合理评估分片与集群规划

新建库前必须评估数据体量和吞吐量。预计超过 3TB 或工作集超出内存容量的集合，应提前设计分片方案。

#### 1.1.4. 【推荐】利用 TTL 索引实现自动过期

日志、会话等有时效性的数据，必须在时间字段上创建 TTL 索引。字段类型必须是 Date。

#### 1.1.5. 【推荐】合理使用 Capped Collection

固定大小、先进先出场景（如最新日志轮询）使用 capped collection。不支持常规 `remove()` 和基于大小增量的 `update()`。

#### 1.1.6. 【推荐】不同业务使用不同库

避免库级锁带来的问题，不同业务使用不同的数据库。

---

### 1.2. 文档建模规约

#### 1.2.1. 【推荐】保持文档结构的一致性

同一集合内的文档保持相似结构，提升索引效率和查询可预测性。

#### 1.2.2. 【强制】谨慎处理 `_id` 主键

严禁向 `_id` 写入非自增、无规律的内容（如随机字符串）。`_id` 无序会导致 B-Tree 页分裂和索引重组，写入性能断崖式下跌。使用默认 `ObjectId`。

#### 1.2.3. 【强制】控制文档大小与嵌套深度

单个 BSON 文档 ≤16MB，嵌套层级 ≤3 层。过大文档占用内存碎片，更新易触发文档移动。

#### 1.2.4. 【推荐】嵌入 vs 引用

- **嵌入优先**：数据一起查询、具有「包含」关系、一起更新、同时归档
- **引用优先**：数据单独存在、频繁更新、写入负载高、文档无限增长

#### 1.2.5. 【推荐】文档字段设计规约

- 文档中包含 `sys_ctime`（创建时间）和 `sys_utime`（更新时间）
- key 禁止使用 `_` 以外的特殊字符，key 全部小写，多单词下划线分隔
- 禁止数字打头的 key

---

### 1.3. 索引设计规约

#### 1.3.1. 【强制】遵循最左前缀原则

组合索引符合查询的最左前缀匹配逻辑。索引 `{a: 1, b: 1}` 支持 `a` 或 `a, b` 的查询，无法高效支持单独 `b`。

#### 1.3.2. 【强制】查询与排序字段必须有索引

所有 `find` 过滤条件、`sort` 排序条件中的字段必须建索引。无索引排序在内存中进行，结果集超过 32MB 直接报错。

#### 1.3.3. 【强制】线上建索引必须使用 background 参数

MongoDB 4.2 之前版本 `createIndex()` 默认 foreground 模式会阻塞所有操作，必须添加 `background: true`。

#### 1.3.4. 【强制】限制单表索引数量

单表索引不超过 10 个。索引越多写入代价越大，禁止对每个字段建索引。

#### 1.3.5. 【推荐】复合索引字段顺序优化

遵循 ESR 规则（Equality → Sort → Range）：等值字段最左，排序字段次之，范围字段最后。`$ne`、`$nin` 无法有效利用索引。

#### 1.3.6. 【推荐】优先使用覆盖索引

将查询返回的字段也包含在索引中，MongoDB 直接从索引获取数据无需回表。

#### 1.3.7. 【推荐】在区分度较大的字段上建立索引

优先为高选择性（基数大）的字段建立索引。区分度小的索引扫描行数依然多。

#### 1.3.8. 【推荐】善用隐藏索引

MongoDB 4.4+ 使用 hidden index 先隐藏无用索引，验证业务正常后再删除，避免误删。

#### 1.3.9. 【推荐】索引选择策略

- **单键索引**：所有查询都是单键查询时使用
- **复合索引**：查询涉及多个键时（至多 32 个键）
- **文本索引**：大量文本字段中匹配特定单词

---

### 1.4. 查询与聚合优化

#### 1.4.1. 【强制】限制返回条数与排序范围

单次查询返回 ≤2000 条。排序字段必须建索引，排序操作 ≤32MB 内存。

#### 1.4.2. 【强制】禁止高危操作符

严禁在生产环境使用 `$where`；慎用 `$ne`、`$nin`、`$or`，这些操作符极易导致索引失效。

#### 1.4.3. 【推荐】善用聚合框架与 Explain

- 复杂统计优先使用 Aggregation Pipeline 而非 MapReduce
- 上线前必须使用 `explain("executionStats")` 分析执行计划，确保 `stage` 为 `IXSCAN`
- 聚合管道中 `$match` 阶段前置，尽早过滤数据
- `$lookup` 关联查询在外层集合创建索引

#### 1.4.4. 【推荐】投影查询

查询时使用 Projection 指定需要的字段，减少网络传输和内存占用，提高覆盖索引命中率。

---

### 1.5. 写入与原子性

#### 1.5.1. 【推荐】批量写入

高频写入使用 `bulkWrite` 或 `insertMany`，单次批量 ≤1000 条或 16MB。

#### 1.5.2. 【强制】理解原子性边界

MongoDB 原子性仅限于单文档级别。业务应通过嵌入式文档和数组结构将关联数据构造为单个文档。

#### 1.5.3. 【推荐】条件更新使用 `findAndModify`

需要原子性「查找并更新」操作时使用 `findAndModify`，同一文档上的操作是原子的。

#### 1.5.4. 【推荐】高效清理数据

清空集合数据使用 `drop()` 代替 `remove({})`。`drop()` 直接删除文件瞬间完成。

#### 1.5.5. 【推荐】多文档事务的使用限制

MongoDB 4.0+ 支持多文档事务，但需谨慎使用，避免在高性能写入场景中频繁使用。优先通过单文档原子操作满足需求。

---

### 1.6. 集群与高可用

#### 1.6.1. 【强制】副本集连接模式

必须通过副本集（Replica Set）方式连接，禁止直连单点。

#### 1.6.2. 【推荐】读写分离与读偏好配置

根据业务需求配置 `ReadPreference`，将查询压力分摊到从节点。使用从节点需注意数据延迟。

#### 1.6.3. 【推荐】监控关键指标

- 慢查询阈值默认 100ms，通过 `db.setProfilingLevel` 调整
- 缓存命中率通过 `db.serverStatus().wiredTiger.cache` 监控，<90% 需扩容
- 分片集群定期运行 `db.stats()` 和 `sh.status()` 监控健康状态

#### 1.6.4. 【推荐】分片键选择

分片键应具有高基数（大量唯一值），避免使用小基数片键。官方推荐使用 `analyzeShardKey` 辅助选择。

#### 1.6.5. 【推荐】监控与优化工具

- `mongotop`：按集合分析读写负载
- `mongostat`：定期报告服务器统计信息
- `db.currentOp()`：定位长时间运行的查询
- `db.collection.stats()`：集合详细统计（索引大小、文档数量等）

---

### 1.7. 性能优化

#### 1.7.1. 【推荐】WiredTiger 缓存配置

通过 `storage.wiredTiger.engineConfig.cacheSizeGB` 设置缓存大小，建议可用内存的 50%-60%。缓存命中率 <90% 需扩容。

#### 1.7.2. 【推荐】工作集分析

确保活跃数据（工作集）能容纳在内存中，获得最佳查询性能。工作集超出内存时磁盘访问增加，延迟上升。

#### 1.7.3. 【推荐】聚合框架优化

- `$match` 前置尽早过滤数据
- `$lookup` 外层关联集合创建索引
- 大数据量聚合设置 `allowDiskUse: true`

---

### 1.8. 反模式

| 反模式                                          | 问题描述                          | 正确实践                       |
| :---------------------------------------------- | :-------------------------------- | :----------------------------- |
| `_id` 使用自增序列或随机字符串                  | B-Tree 索引重组频繁，写入性能下降 | 使用默认 `ObjectId`            |
| 为每个字段创建索引                              | 写入性能严重下降，存储浪费        | 单表索引不超过 10 个           |
| 不设 TTL 或不分表                               | 数据无限增长，性能逐年下降        | 必须设定 TTL，必要时分表或分片 |
| 生产环境使用无索引的全表扫描                    | 集群负载飙升甚至宕机              | 所有查询必须有对应索引         |
| MongoDB 4.2 及之前版本线上建索引不加 background | 阻塞数据库所有操作                | 必须添加 `background: true`    |
| 使用数组字段作为主要查询条件                    | 数组索引体积大，查询效率低        | 避免将数组字段作为主要查询条件 |
| 使用 `$where` 进行复杂查询                      | 性能极差，无法利用索引            | 使用聚合框架或应用层处理       |
| 频繁创建和关闭数据库连接                        | 连接开销大，资源浪费              | 使用连接池管理连接             |

---

## 2. 工程化规约（Spring Data MongoDB）

> **[FOR HUMAN REFERENCE]** 以下内容为工程化配置说明，AI 编码时通常无需加载。
>
> 本节基于 **Spring Data MongoDB** 标准用法编写。项目级 Skill 可覆盖为项目自定义封装。

### 2.1. 快速上手

#### 2.1.1. 添加依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-mongodb</artifactId>
</dependency>
```

#### 2.1.2. 配置

```yaml
spring:
  data:
    mongodb:
      uri: ${MONGODB_URI}
      database: ${MONGODB_DATABASE}
```

```java
// 方式一：MongoTemplate（复杂查询首选）
@Autowired
private MongoTemplate mongoTemplate;

// 方式二：Repository（简单 CRUD 首选）
@Autowired
private ArticleMongoRepository articleRepository;
```

---

### 2.2. 数据库与集合规范

| 配置项   | 值                      | 说明                                   |
| -------- | ----------------------- | -------------------------------------- |
| 数据库名 | 由项目配置管理          | 通过配置中心管理                       |
| 集合命名 | 小写字母 + `_`          | 如 `article_content`、`author_profile` |
| 主键     | `@Id` 标注，String 类型 | 对应 MongoDB `_id`                     |

---

### 2.3. 实体定义规范

```java
@Data
@Document(collection = "article_content")
public class ArticleContentDO {

    @Id
    private String id;

    @Field("article_id")
    private Long articleId;

    @Field("title")
    private String title;

    @Field("content")
    private String content;

    @Field("author_id")
    private Long authorId;

    @Field("version")
    private Integer version;

    @Field("create_time")
    private LocalDateTime createTime;

    @Field("update_time")
    private LocalDateTime updateTime;
}
```

**规范约束**：

- 必须使用 `@Document` 注解标注集合名
- 字段名使用 `@Field` 显式指定存储名（下划线命名）
- 单文档大小不超过 16MB

---

### 2.4. Repository 模式（简单 CRUD）

```java
public interface ArticleMongoRepository
        extends MongoRepository<ArticleContentDO, String> {

    List<ArticleContentDO> findByAuthorId(Long authorId);
    Optional<ArticleContentDO> findByArticleId(Long articleId);
    List<ArticleContentDO> findByAuthorIdAndVersionOrderByCreateTimeDesc(
            Long authorId, Integer version);
    long countByAuthorId(Long authorId);
    void deleteByArticleId(Long articleId);
}
```

---

### 2.5. MongoTemplate 模式（复杂查询）

#### 2.5.1. 条件查询

```java
public Page<ArticleContentDO> pageArticles(ArticlePageQRY qry) {
    Query query = new Query();
    Criteria criteria = new Criteria();
    if (qry.getAuthorId() != null) {
        criteria.and("author_id").is(qry.getAuthorId());
    }
    if (StringUtils.isNotBlank(qry.getTitle())) {
        criteria.and("title").regex(qry.getTitle());
    }
    if (qry.getVersion() != null) {
        criteria.and("version").is(qry.getVersion());
    }
    query.addCriteria(criteria);
    query.with(Sort.by(Sort.Direction.DESC, "create_time"));

    long total = mongoTemplate.count(query, ArticleContentDO.class);
    query.skip((long) (qry.getPageNum() - 1) * qry.getPageSize())
         .limit(qry.getPageSize());
    List<ArticleContentDO> list = mongoTemplate.find(query, ArticleContentDO.class);
    return new PageImpl<>(list, PageRequest.of(qry.getPageNum() - 1,
            qry.getPageSize()), total);
}
```

#### 2.5.2. 局部更新

```java
public void updateContent(Long articleId, String newContent) {
    Query query = new Query(Criteria.where("article_id").is(articleId));
    Update update = new Update()
            .set("content", newContent)
            .set("version", newVersion)
            .set("update_time", LocalDateTime.now());
    mongoTemplate.updateFirst(query, update, ArticleContentDO.class);
}
```

#### 2.5.3. 聚合查询

```java
public List<AuthorArticleCountDTO> countByAuthor() {
    Aggregation aggregation = Aggregation.newAggregation(
            Aggregation.match(Criteria.where("version").is(1)),
            Aggregation.group("author_id").count().as("articleCount"),
            Aggregation.sort(Sort.Direction.DESC, "articleCount"),
            Aggregation.limit(100)
    );
    AggregationResults<AuthorArticleCountDTO> results = mongoTemplate.aggregate(
            aggregation, "article_content", AuthorArticleCountDTO.class);
    return results.getMappedResults();
}
```

#### 2.5.4. 方式选择指南

| 场景           | 推荐方式      | 原因               |
| -------------- | ------------- | ------------------ |
| 标准 CRUD      | Repository    | 代码简洁，自动实现 |
| 按方法名查询   | Repository    | 零 SQL，可读性高   |
| 动态多条件查询 | MongoTemplate | 灵活构建 Criteria  |
| 聚合统计       | MongoTemplate | 支持完整聚合管道   |
| 批量局部更新   | MongoTemplate | 精确控制更新字段   |

---

### 2.6. 索引设计规范

```java
@Document(collection = "article_content")
@CompoundIndex(name = "idx_author_version", def = "{'author_id': 1, 'version': 1}")
public class ArticleContentDO {

    @Indexed(unique = false)
    @Field("article_id")
    private Long articleId;
    // ...
}
```

- 单字段查询 → `@Indexed`
- 多字段联合查询 → `@CompoundIndex`（字段顺序与查询条件一致）
- 唯一约束 → `@Indexed(unique = true)`
- 避免过多索引

---

### 2.7. 安全规范

```
✅ 禁止将用户输入直接作为 Criteria 查询值（防 NoSQL 注入）
✅ 必须对用户输入进行类型校验和格式校验
✅ 禁止在 Criteria 中使用 $where
✅ 生产环境连接信息通过配置中心管理
❌ 禁止正则查询不设 limit
```

---

### 2.8. 开发 Checklist 与反模式

#### Checklist

- [ ] 创建 `XxxDO.java`，加 `@Document(collection = "xxx_yyy")`
- [ ] 字段使用 `@Field` 显式指定存储名
- [ ] 高频查询字段添加 `@Indexed` 或 `@CompoundIndex`
- [ ] 简单 CRUD 创建 Repository，复杂查询使用 MongoTemplate
- [ ] 单文档大小评估（不超过 16MB）
- [ ] 配置中心确认 MongoDB 连接配置

#### 常见反模式（禁止）

```
❌ 不加 @Field 注解
❌ 用 save() 全文档更新（应使用 Update.set() 局部更新）
❌ 正则查询不加 limit（全集合扫描）
❌ 单文档超过 16MB
❌ 不建索引直接上线
❌ 使用 $where 执行 JS 代码（注入风险）
❌ 硬编码连接参数
```

---

## 参考资料

- MongoDB 官方文档
- 《MongoDB 权威指南（第3版）》
