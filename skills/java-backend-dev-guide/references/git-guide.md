# Git Standards

> **Summary**
>
> - **Core constraint**: Branch strategy uses Git Flow (main / develop / feature / release / hotfix); Commit Message uses Angular convention (`<type>(<scope>): <subject>`)
> - **Key thresholds**: feature branches from develop, release branches from develop merged back to main + develop, hotfix branches from main merged back to main + develop
> - **Common violations**: Direct development on main, commit message without type prefix, single commit containing multiple unrelated changes, feature branches shelved long-term without merging

---

## 1. Branch Strategy (Git Flow)

### 1.1. Branch Types

| Branch | Naming format | Purpose | Lifecycle |
|--------|--------------|---------|-----------|
| `main` | `main` | Production environment code, each version node traceable | Permanent |
| `develop` | `develop` | Development integration branch, integrates latest development results | Permanent |
| `feature` | `feature/{issuePrefix}--<description>` | Single feature or requirement development | Deleted after merge |
| `release` | `release/<version>` | Release preparation (testing, fixes, metadata) | Deleted after merge |
| `hotfix` | `hotfix/{issuePrefix}--<description>` | Production environment urgent fix | Deleted after merge |

### 1.2. Branch Flow

```
main ──────────────────────────────────── hotfix ──→ main
 │                                         │
 │  ←──────────────── release ─────────────┘
 │         │
develop ──┤── feature/* ──→ develop
          │
          └── feature/* ──→ develop
```

### 1.3. Rules

- **MUST NOT** commit code directly on `main` (`main` only accepts release and hotfix merges)
- **MUST NOT** develop features directly on `develop` (create feature branches from `develop`)
- feature branches **MUST** be created from the latest `develop`, merged back to `develop` after development is complete
- release branches **MUST** be created from `develop`, merged back to `main` (create a tag on `main`) and `develop` after testing passes
- hotfix branches **MUST** be created from `main`, merged back to `main` (create a tag on `main`) and `develop` after fix is complete
- the remote branch **MUST** be deleted after a feature / release / hotfix branch is merged

### 1.4. Naming Examples

> Use `--` (double hyphen) to separate requirement ID from feature description, to avoid confusion with `-` inside the ID.

```
feature/VR260810-020--data-preview
feature/VR260810-035--article-publish
release/1.5.0
hotfix/VR260810-020--fix-null-pointer
```

---

## 2. Commit Message Convention (Angular)

### 2.1. Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

| Section | Rules |
|---------|-------|
| `type` | **MUST**, see §2.2 type table |
| `scope` | Optional, impact scope (module name or component name), see §2.3 |
| `subject` | **MUST**, use Chinese, imperative mood, no period, ≤50 characters |
| `body` | Optional, explains **why** not what (the diff itself explains what), each line ≤72 characters |
| `footer` | Optional, `BREAKING CHANGE:` description / related Issue (`Fixes #123`) / related requirement ID (`Refs: VR260810-020`), see Refs rules below |

**Breaking Change marker** (choose one of two):

```
# 方式一：type 后加 !
feat(api)!: 移除废弃的用户搜索接口

# 方式二：footer 中声明
feat(biz-order): 重构订单创建逻辑

BREAKING CHANGE: OrderDTO.status 字段类型从 String 变更为 OrderStatusEnum。
所有调用方须同步修改。

Fixes #1234
```

### 2.2. Type Values

| type | Purpose | Example |
|------|---------|---------|
| `feat` | New feature | `feat(biz-author): 新增文章发布流程` |
| `fix` | Bug fix | `fix(dal): 修复 Redis 超时导致的空指针异常` |
| `refactor` | Refactoring (no new feature, no bug fix) | `refactor(core): 提取 ResultCode 为枚举类` |
| `docs` | Documentation changes | `docs: 更新本地部署说明` |
| `chore` | Build/tools/dependency changes | `chore: 升级 mybatis-plus 至 3.5.9` |
| `test` | Test related | `test(biz-author): 补充业务层单元测试` |
| `ci` | CI/CD configuration | `ci: 新增 PMD 检查到流水线` |
| `build` | Build system | `build: 调整 flatten-maven-plugin 配置` |
| `perf` | Performance optimization | `perf(redis): 使用 pipeline 批量查询优化` |
| `revert` | Revert commit | `revert: 回退 feat(biz-author): 新增文章发布流程` |

### 2.3. Scope Values

> Scope should reflect actual module names, specific values defined by project-level Skill. General examples:

| scope | Meaning |
|-------|---------|
| `biz-{domain}` | Business domain module |
| `{coreModule}` | Public contract layer |
| `{dalModule}` | Storage adaptation layer |
| `{bootModule}` | Startup auto-configuration |
| `{bomModule}` | Version management |

### 2.4. Refs Rules (Requirement Linking)

> Feature development (`feat`) and bug fixes (`fix`) **MUST** link requirement IDs in footer, for code traceability and Review.

**Format**: `Refs: <requirement ID>`, multiple requirements on separate lines.

```
Refs: VR260810-020
Refs: VR260810-021
```

**Applicable scope**:
- `feat` / `fix` → **MUST** link requirement ID
- `refactor` / `perf` → **SHOULD** link (if corresponding requirement exists)
- `docs` / `chore` / `ci` / `build` / `test` → Optional

### 2.5. Correct Examples

```
feat(biz-author): 新增文章发布流程

实现文章发布功能，包含状态机流转和消息通知。
- 新增 ArticlePublishService 领域服务
- 新增 ARTICLE_PUBLISH ResultCode

Refs: VR260810-020

feat(biz-article): 文章列表支持滚动分页

Refs: VR260810-021

fix(dal): 修复 HBase 连接池连接泄漏

Refs: VR260810-015

chore: 升级 bom 中 Redis 版本至 4.0.12

feat(api)!: 移除废弃的用户搜索接口

旧版 /api/v1/users/search 接口自 v2.0 起已由
/api/v2/users/search 替代，移除以减少维护负担。

BREAKING CHANGE: /api/v1/users/search 已移除，请使用 /api/v2/users/search。

Refs: VR260810-030

fix(biz-order): 修复优惠券为空时的空指针异常

根因：未使用优惠券时 getCoupon() 返回 null，
但折扣计算逻辑未做空值判断。

Fixes #2345
Refs: VR260810-025
```

### 2.6. Incorrect Examples

```
# ❌ 无 type 前缀
更新文章服务

# ❌ subject 使用英文
feat(biz-author): add article publish workflow

# ❌ subject 太长
feat(biz-author): 实现文章发布流程并集成状态机流转与消息通知功能

# ❌ 一次提交包含多个不相关改动
feat: 新增文章发布并修复 Redis 超时和更新文档

# ❌ Breaking Change 未标记（仅改 subject，无 ! 也无 footer）
feat(api): 移除废弃的用户搜索接口

# ❌ footer 格式错误（应使用 Fixes/Closes 而非 fix/close）
fix(dal): 修复缓存层空指针异常
fix: #1234

# ❌ feat 缺少 Refs（功能提交 MUST 关联需求 ID）
feat(biz-author): 新增文章发布流程

实现文章发布功能，包含状态机流转和消息通知。
```

### 2.7. Commit Template and Enforcement (Team Shared)

> Two hooks work together: `prepare-commit-msg` injects template + `commit-msg` enforces format validation.
> **MUST** execute setup script once after clone.

```bash
# 新人 clone 后执行一次（仅一次）
python3 scripts/setup-git.py
```

**Hook Mechanism**:

| Hook | Trigger timing | Purpose |
|------|---------------|---------|
| `prepare-commit-msg` | During interactive `git commit` | Auto-fill template comments (including Refs prompt) |
| `commit-msg` | After commit message written, before commit | **Validate format, reject non-conforming commits** |

**commit-msg validation rules**:
- First line must match `<type>(<scope>): <subject>` format
- type must be: `feat | fix | refactor | docs | chore | test | perf | ci | build | revert`
- scope optional, subject required
- subject first letter lowercase, no period, ≤50 characters
- Exemptions: merge commits, revert commits, initial commits

**Files involved**:

| File | Purpose |
|------|---------|
| `scripts/hooks/prepare-commit-msg` | hook: auto-inject template (Python 3) |
| `scripts/hooks/commit-msg` | hook: enforce Angular format validation (Python 3) |
| `scripts/setup-git.py` | One-time configuration script (Python 3) |

---

## 3. Commit Discipline

- **MUST** one commit contains only one logical change (single responsibility)
- **MUST NOT** commit code that fails to compile or pass tests
- **MUST NOT** commit files containing sensitive information (keys, passwords, Tokens)
- **MUST NOT** use `git push --force` to `main` / `develop` branches
- **MUST** ensure CI pipeline all passes before merging PR
