---
name: java-backend-dev-guide
version: 2.1.0
description: "Java Backend AI Coding Standards: SDD Workflow + DDD Architecture + Coding Red Lines + Security/Testing Gates, covering the full lifecycle from requirements → design → coding → testing → acceptance. Trigger words: Java backend coding, SpringBoot, DDD, code review, unit testing. Scope: does not cover frontend/scripting/pure documentation changes."
---

# Java Backend AI Coding Development Standards

> **Default role**: Senior technical expert. AI executes all tasks as a senior Java backend technical expert, delivering professional-grade solutions and code.
>
> **Positioning**: Universal Java backend project standards, applicable to Java backend projects using Spring Boot + DDD architecture. Project-level customization is handled through extension Skills that override parameters in this specification.
>
> **Conflict arbitration**: User explicit instructions > Project-level extension Skill > This Skill > Public Rules > Alibaba Java Coding Guidelines (Huangshan Edition) > Framework official documentation.
>
> **Loading method**: Default loading during Java backend project coding / review; technical specifications loaded on demand from corresponding documents in `references/`.
>
> **Loading scenarios**: New feature development, business logic modification, creating entity/DAO/Service/Controller, API design, code review, storage operations (MySQL/Redis/ES/MongoDB/HBase), unit test writing.
>
> **Non-loading scenarios**: Pure documentation changes (README/CHANGELOG), configuration file adjustments (yaml/properties non-code logic), Maven POM version sync (version number changes only, no plugin configuration changes).

**Quick routing**:

1. Identify the scenario (§6.1 routing table) → load the corresponding references (§5) → check 🔴 STOP conditions (§1.3) → execute
2. No scenario matches → take the default path (load `java-guide.md` + the corresponding storage guide) → record the Prompt characteristics for later addition to the routing table
3. Extension Skill unavailable → use base default parameters as fallback → notify the user and ask whether to install

**Path 1 criteria** (match any one): User Prompt contains one of the following keywords → Match §6.1 routing table #1-#8:
- New feature/requirement/module/architecture → #1 or #2
- Write code/implement API → #3
- Review/inspection → #4
- Unit test/add tests → #5
- Redis/ES/MongoDB/cache/search → #6
- Thread pool/concurrency/batch → #7
- Maven/dependency/version → #8

**Path 2 criteria** (must satisfy all): `git diff --name-only` ≤ 2 `src/main` files + does not involve `api/` path + no `*.sql`/DDL + no sensitive fields + no new `<dependency>` (see §1.2 for five objective criteria).

**Path 3 criteria**: The project declares a project-level extension Skill (e.g. a distinctive base package or BOM module indicates one) → Check whether the corresponding extension Skill is available (see §1.5).

**None satisfied** → Follow default path (load `java-guide.md` + corresponding storage guide).

**🔴 CHECKPOINT — Route confirmation**: After path selection, MUST confirm the following three items before proceeding:
1. Matched a specific number in §6.1 routing table (or explicitly following default path); if no match, record Prompt characteristics
2. Identified corresponding 🔴 STOP conditions, explicitly listing reference files to be loaded
3. Confirmed no project-level extension Skill is involved (Path 3), or extension Skill availability has been detected and handled

## 0. Project Parameter Conventions

> Content marked with `{placeholder}` in this Skill represents project-level configurable parameters. Project-level extension Skills **MUST** define default values for the following parameters; when undefined, use the universal defaults below.

| Parameter              | Default                 | Description                            |
| ---------------------- | ----------------------- | -------------------------------------- |
| `{basePackage}`        | `com.example.{project}` | Base package path                      |
| `{BizException}`       | `BizException`          | Business exception class name           |
| `{ResultCode}`         | `ResultCode`            | Error code enum class name              |
| `{ResponseWrapper}`    | `Result<T>`             | Single object response wrapper class    |
| `{PageResponse}`       | `PageResult<T>`         | Paginated response wrapper class        |
| `{ScrollResponse}`     | `ScrollResult<T>`       | Cursor scroll response wrapper class    |
| `{bomModule}`          | None                    | BOM module name (when using BOM mode)   |
| `{ConfigManager}`      | Config center API       | Configuration retrieval method          |
| `{AuditLogAnnotation}` | None                    | Audit log annotation (e.g. `@AuditLog`) |
| `{issuePrefix}`        | None                    | Branch Issue prefix                     |

> Project-level extension Skills override the placeholders above with project-specific values (e.g. a custom exception class or response wrapper). For the complete override list, see the corresponding project-level extension Skill. When no extension Skill is installed, base defaults are used as fallback.

---

## 1. SDD Development Workflow

**MUST NOT skip stages**: Each stage must first produce an Artifact and obtain user confirmation before proceeding to the next stage. When detailed design (`tasks.md`) is not completed, coding is prohibited.

### 1.1 Full Process (New feature / Architecture change / Public contract modification)

| Stage | Companion Skill | Input | Artifact (Output) | Stage Gate |
| ----- | --------------- | ----- | ----------------- | ---------- |
| Requirements analysis | `brainstorming` | PRD / verbal description | `spec.md` (What + Why + acceptance criteria) | User confirmation |
| High-level design | `brainstorming` + `writing-plans` | `spec.md` | `plan.md` (module breakdown, API contracts, data model) | Review passed |
| Detailed design | `writing-plans` | `plan.md` | `tasks.md` (executable task list with acceptance criteria) | User confirmation |
| Knowledge generation | Project-level extension Skill | `plan.md` + `tasks.md` | Knowledge entry draft + review request | Extension Skill gate |
| Coding | `java-backend-dev-guide` | `tasks.md` | Code + JavaDoc | LSP zero Errors |
| Unit testing | `test-driven-development` | Code + acceptance criteria | Test code + coverage ≥ 80% | All Pass |
| Acceptance | `verification-before-completion` | Code + tests + `spec.md` | Pass / issue list | User acceptance |

> Artifacts are stored uniformly in `docs/specs/{requirement-name}/`. Knowledge generation stage output location, naming, and gates are defined by the project-level extension Skill; when no extension Skill is installed, skip this stage and notify the user. See `references/sdd-guide.md` for detailed stage specifications.

### 1.2 Quick Path (Simple changes: single-file changes, no architecture/contract/security impact)

**Applicability conditions** (all must be satisfied to take the quick path; if any is not satisfied → 🔴 STOP fall back to §1.1):

| # | Condition | Objective criteria |
|---|-----------|-------------------|
| 1 | Changes ≤ 2 business files (excluding tests) | `git diff --name-only` output lines ≤ 2, all under `src/main` |
| 2 | No public contract changes involved | Modified files do not include classes under `api/` path; no new or field changes to `*DTO` / `*VO` / `*Request` / `*Response` / `ResultCode` classes |
| 3 | No storage Schema changes involved | No `*.sql` file modifications; no `@Table` / `@Column` annotation additions or deletions; no DDL statements |
| 4 | No security-sensitive fields involved | Modified fields do not contain sensitive keywords such as `password` / `token` / `secret` / `key` / `credential`; no authorization / encryption / data masking logic involved |
| 5 | No cross-module dependencies involved | The `pom.xml` of the modified file's module has no new `<dependency>` declarations; does not introduce server package classes from other `biz-{domain}` modules |

**Quick path reference loading whitelist**:

| Load | Do not load |
|------|-------------|
| `java-guide.md` (coding standards quick reference) | `sdd-guide.md` (no spec/plan/tasks needed) |
| Storage guide corresponding to target files (if SQL/Redis/ES involved) | `review-guide.md` (no five-dimension self-check needed) |
| — | `security-guide.md` (condition 4 excludes security scenarios) |
| — | `concurrency-guide.md` (quick path does not involve concurrency design) |
| — | `consistency-guide.md` (no cross-storage involved) |

> **Token budget reference**: Quick path expects ≤ 2 reference files loaded, Token consumption < 20% of full loading.

**Execution steps**:

1. Identify a simple change → check the five objective criteria above one by one
2. Load whitelisted references (if needed)
3. Code directly → modify the target files
4. Verify → `lsp_diagnostics` zero Errors
5. Report impact scope → list affected callers/modules
6. Done

**🔴 STOP**: When any condition is not satisfied, must fall back to full process §1.1.

### 1.5 Project-level Extension Skill Detection

> When a project declares a project-level extension Skill, MUST check whether it is available:

| Project characteristic | Detection method | Extension Skill | Behavior when unavailable |
|----------------------|-----------------|----------------|--------------------------|
| Project declares an extension Skill | Extension Skill declared in project config, or a distinctive base package / BOM module indicates a project-level extension | Corresponding extension Skill | Notify user of missing Skill, ask whether to install; use base default parameters as fallback to continue |

**Fallback rules**: When extension Skill is unavailable, MUST use base default parameters to complete the current task, MUST NOT silently skip without notifying the user.

### 1.3 Stage Blocking Rules 🔴

> **CHECKPOINT**: When the following blocking conditions are not satisfied, **STOP** — proceeding to the next stage is prohibited, must fix or fall back first.

| Stage transition | 🔴 Blocking condition | STOP behavior | Fallback action |
|-----------------|----------------------|---------------|----------------|
| Requirements → HLD | `spec.md` not confirmed by user | Stop outputting any technical solution | Ask the user each open question explicitly, wait for user decision |
| Requirements → HLD | Open questions list is non-empty | Stop proceeding to HLD | Confirm open questions one by one, only remove after user explicitly responds |
| HLD → LLD | `plan.md` has < 2 solutions | Stop task decomposition | Require ≥ 2 solution comparisons and ADR |
| HLD → LLD | Key API contracts undefined | Stop detailed design | Revert and supplement method signatures, parameters, return values, error codes |
| LLD → Coding | `tasks.md` has no acceptance criteria | Stop coding | Revert and add testable acceptance criteria for each task |
| LLD → Coding | Single task estimated > 4h | Stop coding | Split into smaller tasks, each ≤ half a day |
| Coding → Testing | `lsp_diagnostics` has Errors | Stop submitting for testing | Fix compilation errors, confirm LSP zero Errors |
| Coding → Testing | Violates §4 coding red lines | Stop submitting for testing | Fix each MUST NOT item |
| Testing → Acceptance | Unit tests not all Pass | Stop acceptance | Fix failing test cases, skipping or commenting out assertions is prohibited |
| Testing → Acceptance | Line coverage < 80% | Stop acceptance | Add test cases until standard is met |
| Testing → Acceptance | DomainService branch coverage < 100% | Stop acceptance | Add domain logic branch tests |
| Testing → Acceptance | Project-level extension Skill declares knowledge output as a hard gate, and its output command was not invoked or its validation script exit code is non-0 | Stop acceptance, prohibit submitting MR | Invoke extension Skill's knowledge output command, re-enter acceptance after validation passes; when no extension Skill, user explicitly confirms skip and records it |

### 1.4 SDD Workflow Failure Mode Fallback

> **If-then three-stage fallback**: When SDD stages encounter blockers, handle according to the following paths.

| Trigger condition | First-line fix | Still failing fallback |
|------------------|---------------|----------------------|
| Requirements analysis stage: user cannot confirm open questions (business side absent / decision delayed) | Record as "pending confirmation", annotate assumptions in spec.md, continue advancing | Degrade to quick path, implement minimum viable product (MVP) first, supplement in subsequent iterations |
| HLD stage: cannot find ≥ 2 feasible solutions (technical constraints too strong) | Record single-solution ADR, explain why no other choices, annotate risk points | Invite the architecture group to step in and review, pause current task until guidance is received |
| LLD stage: task decomposition still > 4h (high complexity) | Further decompose subtasks, identify parallelizable parts, annotate dependencies | Escalate to technical challenge, create Spike Task for dedicated research, not counted in normal development time |
| Coding stage: LSP keeps reporting errors and cause cannot be identified (dependency conflict / environment issue) | Clean Maven local repository (`mvn dependency:purge-local-repository`), rebuild | Fall back to last stable commit, create new branch to reapply changes, isolate the issue |
| Unit test coverage cannot reach 80% (legacy code / third-party dependencies hard to Mock) | Identify untestable code segments, request exemption (must explain reason in code review) | Lower gate to 70%, but MUST supplement integration tests covering core paths |
| Cross-module dependency conflict (module A upgrading DTO causes module B compilation failure) | Revert module A's changes, uniformly coordinate versions at the BOM layer, notify module B Owner to sync upgrade | Create cross-module upgrade Epic, each module Owner adapts in parallel then unified integration verification |
| Third-party API integration failure (API docs missing / sandbox unavailable / auth timeout) | Define Anti-Corruption Layer interface, decouple third-party dependency with Mock implementation | Pause integration, create Spike Task to research alternatives, invite architecture group review |
| `references/` file loading failure (path does not exist / insufficient permissions) | Try loading other available guide on the same topic; if no alternative, continue with baseline knowledge but MUST annotate "⚠️ reference missing" | Notify user of reference file missing, record in spec.md risk items, pause coding on that topic |
| §6.1 routing table: all 8 scenario categories do not match (user Prompt characteristics cannot be classified) | Follow default path: load `java-guide.md` + corresponding storage guide to continue | Record unmatched Prompt characteristics in spec.md, suggest user supplement routing table |
| Coding stage: design defect discovered (tasks.md missed key scenarios, impact > 3 files) | 🔴 STOP coding, assess impact scope; if impact ≤ 3 files, supplement in current task and update tasks.md | Impact > 3 files → fall back to HLD stage, update plan.md, re-decompose tasks |

> For middleware-related fallback (MapStruct / Dubbo / Redis etc.), see `middleware-guide.md`.

**🔴 STOP — Fallback exhausted, escalate process**:

When any of the following conditions are met, MUST stop coding and escalate:
- Same issue fails fallback 2 consecutive times
- Blocker exceeds 1 working day with no progress
- Cross-team dependency involved (other module Owner unresponsive ≥ 2 days)

Escalation steps:
1. Record in `spec.md` or `tasks.md`: blocker cause + attempted fallbacks + impact scope
2. Notify technical lead (with link to above record)
3. Switch to other unblocked tasks, prohibit idle waiting

---

## 2. Engineering Architecture Overview

### 2.1 Universal DDD Layered Architecture

```
{project}/
├── {bomModule}         # Version management (all jar versions declared here; sub-modules MUST NOT hardcode versions)
├── {buildModule}       # Build resources package (checkstyle rule files, etc.)
├── {coreModule}        # Public contract layer (exceptions, DTOs, response models, constants)
├── {utilModule}        # Stateless utilities (reuse first, prohibit reinventing the wheel)
├── {dalModule}/        # Storage adaptation layer (mysql / redis / es / hbase / mongo, as needed)
├── {bootModule}/       # Startup auto-configuration (Spring Boot Starter)
├── {moduleDir}/        # Business modules (DDD+COLA domain implementation)
│   └── biz-{domain}/
│       ├── api/        # External API definitions + DTOs
│       ├── client/     # RPC client
│       └── server/     # Domain implementation (controller / service / domain / repository)
└── {appModule}         # SpringBoot application-layer service
```

> Project-level extension Skills **MUST** define concrete module naming. When undefined, follow the universal pattern above.

### 2.2 DDD+COLA Package Structure

> For package naming conventions, layer responsibilities, and suffix conventions, see `references/java-guide.md §1`.

Module design principle: Split modules by DDD domain (`biz-xxx/api`, `biz-xxx/server`), prohibit splitting by technical responsibility into traditional `web`, `service`, `dal`, `common` structures.

---

## 3. Architecture Design Standards

Call chain is strictly unidirectional, **MUST NOT** call across layers:

```
Controller → ApplicationService → DomainService → Repository (interface)
                                                          ↓
                                                 RepositoryImpl / DAO
```

> For layer responsibilities, package naming conventions, and complete DDD+COLA structure: `references/java-guide.md`
>
> For architecture compliance checklist (call chain direction, anti-corruption layer, DO exposure, etc.): `references/review-guide.md §2`

---

## 4. Core Coding Constraints

> For naming conventions, error code standards, and specific constraints: `references/java-guide.md`
>
> For general coding conventions (method line count, JavaDoc, dependency injection, transactions, log levels, etc.), follow "Alibaba Java Coding Guidelines (Huangshan Edition)".

When coding, **MUST** first load `references/java-guide.md` (contains all coding red lines and anti-examples) before starting.

**🔴 CHECKPOINT — Pre-coding confirmation**: Before starting coding, MUST confirm each item:
1. Route path has been determined (§6.1 #1-#8 or default path), reference files loaded
2. For full path: `tasks.md` exists and each task has acceptance criteria; if not → 🔴 STOP fall back to detailed design
3. For quick path: §1.2 five conditions checked and passed one by one
4. Security-sensitive inputs identified (user input / file upload / external API returns), code generation security gate is ready

**Routing rules**:
- Naming / error codes / layering / conversion / response / dependencies → `references/java-guide.md`
- Anti-pattern self-check (coding / architecture / security / testing / workflow) → `references/antipatterns.md`
- General coding conventions (method line count / JavaDoc / transactions / logging) → Alibaba Java Coding Guidelines (Huangshan Edition)

### 4.1 AI Anti-Example Blacklist 🔴

> **MUST** self-check against the following 5 categories of anti-patterns before coding. Hitting any one → stop immediately and correct. Complete anti-example catalog → `references/antipatterns.md`.

| Category | 🔴 Absolutely prohibited | Correct approach | ⚠️ Gray area (requires judgment) |
|----------|------------------------|-----------------|-------------------------------|
| Coding | `BeanUtils` / field injection / empty catch / `new ThreadPoolExecutor` / DB in for loop | MapStruct / constructor injection / throw or log+rethrow / project thread pool / batch query | Prototype validation scripts may use BeanUtils (must not enter production code); utility class static methods exempt from constructor injection |
| Architecture | Package by technical responsibility / Controller directly calls DAO / DO exposed in API / sub-module hardcoded versions | DDD domain splitting / strict layering / DO→DTO→VO / BOM manages versions | Pure CRUD queries can skip VO layer and return DTO directly; internal scheduled task modules can simplify layering |
| Security | SQL concatenation / extension-only validation / hardcoded credentials / deserialization without whitelist / Prompt injection | Parameterization / file header validation / config center / type whitelist / input isolation | Test code may use `@Value` injection for test values (MUST read from environment variables, prohibit hardcoding) |
| Testing | Implement first then add tests / Mock internal logic / hardcoded credentials / `@Ignore` to skip failures | TDD / only Mock external boundaries / environment variable injection / fix root cause | Legacy code refactoring can add integration tests first then split into unit tests (must annotate migration plan) |
| Workflow | Code directly upon receiving requirements / single solution / task > 4h / no acceptance criteria / starting work on a vague requirement | 🔴 STOP spec first / ≥ 2 solutions / split to ≤ half day / Given-When-Then / follow up for clarification | Hotfix (P0/P1) can skip spec but MUST supplement change description; 1-line config changes can skip solution comparison |

**🔴 Five red lines quick reference** (hitting any one = Code Review direct failure):

1. ❌ `@Autowired` field injection → ✅ Constructor injection
2. ❌ `BeanUtils.copyProperties` → ✅ MapStruct Converter
3. ❌ SQL string concatenation → ✅ `#{}` parameterization / QueryBuilder
4. ❌ `new ThreadPoolExecutor` → ✅ Project unified thread pool Bean
5. ❌ Single task > 4h without splitting → ✅ Split to ≤ half day, with Given-When-Then acceptance criteria

---

## 5. Quick Reference

| Scenario | Document |
|----------|----------|
| SDD stage Artifact templates and specifications (requirements analysis, solution design) | `references/sdd-guide.md` |
| Stage quality gates and Maven plugin gates | `references/quality-gate.md` |
| Code review (AI check items, manual must-check, Comment format) | `references/review-guide.md` |
| Java coding (error code standards, DDD layering, naming conventions) | `references/java-guide.md` |
| Middleware (Dubbo / RabbitMQ / scheduled tasks / logging / ORM / circuit breaker degradation) | `references/middleware-guide.md` |
| Concurrent programming (thread pool template / CF async chain / distributed locks) | `references/concurrency-guide.md` |
| API design (response format, Swagger, parameter validation) | `references/api-guide.md` |
| Data security (encryption levels, injection prevention, config security, code generation security gate) | `references/security-guide.md` |
| Unit testing (TDD workflow, Mock strategy, coverage gates) | `references/test-guide.md` |
| MySQL / MyBatis-Plus / ShardingSphere | `references/mysql-guide.md` |
| Redis (caching, distributed locks) | `references/redis-guide.md` |
| Elasticsearch (index design, pagination strategy) | `references/es-guide.md` |
| MongoDB document storage | `references/mongo-guide.md` |
| HBase mass storage | `references/hbase-guide.md` |
| Cross-storage data consistency (MySQL→ES sync, cache consistency, compensation mechanisms) | `references/consistency-guide.md` |
| Performance benchmarking (target definition, gates, JMH micro-benchmarks) | `references/perf-benchmark-guide.md` |
| Observability (logging standards, metric instrumentation, distributed tracing, health checks) | `references/observability-guide.md` |
| Knowledge base construction (layered architecture, maintenance mechanisms, Rule/Skill governance, effectiveness measurement) | Project-level extension Skill |
| Maven engineering standards (BOM / plugin inheritance / APT / Profile) | `references/maven-guide.md` |
| Git standards (Git Flow branch strategy / Angular Commit) | `references/git-guide.md` |
| AI anti-example blacklist (coding/architecture/security/testing/workflow anti-patterns) | `references/antipatterns.md` |

### 5.1 SDD Stage → Reference Loading Mapping

> Load corresponding references by SDD stage, avoid loading all at once.

| SDD Stage | Must load | Load as needed | Prohibited from loading |
|-----------|-----------|---------------|----------------------|
| Requirements analysis | `sdd-guide.md` | — | Coding detail docs (java-guide / storage guides) |
| HLD | `sdd-guide.md` + `api-guide.md` | Storage guides (based on technology selection decisions) | Coding detail docs |
| LLD | `sdd-guide.md` + `api-guide.md` | Storage guides + `quality-gate.md` | — |
| Coding | `java-guide.md` + the corresponding storage guide | `middleware-guide.md` (if middleware involved) | `sdd-guide.md` (design already completed) |
| Unit testing | `test-guide.md` | `quality-gate.md` (coverage gates) | Coding detail docs |
| Acceptance | `quality-gate.md` + `review-guide.md` | `security-guide.md` (security-related changes) | — |
| Code review | `review-guide.md` + `security-guide.md` + `java-guide.md` | `antipatterns.md` | `sdd-guide.md` |
| Quick path | `java-guide.md` | The corresponding storage guide (if involved) | `sdd-guide.md` / `review-guide.md` / `security-guide.md` / `concurrency-guide.md` |

### 5.2 References Dependency Graph

> When loading by scenario, must also load associated documents pointed to by arrows in the graph. Avoid missing associated constraints.

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

observability-guide (standalone, loaded on demand)
perf-benchmark-guide (standalone, loaded on demand)
```

**Loading rules**: When loading a document, **MUST** also load its downstream documents pointed to by arrows. Example: When loading `review-guide`, must also load `security-guide` + `java-guide`.

---

## 6. Typical Usage Examples

> After AI loads this Skill, match the scenarios in the table below based on user Prompt, and execute according to "AI first response". **MUST NOT** skip the prerequisite steps listed in the table.

### 6.1 Scenario Routing Table

> **Matching priority**: Match in # order, execute on first match.

| # | Judgment condition | Prompt characteristics | Load references | 🔴 Blocking / AI first response |
|---|-------------------|----------------------|----------------|-------------------------------|
| 1 | Involves new feature / new module / architecture change | "Add XX feature" / "Help me do XX requirement" | `sdd-guide.md` | 🔴 STOP: First produce `spec.md` (with acceptance criteria + non-functional requirements + open questions), prohibit writing code directly. After design completion MUST proceed to §1.1 "Knowledge generation" stage (identification rules see project-level extension Skill) |
| 2 | Involves solution selection / architecture decision | "Design XX solution" / "How to choose XX architecture" | `sdd-guide.md` + `api-guide.md` | 🔴 STOP: Require ≥ 2 solution comparisons + ADR, prohibit listing only one solution. After ADR completion MUST proceed to §1.1 "Knowledge generation" stage |
| 3 | Writing specific implementation code | "Write XX code" / "Implement XX API" | `java-guide.md` + the corresponding storage guide | 🔴 STOP: Check whether `tasks.md` exists; if not, fall back to detailed design |
| 4 | Reviewing existing code | "Review" / "Look at this code" | `review-guide.md` + `security-guide.md` | Output item by item according to five-dimension self-check (architecture/coding/exception-transactions/security/testing) |
| 5 | Writing or supplementing tests | "Write unit tests" / "Add tests" | `test-guide.md` | 🔴 STOP: TDD workflow — write failing test first → minimal implementation → refactor; prohibit implementing first then adding tests |
| 6 | Involves storage operations (cache/search/documents) | "Add Redis cache" / "ES search" | The corresponding storage guide + `consistency-guide.md` | 🔴 STOP: First confirm consistency strategy (Cache-Aside / Write-Through / async sync) before coding |
| 7 | Involves concurrency / threads / batch processing | "Concurrency issue" / "Thread pool" / "Batch processing" | `concurrency-guide.md` | 🔴 STOP: Use project thread pool template + distributed locks, prohibit `new ThreadPoolExecutor` on your own |
| 8 | Involves Maven / dependency management | "Maven" / "Dependencies" / "Versions" | `maven-guide.md` | 🔴 STOP: Under BOM, hardcoding versions is prohibited; new dependencies MUST be reviewed by architecture group |
| Default | None of the above 8 categories match | Other Java backend questions | `java-guide.md` + the corresponding storage guide | Follow default path to continue; record Prompt characteristics and suggest supplementing routing table |

### 6.2 Complete Interaction Examples

> The following examples show the **complete dialogue flow** for AI in each scenario. For specific coding rules, see the corresponding reference guide.

**Example 1: New feature development**

```
用户：帮我新增文章收藏功能 (User: Help me add an article-favorites feature)

AI 首次响应： (AI first response:)
🔴 STOP → 加载 sdd-guide.md (load sdd-guide.md)
按六维度逐项澄清（功能边界 / 用户场景 / 异常边界 / 并发场景 / 非功能需求 / 验收标准） (Clarify item by item across six dimensions: feature scope / user scenarios / exception boundaries / concurrency scenarios / non-functional requirements / acceptance criteria)
输出 spec.md 框架，禁止写代码 (Output the spec.md skeleton; prohibit writing code)
```

**Example 2: Code review**

```
用户：帮我 Review 这段代码 (User: Help me review this code)

AI 响应： (AI response:)
加载 review-guide.md + security-guide.md + java-guide.md (load review-guide.md + security-guide.md + java-guide.md)
按五维自检逐项输出： (Output item by item according to the five-dimension self-check:)
- 架构：[缺陷] 文件名:行号 MUST-FIX (Architecture: [defect] filename:line MUST-FIX)
- 编码：[缺陷] 文件名:行号 SUGGEST (Coding: [defect] filename:line SUGGEST)
- 异常事务：[缺陷] ... (Exception-transactions: [defect] ...)
- 安全：[缺陷] ... (Security: [defect] ...)
- 测试：[缺陷] ... (Testing: [defect] ...)
```

**Example 3: Quick path**

```
用户：给 ArticleMapper.xml 加 is_deleted=0 (User: Add is_deleted=0 to ArticleMapper.xml)

AI 响应： (AI response:)
评估满足快速路径 5 项条件 → 直接修改 (Assess that the 5 quick-path conditions are satisfied → modify directly)
输出 diff（修改前/修改后） (Output diff — before / after modification blocks)
确认 LSP 零 Error → 列出受影响调用方 (Confirm LSP zero Errors → list affected callers)
```

**Example 4: Security scenario**

```
用户：写创建评论接口，用户输入保存到 DB (User: Write a create-comment API that saves user input to the DB)

AI 首次响应： (AI first response:)
🔴 STOP → 加载 security-guide.md (load security-guide.md)
代码生成安全门 7 项逐条确认（SQL 参数化 / XSS 过滤 / ...） (Confirm the 7 code-generation security gate items one by one: SQL parameterization / XSS filtering / ...)
用户确认后再编码 (Code only after user confirmation)
```

**Example 5: Concurrency scenario**

```
用户：批量处理 10000 条订单 (User: Batch-process 10000 orders)

AI 首次响应： (AI first response:)
🔴 STOP → 加载 concurrency-guide.md (load concurrency-guide.md)
确认线程池 / 幂等 / 重试 / 超时策略 (Confirm thread pool / idempotency / retry / timeout strategy)
使用项目线程池 + 分布式锁 (Use the project thread pool + distributed lock)
```

### 6.3 Self-Check Verification Checklist

> After AI completes the response for any of the above scenarios, **MUST** self-check against the following checklist item by item. Only when all pass can "complete" be declared.

| Scenario | Check item | Verification method |
|----------|-----------|-------------------|
| #1 New feature | First response contains no code (Java/XML/YAML) | Search output for no `class` / `@Service` / `<mapper` / `application.yml` |
| #1 New feature | Clarified item by item across six dimensions | 功能边界 / 用户场景 / 异常边界 / 并发场景 / 非功能需求 / 验收标准 (feature scope / user scenarios / exception boundaries / concurrency scenarios / non-functional requirements / acceptance criteria) each ≥ 1 item |
| #1 New feature | Uses 🔴 STOP marker | Output contains `🔴 STOP` or `🔴 阻断` |
| #1 New feature | Knowledge generation stage explicitly handled | Output contains "knowledge output executed" or "no knowledge output this time + reason"; when no extension Skill, contains "skip knowledge generation" notification |
| #2 Architecture | ≥ 2 solution comparisons + ADR | Output contains "方案 A / 方案 B" (Solution A / Solution B) + comparison table + recommendation conclusion; ADR (架构决策记录) recorded |
| #3 Coding | `tasks.md` existence check | Output contains "tasks.md confirmed" or 🔴 STOP fallback |
| #3 Coding | Code has no §4.1 blacklist hits | Search output for no `BeanUtils` / `@Autowired` / SQL concatenation |
| #4 Review | Five-dimension self-check 100% coverage | 架构/编码/异常事务/安全/测试 (Architecture/Coding/Exception-transactions/Security/Testing) five top-level headings all appear |
| #4 Review | Each defect contains file path + line number | Format matches `filename:line` |
| #4 Review | MUST-FIX includes fix plan | Each MUST-FIX is immediately followed by its own "修复：" / "建议：" (Fix: / Suggestion:) line |
| #5 Testing | TDD workflow (red → green → refactor) | Output first contains failing test → then contains minimal implementation → finally contains refactored code |
| #5 Testing | Coverage ≥ 80% | Output contains coverage declaration or `mvn jacoco:check` passes |
| #6 Storage | Consistency strategy confirmed | Output contains one of Cache-Aside / Write-Through / async sync |
| #7 Concurrency | Uses project thread pool | Code has no `new ThreadPoolExecutor`, references project Bean |
| #7 Concurrency | Idempotency + retry considered | Output contains idempotency key generation method + retry strategy description |
| #8 Maven | No hardcoded versions under BOM | New `<dependency>` has no `<version>` tag |
| Quick path | Did not output spec.md/plan.md/tasks.md | Search output for no above three filenames |
| Quick path | Changes contain diff (before/after) | Output contains the `修改前` + `修改后` (before / after modification) code blocks, or a `diff` block |
| Quick path | Affected callers listed | Output contains caller file path list |
| Security | Code generation security gate 7 items confirmed one by one | All 7 items appear (including "not involved" markers) |
| Security | User input filtered for XSS/injection/sensitive fields | Code contains sanitize/detect/validate calls |

**🔴 CHECKPOINT — Post-change verification**: After code changes, MUST confirm each item:
1. `mvn compile -q` passes / LSP zero Errors
2. Affected callers/modules listed (quick path MUST execute)
3. Drift detection executed (new public API / changed config items / new dependencies)

### 6.4 Non-SDD Scenario Blocking Rules 🔴

> The following scenarios, while not going through the complete SDD workflow, still have blocking conditions.

| Scenario | 🔴 Blocking condition | STOP behavior | Fallback action |
|----------|----------------------|---------------|----------------|
| Direct coding (no spec.md) | User has not explicitly stated "skip SDD" | Stop coding, prompt to follow SDD workflow | Ask the user whether they confirm skipping SDD; only after they confirm, follow the quick path |
| Code review | Review comments not responded to item by item | Stop merging PR | Respond to each MUST-FIX/SUGGEST/NIT item by item |
| Security-related changes | security-guide §6 self-check not executed | Stop committing | Complete security self-check checklist item by item |
| Storage Schema changes | Not reviewed | Stop executing DDL | Submit for DBA/architecture group review |
| Dependency introduction | Not declared in BOM | Stop using that dependency | First add to BOM and submit for review |

---

## 7. Technology Selection Decision Guide

> The following decision trees have been migrated to corresponding reference guides, load as needed.

| Decision scenario | Reference document |
|------------------|-------------------|
| Storage selection (data type/volume/read-write ratio/consistency) | Each storage-guide.md + `consistency-guide.md` |
| Design pattern selection (strategy / factory / whether the design is over-engineered) | `java-guide.md` |
| Concurrency solution (thread pool/distributed lock/retry strategy) | `concurrency-guide.md` + `redis-guide.md` |
| Exception handling (business exception/system exception/degradation/alerting) | `java-guide.md` + `security-guide.md` |
