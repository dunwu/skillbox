# Elasticsearch 整合开发规约

> **摘要**
>
> - **核心约束**：必须显式定义 Mapping 禁动态映射；text 用于全文检索禁排序聚合、keyword 用于精确匹配排序聚合；非全文过滤条件必须用 filter context
> - **关键阈值**：单分片 10-30GB（日志 30-50GB）、字段数 ≤100、禁 from+size 深分页（用 search_after）、单次返回 ≤2000 条
> - **常见违规**：动态映射导致存储冗余、text 字段上排序/聚合、深度分页用 from+size、\*开头的 wildcard 查询、直接硬编码索引名

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 通用开发规约

### 1.1. 索引与分片规约

#### 1.1.1. 【强制】合理设置分片容量与数量

非日志型索引单分片 10GB~30GB；日志型 30GB~50GB。单个 shard 文档数不超过 21 亿。单个分片 ≤50GB，单节点 shard ≤600 个。副本数默认 1，核心搜索索引可配置 2 个副本。

#### 1.1.2. 【强制】禁止使用通配符查询所有索引

严禁生产环境使用 `indexName-*` 或 `_all` 进行全量索引查询。应通过 Alias 或明确指定索引名。

#### 1.1.3. 【推荐】使用索引别名管理生命周期

业务层必须通过 Alias 访问索引，禁止硬编码索引名。Alias 下挂载索引 ≤20 个，避免读放大。

#### 1.1.4. 【推荐】大索引拆分策略

- 日志类按时间分索引：`index_2024_01`、`index_2024_02`
- 业务大索引按日期滚动：`article_content_{$date}`
- 使用 Alias 统一对外暴露访问入口

#### 1.1.5. 【推荐】冷热数据分层

使用 ILM 将热数据分配到 SSD 节点、冷数据迁移至 HDD 节点。3 个月内的热数据存 SSD。

#### 1.1.6. 【强制】预先定义 Mapping，禁用动态映射

必须显式定义 Index Mapping，关闭 `dynamic: strict` 或设为 `false`。默认动态映射可能将文本设为 text+keyword 双类型，造成存储冗余且一旦定义无法修改。

#### 1.1.7. 【推荐】使用索引模板规约新索引

为同类索引创建 Index Template，统一 settings 和 mappings，确保新增索引自动继承相同配置。

---

### 1.2. 字段与建模规约

#### 1.2.1. 【强制】区分 Text 与 Keyword 类型

| 类型      | 特性               | 适用场景             |
| --------- | ------------------ | -------------------- |
| `text`    | 分词，用于全文检索 | 文章内容、产品描述   |
| `keyword` | 不分词，精确匹配   | 状态码、分类 tag、ID |

需要全文检索的字段用 text；需要排序、聚合、精确匹配的字段用 keyword。text 默认关闭 fielddata，不支持聚合/排序。禁止在 text 字段上做模糊搜索或正则匹配。

#### 1.2.2. 【推荐】按需开启 Doc Values 和禁用 norms

不需要聚合、排序的字段设 `"doc_values": false`；text 字段不需要计算文档权重时设 `"norms": false`。

#### 1.2.3. 【强制】避免宽表与过度嵌套

单个索引字段数 ≤100（严禁超过 1000）。`nested` 或 `parent-child` 查询性能开销极大，应谨慎使用。

#### 1.2.4. 【推荐】字段命名规约与大小写统一

字段名统一采用 snake_case（如 `user_name`、`order_id`）。

#### 1.2.5. 【推荐】使用 runtime fields 应对未知字段

无法预定义 Mapping 且无需高性能查询的字段，使用 runtime fields 替代动态映射。runtime fields 查询时实时计算，不增加索引存储。

---

### 1.3. 搜索优化

#### 1.3.1. 【强制】禁止深度分页

禁止 `from + size > 10000`（ES 默认 `max_result_window = 10000`）。单次查询返回 ≤2000 条。

- 浅分页使用 `from+size`
- 深分页/实时滚动使用 `search_after`（需搭配唯一排序字段）
- 全量导出 >10000 hits 使用 PIT + search_after 或 scroll API

#### 1.3.2. 【强制】禁止低效通配查询

严禁 `*` 开头的 wildcard 或 regexp 查询。这类查询无法利用倒排索引，需遍历所有词条。前缀或中间匹配建议使用 ngram 分词器替代。

#### 1.3.3. 【强制】使用 filter 替代 query 进行过滤

非全文检索、仅需判断是否匹配的条件必须使用 filter context。filter 不计算 `_score`，可缓存且性能远高于 query。

```java
builder.query(QueryBuilders.boolQuery()
        .must(QueryBuilders.matchQuery("title", keyword))      // 全文检索用 must
        .filter(QueryBuilders.termQuery("status", 1))          // 精确过滤用 filter
        .filter(QueryBuilders.termQuery("authorId", authorId)));
```

#### 1.3.4. 【推荐】优化聚合与排序

- 聚合字段类型应为 keyword 或数值，避免 text 类型聚合
- 排序字段必须启用 doc_values，禁止 text 字段排序
- 聚合避免过多嵌套（每层嵌套是指数级性能消耗）
- 高基数字段聚合使用 terms + size 限制桶数

#### 1.3.5. 【推荐】控制返回字段

`_source` 中只返回业务必需字段，避免全量返回。

```java
builder.fetchSource(new String[]{"title", "summary", "authorName", "publishTime"}, null);
```

---

### 1.4. 写入优化

#### 1.4.1. 【推荐】合理使用 Bulk 批量写入

生产环境必须使用 Bulk API，单次 Bulk 5MB~15MB 或 500~5000 条文档。小批量 ≤1000 条用同步批量，大批量 >1000 条用异步 BulkProcessor。

**BulkProcessor 触发条件**（任一满足即触发）：累积 1000 条 / 累积 5MB / 距上次刷新超过 1000ms。

#### 1.4.2. 【强制】谨慎使用 Refresh 策略

默认 `refresh_interval` 1s。高吞吐写入场景可调大至 30~120s，完成后恢复默认。写入时禁止 `wait_for_refresh=true`。不要在写入中主动触发 refresh。

#### 1.4.3. 【推荐】导入阶段副本降级

索引初始化或全量导入时将副本数暂设为 0，完成后调回 1。

#### 1.4.4. 【强制】避免使用 Update/Delete By Query

严禁高频使用 `update_by_query` / `delete_by_query`。本质是「查询+重写」，不支持事务，易引发版本冲突。大数据量删除使用 TTL（ILM）或按索引删除。

---

### 1.5. 集群与高可用

#### 1.5.1. 【强制】副本集连接模式

必须通过副本集方式连接，禁止直连单点。推荐域名连接。

#### 1.5.2. 【强制】主节点数量与避免脑裂

集群至少配置 3 个候选主节点，`discovery.zen.minimum_master_nodes` 设为 `N/2+1`（ES <7.0 适用；ES 7.0+ 由集群自动管理）。

#### 1.5.3. 【推荐】使用滚动重启

集群维护升级时必须使用 Rolling Restart 逐个节点重启，等待集群恢复 green 后再继续。

#### 1.5.4. 【推荐】监控关键指标

- **节点**：JVM Heap 使用率、GC、磁盘使用率、Segment Memory
- **索引**：Docs Count、Deleted Docs、Store Size、Query/Index 延迟
- **集群**：Health Status、Pending Tasks、Unassigned Shards
- **性能**：Search/Index 线程池积压、Bulk Rejection、查询熔断次数
- **慢查询**：在 index template 中配置 `index.search.slowlog.threshold.query.warn: 10s` 等

#### 1.5.5. 【推荐】使用熔断器防止 OOM

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

fielddata 默认无限内存，text 聚合若未禁用必须配合熔断器。

#### 1.5.6. 【推荐】使用快照备份

核心业务数据必须定期创建快照备份至 HDFS/S3，建议每日至少一次。

#### 1.5.7. 【推荐】读写分离与查询路由

读负载较高时通过增加副本数实现读扩展。增加副本会增加存储和索引写入开销。

---

### 1.6. 性能优化

#### 1.6.1. 【推荐】JVM 与操作系统配置

JVM 堆内存配置为物理内存的一半且不超过 32GB（建议 28GB）。关闭交换分区（swap off）。

#### 1.6.2. 【推荐】合理配置分片

分片容量 10-50 GB，分片数为节点数倍数。设计分片前预估未来 3~6 个月数据量。

#### 1.6.3. 【推荐】使用 Sliced Scroll 加速大数据导出

Scroll API 导出大量数据时开启 sliced scroll 并行拉取。

#### 1.6.4. 【推荐】节点角色分离

生产环境配置专用主节点、专用协调节点、数据节点（Hot/Warm/Cold 分层）。

---

### 1.7. 反模式

| 反模式                                     | 问题                     | 正确实践                        |
| :----------------------------------------- | :----------------------- | :------------------------------ |
| 动态 mapping                               | 字段类型不可控           | 必须显式定义 Mapping            |
| from + size 超过 10000                     | 内存消耗爆炸             | 使用 SearchAfter 或 Scroll      |
| 未释放 Scroll 游标                         | ES 内存泄漏              | 查询后必须调用 clearScroll      |
| indexName-\* 通配符查询                    | 扫描所有匹配索引         | 使用 Alias 或明确指定索引名     |
| script / update_by_query / delete_by_query | 版本冲突风险高           | 使用 Bulk API 或按 ID 更新      |
| 正则匹配查询                               | O(N) 全索引扫描          | 使用 ngram 分词器替代           |
| 宽表（字段超过 100 个）                    | 列式存储效率下降         | 拆分索引或应用层组装            |
| text 字段做聚合                            | 需开 fielddata，内存极大 | 改用 keyword 或多字段映射       |
| 循环单条写入                               | 网络 RTT 开销大          | 使用 Bulk API 或 BulkProcessor  |
| wait_for_refresh=true                      | 写入性能急剧下降         | 依赖默认 1s refresh 间隔        |
| 不指定 fetchSource                         | 返回全部字段浪费带宽     | 只返回业务必需字段              |
| 忽略 BulkProcessor afterBulk 失败回调      | 批量写入失败无法感知     | 必须处理失败回调并记录日志      |

---

## 2. 工程化规约（RestHighLevelClient / ElasticsearchRestTemplate）

> **[FOR HUMAN REFERENCE]** 以下内容为工程化配置说明，AI 编码时通常无需加载。
>
> 本节基于 **Spring Data Elasticsearch + RestHighLevelClient** 标准用法编写。项目级 Skill 可覆盖为项目自定义封装。

### 2.1. 快速上手

#### 2.1.1. 添加依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-elasticsearch</artifactId>
</dependency>
```

#### 2.1.2. 配置

```yaml
spring:
  elasticsearch:
    rest:
      uris: ${ES_CLUSTER_URIS}
      connection-timeout: 5s
      read-timeout: 30s
```

```java
@Autowired
private ElasticsearchRestTemplate esTemplate;
```

---

### 2.2. 索引设计规范

#### 2.2.1. 索引命名

```
{业务域}_{数据类型}_{版本号}
```

示例：`article_content_v1`、`author_profile_v1`

- 全小写，使用 `_` 分隔
- **必须带版本号**（支持零停机重建）
- 通过 Alias 对外提供统一访问入口
- **禁止**查询时使用 `indexName-*` 通配符

#### 2.2.2. 创建索引

```java
IndexOperations indexOps = esTemplate.indexOps(ArticleEsDO.class);
indexOps.createWithMapping();
```

#### 2.2.3. 零停机重建索引

```java
// 1. 创建新版本索引
indexOps.createWithMapping();  // ArticleEsDO 使用 @Setting(shards=3, replicas=1)
// 2. 数据迁移后切换别名
// 3. 删除旧版本索引
```

---

### 2.3. 实体定义规范

ES 实体使用 Spring Data Elasticsearch 注解，命名后缀 `EsDO`：

```java
@Data
@Document(indexName = "article_content_v1")
@Setting(shards = 3, replicas = 1)
public class ArticleEsDO {

    @Id
    private String docId;  // ES _id，必须赋值

    @Field(type = FieldType.Text, analyzer = "ik_max_word")
    private String title;

    @Field(type = FieldType.Text, analyzer = "ik_max_word")
    private String summary;

    @Field(type = FieldType.Keyword)
    private Long authorId;

    @Field(type = FieldType.Keyword)
    private String authorName;

    @Field(type = FieldType.Keyword)
    private String category;

    @Field(type = FieldType.Keyword)
    private Integer status;

    @Field(type = FieldType.Long)
    private Long publishTime;
}
```

---

### 2.4. 写操作规范

#### 2.4.1. 单条保存/更新

```java
ArticleEsDO entity = new ArticleEsDO();
entity.setDocId(String.valueOf(article.getId())); // 必须设置 docId
entity.setTitle(article.getTitle());
entity.setPublishTime(System.currentTimeMillis());
esTemplate.save(entity);
```

#### 2.4.2. 批量写入

```java
// 小批量 ≤1000 条：同步批量
esTemplate.save(entities);

// 大批量 >1000 条：异步 BulkProcessor（需自定义配置）
BulkProcessor bulkProcessor = BulkProcessor.builder(
    (request, bulkListener) -> esTemplate.getClient().bulkAsync(request, RequestOptions.DEFAULT, bulkListener),
    new BulkProcessor.Listener() {
        @Override
        public void beforeBulk(long executionId, BulkRequest request) { }

        @Override
        public void afterBulk(long executionId, BulkRequest request, BulkResponse response) {
            if (response.hasFailures()) {
                log.error("ES 批量写入部分失败: {}", response.buildFailureMessage());
            }
        }

        @Override
        public void afterBulk(long executionId, BulkRequest request, Throwable failure) {
            log.error("ES 批量写入异常", failure);
        }
    })
    .setBulkActions(1000)
    .setBulkSize(new ByteSizeValue(5, ByteSizeUnit.MB))
    .setFlushInterval(TimeValue.timeValueSeconds(1))
    .build();
```

**BulkProcessor 触发条件**：累积 1000 条 / 累积 5MB / 距上次刷新超过 1000ms。

#### 2.4.3. Refresh 规范

```
【强制】写入时禁止 wait_for_refresh=true
【强制】不要在写入中主动触发 refresh
【说明】ES 默认 refresh 间隔 1s，1s 延迟通常可接受
```

#### 2.4.4. 禁止的写操作

```
❌ update_by_query  → 版本冲突，不支持事务
❌ delete_by_query  → 大量数据删除风险极高
❌ 循环单条写入     → 必须使用 saveBatch 或 BulkProcessor
```

---

### 2.5. 查询规范

#### 2.5.1. 浅分页（<10000 条）

```java
NativeSearchQueryBuilder queryBuilder = new NativeSearchQueryBuilder();
queryBuilder.withQuery(QueryBuilders.boolQuery()
        .must(QueryBuilders.matchQuery("title", keyword))
        .filter(QueryBuilders.termQuery("status", 1))
        .filter(QueryBuilders.termQuery("authorId", authorId)));
queryBuilder.withSort(SortBuilders.fieldSort("publishTime").order(SortOrder.DESC));
queryBuilder.withPageable(PageRequest.of(0, 10));
queryBuilder.withSourceFilter(new FetchSourceFilter(
    new String[]{"title", "summary", "authorName", "publishTime"}, null));

SearchHits<ArticleEsDO> hits = esTemplate.search(queryBuilder.build(), ArticleEsDO.class);
```

#### 2.5.2. 深分页（≥10000 条）

| 方案        | 适用场景          | 特点                              |
| ----------- | ----------------- | --------------------------------- |
| SearchAfter | 用户翻页          | 无状态，性能恒定，不支持跳页      |
| Scroll      | 全量导出/批量处理 | 有状态（游标），不适合实时查询    |
| from+size   | 禁止超过 10000    | 超出报 Result window is too large |

**SearchAfter 示例**：

```java
NativeSearchQueryBuilder queryBuilder = new NativeSearchQueryBuilder();
queryBuilder.withQuery(QueryBuilders.matchAllQuery());
queryBuilder.withSort(SortBuilders.fieldSort("publishTime").order(SortOrder.DESC));
queryBuilder.withSort(SortBuilders.fieldSort("docId").order(SortOrder.ASC));
queryBuilder.withPageable(PageRequest.of(0, 100));

SearchHits<ArticleEsDO> page1 = esTemplate.search(queryBuilder.build(), ArticleEsDO.class);
// 后续页：将最后一行的排序值设为 search_after
```

**Scroll 示例（全量导出）**：

```java
SearchScrollHits<ArticleEsDO> scrollHits = esTemplate.searchScrollStart(
    60000L, queryBuilder.build(), ArticleEsDO.class);
String scrollId = scrollHits.getScrollId();
List<ArticleEsDO> allData = new ArrayList<>(scrollHits.getContent());

while (scrollHits.hasSearchHits()) {
    scrollHits = esTemplate.searchScrollContinue(scrollId, 60000L, ArticleEsDO.class);
    if (!scrollHits.hasSearchHits()) break;
    allData.addAll(scrollHits.getContent());
    scrollId = scrollHits.getScrollId();
}
// ✅ 必须释放 Scroll 资源
esTemplate.searchScrollClear(Collections.singletonList(scrollId));
```

#### 2.5.3. 聚合查询规范

```
【推荐】聚合避免过多嵌套
【禁止】在 text 字段上做聚合
【推荐】高基数字段聚合使用 terms + size 限制桶数
```

#### 2.5.4. 禁止的查询操作

```
❌ indexName-* 通配符查询
❌ script 查询
❌ 正则匹配查询
❌ from+size 超过 10000
❌ 不指定 fetchSource
```

---

### 2.6. 慢日志配置

```json
PUT _template/app_template
{
  "index_patterns": ["article_*", "author_*"],
  "settings": {
    "index.search.slowlog.threshold.query.warn": "10s",
    "index.search.slowlog.threshold.query.info": "5s",
    "index.search.slowlog.threshold.fetch.warn": "1s",
    "index.indexing.slowlog.threshold.index.warn": "10s"
  }
}
```

---

### 2.7. 连接规范

```
✅ 使用域名地址 + 端口连接（非 IP）
✅ 使用 HTTP 协议连接
✅ 生产环境地址通过配置中心获取
❌ 禁止硬编码 ES 地址
```

---

### 2.8. 安全规范

```
✅ 用户输入必须经过参数校验
✅ 使用 QueryBuilders 构建查询，禁止原生 JSON 字符串拼接
❌ 禁止 script 查询执行用户输入
❌ 禁止正则匹配查询用户输入
```

---

### 2.9. 开发 Checklist 与反模式

#### Checklist

- [ ] 创建 `XxxEsDO.java`，使用 `@Document` + `@Field` 明确定义字段类型
- [ ] text/keyword 选型已评估
- [ ] 不需要聚合/排序的字段已禁用 doc_value
- [ ] 字段数 ≤ 100
- [ ] 索引名含版本号，通过别名对外暴露
- [ ] 分片数根据数据量评估（单分片约 10GB）
- [ ] 副本数设为 1
- [ ] 分页 > 10000 条使用 SearchAfter 或 Scroll
- [ ] Scroll 查询后调用 clearScroll 释放资源
- [ ] 批量写入 > 1000 条使用异步 BulkProcessor
- [ ] 未使用 wait_for_refresh=true

#### 常见反模式（禁止）

```
❌ 动态 mapping
❌ from + size 超过 10000
❌ 未释放 Scroll 游标
❌ indexName-* 通配符查询
❌ script / update_by_query / delete_by_query
❌ 正则匹配查询
❌ 宽表（字段超过 100 个）
❌ text 字段做聚合
❌ 循环单条写入
❌ wait_for_refresh=true
❌ 不指定 fetchSource
❌ 忽略 BulkProcessor afterBulk 失败回调
❌ 硬编码 ES 地址
```

---

## 参考资料

- Elasticsearch 官方文档
- Elasticsearch 实战
- Elasticsearch 权威指南

