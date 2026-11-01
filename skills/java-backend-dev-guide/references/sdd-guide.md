# SDD Development Workflow Standards

> **Summary**
>
> - **Core constraint**: AI is advisor not decision-maker; spec.md must contain acceptance criteria + non-functional requirements + open questions (all resolved before considered complete); plan.md must have ≥ 2 solution comparisons + ADR; tasks.md single task ≤ half day and must contain acceptance criteria
> - **Key thresholds**: Single task estimated ≤ 4h, solution comparisons ≥ 2, spec acceptance criteria each independently testable
> - **Common violations**: Cross-stage jumping, spec.md missing non-functional requirements, plan.md listing only one solution, tasks.md without acceptance criteria

This document provides detailed specifications for each stage of SKILL.md §1 SDD workflow.

---

## 1. Requirements Analysis

### 1.1. AI Role Positioning

AI is an **advisor, not decision-maker**. Responsibilities: enumerate boundary conditions, clarify ambiguous requirements, identify technical risks; all directional judgments must be confirmed by a human.

### 1.2. Trigger Method

```
加载 brainstorming Skill，向 AI 描述需求背景与初步想法。
```

### 1.3. Questions AI MUST Proactively Clarify

Before producing `spec.md`, AI must confirm the following dimensions, proactively ask if missing; open questions are recorded separately in the "Open questions" section of spec.md:

| Dimension | Clarification points |
|-----------|---------------------|
| Feature scope | Which features are in scope for this round, which explicitly excluded |
| User scenarios | Who uses it in what scenario, what is the core need |
| Exception boundaries | Expected behavior when input is null or empty / exceeds limits |
| Concurrency scenarios | Expected behavior under concurrency / peak load / duplicate submission |
| Non-functional requirements | Performance targets, data scale (order of magnitude), compatibility requirements, SLA |
| Acceptance criteria | How to judge "done" and "done correctly" |

### 1.4. spec.md Template

```markdown
## 背景与目标

<!-- 一句话说明为什么要做，解决什么问题 -->

## 用户故事

<!-- As a [用户]，I want [功能]，So that [价值] -->

## 功能范围

### In Scope

### Out of Scope

## 验收标准

<!-- 每条标准必须可测试，推荐 Given-When-Then 格式 -->

- [ ] Given ... When ... Then ...

## 非功能需求

- 性能：
- 安全：
- 兼容性：

## 开放问题

<!-- 尚未确认、需要决策的事项，确认后删除对应条目 -->
```

### 1.5. Stage Constraints

- **MUST NOT** output any technical solution or code before `spec.md` is confirmed by user
- **MUST NOT** skip non-functional requirements (performance, security are commonly omitted)
- **MUST** all open questions resolved before marking requirements analysis complete ("resolved" defined as: user explicitly replies with decision in conversation, or AI has received clear requirement description making the question no longer applicable; **MUST NOT** have AI mark open questions as resolved on its own)
- **MUST** read `GLOSSARY.md` and `ARCHITECTURE.md` before writing `spec.md`
- **MUST NOT** directly output `spec.md` without reading above documents

---

## 2. High-Level Design (HLD)

### 2.1. Objective

Clarify module division and API contracts, provide basis for tasks.md decomposition.

### 2.2. plan.md Must Include

| Section | Content requirements |
|---------|---------------------|
| Solution comparison | ≥ 2 feasible solutions, list respective pros/cons and applicable conditions |
| Architecture decision | Selected solution and reasons, record reasons for rejected solutions (ADR) |
| Module division | Involved modules / services, responsibility boundary description |
| API contracts | Key API method signatures, parameters, return values, error codes |
| Data model | Core table structures / document structures / cache key designs |
| Risks and dependencies | External dependencies, technical risks, degradation strategies |

### 2.3. plan.md Markdown Template

```markdown
## 一、方案对比

| 方案   | 优点 | 缺点 | 适用条件 |
| ------ | ---- | ---- | -------- |
| 方案 A | ...  | ...  | ...      |
| 方案 B | ...  | ...  | ...      |

## 二、架构决策（ADR）

**选定方案**：方案 X

**理由**：...

**被否决方案**：方案 Y — 原因：...

## 三、模块划分

| 模块 | 职责 | 影响范围 |
| ---- | ---- | -------- |
| ...  | ...  | ...      |

## 四、接口契约

### `{ServiceName}.{methodName}()`

| 参数 | 类型 | 说明 |
| ---- | ---- | ---- |
| ...  | ...  | ...  |

**返回值**：`{ResponseWrapper}<XxxVO>`

**错误码**：`{ResultCode}.XXX`

## 五、数据模型

<!-- 核心表结构 / 缓存 Key / 文档结构 -->

## 六、风险与依赖

| 风险 | 影响 | 降级策略 |
| ---- | ---- | -------- |
| ...  | ...  | ...      |
```

### 2.4. Technology Selection Evaluation Dimensions

When doing technology selection, AI must analyze from the following dimensions, must not select based on inertia alone:

1. **Reuse first**: Whether existing components satisfy requirements
2. **Team familiarity**: Learning and maintenance cost of introducing new technology
3. **Performance and capacity**: Whether data volume, QPS match
4. **Operations cost**: Complexity of monitoring, alerting, troubleshooting
5. **Long-term evolution**: Whether technology selection is locked in, future extensibility

### 2.5. Stage Constraints

- **MUST NOT** list only one solution in comparison
- **MUST NOT** enter detailed design before API contracts defined
- **MUST** wait for architecture review to pass before entering next stage
- **MUST** read `ARCHITECTURE.md` and `API-CONTRACTS.md` before outputting `plan.md`
- **SHOULD** read `CONFIGURATION.md` when configurable logic is involved
- **MUST** load corresponding Skill refs as needed during detailed design (such as `java-guide.md`, `api-guide.md` etc.)

---

## 3. Detailed Design (LLD)

### 3.1. Objective

Decompose `plan.md` into atomic tasks that AI can execute one by one, each task independent and verifiable.

### 3.2. tasks.md Standards

**Task granularity**: Each task estimated effort ≤ half day (4h), independently implementable and testable.

**Each task must include:**

```markdown
### Task N：{动词 + 名词，描述做什么}

**目标**：一句话说明本 task 的交付物
**优先级**：P0（核心链路）/ P1（重要）/ P2（增强）
**前置条件**：依赖哪些 task 完成（并行 / 串行）
**实现步骤**：

1. ...
2. ...
   **验收条件**：

- [ ] ...
- [ ] ...
```

**Task relationship annotation**:

```markdown
<!-- 串行（必须按序）-->

Task 1 → Task 2 → Task 3

<!-- 并行（可同时进行）-->

Task 1 ┬→ Task 2
└→ Task 3
→ Task 4（合并后）
```

### 3.3. Stage Constraints

- **MUST NOT** have tasks without acceptance criteria
- **MUST NOT** task granularity too large (single task exceeding half day must be forcibly split)
- **MUST** wait for user to confirm `tasks.md` before starting coding
- **MUST** read corresponding module's `docs/{module}.md` before decomposing tasks, understand responsibility boundaries
- **MUST** decompose tasks involving public APIs against `API-CONTRACTS.md`

---

## 4. End-to-End Example

### 4.1. Scenario: Article Publishing Feature

#### 4.1.1. spec.md (Requirements Analysis Output)

```markdown
## 背景与目标

作者需要发布文章，发布后文章对外可见，同时需要通知关注者。

## 用户故事

As a 内容作者，I want 发布文章后文章立即对外可见，So that 读者可以搜索和阅读。

## 验收标准

- [ ] Given 作者已登录且文章内容不为空 When 点击发布 Then 文章状态变为"已发布"、发布时间被记录
- [ ] Given 文章内容为空 When 点击发布 Then 返回 PARAM_INVALID 错误
- [ ] Given 作者不存在 When 点击发布 Then 返回 AUTHOR_NOT_FOUND 错误

## 非功能需求

- 性能：发布接口 P99 < 200ms
- 安全：仅文章作者本人可发布

## 开放问题

（已全部解决）
```

#### 4.1.2. plan.md (HLD Output, excerpt)

```markdown
## 一、方案对比

| 方案 | 优点 | 缺点 |
| 同步发布 | 简单直接 | 发布耗时影响响应 |
| 异步发布+回调 | 响应快 | 实现复杂度高 |

## 二、架构决策

**选定方案**：同步发布（首版 MVP，数据量可控）
**理由**：当前 QPS < 100，同步方案足够

## 四、接口契约

### `ArticleApplicationService.publish(Long articleId)`

| 参数 | 类型 | 说明 |
| articleId | Long | 文章 ID |
**返回值**：`{ResponseWrapper}<ArticleVO>`
**错误码**：`ARTICLE_NOT_FOUND` / `PARAM_INVALID`
```

#### 4.1.3. tasks.md (LLD Output)

```markdown
### Task 1：创建 Article 实体与 Repository

**目标**：ArticleDO、ArticleRepository 接口与实现
**优先级**：P0
**前置条件**：无
**验收条件**：

- [ ] ArticleDO 包含 id/title/content/authorId/status/publishTime 字段
- [ ] ArticleRepository 接口定义 findById / save 方法
- [ ] ArticleRepositoryImpl 使用 ArticleDao 实现

### Task 2：实现发布业务逻辑

**目标**：ArticleApplicationService.publish() 方法
**优先级**：P0
**前置条件**：Task 1 完成
**验收条件**：

- [ ] 作者不存在时抛 ARTICLE_NOT_FOUND
- [ ] 内容为空时抛 PARAM_INVALID
- [ ] 发布后 status=2、publishTime 非空
- [ ] 返回 {ResponseWrapper}<ArticleVO>

### Task 3：编写发布单元测试

**目标**：ArticleApplicationServiceTest 覆盖正常/异常分支
**优先级**：P0
**前置条件**：Task 2 完成
**验收条件**：

- [ ] 测试作者不存在场景
- [ ] 测试内容为空场景
- [ ] 测试正常发布场景
- [ ] 全部通过
```

---

## 5. Knowledge Base Reference Constraints by Stage

> This chapter constrains "referencing existing knowledge"; "producing new knowledge" (scenario identification, draft standards, disk location and gates for the knowledge generation stage) is defined by project-level extension Skill, see §6.

### 5.1. Reference Constraint Quick Reference Table

| SDD Stage | Must-read documents | Load on demand Skills | Prohibited behavior |
|-----------|-------------------|---------------------|-------------------|
| Requirements analysis | `GLOSSARY.md` + `ARCHITECTURE.md` | `brainstorming` | Writing `spec.md` without reading documents |
| HLD | `ARCHITECTURE.md` + `API-CONTRACTS.md` | Design pattern related refs | Listing only one solution |
| LLD | `docs/{module}.md` + `API-CONTRACTS.md` | Tech stack related refs | Tasks without acceptance criteria |
| Knowledge generation | `plan.md` + `tasks.md` (this requirement's output) | Project-level extension Skill | Silently skipping this stage without recording reason |
| Coding | `docs/{module}.md` + `API-CONTRACTS.md` | `java-guide` / `middleware-guide` etc. | Referencing unverified symbols |
| Testing | `spec.md` + `API-CONTRACTS.md` | `test-guide.md` | Tests not covering acceptance criteria |

> "Must-read documents" in the table refers to **in-repository documents**. Team knowledge base (independent document repository) retrieval and referencing has deterministic entry points provided by the project-level extension Skill; the base does not mandate its retrieval method — knowledge base location, Schema, and timeliness criteria are all the project's own business.

---

## 6. Knowledge Generation (Extension Point)

> This base **does not define** knowledge entry output specifications — entry Schema, naming, disk location, scenario identification rules, and validation scripts all strongly depend on specific knowledge base repositories, writing them into the base would cause other projects to copy inapplicable contracts.

**What the base specifies**:

- SDD workflow has a "knowledge generation" stage after `plan.md` confirmation, **MUST** explicitly handle: when scenarios hit, invoke project-level extension Skill's output command; when not hit, record "no knowledge output this time + reason" in `tasks.md`. **MUST NOT** silently skip.
- The artifact gate for this stage belongs to "testing → acceptance" blocking conditions (SKILL.md §1.3 "Stage Blocking Rules"), validation conclusions only recognize script exit codes, not executor self-reports.

**What is defined by project-level extension Skill**: Identification rules, entry Schema and templates, authoritative-source resolution, directory and numbering rules, validation commands, MR format. See the corresponding project-level extension Skill for its concrete knowledge-generation contract.

**When extension Skill is unavailable**: Inform user "skipping knowledge generation stage this time" and explain reason, record in `tasks.md`, **MUST NOT** use this base's assumptions to replace extension Skill output entries.
