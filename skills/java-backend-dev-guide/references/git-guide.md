# Git 规范

> **摘要**
>
> - **核心约束**：分支策略采用 Git Flow（main / develop / feature / release / hotfix）；Commit Message 采用 Angular 规范（`<type>(<scope>): <subject>`）
> - **关键阈值**：feature 从 develop 创建、release 从 develop 创建合并回 main + develop、hotfix 从 main 创建合并回 main + develop
> - **常见违规**：直接在 main 上开发、commit message 无 type 前缀、一次提交包含多个不相关改动、feature 未合并就长期搁置

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 分支策略（Git Flow）

### 1.1. 分支类型

| 分支      | 命名格式                           | 用途                               | 生命周期   |
| --------- | ---------------------------------- | ---------------------------------- | ---------- |
| `main`    | `main`                             | 生产环境代码，每个版本节点可追溯   | 永久       |
| `develop` | `develop`                          | 开发集成分支，集成最新开发成果     | 永久       |
| `feature` | `feature/{issuePrefix}-<简述>`     | 单个功能或需求开发                 | 合并后删除 |
| `release` | `release/<version>`                | 版本发布准备（测试、修复、元数据） | 合并后删除 |
| `hotfix`  | `hotfix/{issuePrefix}-<简述>`      | 生产环境紧急修复                   | 合并后删除 |

### 1.2. 分支流转

```
main ──────────────────────────────────── hotfix ──→ main
 │                                         │
 │  ←──────────────── release ─────────────┘
 │         │
develop ──┤── feature/* ──→ develop
          │
          └── feature/* ──→ develop
```

### 1.3. 规则

- **MUST NOT** 直接在 `main` 上提交代码（`main` 仅接受 release 和 hotfix 合并）
- **MUST NOT** 直接在 `develop` 上开发功能（从 `develop` 创建 feature 分支）
- feature 分支 **MUST** 从最新的 `develop` 创建，开发完成后合并回 `develop`
- release 分支 **MUST** 从 `develop` 创建，测试通过后合并回 `main`（打 tag）和 `develop`
- hotfix 分支 **MUST** 从 `main` 创建，修复完成后合并回 `main`（打 tag）和 `develop`
- feature / release / hotfix 合并后 **MUST** 删除远程分支

### 1.4. 命名示例

```
feature/JIRA-1234-article-publish
feature/JIRA-5678-author-crud
release/1.5.0
hotfix/JIRA-9999-fix-null-pointer
```

---

## 2. Commit Message 规范（Angular）

### 2.1. 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

| 部分      | 规则                                                     |
| --------- | -------------------------------------------------------- |
| `type`    | **MUST**，见下方类型表                                   |
| `scope`   | 可选，影响范围（模块名或组件名）                         |
| `subject` | **MUST**，简述改动，不超过 50 字符，首字母小写，不加句号 |
| `body`    | 可选，详细说明改动原因与影响面                           |
| `footer`  | 可选，Breaking Change 标记或关联 Issue                   |

### 2.2. Type 取值

| type       | 用途                           | 示例                                            |
| ---------- | ------------------------------ | ----------------------------------------------- |
| `feat`     | 新功能                         | `feat(biz-author): add article publish workflow`|
| `fix`      | 修复 Bug                       | `fix(dal): resolve NPE when Redis timeout`      |
| `refactor` | 重构（不新增功能、不修复 Bug） | `refactor(core): extract ResultCode to enum`    |
| `docs`     | 文档变更                       | `docs: update README for local setup`           |
| `chore`    | 构建/工具/依赖变更             | `chore: upgrade mybatis-plus to 3.5.9`          |
| `test`     | 测试相关                       | `test(biz-author): add unit tests for service`  |
| `ci`       | CI/CD 配置                     | `ci: add PMD check to pipeline`                 |
| `build`    | 构建系统                       | `build: update flatten-maven-plugin config`     |
| `perf`     | 性能优化                       | `perf(redis): use pipeline for batch queries`   |
| `revert`   | 回退提交                       | `revert: revert feat(biz-author): add publish`  |

### 2.3. Scope 取值

> Scope 应反映实际模块名，由项目级 Skill 定义具体取值范围。通用示例：

| scope          | 含义           |
| -------------- | -------------- |
| `biz-{domain}` | 业务领域模块   |
| `{coreModule}` | 公共契约层     |
| `{dalModule}`  | 存储适配层     |
| `{bootModule}` | 启动自动配置   |
| `{bomModule}`  | 版本管理       |

### 2.4. 正确示例

```
feat(biz-author): add article publish workflow

实现文章发布功能，包含状态机流转和消息通知。
- 新增 ArticlePublishService 领域服务
- 新增 ARTICLE_PUBLISH ResultCode

feat(biz-article): support scroll pagination for article list

fix(dal): resolve connection leak in HBase pool

chore: upgrade redis to 4.0.12 in bom
```

### 2.5. 错误示例

```
# ❌ 无 type 前缀
update article service

# ❌ subject 首字母大写
feat(Biz-Author): Add article publish workflow

# ❌ subject 太长且含句号
feat(biz-author): implement the article publish workflow feature with state machine and notification.

# ❌ 一次提交包含多个不相关改动
feat: add article publish and fix redis timeout and update readme
```

---

## 3. 提交纪律

- **MUST** 一次提交只包含一个逻辑改动（单一职责）
- **MUST NOT** 提交编译失败或测试未通过的代码
- **MUST NOT** 提交包含敏感信息（密钥、密码、Token）的文件
- **MUST NOT** 使用 `git push --force` 到 `main` / `develop` 分支
- **MUST** 在合并 PR 前确保 CI 流水线全部通过
