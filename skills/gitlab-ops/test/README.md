# gitlab-ops Skill 测试套件

本目录包含 gitlab-ops Skill 的自动化测试，覆盖所有 SKILL 文档中记录的 git 命令、glab 子命令和 GitLab REST API。

## 环境要求

- Python 3.9+
- git 已安装并在 PATH 中
- [glab CLI](https://gitlab.com/gitlab-org/cli) 已安装（`glab --version` 可执行）
- 一个可用于测试的 GitLab 项目和 Access Token

## 环境变量

测试通过环境变量获取凭据，**不提供默认值**，避免凭据随代码提交。

| 变量 | 说明 | 示例 |
|------|------|------|
| `GITLAB_URL` | GitLab 实例地址 | `https://gitlab.example.com` |
| `GITLAB_TOKEN` | Personal Access Token（需 `api` scope） | `glpat-xxxxxxxx` |
| `GITLAB_PROJECT` | 测试项目路径（`namespace/project`） | `mygroup/myproject` |
| `GITLAB_HOST` | （可选）GitLab 主机名，默认从 `GITLAB_URL` 推导 | `gitlab.example.com` |

### 配置方式

**方式 1：直接设置环境变量**

```bash
# Linux / macOS
export GITLAB_URL=https://gitlab.example.com
export GITLAB_TOKEN=glpat-xxxxxxxx
export GITLAB_PROJECT=mygroup/myproject

# Windows PowerShell
$env:GITLAB_URL="https://gitlab.example.com"
$env:GITLAB_TOKEN="glpat-xxxxxxxx"
$env:GITLAB_PROJECT="mygroup/myproject"
```

**方式 2：使用 .env 文件（推荐）**

```bash
cp test/.env.example test/.env
# 编辑 .env 填入实际值
```

> `.env` 已被 `.gitignore` 排除，不会随代码提交。

## 运行测试

```bash
# 进入 test 目录
cd test

# 运行全部测试
python -m unittest discover -v

# 运行单个测试文件
python -m unittest test_gitlab_repo -v

# 运行单个测试类
python -m unittest test_gitlab_repo.TestRepoView -v

# 运行单个测试方法
python -m unittest test_gitlab_repo.TestRepoView.test_repo_view_current -v
```

## 测试文件说明

### test_git_local.py — 本地 Git 命令（git-local.md）

验证 `git-local.md` 中记录的所有本地 git 命令。

| 场景 | 验证内容 |
|------|---------|
| 全局配置 | `git config --global` 读写 |
| 仓库初始化 | `git init` |
| 克隆 | `git clone`、`git clone --depth 1`（浅克隆） |
| 分支 | `git branch`、`git checkout -b`、`git switch`、`git branch -d/-D`（含强制删除未合并分支） |
| 提交 | `git commit`、`git commit --amend` |
| 暂存 | `git stash`、`git stash pop`、`git stash list`、`git stash push -m`（带描述）、`git stash -u`（含未跟踪文件） |
| 远程 | `git remote add/list` |
| 标签 | `git tag`、`git tag -a` |
| diff / log | `git diff`（暂存区）、`git diff`（未暂存工作区变更）、`git diff A..B`（跨分支比较）、`git diff --stat`、`git log --oneline` |
| cherry-pick | `git cherry-pick`（单个）、`git cherry-pick`（多个连续提交） |
| merge / rebase | `git merge`（默认）、`git merge --no-ff`（强制合并提交）、`git merge --ff-only`（仅快进）、`git rebase` |
| revert | `git revert HEAD`（安全回滚，生成逆向提交） |
| reset | `git reset --soft`（保留暂存区）、`git reset --hard`（丢弃所有变更） |
| reflog / 灾难恢复 | `git reflog`、删除分支后通过 reflog SHA 恢复 |
| .gitignore | 规则语法验证 |
| .gitattributes | 规则语法验证 |

> 全部在本地临时仓库中执行，不需要 GitLab 连接（但需要环境变量存在）。

### test_gitlab_auth.py — 认证与身份（gitlab-auth.md）

| 场景 | 验证内容 |
|------|---------|
| auth login | `--help` 输出包含 `--hostname`、`--stdin` |
| auth status | 当前认证状态查询 |
| auth status --hostname | 指定主机名查询 |
| auth switch | 验证 `switch` 子命令**不存在**（应使用 logout + login） |
| auth logout | `--help` 输出包含 `--hostname` |
| ssh-key | list / add / get / delete 的 `--help` 验证 |
| token | create / list / revoke 的 `--help` 验证 |
| credential helper | git credential helper 配置验证 |

### test_gitlab_repo.py — 仓库管理（gitlab-repo.md）

| 场景 | 验证内容 |
|------|---------|
| repo view | 查看当前项目、指定项目、JSON 输出 |
| repo browse | 验证 `browse` 子命令**不存在** |
| repo fork | `--help` 验证，确认 `--name`、`--clone` 标志 |
| repo archive | `--help` 验证（该命令下载 zip，**不是**归档项目） |
| repo transfer | `--help` 验证 `--target-namespace` 标志 |
| 分支 REST API | 通过 REST API 创建/列出/删除分支 |

### test_gitlab_mr.py — 合并请求（gitlab-mr.md）

| 场景 | 验证内容 |
|------|---------|
| mr create | `--help` 验证 `--title`、`--source-branch`、`--fill` 等标志 |
| mr list | `--help` 验证 `--state`、`--label` 等过滤标志 |
| mr view | `--help` 验证 |
| mr merge | `--help` 验证 `--squash`、`--remove-source-branch` 标志 |
| mr close | `--help` 验证（**无** `--comment` 标志） |
| mr note | `--help` 验证 `create` 子命令 |
| mr diff | `--help` 验证 |
| mr approve | `--help` 验证 |
| mr rebase | `--help` 验证 |
| 分支管理 | REST API 分支操作 |

### test_gitlab_issue.py — Issue 管理（gitlab-issue.md）

| 场景 | 验证内容 |
|------|---------|
| issue create | `--help` 验证 `--title`、`--label`、`--assignee` 等标志 |
| issue list | `--help` 验证过滤标志；验证 `--state opened` **不存在**（默认即 opened） |
| issue view | `--help` 验证 |
| issue close | `--help` 验证（**无** `--comment` 标志） |
| issue note | `--help` 验证 |
| issue update | `--help` 验证 |
| issue delete | `--help` 验证（**无** `--yes` 标志） |
| issue CRUD | 通过 REST API 完整创建/查询/更新/关闭/删除流程 |

### test_gitlab_ci.py — CI/CD 流水线（gitlab-ci.md）

| 场景 | 验证内容 |
|------|---------|
| ci status | `--help` 验证 |
| ci list | `--help` 验证 `--scope`、`--ref` 过滤 |
| ci view | `--help` 验证 |
| ci get | `--help` 验证 `--pipeline-id` 标志（**非**位置参数） |
| ci trace | `--help` 验证 |
| ci retry | `--help` 验证参数为 job-id（**非** pipeline-id） |
| ci cancel | `--help` 验证 `pipeline` 子命令用法 |
| ci trigger | `--help` 验证（触发手动 job，**非** `--branch`） |
| schedule | list / create / update / delete 的 `--help` 验证 |

### test_gitlab_advanced.py — 其他功能（gitlab-advanced.md）

| 场景 | 验证内容 |
|------|---------|
| release | list / create / view / delete 的 `--help` 验证 |
| snippet | create / view 的 `--help` 验证 |
| variable | list / set / get / delete 的 `--help` 验证 |
| label | list / create 的 `--help` 验证 |
| milestone | list 的 `--help` 验证 `--project` / `--group` 标志（**无** `view` 子命令） |
| runner | list 的 `--help` 验证 |
| packages | list 的 `--help` 验证 |
| todo | list / done 的 `--help` 验证 |

### test_gitlab_api.py — REST API 通用模式（gitlab-api.md）

| 场景 | 验证内容 |
|------|---------|
| 认证头 | `PRIVATE-TOKEN` 头认证 |
| 分页 | `?page=1&per_page=5` 参数 |
| 排序 | `?order_by=created_at&sort=desc` 参数 |
| 搜索 | `?search=keyword` 参数 |
| CRUD | 项目信息的 GET 请求 |

### test_gitlab_e2e.py — 端到端场景

验证此前标记为"不可测"的场景，使用测试项目进行真实操作并清理。

| 场景 | 验证内容 |
|------|---------|
| Fork（REST API） | 通过 API fork 项目，验证后删除 |
| Fork（glab 语法） | 验证 `glab repo fork --help` 标志正确 |
| 归档/取消归档 | 通过 REST API archive → 验证 archived → unarchive → 验证恢复 |
| 下载归档 | `glab repo archive` 下载 zip 文件（非项目归档） |
| MR 创建 + 关闭 | 在临时 git 仓库中 `glab mr create`，API 验证后关闭 |
| MR 创建 + 合并 | 在临时 git 仓库中 `glab mr create`，`glab mr merge --squash` 合并 |
| Transfer 语法 | 验证 `--target-namespace` 标志存在 |

### test_scripts.py — 辅助脚本

验证 `scripts/` 目录下的 Python 脚本语法正确且 `--help` 可执行。

| 脚本 | 验证内容 |
|------|---------|
| branch_cleanup.py | 语法 + `--help` + `--dry-run` |
| ci_retry_failed.py | 语法 + `--help` |
| env_check.py | 语法 + `--help` |
| issue_triage.py | 语法 + `--help` |
| mr_batch_merge.py | 语法 + `--help` |
| release_notes.py | 语法 + `--help` |
| repo_audit.py | 语法 + `--help` |

## 注意事项

### 测试项目要求

- e2e 测试（`test_gitlab_e2e.py`）会对项目执行真实操作（创建分支、MR、fork 等），请确保使用**专用测试项目**，不要在生产项目上运行。
- Token 需要以下权限：`api`（完整 API 访问）。
- 用户需要对测试项目有 Maintainer 或 Owner 权限。

### glab 认证

- 测试通过环境变量 `GITLAB_TOKEN` 注入认证，不依赖 glab 的 keyring。
- `conftest.py` 中的 `_glab_env()` 会自动将 token 注入子进程环境。

### 已知行为

- `glab repo archive` 下载仓库 zip 包，**不是**将项目设为只读。项目归档需使用 REST API。
- `glab repo fork` 的 `--clone` 和 `--remote` 标志需用 `=` 连接（如 `--clone=false`），不能用空格。
- `glab mr create` 必须在 git 仓库目录内执行，且仓库 remote 需匹配 GitLab 主机。
- MR/Issue 关闭 API 使用 `PUT` + `state_event: "close"`，不存在 `POST .../close` 端点。
- `glab mr close` 没有 `--comment` 标志，需先用 `glab mr note create` 添加评论。
- Windows 环境下 glab 输出为 UTF-8，Python subprocess 需指定 `encoding="utf-8", errors="replace"`。

### 清理

- 每个 e2e 测试都有 `tearDown` 清理创建的分支、MR、fork 等资源。
- 如果测试中断导致残留数据，手动删除即可：
  - 分支：GitLab 项目页面 → Repository → Branches
  - MR：GitLab 项目页面 → Merge requests
  - Fork：删除 fork 后的项目
