---
name: java-backend-dev-guide
version: 1.0.0
description: "Java 后端全场景 AI Coding 规范（SDD 工作流 + DDD 架构 + 编码红线 + 安全门禁 + 测试门禁）。触发词：Java后端编码、SpringBoot、DDD、BizException、ResultCode、MapStruct、MyBatis-Plus、代码评审、单元测试、Java backend coding、Spring Boot、DDD architecture、code review。能力：需求→设计→编码→测试→验收全生命周期管控。边界：不覆盖前端/脚本/纯文档修改"
---

# Java 后端 AI Coding 开发规范

> **定位**：通用 Java 后端项目规约，适用于 Spring Boot + DDD 架构的 Java 后端项目。项目级定制通过扩展 Skill 覆盖本规范中的参数。
>
> **冲突仲裁**：用户显式指令 > 项目级扩展 Skill > 本 Skill > 阿里 Java 黄山版 > 框架官方文档。
>
> **加载方式**：Java 后端项目编码 / 评审时默认加载；技术规范按需读取 `references/` 对应文档。
>
> **加载场景**：新增功能、修改业务逻辑、创建实体/DAO/Service/Controller、接口设计、代码评审、存储操作（MySQL/Redis/ES/MongoDB/HBase）、单元测试编写。
>
> **不加载场景**：纯文档修改（README/CHANGELOG）、配置文件调整（yaml/properties 非代码逻辑）、Maven POM 版本同步（仅版本号修改，不含插件配置变更）。

## 0. 项目参数约定

> 本 Skill 中以 `{placeholder}` 标注的内容为项目级可配置参数。项目级扩展 Skill **MUST** 定义以下参数的默认值；未定义时使用下方通用默认值。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `{basePackage}` | `com.example.{project}` | 基础包路径 |
| `{BizException}` | `BizException` | 业务异常类名 |
| `{ResultCode}` | `ResultCode` | 错误码枚举类名 |
| `{ResponseWrapper}` | `Result<T>` | 单对象响应包装类 |
| `{PageResponse}` | `PageResult<T>` | 分页响应包装类 |
| `{ScrollResponse}` | `ScrollResult<T>` | 游标滚动响应包装类 |
| `{bomModule}` | 无 | BOM 模块名（如使用 BOM 模式） |
| `{ConfigManager}` | 配置中心 API | 配置获取方式 |
| `{AuditLogAnnotation}` | 无 | 审计日志注解（如 `@AuditLog`） |
| `{issuePrefix}` | 无 | 分支 Issue 前缀 |

---

## 1. SDD 开发工作流

**MUST NOT 跨阶段跳跃**：每阶段必须先产出 Artifact 并经用户确认，才能进入下一阶段。未完成详细设计（`tasks.md`）时，禁止开始编码。

### 1.1 全量流程（新功能 / 架构变更 / 公共契约修改）

| 阶段     | 配套 Skill                        | 输入                    | Artifact（输出）                          | 阶段门       |
| -------- | --------------------------------- | ----------------------- | ----------------------------------------- | ------------ |
| 需求分析 | `brainstorming`                   | PRD / 口头描述          | `spec.md`（What + Why + 验收标准）        | 用户确认     |
| 概要设计 | `brainstorming` + `writing-plans` | `spec.md`               | `plan.md`（模块划分、接口契约、数据模型） | 评审通过     |
| 详细设计 | `writing-plans`                   | `plan.md`               | `tasks.md`（可执行任务清单，含验收条件）  | 用户确认     |
| 编码     | `java-backend-dev-guide`          | `tasks.md`              | 代码 + JavaDoc                            | LSP 无 Error |
| 单元测试 | `test-driven-development`         | 代码 + 验收条件         | 测试代码 + 覆盖率 ≥ 80%                   | 全部 Pass    |
| 验收     | `verification-before-completion`  | 代码 + 测试 + `spec.md` | 通过 / 问题清单                           | 用户验收     |

> Artifact 统一存放于 `docs/specs/{需求名}/` 目录。各阶段详细规范见 `references/sdd-guide.md`。

### 1.2 快速路径（简单修改：单文件变更、无架构/契约/安全影响）

```
识别简单修改 → 直接编码 → lsp_diagnostics 零 Error → 提示影响面 → 完成
```

适用条件（**全部满足**才走快速路径）：
- 变更 ≤ 2 个业务文件（不含 test）
- 不涉及公共契约（API/DTO/错误码）变更
- 不涉及存储 Schema 变更
- 不涉及安全敏感字段
- 不涉及跨模块依赖

**🔴 STOP**：不满足上述任一条件时，必须回退到全量流程。

### 1.3 阶段阻断规则🔴

> **CHECKPOINT**：以下阻断条件未满足时，**STOP**——禁止进入下一阶段，必须先修复或回退。

| 阶段转换 | 🔴 阻断条件 | STOP 行为 | 回退动作 |
|----------|------------|-----------|---------|
| 需求→概要 | `spec.md` 未经用户确认 | 停止输出任何技术方案 | 追问开放问题，等待用户决策 |
| 需求→概要 | 开放问题列表非空 | 停止进入概要设计 | 逐条确认开放问题，用户明确回复后才删除 |
| 概要→详细 | `plan.md` 方案 < 2 个 | 停止拆解任务 | 要求补充 ≥2 方案对比及 ADR |
| 概要→详细 | 关键接口契约未定义 | 停止详细设计 | 回退补充方法签名、入参、出参、错误码 |
| 详细→编码 | `tasks.md` 无验收条件 | 停止编码 | 回退为每个 task 补充可测试的验收条件 |
| 详细→编码 | 单 task 预计 > 4h | 停止编码 | 拆分为更小 task，每个 ≤ 半天 |
| 编码→测试 | `lsp_diagnostics` 有 Error | 停止提测 | 修复编译错误，确认 LSP 零 Error |
| 编码→测试 | 违反 §4 编码红线 | 停止提测 | 逐条修复 MUST NOT 项 |
| 测试→验收 | 单元测试未全 Pass | 停止验收 | 修复失败用例，禁止跳过或注释断言 |
| 测试→验收 | 行覆盖率 < 80% | 停止验收 | 补充测试用例至达标 |
| 测试→验收 | DomainService 分支覆盖率 < 100% | 停止验收 | 补充领域逻辑分支测试 |

### 1.4 SDD 流程失败模式 fallback

> **if-then 三段式 fallback**：当 SDD 各阶段遇到阻塞时，按以下路径处理。

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|----------|
| 需求分析阶段用户无法确认开放问题（业务方缺席/决策延迟） | 记录为「待确认」，在 spec.md 中标注假设条件，继续推进 | 降级为快速路径，先实现最小可用版本（MVP），后续迭代补充 |
| 概要设计阶段无法找到 ≥2 个可行方案（技术约束过强） | 记录单一方案的 ADR，说明为何无其他选择，标注风险点 | 邀请架构组介入评审，暂停当前任务直至获得指导 |
| 详细设计阶段 task 拆解后仍 > 4h（复杂度高） | 进一步拆分子任务，识别可并行部分，标注依赖关系 | 升级为技术难题，创建 Spike Task 专门调研，不计入正常开发时间 |
| 编码阶段 LSP 持续报错且无法定位原因（依赖冲突/环境问题） | 清理 Maven 本地仓库（`mvn dependency:purge-local-repository`），重新构建 | 回退到上一个稳定 commit，创建新分支重新应用变更，隔离问题 |
| 单元测试覆盖率无法达到 80%（遗留代码/第三方依赖难 Mock） | 识别不可测代码段，申请豁免（需在 code review 中说明原因） | 降低门禁至 70%，但 MUST 补充集成测试覆盖核心路径 |
| MapStruct 编译失败（APT 处理器未激活） | 检查 `maven-compiler-plugin` 是否配置 `annotationProcessorPaths` | 临时使用手动转换（标注 TODO），提交 Issue 跟踪修复 |
| Dubbo RPC 调用超时（服务提供者未启动/网络问题） | 检查 Zookeeper/Nacos 注册中心，确认服务已注册且健康 | 启用本地 Mock 实现（`@DubboReference(mock = "true")`），继续开发消费者逻辑 |
| Redis 缓存穿透导致数据库压力激增 | 增加布隆过滤器前置判断，空值也缓存（短 TTL） | 降级关闭缓存，直接查库 + 限流保护（Sentinel 熔断） |

**🔴 STOP**: 如果 fallback 后仍无法解决，MUST 抛出 `BizException(ResultCode.TECH_BLOCKER)` 并升级至技术负责人，禁止强行推进。

---

## 2. 工程架构总览

### 2.1 通用 DDD 分层架构

```
{project}/
├── {bomModule}         # 全局版本管理（所有 jar 版本在此声明，子模块禁止硬编码版本）
├── {buildModule}       # 构建资源包（checkstyle 规则文件等）
├── {coreModule}        # 公共契约层（异常、DTO、响应模型、常量）
├── {utilModule}        # 无状态工具（优先复用，禁止重复造轮子）
├── {dalModule}/        # 存储适配（mysql / redis / es / hbase / mongo，按需）
├── {bootModule}/       # 启动自动配置（Spring Boot Starter）
├── {moduleDir}/        # 业务模块（DDD+COLA 领域落地）
│   └── biz-{domain}/
│       ├── api/        # 对外接口定义 + DTO
│       ├── client/     # RPC 客户端
│       └── server/     # 领域实现（controller / service / domain / repository）
└── {appModule}         # SpringBoot 应用层服务
```

> 项目级扩展 Skill **MUST** 定义具体的模块命名。未定义时遵循上述通用模式。

### 2.2 DDD+COLA 包结构

> 包命名规范、各层职责与后缀约定详见 `references/java-guide.md §1`。

模块设计原则：按 DDD 领域拆分模块（`biz-xxx/api`、`biz-xxx/server`），禁止按技术职责拆分为 `web`、`service`、`dal`、`common` 传统结构。

---

## 3. 架构设计规范

调用链严格单向，不得跨层：

```
Controller → ApplicationService → DomainService → Repository（接口）
                                                          ↓
                                                 RepositoryImpl / DAO
```

> 分层职责、包命名规范、DDD+COLA 完整结构：`references/java-guide.md`
>
> 架构合规检查清单（调用链方向、防腐层、DO 暴露等）：`references/review-guide.md §2`

---

## 4. 编码核心约束

> 命名规范、异常码规范、特有约束：`references/java-guide.md`
>
> 通用编码规约（方法行数、JavaDoc、依赖注入、事务、日志级别等）遵循《阿里巴巴 Java 开发手册（黄山版）》。

以下为最高频红线，**无例外**：

### 4.1 转换：MapStruct Only

```java
// ❌ MUST NOT
ArticleVO vo = new ArticleVO();
BeanUtils.copyProperties(articleDO, vo);

// ✅ MUST
@Mapper(componentModel = "spring")
public interface ArticleConverter {
    ArticleVO toVO(ArticleDO articleDO);
}
```

### 4.2 异常：禁止静默吞掉

```java
// ❌ MUST NOT
try { rpc.call(); } catch (Exception e) { /* 吞掉 */ }

// ✅ MUST
try { rpc.call(); } catch (Exception e) {
    throw new {BizException}({ResultCode}.ARTICLE_RPC_FAILED, e);
}
```

### 4.3 响应：统一包装

```java
// ❌ MUST NOT
@GetMapping("/{id}")
public Map<String, Object> getById(@PathVariable Long id) { ... }

// ✅ MUST
@GetMapping("/{id}")
public {ResponseWrapper}<ArticleVO> getById(@PathVariable Long id) { ... }
```

### 4.4 Maven：BOM 版本管控

```xml
<!-- ❌ MUST NOT：子模块硬编码版本 -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>33.0.0</version>
</dependency>

<!-- ✅ MUST：BOM 管控，子模块省略 version -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
</dependency>
```

### 4.5 依赖：BOM 外坐标须评审

- 如使用 BOM，MUST NOT 引入 BOM 外的新 Maven 坐标
- 如需引入，MUST 提交架构组评审，评审通过后在 BOM 中统一声明

### 4.6 过度设计：简单 CRUD 禁设计模式

```java
// ❌ MUST NOT：3 个 if 以内的 CRUD 引入策略模式
public interface StatusStrategy { void handle(ArticleDO article); }
public class DraftStrategy implements StatusStrategy { ... }
public class PublishedStrategy implements StatusStrategy { ... }

// ✅ MUST：直接在 Service 方法内实现
public void updateStatus(Long id, ArticleStatus status) {
    ArticleDO article = articleDao.selectById(id);
    if (status == DRAFT) { article.setDraft(); }
    else if (status == PUBLISHED) { article.setPublished(); }
    else { article.setArchived(); }
    articleDao.updateById(article);
}
```

---

## 5. 快速参考

| 场景                                                            | 文档                                 |
| --------------------------------------------------------------- | ------------------------------------ |
| SDD 各阶段 Artifact 模板与规范（需求分析、方案设计）            | `references/sdd-guide.md`            |
| 各阶段质量门禁与 Maven 插件门禁                                 | `references/quality-gate.md`         |
| 代码评审（AI 检查项、人工必查、Comment 格式）                   | `references/review-guide.md`         |
| Java 编码（异常码规范、DDD 分层、命名约定）                     | `references/java-guide.md`           |
| 中间件（Dubbo / RabbitMQ / 定时任务 / 日志 / ORM / 熔断降级）   | `references/middleware-guide.md`     |
| 并发编程（线程池模板 / CF 异步链 / 分布式锁）                   | `references/concurrency-guide.md`    |
| 接口设计（响应格式、Swagger、参数校验）                         | `references/api-guide.md`            |
| 数据安全（加密等级、注入防护、配置安全、代码生成安全门）        | `references/security-guide.md`       |
| 单元测试（TDD 流程、Mock 策略、覆盖率门禁）                     | `references/test-guide.md`           |
| MySQL / MyBatis-Plus / ShardingSphere                           | `references/mysql-guide.md`          |
| Redis（缓存、分布式锁）                                         | `references/redis-guide.md`          |
| Elasticsearch（索引设计、分页策略）                             | `references/es-guide.md`             |
| MongoDB 文档存储                                                | `references/mongo-guide.md`          |
| HBase 海量存储                                                  | `references/hbase-guide.md`          |
| 跨存储数据一致性（MySQL→ES 同步、缓存一致性、补偿机制）         | `references/consistency-guide.md`    |
| 性能基准测试（目标定义、门禁、JMH 微基准）                      | `references/perf-benchmark-guide.md` |
| 可观测性（日志规范、指标埋点、链路追踪、健康检查）              | `references/observability-guide.md`  |
| 知识库构建（分层架构、维护机制、Rule/Skill 治理、效果度量）       | `references/knowledge-base-guide.md` |
| Maven 工程规范（BOM / 插件继承 / APT / Profile）                | `references/maven-guide.md`          |
| Git 规范（Git Flow 分支策略 / Angular Commit）                  | `references/git-guide.md`            |

### 5.1 References 依赖关系图

> 按场景加载时，需同时加载图中箭头指向的关联文档。避免遗漏关联约束。

```
sdd-guide ─────────────────────────────────────┐
  │                                            │
  ▼                                            ▼
quality-gate ←── review-guide ←── security-guide
  │                    │               │
  │                    ▼               ▼
  │              java-guide        mysql-guide
  │                │               redis-guide
  │                ▼               es-guide
  │          middleware-guide      mongo-guide
  │                │               hbase-guide
  │                ▼               │
  │          concurrency-guide     ▼
  │                          consistency-guide
  ▼                                │
test-guide ◄───────────────────────┘
  │
  ▼
api-guide → maven-guide → git-guide

observability-guide（独立，按需加载）
knowledge-base-guide（独立，按需加载）
perf-benchmark-guide（独立，按需加载）
```

**加载规则**：加载某文档时，**MUST** 同时加载其箭头指向的下级文档。例：加载 `review-guide` 时必须同时加载 `security-guide` + `java-guide`。

---

## 6. 典型使用示例

> AI 加载本 Skill 后，根据用户 Prompt 匹配下表场景，按"AI 首次响应"执行。**MUST NOT** 跳过表格中列出的前置步骤。

### 6.1 场景路由表

| # | 用户 Prompt 特征 | 加载 references | AI 首次响应 |
|---|-----------------|-----------------|------------|
| 1 | "新增 XX 功能" / "帮我做 XX 需求" | `sdd-guide.md` | 🔴 STOP：先产出 `spec.md`（含验收标准+非功能需求+开放问题），禁止直接写代码 |
| 2 | "设计 XX 方案" / "XX 架构怎么选" | `sdd-guide.md` + `api-guide.md` | 要求 ≥2 方案对比 + ADR，禁止只列一个方案 |
| 3 | "写 XX 的代码" / "实现 XX 接口" | `java-guide.md` + 对应存储 guide | 检查 `tasks.md` 是否存在；不存在则 🔴 STOP 回退到详细设计 |
| 4 | "Review" / "看看这代码" | `review-guide.md` + `security-guide.md` | 按 §2 五维自检逐项输出 |
| 5 | "写单元测试" / "补测试" | `test-guide.md` | TDD：先写失败测试→最小实现→重构；禁止先实现后补测试 |
| 6 | "加 Redis 缓存" / "ES 搜索" | 对应存储 guide + `consistency-guide.md` | 先确认一致性策略再编码 |
| 7 | "并发问题" / "线程池" | `concurrency-guide.md` | 使用项目线程池模板，禁止自行 `new ThreadPoolExecutor` |
| 8 | "Maven / 依赖" | `maven-guide.md` | BOM 下禁止硬编码版本；新依赖必须评审 |

### 6.2 完整交互示例

> 以下示例展示 AI 加载本 Skill 后**实际应输出的完整响应**，非抽象描述。对照检查项用于验证 AI 是否遵守规范。

**示例 1：新功能开发（全量流程）**

```
用户：帮我新增文章收藏功能

AI 首次响应（🔴 STOP，禁止写代码）：

  【阶段】需求分析
  【加载】sdd-guide.md

  在输出 spec.md 之前，需确认以下维度：

  | 维度 | 待确认问题 |
  |------|-----------|
  | 功能边界 | 收藏上限？取消收藏是软删除还是物理删除？ |
  | 用户场景 | 是否需要收藏夹分组？是否需要收藏列表分页？ |
  | 异常边界 | 同一用户重复收藏同一文章 → 幂等返回还是报错？ |
  | 并发场景 | 高并发下收藏数计数是否允许短暂不一致？ |
  | 非功能 | 预计收藏量级？是否需要缓存？ |
  | 验收标准 | 如何判断"收藏功能完成且正确"？ |

  请确认以上问题后，我将输出 spec.md。

  验证点：
  ✅ 未输出任何代码（Java/XML/YAML 均无）
  ✅ 按 sdd-guide §1.3 六个维度逐项澄清
  ✅ 使用 🔴 STOP 标记阻断编码
  ❌ 违规标志：如果 AI 在确认前输出了 Controller/Service/DAO 代码 → 违反 §1
```

**示例 2：代码评审（编码→测试阶段）**

```
用户：帮我 Review 这段代码

  @Service
  public class ArticleServiceImpl {
      @Autowired
      private ArticleDao articleDao;  // ← 字段注入

      public Result<ArticleVO> getArticle(Long id) {
          ArticleDO articleDO = articleDao.selectById(id);
          ArticleVO vo = new ArticleVO();
          BeanUtils.copyProperties(articleDO, vo);  // ← BeanUtils
          return Result.success(vo);
      }

      public void updateStatus(Long articleId, String status) {
          try {
              articleDao.updateStatus(articleId, status);
          } catch (Exception e) {
              // ignore  // ← 吞异常
          }
      }
  }

AI 响应（加载 review-guide.md + security-guide.md）：

  【架构合规】
  ✅ 调用链方向正确（ServiceImpl → Dao → DB）
  ❌ @Autowired 字段注入，应改为构造器注入
    → [MUST-FIX] ArticleServiceImpl.java:3
    → 修复：添加 private final + @RequiredArgsConstructor 构造器

  【编码规范】
  ❌ 使用 BeanUtils.copyProperties（违反 §4.1）
    → [MUST-FIX] ArticleServiceImpl.java:8
    → 修复：创建 ArticleConverter MapStruct 接口

  【异常与事务】
  ❌ catch 后静默吞掉异常
    → [MUST-FIX] ArticleServiceImpl.java:15
    → 修复：throw new {BizException}({ResultCode}.ARTICLE_UPDATE_FAILED, e)

  【安全】
  ✅ 未发现明文密钥/Token
  ❌ 未校验：getArticle 是否返回敏感字段（手机号/身份证？）
    → [SUGGEST] 确认 ArticleVO 不含 S3/S4 级敏感字段

  【测试】
  ❌ 未发现对应单元测试
    → [MUST-FIX] 创建 ArticleServiceImplTest，覆盖 getArticle + updateStatus

  验证点：
  ✅ 五维自检 100% 覆盖（无跳项）
  ✅ 每条 MUST-FIX 含 文件:行号 + 修复方案
  ✅ 安全维度包含敏感字段脱敏检查
  ❌ 违规标志：如果 AI 只输出 "[✓] 代码看起来没问题" → 违反 review-guide §2
```

**示例 3：简单修改快速路径**

```
用户：给 ArticleMapper.xml 的 selectById 查询加一个 is_deleted=0 过滤

AI 响应（识别为快速路径）：

  1. 变更评估：单文件变更（XML），无公共契约/架构/安全影响 → 满足快速路径条件
  2. 直接修改：

  <!-- 修改前 -->
  SELECT * FROM t_article WHERE id = #{id}

  <!-- 修改后 -->
  SELECT * FROM t_article WHERE id = #{id} AND is_deleted = 0

  3. lsp_diagnostics 零 Error ✓
  4. 影响提示：此修改影响所有通过 selectById 查询的调用方，建议确认是否需要同步更新 XML 中其他查询语句的 is_deleted 过滤。

  验证点：
  ✅ 未启动完整 SDD 流程（无 spec.md/plan.md/tasks.md）
  ✅ 变更内容具体可执行（含修改前后 diff）
  ✅ 识别到影响面并提示
  ❌ 违规标志：如果 AI 输出了 spec.md → 过度流程，违反快速路径规则
```

**示例 4：安全场景（XSS 注入 + 敏感字段脱敏）**

```
用户：帮我写一个创建评论的接口，用户输入评论内容保存到数据库

AI 首次响应（加载 security-guide.md + api-guide.md）：

  🔴 在编码前，先确认安全约束：

  【代码生成安全门】
  | 检查项 | 状态 | 说明 |
  |--------|------|------|
  | SQL 注入 | 🔴 待确认 | 使用 MyBatis #{} 参数绑定，禁止 ${} |
  | XSS 防护 | 🔴 待确认 | 用户输入的评论内容是否需 HTML 转义？ |
  | 敏感字段 | 🔴 待确认 | 评论内容是否含手机号/身份证？存储前是否脱敏？ |
  | 文件路径 | — | 不涉及文件上传，跳过 |
  | 随机安全值 | — | 不涉及 token 生成，跳过 |
  | 反序列化 | — | 不涉及反序列化，跳过 |
  | SSRF | — | 不涉及外部 URL 请求，跳过 |

  请确认 XSS 策略和敏感字段范围后，我将按以下规格编码：

  【接口契约】
  POST /api/v1/comments
  Request: { "content": "string", "articleId": "long" }
  Response: {ResponseWrapper}<CommentVO>

  【代码骨架】
  @PostMapping
  public {ResponseWrapper}<CommentVO> create(@Valid @RequestBody CreateCommentCMD cmd) {
      // 1. XSS 过滤（如果启用）
      String sanitized = xssFilter.sanitize(cmd.getContent());
      // 2. 敏感字段检测
      if (sensitiveDetector.containsSensitive(sanitized)) {
          throw new {BizException}({ResultCode}.COMMENT_CONTAINS_SENSITIVE);
      }
      // 3. 持久化
      CommentDO commentDO = commentConverter.toDO(cmd);
      commentDO.setContent(sanitized);
      commentDao.insert(commentDO);
      return {ResponseWrapper}.success(commentConverter.toVO(commentDO));
  }

  验证点：
  ✅ 编码前先执行 security-guide §7 代码生成安全门（7 项逐条确认）
  ✅ SQL 使用 #{} 参数绑定（MyBatis-Plus insert 默认）
  ✅ 用户输入经过 XSS 过滤 + 敏感字段检测
  ✅ 响应使用 {ResponseWrapper}<T> 统一包装
  ✅ 接口契约含方法签名+入参+出参
  ❌ 违规标志：如果 AI 直接输出代码而未执行安全门 → 违反 security-guide §7
```

**示例 5：并发编程场景（线程池 + 分布式锁）**

```
用户：我需要批量处理 10000 条订单，要求高性能且不能重复处理

AI 首次响应（加载 concurrency-guide.md + redis-guide.md）：

  🔴 在编码前，先确认并发约束：

  【并发设计确认】
  | 维度 | 待确认问题 |
  |------|-----------|
  | 线程池选择 | 使用项目统一的 TraceableExecutor 还是自定义线程池？ |
  | 幂等性保证 | 如何防止同一条订单被多次处理？使用分布式锁还是数据库唯一索引？ |
  | 失败重试 | 处理失败的订单是否需要重试？重试几次？ |
  | 进度追踪 | 是否需要实时显示处理进度？使用 Redis incr 还是数据库计数？ |
  | 超时控制 | 单条订单处理超时时间？整体批次超时时间？ |

  请确认后，我将按以下方案编码：

  【方案选型】
  - 线程池：使用 `TraceableExecutor`（MDC 上下文透传）
  - 幂等性：Redis 分布式锁（key: `order:process:{orderId}`，TTL: 30s）
  - 失败重试：最多 3 次，指数退避（1s/2s/4s）
  - 进度追踪：Redis incr `order:batch:{batchId}:progress`
  - 超时控制：单条 5s，整体批次 10min

  【代码骨架】
  @Service
  public class OrderBatchProcessor {
      @Autowired
      private TraceableExecutor executor;  // ← 项目统一线程池
      
      @Autowired
      private RedissonClient redissonClient;

      public void processBatch(List<Long> orderIds, String batchId) {
          // 1. 初始化进度计数器
          redisTemplate.opsForValue().set("order:batch:" + batchId + ":progress", 0);
          
          // 2. 并行处理（CF 异步链）
          List<CompletableFuture<Void>> futures = orderIds.stream()
              .map(orderId -> CompletableFuture.runAsync(() -> {
                  processSingleOrder(orderId, batchId);
              }, executor))  // ← 使用项目线程池
              .collect(Collectors.toList());
          
          // 3. 等待所有任务完成
          CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
              .get(10, TimeUnit.MINUTES);  // ← 整体超时控制
      }

      private void processSingleOrder(Long orderId, String batchId) {
          String lockKey = "order:process:" + orderId;
          RLock lock = redissonClient.getLock(lockKey);
          
          try {
              // 尝试获取分布式锁（最多等待 3s，锁定 30s）
              if (lock.tryLock(3, 30, TimeUnit.SECONDS)) {
                  try {
                      // 业务逻辑
                      OrderDO order = orderDao.selectById(orderId);
                      if (order.getStatus() != OrderStatus.PENDING) {
                          return;  // 已处理，幂等返回
                      }
                      // ... 处理订单 ...
                      
                      // 更新进度
                      redisTemplate.opsForValue().increment("order:batch:" + batchId + ":progress");
                  } finally {
                      lock.unlock();
                  }
              } else {
                  throw new {BizException}({ResultCode}.ORDER_PROCESSING_CONFLICT);
              }
          } catch (InterruptedException e) {
              Thread.currentThread().interrupt();
              throw new {BizException}({ResultCode}.ORDER_PROCESS_TIMEOUT, e);
          }
      }
  }

  验证点：
  ✅ 使用项目统一线程池 `TraceableExecutor`（非自行 new ThreadPoolExecutor）
  ✅ 使用 Redisson 分布式锁保证幂等性
  ✅ CompletableFuture 异步链 + 超时控制
  ✅ 进度追踪使用 Redis incr
  ✅ 异常处理完整（InterruptedException 恢复中断标志）
  ❌ 违规标志：如果 AI 使用 `new ThreadPoolExecutor()` → 违反 concurrency-guide §2
```

### 6.3 自检验证清单

> AI 在完成上述任一场景的响应后，**MUST** 逐条对照以下清单自检。全部通过才可声明"完成"。

| 场景 | 检查项 | 验证方式 |
|------|--------|---------|
| 新功能 | 首次响应无代码（Java/XML/YAML） | 搜索输出中无 `class` / `@Service` / `<mapper` / `application.yml` |
| 新功能 | 按 sdd-guide §1.3 六个维度逐项澄清 | 六个维度各至少一条确认问题 |
| 新功能 | 使用 🔴 STOP 标记 | 输出含 `🔴 STOP` 或 `🔴 阻断` |
| 评审 | 五维自检 100% 覆盖 | 架构/编码/异常事务/安全/测试 五个一级标题全部出现 |
| 评审 | 每条缺陷含文件路径+行号 | 格式匹配 `文件名:行号` |
| 评审 | MUST-FIX 含修复方案 | 每条 MUST-FIX 后紧跟"修复：" |
| 快速路径 | 未输出 spec.md/plan.md/tasks.md | 搜索输出中无上述三个文件名 |
| 快速路径 | 变更内容含 diff（修改前/修改后） | 输出含 `修改前` + `修改后` 代码块 |
| 安全 | 代码生成安全门 7 项逐条确认 | 7 项全部出现（含"不涉及"标记） |
| 安全 | 用户输入经 XSS/注入/敏感字段过滤 | 代码中含 sanitize/detect/validate 调用 |
| 全局 | 响应使用 {ResponseWrapper}<T> 包装 | 返回类型不含裸 Map 或 String |
| 全局 | 异常使用 {BizException}({ResultCode}.XXX) | catch 块含 `throw new {BizException}` |
| 全局 | 对象转换无 BeanUtils.copyProperties | 搜索输出中无 `BeanUtils.copyProperties` |
| 全局 | 依赖注入为构造器注入 | 搜索输出中无 `@Autowired` 字段注入（除 @DubboReference） |

### 6.4 非SDD场景阻断规则🔴

> 以下场景虽不走完整 SDD 流程，但仍有阻断条件。

| 场景 | 🔴 阻断条件 | STOP 行为 | 回退动作 |
|------|------------|-----------|---------|
| 直接编码（无 spec.md） | 用户未明确声明“跳过 SDD” | 停止编码，提示走 SDD 流程 | 询问用户是否确认跳过；确认后走快速路径 |
| 代码评审 | Review 意见未逐条回复 | 停止合并 PR | 逐条回复 MUST-FIX/SUGGEST/NIT |
| 安全相关变更 | 未执行 security-guide §6 自检 | 停止提交 | 逐项完成安全自检清单 |
| 存储Schema变更 | 未评审 | 停止执行 DDL | 提交 DBA/架构组评审 |
| 依赖引入 | 未在 BOM 中声明 | 停止使用该依赖 | 先在 BOM 添加并提交评审 |

---

## 7. AI 行为可观测性

> **目的**：提供机制验证 AI 是否遵守本 Skill 规范，持续改进 Skill 质量。

### 7.1 合规检查清单（AI 自检用）

> AI 在每次响应后 **MUST** 执行以下自检，输出合规报告：

| 检查项 | 验证方法 | 违规标志 |
|--------|---------|----------|
| SDD 阶段合规 | 搜索输出中无代码片段（新功能场景） | 出现 `class` / `@Service` / `<mapper` / `application.yml` |
| 参数替换正确 | 检查是否使用项目特定类名 | 出现 `{BizException}` 未被替换为实际类名 |
| 反例黑名单遵守 | 检查代码中无 MUST NOT 项 | 出现 `BeanUtils.copyProperties` / `new ThreadPoolExecutor` |
| 检查点执行 | 确认 🔴 STOP 标记出现在阻断场景 | 应该 STOP 但未输出标记 |
| 五维自检覆盖 | Review 场景五个维度全部出现 | 缺少架构/编码/异常事务/安全/测试任一项 |
| 文件路径+行号 | 每条缺陷含具体位置 | 格式不匹配 `文件名:行号` |

**自检输出格式**：
```
【AI 合规自检】
✅ SDD 阶段合规：未输出代码
✅ 参数替换正确：已使用 CustomException/DataResult
✅ 反例黑名单遵守：无 BeanUtils/new ThreadPoolExecutor
✅ 检查点执行：🔴 STOP 标记已输出
✅ 五维自检覆盖：5/5 维度完整
✅ 文件路径+行号：3条缺陷均含位置

合规率：100% (6/6)
```

### 7.2 度量指标埋点

> 为持续改进 Skill，建议追踪以下指标（项目级可选实现）：

| 指标 | 计算方式 | 目标值 | 高频触发说明 |
|------|---------|--------|---------------|
| 阶段跳过率 | 用户要求跳过 SDD 的次数 / 总需求数 | < 20% | Skill 流程过于繁琐，需简化 |
| 红线违反率 | AI 生成代码违反 §4 的次数 / 总代码块数 | < 5% | Skill 约束不够清晰或示例不足 |
| fallback 触发率 | 失败模式 fallback 被触发的频率 | < 10% | 常见场景未覆盖，需补充示例 |
| CHECKPOINT 阻断率 | 🔴 STOP 触发的次数 / 总交互数 | 20-40% | 过低说明检查点不足，过高说明规范过严 |
| 实测覆盖率 | 真实子 agent 测试通过的用例比例 | > 90% | Skill 宣称能力与实际表现不符 |

### 7.3 持续改进循环

```
收集违规案例 → 分析根因 → 更新 Skill → 重新测试 → 验证改进
    ↑                                              ↓
    └────────── 每月回顾一次指标趋势 ──────────────┘
```

**示例**：如果「红线违反率」连续 2 周 > 10%，说明 §4 编码约束需要：
1. 补充更多反例代码
2. 增加交互式决策树辅助判断
3. 在 test-prompts.json 中添加对应压力测试用例

---

## 8. 多角色使用指南

> **目的**：适配不同角色的使用习惯，提升 Skill 普适性。

### 8.1 角色路由表

| 角色 | 典型 Prompt | Skill 加载策略 | 输出调整 |
|------|------------|---------------|----------|
| 初级开发 | “帮我写 XX 功能” | 全量加载 + 详细解释 | 每步说明原因，提供学习资源链接 |
| 高级开发 | “Review 这段代码” | 仅加载 review-guide + security-guide | 简洁输出，聚焦 MUST-FIX |
| Tech Lead | “设计 XX 架构方案” | 加载 sdd-guide + api-guide + 中间件 guide | 强调方案对比、ADR、风险评估 |
| QA 工程师 | “为 XX 接口写测试” | 加载 test-guide + api-guide | 侧重边界条件、异常场景覆盖 |
| 架构师 | “评估技术选型” | 加载 java-guide + maven-guide + perf-benchmark | 提供量化对比数据、迁移成本 |

### 8.2 角色特定检查点

**初级开发 🔴 CHECKPOINT**:
- 首次使用 Skill 时，AI **MUST** 询问：“您是初次使用本规范吗？需要详细解释还是快速参考？”
- 如果选择“详细解释”，每个步骤附加“为什么这样做”的说明
- 示例：讲解 MapStruct 时，补充“相比 BeanUtils，MapStruct 在编译期生成代码，性能提升 10x+”

**高级开发 🔴 CHECKPOINT**:
- 如用户明确要求“快速 Review”，AI **MUST** 省略背景说明，直接输出缺陷列表
- 格式：`[MUST-FIX] 文件:行号 - 问题描述 → 修复方案`

**Tech Lead 🔴 CHECKPOINT**:
- 架构决策前，AI **MUST** 询问：“是否需要生成 ADR（Architecture Decision Record）文档？”
- 如涉及公共契约变更，**MUST** 提示影响面分析（哪些模块/接口受影响）

**QA 工程师 🔴 CHECKPOINT**:
- 生成测试用例时，AI **MUST** 询问：“需要覆盖哪些异常场景？（参数校验/并发/超时/降级）”
- 默认生成：正常流程 + 参数为空 + 参数越界 + 数据库异常 四个用例

### 8.3 角色切换示例

```
用户：我是初级开发，帮我写一个用户注册功能

AI 响应：

  【检测到初级开发角色】
  我将为您提供详细解释，包括每个步骤的原因和最佳实践。

  【阶段】需求分析
  【加载】sdd-guide.md

  在开始之前，我需要确认以下问题（这是 SDD 工作流的第一步）：

  1. 功能边界：注册用户需要哪些字段？（用户名/密码/邮箱/手机号？）
     💡 为什么问这个：避免后续返工，明确数据模型
  
  2. 异常边界：用户名重复如何处理？密码强度要求？
     💡 为什么问这个：提前定义错误码，避免硬编码
  
  3. 安全约束：密码是否需要加密存储？使用 BCrypt 还是 Argon2？
     💡 为什么问这个：安全是最高优先级，必须在设计阶段确定
  
  ...（其余维度）

  请回答以上问题后，我将输出 spec.md 并解释每个部分的作用。
```

---

## 9. 交互式决策树

> **目的**：通过结构化决策流程，辅助 AI 快速做出正确技术选型，减少误判。

### 9.1 存储选型决策树

```
用户：我需要存储 XX 数据

AI 决策流程：

1️⃣ 数据结构是什么？
   ├─ 关系型（表格、外键、事务） → MySQL
   ├─ 文档型（JSON、嵌套、灵活 Schema） → MongoDB
   ├─ 键值对（缓存、会话、计数器） → Redis
   ├─ 全文搜索（分词、相关性排序） → Elasticsearch
   └─ 海量列式（时序数据、日志） → HBase

2️⃣ 数据量级？
   ├─ < 1000万 → 单表 MySQL / 单节点 Redis
   ├─ 1000万~1亿 → MySQL + 分库分表（ShardingSphere）/ Redis Cluster
   └─ > 1亿 → HBase / ES 分布式集群

3️⃣ 读写比例？
   ├─ 读多写少（> 10:1） → 加 Redis 缓存层
   ├─ 写多读少（< 1:10） → 考虑异步写入（MQ + 批量入库）
   └─ 均衡 → 正常 CRUD

4️⃣ 一致性要求？
   ├─ 强一致性（金融交易） → MySQL 事务
   ├─ 最终一致性（社交动态） → MySQL → ES 异步同步
   └─ 弱一致性（统计数据） → Redis 直接写入

🔴 CHECKPOINT: 确认选型后，加载对应 storage-guide.md
如果涉及多存储协同，额外加载 consistency-guide.md
```

### 9.2 设计模式选型决策树

```
用户：这个场景需要用设计模式吗？

AI 判断逻辑：

1️⃣ 分支数量？
   ├─ ≤ 3 个 if/switch → ❌ 不使用设计模式（违反 §4.6 过度设计）
   └─ > 3 个 if/switch → 继续判断

2️⃣ 未来扩展性？
   ├─ 固定逻辑，不会新增分支 → ❌ 不使用（YAGNI 原则）
   └─ 可能新增分支（如新增状态/类型/策略） → ✅ 考虑使用

3️⃣ 分支逻辑复杂度？
   ├─ 每个分支 ≤ 10 行代码 → ❌ 不使用（提取方法即可）
   └─ 每个分支 > 10 行代码 → ✅ 使用策略模式/工厂模式

4️⃣ 是否有共同接口？
   ├─ 是 → ✅ 策略模式（Strategy Pattern）
   └─ 否 → ✅ 工厂模式（Factory Pattern）创建不同实现

示例：订单状态处理
- 状态数：5 个（待支付/已支付/发货中/已完成/已取消） → > 3 ✅
- 未来可能新增“退款中”状态 → 可扩展 ✅
- 每个状态处理逻辑 > 20 行 → 复杂 ✅
- 共同接口：OrderStatusHandler → ✅ 策略模式

🔴 CHECKPOINT: 如决定使用设计模式，确保符合 §4.6 非过度设计原则
```

### 9.3 并发方案决策树

```
用户：我需要处理并发场景

AI 决策流程：

1️⃣ 并发类型？
   ├─ CPU 密集型（计算、加密） → 线程池大小 = CPU核数 + 1
   ├─ IO 密集型（数据库、HTTP） → 线程池大小 = CPU核数 * 2
   └─ 混合型 → 分离为两个线程池

2️⃣ 是否需要 MDC 上下文透传？
   ├─ 是（链路追踪、日志关联） → ✅ 使用 TraceableExecutor
   └─ 否 → 可使用原生 ThreadPoolExecutor（但仍建议用项目统一线程池）

3️⃣ 是否需要分布式锁？
   ├─ 单机部署 → ✅ synchronized / ReentrantLock
   ├─ 多机部署 + 强一致性 → ✅ Redisson 分布式锁
   └─ 多机部署 + 最终一致性 → ✅ 数据库唯一索引 / 乐观锁

4️⃣ 失败重试策略？
   ├─ 瞬时故障（网络抖动） → ✅ 指数退避重试（1s/2s/4s/8s）
   ├─ 业务故障（参数错误） → ❌ 不重试，直接返回错误
   └─ 依赖故障（下游服务不可用） → ✅ 熔断降级（Sentinel）

🔴 CHECKPOINT: 确认方案后，加载 concurrency-guide.md 获取线程池模板
```

### 9.4 异常处理决策树

```
用户：这个异常应该怎么处理？

AI 判断逻辑：

1️⃣ 异常类型？
   ├─ 业务异常（参数校验、权限不足） → ✅ BizException + ResultCode
   ├─ 系统异常（数据库连接失败、RPC 超时） → ✅ BizException + 记录日志
   └─ 运行时异常（NullPointerException） → ❌ 禁止 catch，修复代码根因

2️⃣ 是否需要回滚事务？
   ├─ 是（写操作失败） → ✅ @Transactional + 抛出异常
   └─ 否（读操作/幂等操作） → ✅ 捕获异常 + 返回友好提示

3️⃣ 是否需要降级？
   ├─ 核心功能（下单、支付） → ❌ 不降级，直接报错
   ├─ 非核心功能（推荐、统计） → ✅ 降级返回默认值
   └─ 可选功能（积分、优惠券） → ✅ 降级跳过，记录日志

4️⃣ 是否需要告警？
   ├─ P0 级（资损、数据丢失） → ✅ 立即电话告警
   ├─ P1 级（核心功能不可用） → ✅ 钉钉/企业微信告警
   └─ P2 级（性能下降、非核心故障） → ✅ 日志记录 + 日报汇总

🔴 CHECKPOINT: 所有 catch 块 MUST NOT 静默吞掉异常，必须记录日志或抛出
```

---

## 10. Skill 版本管理

> **目的**：提供 Skill 自身的版本演进机制，确保向后兼容和平滑迁移。

### 10.1 版本兼容性矩阵

| Skill 版本 | JDK 版本 | Spring Boot | MyBatis-Plus | 关键变更 | 迁移指南 |
|-----------|---------|-------------|--------------|---------|----------|
| v1.0.0 (当前) | 17+ | 2.5.x+ | 3.5.x | 初始版本 | — |
| v0.9.x (废弃) | 8+ | 2.3.x | 3.4.x | 旧版参数占位符 | 升级至 v1.0，替换 `{CommonResult}` 为 `{ResponseWrapper}` |

### 10.2 破坏性变更通知

> **v1.0.0 破坏性变更**（相比 v0.9.x）：

| 变更项 | 旧值 | 新值 | 影响范围 | 迁移步骤 |
|--------|------|------|---------|----------|
| `{ResponseWrapper}` 默认值 | `CommonResult<T>` | `Result<T>` | 所有响应包装类 | 在项目扩展 Skill 中重新定义为原值 |
| `{BizException}` 包路径 | `com.example.common.exception` | `{basePackage}.common.exception` | 异常类导入 | 更新 import 语句 |
| SDD 阶段门 | 无显式标记 | 🔴 STOP 强制阻断 | 工作流执行 | AI 自动适配，无需手动迁移 |

**检测脚本**：
```bash
# 检查是否仍在使用旧版参数
grep -r "CommonResult" src/ | wc -l  # 如 > 0，需迁移

# 检查是否违反新的检查点规则
grep -r "STOP" docs/specs/*/spec.md | wc -l  # 如 = 0，说明未遵循新规范
```

### 10.3 弃用策略

- **Deprecated**（弃用但支持）：标记为 `@Deprecated`，保留 2 个大版本（约 6 个月）
  - 示例：v1.0 中标记 `{OldParam}` 为 Deprecated，v3.0 时移除
  
- **Removed**（完全移除）：提前 1 个大版本警告，提供迁移指南
  - 示例：v2.0 发布前，在 v1.x 的 CHANGELOG 中预告移除项

- **Breaking Change**（破坏性变更）：仅在主版本号升级时引入（SemVer 规范）
  - 示例：v1.x → v2.0 可引入破坏性变更，v1.0 → v1.1 不得引入

### 10.4 版本升级检查清单

> AI 在检测到 Skill 版本升级时，**MUST** 执行以下检查：

1. ✅ 读取 CHANGELOG，识别破坏性变更
2. ✅ 扫描现有代码，标记需要迁移的部分
3. ✅ 生成迁移报告，列出受影响文件和修改建议
4. ✅ 提供自动化脚本（如 sed 命令）批量替换旧参数
5. ✅ 运行测试用例，验证迁移后功能正常

**示例输出**：
```
【Skill 版本升级检测】
检测到 java-backend-dev-guide 从 v0.9 升级至 v1.0

破坏性变更：
1. {ResponseWrapper} 默认值变更：CommonResult<T> → Result<T>
   影响文件：12 个 Controller 类
   迁移命令：sed -i 's/CommonResult/Result/g' src/**/*.java

2. SDD 阶段门增强：新增 🔴 STOP 强制阻断
   影响：AI 行为变更，无需代码迁移

建议操作：
1. 执行迁移命令
2. 运行 mvn test 验证编译通过
3. 阅读 v1.0 CHANGELOG 了解新特性

是否需要我帮您执行迁移？[是/否]
```
