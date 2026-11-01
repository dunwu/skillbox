# AI Coding Anti-Example Blacklist

> This document collects the most common anti-patterns in AI Java backend coding. Each item is annotated with "why not to do it" and "alternative approach".
> Before coding, **MUST** check against this list. Hitting any one → stop immediately and correct.

---

## 1. Coding Anti-Patterns

| # | Anti-pattern | Why not to do it | Alternative approach |
|---|-------------|-----------------|---------------------|
| A1 | `BeanUtils.copyProperties(source, target)` | Runtime reflection; silently loses fields when names match but types differ; renaming does not cause compile errors, only surfaces in production | MapStruct `@Mapper` + `INSTANCE`, compile-time code generation, type mismatch fails at compile time |
| A2 | `@Autowired` field injection | Cannot declare final; tests must start Spring context; circular dependencies only surface at runtime | Constructor injection + `private final`, compile-time immutability guarantee, unit tests can just use new |
| A3 | Silently swallowing exceptions in catch (empty catch block / only `e.printStackTrace()`) | Upper layers are unaware after exception is swallowed, data inconsistency cannot be traced; `printStackTrace` bypasses logging system | `throw new BizException(ResultCode.XXX, e)` or `log.error("context", e)` then rethrow |
| A4 | `new ThreadPoolExecutor(...)` inside methods | Thread pool parameters scattered everywhere, OOM risk uncontrollable, cannot monitor uniformly | Use project unified thread pool configuration (`concurrency-guide.md §1`), inject via Bean |
| A5 | DB / RPC calls inside for loops | N+1 problem, 1000 records = 1000 network round trips, RT explodes linearly | Batch query `IN (...)` or `IN` batches (each batch ≤ 500), single RPC changed to batch API |
| A6 | Returning bare `Map` / bare `List` | Callers cannot understand field semantics from type signatures; serialization order unstable; Swagger cannot generate documentation | Define DTO/VO classes, return `{ResponseWrapper}<T>` / `{PageResponse}<T>` |
| A7 | `Math.random()` for security-related values | Pseudo-random, predictable, Tokens/keys/verification codes can be brute-force inferred | `SecureRandom`, with seed source managed uniformly by security module |
| A8 | String concatenation to build SQL / ES Query / MongoDB Filter | SQL injection / NoSQL injection, OWASP Top 1 security risk | MyBatis `#{}` parameter binding / ES QueryBuilder / MongoDB Criteria |
| A9 | RPC / HTTP calls inside transactional methods | Long transactions hold connection pools, external service timeout → transaction not released → connection pool exhausted → entire site unavailable | Call outside transaction, only do DB operations inside transaction; or use programmatic transactions to narrow scope |
| A10 | Printing complete sensitive information in logs (phone number/ID card/Token) | Log leak = data leak, compliance red line | Mask before printing: `phone.substring(0,3) + "****" + phone.substring(7)` or use log masking plugin |

---

## 2. Architecture Anti-Patterns

| # | Anti-pattern | Why not to do it | Alternative approach |
|---|-------------|-----------------|---------------------|
| B1 | Package by technical responsibility: `web/service/dal/common` | Conflicts with DDD boundaries, business logic scattered in service layer, cannot be independently deployed and evolved | Split by domain: `biz-{domain}/api` + `biz-{domain}/server` |
| B2 | Controller directly calls Repository / DAO | Skips Application/Domain layers, business rules have no home, Controller bloats | Controller → ApplicationService → DomainService → Repository |
| B3 | DO objects directly exposed at API layer | Database field change = API change, breaks backward compatibility; sensitive fields leaked | DO → DTO → VO conversion chain, API layer only exposes VO |
| B4 | Sub-modules hardcode dependency versions | Versions scattered across 10+ POMs, missing one during upgrade = runtime `NoSuchMethodError` | BOM module manages versions uniformly, sub-module `<dependency>` does not write `<version>` |
| B5 | Introducing strategy pattern + factory with just 3 if branches | Over-engineering, increases class count but logic unchanged, reading cost > benefit | ≤5 branches use if-else / switch directly in method; consider the strategy pattern only when there are >5 branches and growth is expected to continue |
| B6 | Cross-module direct reference to implementation classes (not API module interfaces) | Compile-time coupling between modules, cannot independently build and deploy | Depend on interfaces + DTOs in `biz-xxx/api` module, implementation classes injected via DI |

---

## 3. Security Anti-Patterns

| # | Anti-pattern | Why not to do it | Alternative approach |
|---|-------------|-----------------|---------------------|
| C1 | User input directly concatenated into SQL / NoSQL queries | SQL/NoSQL injection, database can be dumped | Parameterized queries `#{}` / QueryBuilder / Criteria API |
| C2 | File upload only validates extension | Attacker uploads `shell.jsp.jpg`, extension validation is bypassed | Validate file header magic number + MIME type + rename for storage |
| C3 | Hardcoded intranet IP / database addresses in code | Code leak = intranet topology leak; environment switching requires code changes | Config center `{ConfigManager}` dynamic retrieval, zero addresses in code |
| C4 | Deserialization without type whitelist validation | Deserialization vulnerabilities can execute arbitrary code (RCE) | Configure `@type` whitelist / use JSON safe mode |
| C5 | User input directly concatenated into AI Prompt | Prompt injection attack, AI can be induced to output sensitive information or perform unintended operations | Isolate user input with `<user_input>` tags, do not mix into system instructions |
| C6 | Keys/Tokens hardcoded in code or configuration files | Git history retains permanently, cannot be thoroughly cleaned after leak | `{ConfigManager}` dynamic retrieval / environment variables / Vault |

---

## 4. Testing Anti-Patterns

| # | Anti-pattern | Why not to do it | Alternative approach |
|---|-------------|-----------------|---------------------|
| D1 | Write implementation first then add tests | Tests become a formality to "prove implementation is correct", coverage appears high but boundary cases are missing | TDD: write failing test first → minimal implementation → refactor |
| D2 | Mock internal dependencies of tested object (Mock Converter / Mock internal methods) | Testing Mock behavior rather than real logic, tests still green after refactoring but code is broken | Only Mock external boundaries (DB / RPC / MQ), internal logic uses real implementation |
| D3 | Hardcode database URL / Token / user information in tests | Credentials leaked to Git history; changing environment causes all tests to fail | Environment variables / `.env` files / `@Value("${test.xxx}")` injection |
| D4 | `@Ignore` / comment out assertions to make tests pass | Masks real failures, CI all green but functionality is broken | Fix root cause or delete outdated tests; for temporary skips use `Assume.assumeTrue()` with reason annotated |
| D5 | Tests depend on execution order or shared mutable state | Random failures during parallel execution, CI unstable | Each test method independent, `@BeforeEach` resets state |

---

## 5. SDD Workflow Anti-Patterns

| # | Anti-pattern | Why not to do it | Alternative approach |
|---|-------------|-----------------|---------------------|
| E1 | Output code directly upon receiving requirements | Requirement understanding deviation → rework; missing non-functional requirements → production incident | 🔴 STOP → first produce `spec.md`, code only after user confirms six-dimension clarification |
| E2 | List only one design solution | Cannot compare trade-offs, single solution may have undiscovered fatal flaws | ≥ 2 solution comparisons + ADR (Architecture Decision Record) |
| E3 | Task granularity > 4h | Too large to verify, deviation mid-way cannot be detected in time | Split into ≤ half-day small tasks, each with independent acceptance criteria |
| E4 | Skip acceptance criteria and code directly | Cannot determine "done" standard, disputes and rework | Each task must have testable acceptance criteria (Given-When-Then) |
| E5 | Start working on vague requirements directly ("build something like WeChat") | Scope uncontrollable, infinite creep | 🔴 STOP → follow up on specific feature scope, decompose into executable independent requirements |

---

## 6. Quick Self-Check Checklist

> Before coding is complete, check against each item. Hitting any one → fall back and correct.

```
[ ] 无 BeanUtils（→ A1）
[ ] 无字段注入（→ A2）
[ ] 无空 catch 块（→ A3）
[ ] 无自行 new 线程池（→ A4）
[ ] 无 for 循环内 DB/RPC（→ A5）
[ ] 无裸 Map/List 返回（→ A6）
[ ] 无字符串拼接 SQL（→ A8）
[ ] 无事务内 RPC（→ A9）
[ ] 无敏感信息明文日志（→ A10）
[ ] 无用户输入直拼 Prompt（→ C5）
[ ] 无硬编码凭据/地址（→ C3/C6）
[ ] 测试无硬编码环境信息（→ D3）
[ ] 新需求未直接写代码（→ E1）
```
