# MySQL 整合开发规约

> **摘要**
>
> - **核心约束**：联合索引等值字段在前范围在后；禁 LIMIT 深分页（用游标或延迟关联）；大表 DDL 用 gh-ost 禁直接 ALTER；刚写入后读必须强制路由主库
> - **关键阈值**：分区表阈值 500 万行、前缀索引区分度 ≥90%、冷数据 >6 月归档、慢查询 >1s 告警
> - **常见违规**：百万级数据用 LIMIT offset 深分页、字符集不一致导致隐式转换索引失效、事务内含 RPC/HTTP 调用

> **版本**：v1.0 | 最后更新：2026-06-08 | 适用 SKILL 版本：≥ v1.0.0

> 本规约旨在补充《阿里巴巴 Java 编码规范（黄山版）》中「MySQL 数据库」章节未覆盖或需针对企业级场景细化的准则。若存在冲突，以黄山版为准。

---

## 1. 通用开发规约

### 1.1. 建表规约

#### 1.1.1. 【推荐】反范式化与冗余同步机制

高频读取且更新不频繁的场景，允许适度冗余核心字段（如订单表中冗余商品名称）以减少 `JOIN`，但必须建立可靠的数据同步机制（Canal 监听 Binlog 或 MQ 异步通知）保证最终一致性。

允许冗余需满足：

1. 不是频繁修改的字段
2. 不是唯一索引的字段
3. 不是 `varchar` 超长字段，更不能是 `text` 字段

#### 1.1.2. 【强制】JSON 字段的性能边界

仅在数据结构极度灵活且无需对内部字段进行复杂索引时使用 `JSON` 类型。核心检索字段必须拆分为独立列。

#### 1.1.3. 【推荐】分区表使用规范

单表数据量超过 500 万行时，可按时间（RANGE）、哈希（HASH）、列表（LIST）等进行分区。优先推荐 RANGE 分区按月或按年切分。

通过分区修剪（Partition Pruning），优化器可自动排除无关分区。删除过期数据时 `DROP PARTITION` 比 `DELETE` 快数量级，可即刻回收磁盘空间。

---

### 1.2. 索引规约

#### 1.2.1. 【强制】联合索引的「等值 - 范围」排序原则

创建联合索引时，必须将等值查询（`=` / `IN`）的字段放在前面，范围查询（`>` / `<` / `BETWEEN`）的字段放在后面。

例：`WHERE a = 1 AND b > 10 ORDER BY c`，索引应建为 `(a, b, c)`。若范围字段在前，后续字段无法利用索引排序或检索。

#### 1.2.2. 【推荐】前缀索引的区分度量化

长字符串（如 URL、摘要）使用前缀索引时必须确保区分度 ≥ 90%。可通过 `SELECT COUNT(DISTINCT LEFT(col, N)) / COUNT(*)` 评估。

#### 1.2.3. 【推荐】索引下推特性利用

MySQL 5.6+ 的索引条件下推可将过滤条件下推到存储引擎层执行，减少全行读取次数。通过 `EXPLAIN` 中 `Extra` 列出现 `Using index condition` 确认 ICP 生效。

#### 1.2.4. 【推荐】索引长度控制

`VARCHAR` 字段建立索引时，指定合适的索引长度，不必对整个字段建索引。索引长度越长，存储和内存开销越大。

---

### 1.3. SQL 语句规约

#### 1.3.1. 【强制】深分页的性能优化

禁止直接使用 `LIMIT offset, size` 进行百万级以上数据的深分页。应根据场景选择：

- **游标分页（Keyset Pagination）**：适用于连续翻页或无限滚动。`WHERE id > last_id LIMIT size`，时间复杂度 O(log n + m)。
- **延迟关联（Deferred Join）**：适用于随机跳转。子查询先定位主键 ID，再 `JOIN` 原表获取详情。

```sql
-- ❌ 慢：offset 10万时需扫描 100010 行
SELECT * FROM t_article WHERE status=2 LIMIT 100000, 20;

-- ✅ 快：先用覆盖索引定位 id，再关联取数据
SELECT a.* FROM t_article a
                  INNER JOIN (SELECT id FROM t_article WHERE status=2 LIMIT 100000, 20) b
ON a.id = b.id;
```

#### 1.3.2. 【强制】隐式转换的深层排查

除参数类型一致外，还需注意字符集（Charset）和排序规则（Collation）的一致性。表字段为 `utf8mb4` 而连接串指定 `utf8` 时可能导致索引失效。JDBC URL 中的 `characterEncoding` 必须与数据库定义一致。

---

### 1.4. 事务与锁规约

#### 1.4.1. 【强制】死锁预防与重试机制

并发环境下访问同一组资源时，必须保持加锁顺序一致。业务层应具备死锁（Error Code 1213）自动重试机制，采用指数退避策略。

#### 1.4.2. 【推荐】间隙锁风险规避

RR（可重复读）隔离级别下，尽量避免对非唯一索引进行范围更新或删除，防止产生大量间隙锁阻塞并发插入。

#### 1.4.3. 【推荐】避免大事务

- 将日志记录、消息发送、缓存更新等非核心操作移出事务块
- 事务内不要做 RPC / HTTP 调用等耗时操作
- 注意缓存回滚、搜索引擎回滚等补偿方案

---

### 1.5. 集群与高可用规约

#### 1.5.1. 【强制】在线 DDL 变更流程

生产环境超过 100 万行的表结构变更，严禁直接 `ALTER TABLE`，必须使用 `gh-ost` 或 `pt-online-schema-change` 等无锁工具。

#### 1.5.2. 【强制】主从延迟的读写分离策略

刚写入后立即读取的场景（如支付成功后查订单），必须强制路由到主库。高并发写入下从库延迟可能达到秒级。

---

### 1.6. 分区表管理规约

#### 1.6.1. 【推荐】分区策略选型

优先使用 RANGE 分区（按时间范围），避免使用 HASH 分区进行数据清理。`DROP PARTITION` 可高速完成过期数据删除。

---

### 1.7. 数据归档治理规约

#### 1.7.1. 【推荐】冷热数据分离

超过 6 个月的历史数据应从主业务表中归档到归档表或数仓 ODS 层，保持主业务表 ≤500 万行。推荐使用分区表 + `EXCHANGE PARTITION` 快速切分。

---

### 1.8. 运维监控规约

#### 1.8.1. 【推荐】慢日志自动化分析与告警

必须接入慢日志分析平台，对 `Query_time > 1s` 且 `Rows_examined > 10000` 的 SQL 自动告警。开启 `slow_query_log=ON`、`long_query_time≥1.0`；用 `pt-query-digest` 分析。

#### 1.8.2. 【推荐】备份与恢复演练

核心业务表必须开启 Binlog 并定期进行全量备份。每半年至少一次数据恢复演练。

---

### 1.9. SQL 审计与成本规约

#### 1.9.1. 【推荐】开发阶段 SQL 审核

上线前所有 SQL 必须经过审核平台扫描，禁止 `SELECT *`、无索引的条件查询上线。

---

## 2. 工程化规约（MyBatis-Plus）

> **[FOR HUMAN REFERENCE]** 以下内容为工程化配置说明，AI 编码时通常无需加载。
>
> 本节基于 **MyBatis-Plus** 标准用法编写。项目级 Skill 可覆盖为项目自定义封装。

### 2.1. 快速上手

#### 2.1.1. 添加依赖

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-boot-starter</artifactId>
</dependency>
```

#### 2.1.2. 配置

```yaml
mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
  global-config:
    db-config:
      logic-delete-field: deleted   # 全局逻辑删除字段
      logic-delete-value: 1
      logic-not-delete-value: 0
      id-type: auto                # 主键自增
  configuration:
    map-underscore-to-camel-case: true
```

---

### 2.2. 分层架构规范

```
Controller → ApplicationService → Repository（接口）
                                       ↓（基础设施层实现）
                                  RepositoryImpl → Mapper → MySQL
                                                        ↓
                                                   Entity（DO）
```

**核心约束**：Service / Domain 层只能调用 Repository 接口，不得直接依赖 Mapper。

---

### 2.3. 包结构规范

```
{basePackage}.dal.mysql.
├── config/          # 配置类
├── entity/          # 数据库实体（DO，后缀 DO）
├── mapper/          # MyBatis Mapper 接口（@MapperScan 自动扫描）
└── repository/      # Repository 实现
```

---

### 2.4. 实体定义规范

#### 2.4.1. 通用字段标准

每张业务表必须包含以下通用字段：

| 字段          | 类型                                                                      | 说明                         |
| ------------- | ------------------------------------------------------------------------- | ---------------------------- |
| `id`          | `bigint unsigned` NOT NULL AUTO_INCREMENT                                 | 主键，自增，步长为 1         |
| `create_time` | `datetime` NOT NULL DEFAULT CURRENT_TIMESTAMP                             | 创建时间                     |
| `update_time` | `datetime` NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间                     |
| `is_deleted`  | `tinyint unsigned` NOT NULL DEFAULT '0'                                   | 逻辑删除：1=已删除，0=未删除 |
| `status`      | `tinyint unsigned` NOT NULL                                               | 状态值由项目约定定义         |

#### 2.4.2. 实体类示例

```java
@Data
@TableName("t_article")
public class ArticleDO {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;
    private Long authorId;

    /**
     * 状态值含义由项目级 Skill 定义
     */
    private Integer status;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
```

#### 2.4.3. ORM 映射规范

- `is_xxx` 数据库字段映射到 POJO 时去掉 `is`（如 `is_deleted` → `deleted`），通过 `@TableField` 或全局配置映射
- 布尔类型变量**不加** `is` 前缀
- 敏感字段加解密由项目级 Skill 定义（如 MyBatis 拦截器或 TypeHandler）

---

### 2.5. Mapper 规范

```java
@Mapper
public interface ArticleMapper extends BaseMapper<ArticleDO> {
    // 简单查询直接用 MyBatis-Plus，复杂 SQL 在 XML 中定义
}
```

Mapper 接口放在 `mapper` 包下，通过 `@MapperScan` 自动扫描。

### 2.6. Repository 规范

#### 2.6.1. 接口定义

```java
public interface ArticleRepository {
    ArticleDTO findById(Long id);
    Page<ArticleDTO> pageByAuthorId(Pageable pageable, Long authorId);
    void save(ArticleDO article);
}
```

#### 2.6.2. 实现类

```java
@Repository
public class ArticleRepositoryImpl implements ArticleRepository {

    private final ArticleMapper articleMapper;

    public ArticleRepositoryImpl(ArticleMapper articleMapper) {
        this.articleMapper = articleMapper;
    }

    @Override
    public Page<ArticleDTO> pageByAuthorId(Pageable pageable, Long authorId) {
        LambdaQueryWrapper<ArticleDO> wrapper = Wrappers.<ArticleDO>lambdaQuery()
                .eq(ArticleDO::getAuthorId, authorId)
                .eq(ArticleDO::getStatus, 2)
                .eq(ArticleDO::getDeleted, 0)
                .orderByDesc(ArticleDO::getCreateTime);

        Page<ArticleDO> page = new Page<>(pageable.getPageNumber() + 1, pageable.getPageSize());
        Page<ArticleDO> result = articleMapper.selectPage(page, wrapper);
        // 转换为 DTO Page
        return result.convert(dto -> convertToDto(dto));
    }
}
```

#### 2.6.3. BaseMapper 常用方法速查

| 方法                      | 说明               | 场景               |
| ------------------------- | ------------------ | ------------------ |
| `selectById(id)`          | 按 ID 查询         | 详情查询           |
| `selectOne(wrapper)`      | 条件查单条         | 唯一条件查询       |
| `selectList(wrapper)`     | 条件查列表         | 批量查询（量不大） |
| `selectBatchIds(ids)`     | 批量 ID 查询       | ID 列表查询        |
| `selectPage(page, wrapper)` | 分页查询         | 分页列表           |
| `selectCount(wrapper)`    | 按条件计数         | 统计数量           |
| `insert(entity)`          | 单条插入           | 新增               |
| `saveBatch(list)`         | 批量插入（需 IService） | 批量写入      |
| `updateById(entity)`      | 按 ID 更新         | 修改               |
| `deleteById(id)`          | 按 ID 逻辑删除     | 删除               |

---

### 2.7. 查询规范

#### 2.7.1. 条件构造器

```java
// ✅ 推荐：Lambda 条件构造器
LambdaQueryWrapper<ArticleDO> wrapper = Wrappers.<ArticleDO>lambdaQuery()
        .eq(ArticleDO::getStatus, 2)
        .like(StringUtils.isNotBlank(keyword), ArticleDO::getTitle, keyword)
        .orderByDesc(ArticleDO::getCreateTime);

// ❌ 禁止：字符串拼接 SQL / ${} 参数绑定
```

#### 2.7.2. 分页查询

```java
// ✅ 使用 MyBatis-Plus 分页插件，物理分页
Page<ArticleDO> page = new Page<>(pageNum, pageSize);
Page<ArticleDO> result = articleMapper.selectPage(page, wrapper);

// ❌ 禁止：selectList 全量返回再手动截取
```

#### 2.7.3. 批量操作

```java
// ✅ 单次批量 ≤ 500 条（需继承 ServiceImpl 使用 IService）
articleService.saveBatch(batch, 500);

// ❌ 禁止：循环单条插入
```

---

### 2.8. 事务规范

```java
// 写操作加 @Transactional
@Transactional(rollbackFor = Exception.class)
public void createArticle(CreateArticleCMD cmd) {
  articleMapper.insert(article);
  // 发 MQ 事件在事务提交后执行（用 TransactionSynchronizationManager）
}

// 读操作加 readOnly = true
@Transactional(readOnly = true)
public ArticleVO getArticle(Long id) {
  return convertToVo(articleMapper.selectById(id));
}
```

---

### 2.9. 开发 Checklist 与反模式

#### Checklist

新增一张 MySQL 表时：

- [ ] 设计表结构，包含通用字段（id / create_time / update_time / is_deleted / status）
- [ ] 表名使用 `{业务名}_{表的作用}` 格式，字符集 utf8mb4
- [ ] status 字段值约定由项目级 Skill 定义
- [ ] 高频查询字段建索引，索引命名遵循 pk* / uk* / idx\_ 前缀规范
- [ ] 在 `entity/` 下创建 `XxxDO.java`（加 `@TableName`、字段注释）
- [ ] 在 `mapper/` 下创建 `XxxMapper.java`（继承 `BaseMapper<XxxDO>`）
- [ ] 在 `repository/` 下创建 `XxxRepositoryImpl.java` 实现 Repository 接口
- [ ] 复杂 SQL 的 XML 文件放在对应路径下

#### 常见反模式（禁止）

```
❌ HashMap/Hashtable 作为查询结果集输出（定义明确的 DO/DTO）
❌ 超过 3 张表 JOIN
❌ float/double 存储小数（使用 decimal）
❌ 外键与级联（应用层维护关系）
❌ 存储过程
❌ Repository 层写业务逻辑
❌ Controller 直接调 Mapper
❌ 直接暴露 DO 到接口层（必须转换为 VO/DTO）
❌ selectList 全量返回大表数据
❌ 循环单条 INSERT（使用 saveBatch）
❌ 硬编码连接信息（走配置中心）
```

---

## 参考资料

- MySQL 官方文档
- 《高性能 MySQL》
- 《MySQL 技术内幕：InnoDB 存储引擎》
- 《阿里巴巴 Java 开发手册（黄山版）》
