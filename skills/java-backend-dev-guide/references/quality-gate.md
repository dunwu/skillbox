# Quality Gate Standards

> **Summary**
>
> - **Core constraint**: 6-stage gates (requirements → design → coding → testing → acceptance → release) + Maven plugin gates (enforcer / checkstyle / PMD P3C), blocking items not satisfied MUST NOT proceed to next stage; AI MUST check corresponding stage blocking items one by one before claiming stage completion
> - **Key thresholds**: Core business branch coverage = 100%, overall line coverage ≥ 80%, no commented-out assertions or skipped tests; Maven gates all enabled by default (`-Ddev` local mode exempted)
> - **Common violations**: Declaring stage complete without checking gates item by item, recommendation items not satisfied without stating reasons, launch missing gray-release/rollback/monitoring plan, sub-modules hardcoding dependency versions, introducing bannedDependencies

Each development stage has clear exit criteria. When **blocking items** are not satisfied, proceeding to the next stage is prohibited; when **recommendation items** are not satisfied, reasons must be stated and technical debt recorded.

> **Cross-reference note**: `→ {filename} §{section}` paths in this document are all relative to the `references/` directory.

---

## 1. Stage Gate Standards

### 1.1. Requirements Analysis → High-Level Design

| Type | Standard |
|------|----------|
| 🔴 Blocking | `spec.md` sections complete (background, user stories, scope, acceptance criteria, non-functional requirements) |
| 🔴 Blocking | Each acceptance criterion independently testable (no vague expressions like "system runs normally") |
| 🔴 Blocking | Open questions list is empty (all pending items decided) |
| 🟡 Recommendation | Product / business side has signed off on `spec.md` |

---

### 1.2. High-Level Design → Detailed Design

| Type | Standard |
|------|----------|
| 🔴 Blocking | `plan.md` contains ≥ 2 solution comparisons and selection decision |
| 🔴 Blocking | Key API contracts defined (method signatures, parameters, return values, error codes) |
| 🔴 Blocking | Core data model designed (table structure / cache keys / document structure) |
| 🔴 Blocking | Architecture review passed (changes involving public contracts must have review records) |
| 🟡 Recommendation | Architecture decisions recorded in ADR (including reasons for rejected solutions) |

---

### 1.3. Detailed Design → Coding

| Type | Standard |
|------|----------|
| 🔴 Blocking | `tasks.md` each task contains objectives, steps, acceptance criteria |
| 🔴 Blocking | Single task estimated effort ≤ half day (must split if exceeding) |
| 🔴 Blocking | Task dependencies (serial / parallel) clearly annotated |
| 🟡 Recommendation | Technical review passed (changes involving storage Schema must be reviewed) |

---

### 1.4. Coding → Unit Testing

| Type | Standard |
|------|----------|
| 🔴 Blocking | Compilation passes: when IDE available `lsp_diagnostics` has no Error-level diagnostics; when IDE unavailable `mvn compile -q` passes |
| 🔴 Blocking | `→ review-guide.md §2` AI auto-check items all pass |
| 🟡 Recommendation | `lsp_diagnostics` has no Warning-level diagnostics |

---

### 1.5. Unit Testing → Acceptance

| Type | Standard |
|------|----------|
| 🔴 Blocking | All unit tests Pass |
| 🔴 Blocking | Overall line coverage ≥ 80% |
| 🔴 Blocking | Core business branches (DomainService / Domain layer) coverage = 100% |
| 🔴 Blocking | No commented-out assertions or skipped test cases |
| 🟡 Recommendation | Integration tests cover critical paths |

---

### 1.6. Acceptance → Merge / Release

| Type | Standard |
|------|----------|
| 🔴 Blocking | `spec.md` acceptance criteria checked item by item, all pass |
| 🔴 Blocking | No P0 / P1 defects unresolved |
| 🔴 Blocking | Code Review all `MUST-FIX` items fixed |
| 🔴 Blocking | Public contract changes notified to downstream teams |
| 🟡 Recommendation | Performance benchmark test results meet non-functional requirements |
| 🔴 Blocking | Launch Checklist completed (gray-release strategy, rollback plan, monitoring alerts) |

---

## 2. Maven Plugin Quality Gates

Three static analysis plugins integrated in build pipeline, enforced before merging to main branch. All plugins declared uniformly in root POM's `<pluginManagement>`, sub-modules automatically obtain through inheritance, **no need to repeat configuration in each**.

> For Maven engineering standards (BOM rules, plugin inheritance, dev profile), see → maven-guide.md.

### 2.1. Gate Overview

| Plugin | Phase | Check scope | Failure behavior |
|--------|-------|-------------|----------------|
| `maven-enforcer-plugin` | `validate` | Prohibit specific dependencies, dependency version convergence | Build aborts when `enforce.enabled=true` |
| `maven-checkstyle-plugin` | `validate` | Code style (naming, whitespace, comments, etc.) | Build aborts when `checkstyle.validate.disabled=false` |
| `maven-pmd-plugin` + p3c-pmd | `verify` | Alibaba P3C standards (potential bugs, code smells) | Violations abort build when `pmd.enforce.validate=true` |

> **Switch defaults**: All three gates are **enabled** in normal builds. `-Ddev` local development mode auto-exempts (→ maven-guide.md §5).

### 2.2. maven-enforcer-plugin — Dependency Governance

Before any Java code compilation, enforces two hard constraints on dependency tree:

#### 2.2.1. Prohibited Dependencies

| Coordinates | Prohibition reason |
|-------------|-------------------|
| `org.bouncycastle:bcprov-jdk16` | Discontinued old cryptography library, has security vulnerabilities |
| `org.hibernate:hibernate-validator` | Conflicts with Spring Boot built-in version, uncertain validation behavior |

To add new prohibitions, append in root POM's `<bannedDependencies><excludes>`.

#### 2.2.2. Dependency Version Convergence

When the same `groupId:artifactId` appears with multiple versions in the dependency tree, build fails immediately. **MUST** explicitly declare target version in BOM's `<dependencyManagement>` to force alignment.

#### 2.2.3. Control Switches

```properties
enforce.enabled=true   # 启用（默认）
enforce.enabled=false  # 豁免（-Ddev 自动设置）
```

### 2.3. maven-checkstyle-plugin — Code Style Check

Validates whether hand-written Java source code conforms to team-unified style standards.

#### 2.3.1. Rule File Distribution

Rule file `checkstyle.xml` packaged in build base module's jar, added to check plugin's classpath via plugin dependency. To modify rules, only update rule file source code, re-`mvn install` and it auto-takes effect.

#### 2.3.2. Check Scope

Only scans hand-written source directories (`src/main/java`), **excludes** auto-generated code in `target/generated-sources` such as MapStruct.

#### 2.3.3. Control Switches

```properties
checkstyle.validate.disabled=false   # 启用检查（默认）
checkstyle.validate.disabled=true    # 跳过检查（-Ddev 自动设置）
```

#### 2.3.4. New Environment Bootstrap

After the first clone in a brand new environment, run the bootstrap install once:

```bash
mvn install -pl {build-module} -DskipTests   # 仅需执行一次
```

### 2.4. maven-pmd-plugin + p3c-pmd — Alibaba P3C Standards Check

Performs static semantic analysis on Java source code, discovers potential bugs, performance risks, and code smells. Rule set uses Alibaba P3C (p3c-pmd 2.x, 10 independent ruleset files).

#### 2.4.1. Rule Set Coverage

| ruleset | Check scope |
|---------|-------------|
| `ali-comment.xml` | Comment standards (Javadoc format, classes must have author, etc.) |
| `ali-concurrent.xml` | Concurrency safety (thread pool, lock usage, etc.) |
| `ali-constant.xml` | Constant standards (magic values, constant naming, etc.) |
| `ali-exception.xml` | Exception standards (exception catching, return values, etc.) |
| `ali-flowcontrol.xml` | Flow control (switch-default, loops, etc.) |
| `ali-naming.xml` | Naming standards (class name camelCase, method names, etc.) |
| `ali-oop.xml` | OOP standards (POJO toString, equals, etc.) |
| `ali-orm.xml` | ORM standards (SQL concatenation, Mapper, etc.) |
| `ali-other.xml` | Other standards (collection initialization capacity, etc.) |
| `ali-set.xml` | Collection standards (ArrayList initialization, subList, etc.) |

#### 2.4.2. Exclusion Scope

Excludes auto-generated code under `target/generated-sources` (such as MapStruct Impl).

#### 2.4.3. Typical Detection Scenarios

- Directly deleting elements during collection iteration (`ConcurrentModificationException` risk)
- `switch` statement missing `default` branch
- Thread pool using `Executors` factory methods (detection prevents unbounded-queue OOM)
- Manually concatenated SQL strings (SQL injection risk)
- Methods too long (exceeding 80 lines)
- Magic values used directly (`if (status == 1)` → should define constant)
- Class missing `@author` comment

#### 2.4.4. Control Switches

```properties
pmd.enforce.validate=true    # PMD 运行且违规直接中止构建（默认）
pmd.enforce.validate=false   # PMD 运行但违规仅警告（-Ddev 自动设置）
```

### 2.5. dev Profile Impact on Quality Gates

| Gate | Default build | `-Ddev` local mode |
|------|--------------|-------------------|
| enforcer dependency convergence | ✓ Enforced | ✗ Skipped |
| checkstyle style check | ✓ Violations abort | ✗ Skipped |
| PMD P3C check | ✓ Violations abort | ✗ Warn only |
| sources.jar packaging | ✓ Generated | ✗ Skipped |

---

## 3. Gate Execution Instructions

- Before AI claims "current stage complete" each time, AI **MUST** itself check against this document's corresponding stage blocking items one by one
- When any blocking item is not satisfied, **MUST NOT** declare completion or proceed to next stage, **MUST** list specific non-passing items
- When recommendation items are not satisfied, **MUST** explain reasons to user, user decides whether to accept risk and continue

### 3.1. Gate Failure Handling Process

When blocking items fail, AI **MUST** respond according to the following process:

```
1. 列出具体未通过的阻断项（逐条引用本规范原文）
2. 给出每条未通过项的修复建议（具体到文件/代码行/修改方式）
3. 等待用户决策：
   - 用户选择修复 → 修复后重新核查门禁
   - 用户选择跳过（仅建议项）→ 记录技术债，继续推进
   - 用户选择回退到上一阶段 → 回退并更新对应 Artifact
4. MUST NOT 在用户未明确决策的情况下自行继续推进
```

> **Fallback scenarios**: When requirement changes cause need to fall back to previous stage, **MUST** update corresponding Artifact (spec.md / plan.md / tasks.md), annotate change reason, re-run gates after user confirmation.
