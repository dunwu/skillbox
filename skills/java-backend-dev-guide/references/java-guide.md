# Java Development Standards

---

## 1. Package Naming Conventions

Follow DDD+COLA layering, unified base package path: `{basePackage}.{module-name}`

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

Module design principle: Split modules by DDD domain (`biz-xxx/api`, `biz-xxx/server`), prohibit splitting by technical responsibility into traditional `web`, `service`, `dal`, `common` structures. Historical modules keep original structure, no forced migration.

---

## 2. Naming Conventions

| Type | Suffix | Example |
|------|--------|---------|
| Database entity | `DO` | `ArticleDO` |
| Data transfer object | `DTO` | `ArticleDTO` |
| View object | `VO` | `ArticleVO` |
| Write operation parameter | `CMD` | `CreateArticleCMD` |
| Query parameter | `QRY` | `ArticlePageQRY` |
| DAO interface | `Dao` | `ArticleDao` |
| DAO implementation | `DaoImpl` | `ArticleDaoImpl` |
| Repository interface | `Repository` | `ArticleRepository` |
| Repository implementation | `RepositoryImpl` | `ArticleRepositoryImpl` |

---

## 3. ResultCode Error Code Standards

### 3.1. Naming Format

**MUST** follow `{DOMAIN}_{ACTION_RESULT}` format, all uppercase with underscore separation:

```
{DOMAIN}_{ACTION_RESULT}
```

| Component | Description | Example |
|-----------|-------------|---------|
| DOMAIN | Business domain (module name abbreviation) | `ARTICLE`, `AUTHOR`, `USER` |
| ACTION | Operation type or resource name | `NOT_FOUND`, `SAVE_FAILED`, `DUPLICATE` |
| RESULT | Result description | `EXPIRED`, `UNAUTHORIZED`, `QUOTA_EXCEEDED` |

### 3.2. Common Suffix Categories

| Suffix | Semantics | Example |
|--------|-----------|---------|
| `NOT_FOUND` | Resource not found | `ARTICLE_NOT_FOUND`, `AUTHOR_NOT_FOUND` |
| `SAVE_FAILED` | Write/update failure (including DB constraint conflicts) | `ARTICLE_SAVE_FAILED`, `USER_UPDATE_FAILED` |
| `DUPLICATE` | Unique constraint conflict | `PHONE_DUPLICATE`, `TITLE_DUPLICATE` |
| `UNAUTHORIZED` | Not logged in or Token invalid/expired | `TOKEN_EXPIRED`, `UNAUTHORIZED` |
| `FORBIDDEN` | Insufficient permissions | `ARTICLE_DELETE_FORBIDDEN` |
| `PARAM_INVALID` | Parameter validation failure | `PHONE_FORMAT_INVALID`, `PAGE_SIZE_EXCEEDED` |
| `EXPIRED` | Resource expired | `ARTICLE_EXPIRED`, `INVITATION_EXPIRED` |
| `QUOTA_EXCEEDED` | Quota limit exceeded | `DAILY_PUBLISH_QUOTA_EXCEEDED` |
| `TIMEOUT` | External dependency timeout | `RPC_TIMEOUT`, `ES_TIMEOUT` |

### 3.3. Coding Rules

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

**MUST**:

- Each ResultCode **MUST** be defined in the `{ResultCode}` enum in the public contract layer, creating them inside a business module without authorization is prohibited
- New ResultCode **MUST** include a Chinese message (for logging and frontend display)
- ResultCode with identical semantics **MUST NOT** be defined repeatedly

---

## 4. General Constraints

**MUST**:

- Entity classes in independent files, prohibit internal classes serving as entity responsibilities
- Prefer Stream API, reduce imperative for loops

**MUST NOT**:

- Directly expose DO to interface layer (must convert to VO / DTO)
- Use `Map<String, Object>` to pass business data (must define explicit types)
- Hardcode data source addresses, passwords, and other configurations (must go through config center)

---

## 5. Dependency Injection

- Constructor injection + private final, @Autowired field injection prohibited
- **Sole exception**: `@DubboReference` is a Dubbo framework special case, field injection allowed (→ middleware-guide.md §1)

---

## 6. Object Conversion

Use MapStruct uniformly, `BeanUtils.copyProperties` prohibited.

### 6.1 The Only Allowed Pattern: INSTANCE Static Singleton

All Converters **MUST** use default `@Mapper` + `INSTANCE` pattern, **MUST NOT** use `@Mapper(componentModel = "spring")`:

```java
@Mapper
public interface ArticleConverter {
    /** MapStruct 生成的转换器单例 */
    ArticleConverter INSTANCE = Mappers.getMapper(ArticleConverter.class);

    ArticleDTO toDTO(ArticleDO source);
    ArticleVO toVO(ArticleDTO source);
}

// 调用方直接使用 INSTANCE，无需 Spring 注入
ArticleDTO dto = ArticleConverter.INSTANCE.toDTO(articleDO);
```

**If mapping requires data from other Beans**: Query data in Service layer then pass as Converter method parameters, rather than injecting Beans inside Converter:

```java
// ✅ 正确：Service 层查数据，传给 Converter
ArticleCategoryDO category = categoryDao.getById(articleDO.getCategoryId());
ArticleVO vo = ArticleConverter.INSTANCE.toVO(articleDO, category);

// ❌ 禁止：在 Converter 内注入 Bean
@Mapper(componentModel = "spring")  // 禁止
public interface ArticleConverter {
    @Resource  // 禁止：Converter 不应注入 Bean
    private CategoryDao categoryDao;
}
```

### 6.2 Converter Handling in Tests

When using INSTANCE pattern, unit tests **MUST NOT** Mock Converters:

```java
// ❌ MUST NOT（INSTANCE 模式不需要 Mock）
@Mock
private ArticleConverter articleConverter;
when(articleConverter.toDTO(any())).thenReturn(dto);

// ✅ MUST（直接使用真实 INSTANCE，测试实际映射逻辑）
// 无需 Mock，Converter.INSTANCE 会真实执行字段映射
// 如需模拟 DAO.save() 回填 ID，使用 thenAnswer：
when(articleDao.save(any())).thenAnswer(invocation -> {
    ArticleDO saved = invocation.getArgument(0);
    saved.setId(1L);
    return true;
});
```

---

## 7. Transaction Management

- `@Transactional(rollbackFor = Exception.class)`, set readOnly appropriately
- Large transactions prohibited (move non-core logic out of transactions)
- RPC / HTTP calls inside transactional methods prohibited (→ middleware-guide.md §1, §2)

---

## 8. Utility Class Priority

1. Hutool (preferred)
2. Apache Commons / Guava (secondary)
3. Self-implemented (last resort, requires Code Review)

---
