# Java 开发规范

> **摘要**
>
> - **核心约束**：构造器注入 + private final 禁 @Autowired 字段注入（→ 阿里手册 §六 工程结构）；MapStruct only 禁 BeanUtils.copyProperties；异常用 `{BizException}({ResultCode}.XXX)` 禁静默吞掉；ResultCode 命名格式 `{DOMAIN}_{ACTION_RESULT}` 全大写
> - **关键阈值**：新增 ResultCode 必须在公共契约层枚举中定义
> - **常见违规**：@Autowired 字段注入、BeanUtils.copyProperties 做对象转换、Controller 直接暴露 DO、ResultCode 命名过于笼统（ERROR/FAIL）、在业务模块私自创建 ResultCode

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 包命名规范

遵循 DDD+COLA 分层，统一基础包路径：`{basePackage}.{模块名}`

```
├── controller/      # 接入层（HTTP 入口）
│   ├── app/         # C 端，路由前缀可配置
│   └── admin/       # B 端，路由前缀可配置
├── application/     # 应用服务层（编排，不含业务规则）
├── domain/
│   ├── entity/      # 领域实体（非 DO）
│   ├── service/     # 领域服务
│   ├── repository/  # Repository 接口（防腐层）
│   └── event/       # 领域事件
├── infrastructure/
│   ├── repository/  # Repository 实现
│   ├── gateway/     # 外部服务适配（RPC / HTTP）
│   └── converter/   # 对象转换（MapStruct）
├── dto/
│   ├── cmd/         # Command（写操作入参）
│   ├── qry/         # Query（查询入参）
│   └── vo/          # View Object（出参）
├── constant/        # 常量
├── task/            # 定时任务
└── config/          # 配置类
```

模块设计原则：按 DDD 领域拆分模块（`biz-xxx/api`、`biz-xxx/server`），禁止按技术职责拆分为 `web`、`service`、`dal`、`common` 传统结构。历史模块保持原结构，不做强制迁移。

---

## 2. 命名规范

| 类型            | 后缀             | 示例                    |
| --------------- | ---------------- | ----------------------- |
| 数据库实体      | `DO`             | `ArticleDO`             |
| 数据传输对象    | `DTO`            | `ArticleDTO`            |
| 视图对象        | `VO`             | `ArticleVO`             |
| 写操作入参      | `CMD`            | `CreateArticleCMD`      |
| 查询入参        | `QRY`            | `ArticlePageQRY`        |
| DAO 接口        | `Dao`            | `ArticleDao`            |
| DAO 实现        | `DaoImpl`        | `ArticleDaoImpl`        |
| Repository 接口 | `Repository`     | `ArticleRepository`     |
| Repository 实现 | `RepositoryImpl` | `ArticleRepositoryImpl` |

---

## 3. ResultCode 异常码规范

### 3.1. 命名格式

**MUST** 遵循 `{业务领域}_{操作结果}` 格式，全大写下划线分隔：

```
{DOMAIN}_{ACTION_RESULT}
```

| 组成部分 | 说明                   | 示例                                        |
| -------- | ---------------------- | ------------------------------------------- |
| DOMAIN   | 业务领域（模块名缩写） | `ARTICLE`、`AUTHOR`、`USER`                 |
| ACTION   | 操作类型或资源名称     | `NOT_FOUND`、`SAVE_FAILED`、`DUPLICATE`     |
| RESULT   | 结果描述               | `EXPIRED`、`UNAUTHORIZED`、`QUOTA_EXCEEDED` |

### 3.2. 常见后缀分类

| 后缀             | 语义                            | 示例                                         |
| ---------------- | ------------------------------- | -------------------------------------------- |
| `NOT_FOUND`      | 资源不存在                      | `ARTICLE_NOT_FOUND`、`AUTHOR_NOT_FOUND`      |
| `SAVE_FAILED`    | 写入/更新失败（含 DB 约束冲突） | `ARTICLE_SAVE_FAILED`、`USER_UPDATE_FAILED`  |
| `DUPLICATE`      | 唯一约束冲突                    | `PHONE_DUPLICATE`、`TITLE_DUPLICATE`         |
| `UNAUTHORIZED`   | 未登录或 Token 无效/过期        | `TOKEN_EXPIRED`、`UNAUTHORIZED`              |
| `FORBIDDEN`      | 权限不足                        | `ARTICLE_DELETE_FORBIDDEN`                   |
| `PARAM_INVALID`  | 参数校验失败                    | `PHONE_FORMAT_INVALID`、`PAGE_SIZE_EXCEEDED` |
| `EXPIRED`        | 资源已过期                      | `ARTICLE_EXPIRED`、`INVITATION_EXPIRED`      |
| `QUOTA_EXCEEDED` | 超出配额限制                    | `DAILY_PUBLISH_QUOTA_EXCEEDED`               |
| `TIMEOUT`        | 外部依赖超时                    | `RPC_TIMEOUT`、`ES_TIMEOUT`                  |

### 3.3. 编码规则

```java
// ✅ MUST：领域前缀 + 具体原因
throw new {BizException}({ResultCode}.ARTICLE_NOT_FOUND);
throw new {BizException}({ResultCode}.ARTICLE_SAVE_FAILED);
throw new {BizException}({ResultCode}.PHONE_DUPLICATE);

// ❌ MUST NOT：过于笼统
throw new {BizException}({ResultCode}.ERROR);           // 缺乏业务语义
throw new {BizException}({ResultCode}.FAIL);             // 无法定位问题
throw new {BizException}({ResultCode}.ARTICLE_ERROR);    // 未说明是哪种错误

// ❌ MUST NOT：混用驼峰
throw new {BizException}({ResultCode}.articleNotFound);  // 必须全大写
```

**MUST**：

- 每条 ResultCode **MUST** 在公共契约层的 `{ResultCode}` 枚举中定义，禁止在业务模块中私自创建
- 新增 ResultCode **MUST** 附带中文 message（供日志和前端展示）
- 相同语义的 ResultCode **MUST NOT** 重复定义

---

## 4. 通用约束

**MUST**：

- 实体类独立文件，禁止内部类承担实体职责
- 优先 Stream API，减少命令式 for 循环

**MUST NOT**：

- 直接暴露 DO 到接口层（必须转换为 VO / DTO）
- 使用 `Map<String, Object>` 传递业务数据（必须定义明确类型）
- 硬编码数据源地址、密码等配置（必须走配置中心）

> 方法行数、JavaDoc、分层职责等通用规约遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约。

---

## 5. 依赖注入

> 构造器注入 + private final、禁止 @Autowired 字段注入等规约遵循《阿里巴巴 Java 开发手册（黄山版）》§六 工程结构 — 应用分层。
>
> **唯一例外**：`@DubboReference` 是 Dubbo 框架特例，允许字段注入（→ middleware-guide.md §1）。

---

## 6. 对象转换

统一使用 MapStruct，禁止 `BeanUtils.copyProperties`：

```java
@Mapper(componentModel = "spring")
public interface ArticleConverter {
    ArticleDTO toDTO(ArticleDO source);
    ArticleVO toVO(ArticleDTO source);
}
```

---

## 7. 事务管理

> @Transactional(rollbackFor=Exception.class)、readOnly、禁止大事务等规约遵循《阿里巴巴 Java 开发手册（黄山版）》§五 MySQL 数据库 — ORM 映射。
>
> **补充**：禁止事务方法内发起 RPC / HTTP 调用（→ middleware-guide.md §1、§2）。

---

## 8. 工具类优先级

> 工具类选择遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 — OOP 规约。

1. Hutool（首选）
2. Apache Commons / Guava（次选）
3. 自行实现（最后手段，需经 Code Review）

---

## 9. 代码注释规范

> JavaDoc 格式、TODO/FIXME 约定遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 — 注释规约。

---

## 附录：参考书目

- 《阿里巴巴 Java 开发手册（黄山版）》
- 《Effective Java 中文版（原书第3版）》
- 《代码整洁之道》
- 《Java 并发编程的艺术》
