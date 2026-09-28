---
name: gitlab-ops
version: 1.0.0
description: >-
  当需要执行任何 git 或 GitLab 操作时使用——本地 git 操作
  （clone、diff、log、branch、merge、rebase）、GitLab 平台工作流
  （Merge Request、CI/CD、Issue、Release、仓库管理），
  或需要 git 工作流方法论、安全规范、版本控制决策指导时触发。
  覆盖 glab CLI 与 GitLab REST API。
  触发词：git push、git pull、git merge、git rebase、MR、merge request、
  CI/CD、pipeline、glab、GitLab、分支管理、tag、release、issue、
  git clone、git diff、git log、git stash、cherry-pick、冲突解决。
---

# gitlab-ops

git 与 GitLab 全操作指南。覆盖本地 git 操作、GitLab 平台工作流、方法论与安全规范。

## 文件路由

根据操作类型加载对应子文件：

| 操作领域 | 子文件 | 触发场景 |
|---------|--------|---------|
| 本地 git 操作 | [git-local.md](git-local.md) | clone、diff、log、branch、merge、rebase、stash、tag、config、cherry-pick、reflog、.gitignore、.gitattributes、Git Hook、commit 规范 |
| Merge Request | [gitlab-mr.md](gitlab-mr.md) | MR 创建、审查、合并、Stacked MR |
| CI/CD 流水线 | [gitlab-ci.md](gitlab-ci.md) | pipeline 查看、job 管理、schedule、.gitlab-ci.yml |
| Issue 管理 | [gitlab-issue.md](gitlab-issue.md) | Issue 创建、分诊、关闭、与 MR 关联、Issue 模板 |
| 仓库管理 | [gitlab-repo.md](gitlab-repo.md) | 项目信息、fork、归档、分支管理 |
| 认证与身份 | [gitlab-auth.md](gitlab-auth.md) | 登录、SSH key、PAT、凭据缓存、多身份管理 |
| REST API | [gitlab-api.md](gitlab-api.md) | glab 未覆盖的操作、批量更新、Webhook |
| 其他功能 | [gitlab-advanced.md](gitlab-advanced.md) | Release、Snippet、Variable、Label、Runner、Package |
| Quick Actions | [quick-actions.md](quick-actions.md) | 斜杠命令速查（/assign、/label、/merge 等） |
| 端到端工作流 | [workflows.md](workflows.md) | Git Flow、GitHub Flow、Feature Branch、Hotfix、Code Review、发布流程 |
| 通用故障排查 | [troubleshooting.md](troubleshooting.md) | 认证失败、git 冲突、glab 异常、灾难恢复（reflog/ORIG_HEAD） |
| 脚本模板 | [scripts/](scripts/) | 批量操作脚本模板 |

## 安全规范（全局）

### 🛑 STOP — 不可逆操作红线

> **🔴 CHECKPOINT：执行下表任一操作前，必须暂停并向用户确认。未经确认执行 = 事故。**

以下操作**必须**在执行前获得用户确认：

| 操作 | 风险 | 要求 |
|------|------|------|
| `git reset --hard` | 丢弃未提交改动 | 用户确认；先 `git stash` 备份 |
| `git branch -D` | 丢弃未合并分支 | 确认分支可丢弃 |
| `glab mr merge` | 合并代码 | 确认 pipeline 通过、审查完成 |
| `glab issue delete` | 永久删除 | 用户确认 |
| `glab repo archive` | 仓库变只读 | 用户确认 |

### ⚠️ 通用安全规则（每次操作前对照）

1. **操作前检查状态** — `git status` 确认工作区干净或已 stash
2. **共享 worktree 中不用裸 stash** — 用 `git stash push -u -m "unique-tag"`
3. **Token 不落盘** — 不写入代码文件、不打印到日志、不嵌入代码。**唯一例外**：`<skill-base>/scripts/.env`，该文件由对话式引导流程写入，专供本 Skill 读取凭据
4. **密码脱敏** — 脚本中出现的密码/Token 在日志中必须 scrub
5. **写操作前 GET** — REST API 操作前先查询确认目标存在
6. **批量操作加间隔** — 避免触发 GitLab 限流（429）

### 决策树总纲

```
收到 git/GitLab 操作请求？
├── 纯本地操作（不涉及远端） → git-local.md
├── MR 相关 → gitlab-mr.md
├── CI/CD 相关 → gitlab-ci.md
├── Issue 相关 → gitlab-issue.md
├── 仓库管理 → gitlab-repo.md
├── 认证/身份问题 → gitlab-auth.md
├── glab 不覆盖的操作 → gitlab-api.md
├── Release/Snippet/Variable 等 → gitlab-advanced.md
├── 需要斜杠命令 → quick-actions.md
├── 端到端流程 → workflows.md
└── 遇到错误 → troubleshooting.md
```

## Agent 主工作流（收到请求后的执行顺序）

> **严格按以下 5 步顺序执行。跳过任何一步 = 违规。**

```
Step 1: 路由
  ├─ 读取用户请求 → 匹配「决策树总纲」→ 加载对应子文件
  └─ 如果跨多个领域 → 按顺序加载多个子文件

Step 2: 环境门禁
  ├─ 首次操作？ → 运行 python scripts/env_check.py
  ├─ 检查未通过？ → 停止，引导用户安装（见故障降级表）
  └─ 通过 → 进入 Step 3

Step 3: 认证门禁（仅 GitLab 操作）— .env 优先
  ├─ 检查 <skill-base>/scripts/.env 是否存在
  ├─ 存在 → 读取 GITLAB_URL 和 GITLAB_TOKEN
  │   ├─ 变量缺失 → 报错 → 进入「对话式引导配置」
  │   └─ 变量完整 → 用 curl 验证连接（GET /api/v4/user -H "PRIVATE-TOKEN: $GITLAB_TOKEN"）
  │       ├─ 200 OK → 导出环境变量 → 进入 Step 4
  │       └─ 401/403/超时 → 报错 → 进入「对话式引导配置」
  ├─ 不存在 → 报错 → 进入「对话式引导配置」
  │
  └─ 对话式引导配置：
      ├─ 向用户报错：说明 .env 缺失/变量缺失/连接失败的具体原因
      ├─ 逐步询问用户：
      │   ① "请输入 GitLab 地址（如 https://gitlab.example.com）："
      │   ② "请输入 GitLab Personal Access Token："
      ├─ 用用户提供的值验证连接（同上 curl 命令）
      │   ├─ 成功 → 写入 <skill-base>/scripts/.env（GITLAB_URL + GITLAB_TOKEN）→ 导出环境变量 → 进入 Step 4
      │   └─ 失败 → 展示错误原因 → 重新询问（回到 ①）
      └─ .env 写入后提醒用户：该文件包含敏感凭据，确保不被提交到版本控制

Step 4: 状态检查
  ├─ 运行 git status → 确认工作区状态
  ├─ 有未提交改动且即将执行写操作？ → 先 git stash push -u -m "tag" 或 git commit
  └─ 工作区干净 → 进入 Step 5

Step 5: 执行操作
  ├─ 按子文件中的具体命令执行
  ├─ 涉及不可逆操作？ → 🛑 STOP → 向用户确认 → 获得明确同意后才执行
  └─ 执行完毕 → 检查退出码 → 展示结果给用户
```

### 高频操作速查命令

| 场景 | 命令 |
|------|------|
| 创建 feature 分支 | `git checkout -b feature/TICKET-123-desc develop` |
| 非交互式创建 MR | `glab mr create --title "feat(scope): title" --description "## What" --target-branch develop --no-editor` |
| 查看 pipeline 状态 | `glab ci status` |
| 合并 MR（squash） | `glab mr merge <iid> --squash --remove-source-branch` |
| 查看文件 diff | `git diff HEAD~1 -- path/to/file` |
| 安全撤销本地改动 | `git stash push -u -m "backup-$(date +%s)"` |

## 工具依赖

| 工具 | 用途 | 必需 |
|------|------|------|
| `git` | 本地版本控制 | 是 |
| `glab` | GitLab CLI | 是（GitLab 操作） |
| `curl` | REST API 调用 | 否（glab 不够用时） |
| `jq` | JSON 解析 | 推荐（API/JSON 输出场景） |
| `ssh` | SSH 认证 | 否（HTTPS 认证可替代） |

## 🔴 CHECKPOINT — 首次运行环境检查

> **🛑 STOP：Agent 在本项目首次执行任何 git/GitLab 操作前，必须通过本检查。检查未通过 = 不执行任何操作。**

Agent 在本项目**首次**执行任何 git/GitLab 操作前，**必须**先运行环境检查：

```bash
python scripts/env_check.py
```

### 检查项

| 依赖 | 最低版本 | 必需 | 说明 |
|------|---------|------|------|
| `python3` | 3.8+ | 是 | 脚本执行环境 |
| `git` | **2.41+** | 是 | 本地版本控制（低于 2.41 会警告） |
| `glab` | 任意 | 是（GitLab 操作） | GitLab CLI |

### 检查结果处理

1. **全部通过** → 继续执行请求的操作
2. **有缺失或版本不满足** → 向用户报告缺失项，展示安装命令
3. **用户要求自动安装** → 运行 `python scripts/env_check.py --install`
4. **自动安装失败** → 展示手动安装指令，等待用户完成后重试

### 安装后验证

自动安装完成后，重新运行检查确认：

```bash
python scripts/env_check.py
```

### 可选依赖

以下工具非必需，但 API/JSON 场景必须安装：

| 工具 | 用途 | 安装 |
|------|------|------|
| `jq` | JSON 解析（API 场景） | `winget install jqlang.jq` / `brew install jq` / `sudo apt install jq` |
| `ssh` | SSH 认证 | 通常系统自带 |

### 🔴 CHECKPOINT — .env 凭据检查（认证门禁）

> **🛑 STOP：环境检查通过后、执行 GitLab 操作前，必须通过 .env 凭据检查。凭据不可用 = 不执行 GitLab 操作。**

环境检查通过后，如果即将执行 GitLab 操作，**必须**按以下顺序检查凭据：

**1. 检查 `scripts/.env` 文件是否存在**

```bash
# <skill-base> 为本 Skill 的根目录
test -f "<skill-base>/scripts/.env" && echo "EXISTS" || echo "NOT_FOUND"
```

**2. 如果存在，读取变量**

```bash
# 读取 .env 中的变量（不 source 到全局环境，仅提取值）
GITLAB_URL=$(grep '^GITLAB_URL=' "<skill-base>/scripts/.env" | cut -d'=' -f2-)
GITLAB_TOKEN=$(grep '^GITLAB_TOKEN=' "<skill-base>/scripts/.env" | cut -d'=' -f2-)
```

**3. 验证连接**

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/user"
# 期望：200
```

**4. 检查未通过时的处理**

| 情况 | 处理 |
|------|------|
| `scripts/.env` 不存在 | → 进入「对话式引导配置」 |
| 文件存在但 `GITLAB_URL` 或 `GITLAB_TOKEN` 为空 | → 进入「对话式引导配置」 |
| 连接返回 401/403 | → 报错「Token 无效或已过期」→ 进入「对话式引导配置」 |
| 连接超时 / 非 200 | → 报错「无法连接到 GitLab」→ 检查 URL 是否正确 |

### 对话式引导配置流程

> 当 .env 缺失、变量不完整、或连接验证失败时，Agent **必须**按以下步骤引导用户完成配置。

**Step A — 报错并说明原因**

向用户展示具体失败原因（三选一）：
- `scripts/.env 文件不存在，需要配置 GitLab 凭据`
- `scripts/.env 中缺少 GITLAB_URL 或 GITLAB_TOKEN`
- `GitLab 连接验证失败（HTTP 状态码: xxx），Token 可能已过期或地址不正确`

**Step B — 逐步询问**

使用 AskUserQuestion 或对话方式逐步收集：

1. **GitLab 地址**：`请输入你的 GitLab 实例地址（例如 https://gitlab.example.com）：`
2. **Personal Access Token**：`请输入 GitLab Personal Access Token（需要 api scope）：`
   - 如果用户不知道如何获取，提示：`前往 GitLab → Settings → Access Tokens → 创建新 Token，勾选 api scope`

**Step C — 验证并写入**

```bash
# 用用户提供的值验证连接
curl -s -o /dev/null -w "%{http_code}" \
  -H "PRIVATE-TOKEN: <用户提供的TOKEN>" \
  "<用户提供的URL>/api/v4/user"
```

- **200** → 写入 `scripts/.env`：

```bash
cat > "<skill-base>/scripts/.env" << 'EOF'
GITLAB_URL=<用户提供的URL>
GITLAB_TOKEN=<用户提供的TOKEN>
EOF
```

- **非 200** → 展示错误原因，回到 Step B 重新询问

**Step D — 导出变量并提醒**

```bash
export GITLAB_URL
export GITLAB_TOKEN
```

提醒用户：`scripts/.env 已写入，包含敏感凭据。该文件位于 Skill 目录内，不会被提交到项目仓库。`

## 故障降级表

> 每个故障场景按「触发条件 → 一线修复 → 仍失败兜底」三段式处理。不要跳过兜底步骤。

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `scripts/.env` 不存在 | 进入「对话式引导配置」→ 询问用户 GitLab 地址和 Token → 写入 .env | 引导用户手动创建：`GitLab → Settings → Access Tokens → 创建 PAT（api scope）` |
| `.env` 中 `GITLAB_URL` 或 `GITLAB_TOKEN` 为空 | 进入「对话式引导配置」→ 仅询问缺失的变量 → 覆写 .env | 引导用户手动编辑 `scripts/.env`，展示文件模板 |
| curl 验证返回 `401 Unauthorized` | Token 已过期或被撤销 → 进入「对话式引导配置」→ 重新询问 Token | 引导用户到 GitLab 重新生成 PAT → 勾选 `api` scope |
| curl 验证返回 `403 Forbidden` | Token scope 不足 → 提示用户检查 Token 权限 | 引导用户创建新 Token，确保勾选 `api` scope |
| curl 验证超时 / 连接拒绝 | 检查 URL 是否正确（拼写、协议）→ 检查网络连通性 | 进入「对话式引导配置」→ 重新询问 GitLab 地址 |
| `python scripts/env_check.py` 报 `python3: command not found` | 检查 `python --version`（Windows 可能只有 `python`）→ 用 `python scripts/env_check.py` 重试 | 引导用户安装 Python 3.8+：`winget install Python.Python.3` / `brew install python3` / `sudo apt install python3` |
| 环境检查通过但 `glab` 命令报 `command not found` | `winget install glab` / `brew install glab` / 从 GitLab 官网下载 binary | 降级为纯 REST API 模式：所有 GitLab 操作改用 `curl` + `PRIVATE-TOKEN` 头（见 gitlab-api.md） |
| `glab auth status` 报 `no token configured` | 引导用户执行 `glab auth login` 或设置 `GITLAB_TOKEN` 环境变量 | 如果用户无法交互登录（CI 环境），引导创建 PAT：GitLab → Settings → Access Tokens → 勾选 `api` scope |
| `glab auth status` 报 `401 Unauthorized`（Token 过期） | 引导用户到 GitLab 重新生成 PAT → `glab auth login --token <new-token>` | 检查是否多身份冲突：`glab auth status --hostname` 确认目标 hostname 正确 |
| `glab mr create` 报 `403 Forbidden` | 检查 PAT scope 是否包含 `api`；检查保护分支是否允许该用户 push | 如果是 CI `CI_JOB_TOKEN`，确认 `.gitlab-ci.yml` 中 `GITLAB_TOKEN` 变量已配置且 scope 足够 |
| REST API 返回 `429 Too Many Requests` | 等待 `Retry-After` 头指定的秒数后重试 | 降低批量操作并发：加 `sleep 1` 间隔；检查是否触发了 GitLab 全局限流 |
| `git clone` 超时（>5 分钟） | 检查网络连通性：`curl -I https://$GITLAB_HOST` | 尝试 shallow clone：`git clone --depth 1`；如果是大仓库，用 `--filter=blob:none` 做 partial clone |

---

## 🔴 Agent 执行检查点速查

> **以下是本 Skill 中所有强制停止点的汇总。命中任一条 = 暂停执行、等待用户确认或条件满足。**

| # | 检查点 | 触发条件 | 停止动作 |
|---|--------|---------|---------|
| 1 | 🛑 不可逆操作 | 即将执行 `reset --hard` / `branch -D` / `mr merge` / `issue delete` / `repo archive` | 暂停 → 向用户展示风险 → 获得确认 |
| 2 | 🔴 环境检查 | 首次执行任何 git/GitLab 操作前 | 运行 `python scripts/env_check.py` → 未通过则停止 |
| 3 | 🔴 .env 凭据检查 | 环境检查通过后、执行 GitLab 操作前 | 检查 `scripts/.env` → 读取 GITLAB_URL/TOKEN → curl 验证连接 → 失败则进入对话式引导 |
| 4 | ⚠️ 操作前状态 | 每次写操作（commit/push/merge）前 | `git status` 确认工作区状态 |
| 5 | ⚠️ Token 安全 | 任何涉及凭据的操作 | Token 不落盘、不打印、不嵌入代码 |

## Agent 反模式黑名单

> **以下是 Agent 使用本 Skill 时最常见的错误。命中任一条 = 立即停止、纠正后再继续。**

| # | 反模式 | 为什么错 | 正确做法 |
|---|--------|---------|---------|
| 1 | **Token 硬编码到脚本/配置文件** | Token 泄露 = 整个 GitLab 账号被接管；一旦 commit 到仓库无法撤回 | 始终用环境变量 `$GITLAB_TOKEN` 或 `glab auth login` 交互注入；脚本中用 `$VAR` 引用 |
| 2 | **共享 worktree 中裸 `git stash`** | `git stash` 无标记 → 多人/多 agent 共享时无法区分谁的 stash → 恢复错误 stash 导致代码错乱 | `git stash push -u -m "agent-unique-tag"` → 恢复时用 `git stash apply stash^{/agent-unique-tag}` |
| 3 | **`git push --force` 到 main/develop** | 覆盖他人提交、断裂 CI 历史、不可逆 | 只允许 `--force-with-lease` 到个人 feature 分支；共享分支禁止 force push |
| 4 | **跳过环境检查直接执行** | 工具缺失或版本不满足时，git 命令可能静默产生错误结果（如旧版 git 不支持 `--filter`） | 首次操作前必须运行 `python scripts/env_check.py`（见 🔴 CHECKPOINT） |
| 5 | **静默吞掉 git 命令的 stderr** | git 错误信息在 stderr，只看 stdout 会误以为操作成功（如 clone 失败但 stdout 为空） | 始终检查退出码 `$?`；stderr 重定向到日志或展示给用户 |
| 6 | **批量 API 调用不加间隔** | GitLab 全局限流（默认 600 req/min），触发 429 后所有请求被拒 | 批量操作间加 `sleep 1`；遇到 429 读取 `Retry-After` 头等待 |
| 7 | **直接在 main/develop 上 commit** | 违反分支策略 → MR 审查形同虚设 → 未经 CI 验证的代码进入主干 | 始终创建 feature branch → MR → review → merge 流程 |
| 8 | **MR pipeline 未通过就合并** | CI 失败 = 测试未过/构建断裂 → 合并后污染主干 | 合并前用 `glab ci status` 确认 pipeline 为 `passed` |

## 输出规范

> **Agent 执行完操作后，按以下格式向用户报告结果。**

### 成功操作

```
✅ 操作完成：[操作名称]
- 分支：feature/TICKET-123-desc
- 远端：已推送到 origin
- MR：!42 已创建 → https://gitlab.example.com/group/project/-/merge_requests/42
```

### 失败操作

```
❌ 操作失败：[操作名称]
- 错误：[具体错误信息，来自 stderr]
- 原因：[分析的可能原因]
- 修复建议：[来自故障降级表的具体步骤]
```

### 需要用户确认

```
⚠️ 需要确认：即将执行不可逆操作
- 操作：[具体操作，如 git reset --hard]
- 影响：[影响范围，如 3 个未提交文件将丢失]
- 备份：[已做的备份措施，如已 stash]
- 确认执行？(y/n)
```

## 场景判断指南

> **当用户请求模糊时，按以下规则判断意图。**

| 用户说 | 实际意图 | 加载子文件 | 执行路径 |
|--------|---------|-----------|---------|
| "帮我看看改了什么" | 查看 diff | git-local.md | `git diff` 或 `git diff --cached` |
| "提交代码" | commit + push | git-local.md + workflows.md | `git add` → `git commit`（Angular 格式）→ `git push` |
| "开个 MR" | 创建 MR | gitlab-mr.md | 先确认分支已 push → `glab mr create` → 展示 MR 链接 |
| "CI 挂了" | 排查 pipeline | gitlab-ci.md + troubleshooting.md | `glab ci status` → `glab ci view` → 定位失败 job → 分析日志 |
| "合并这个 MR" | 合并 MR | gitlab-mr.md | 🛑 先检查 pipeline 状态 + 审查状态 → 用户确认 → `glab mr merge` |
| "创建 issue" | 创建 Issue | gitlab-issue.md | 收集标题/描述/标签 → `glab issue create` |
| "这个仓库的信息" | 查看项目 | gitlab-repo.md | `glab repo view` 或 REST API |
| "Token 过期了" | 认证问题 | gitlab-auth.md | 引导重新登录或刷新 PAT |

## 🔴 操作完成自检清单

> **每次操作完成后，逐项对照。未通过任何一项 = 操作未完成。**

| # | 检查项 | 验证方法 |
|---|--------|---------|
| 1 | 命令退出码为 0 | 检查 `$?` 或捕获异常 |
| 2 | 远端状态与预期一致 | `git fetch` + `git status` 确认无意外变更 |
| 3 | 无 Token/密码泄露到输出 | 检查 stdout/stderr 日志中无 `glpat-`、`Bearer` 等敏感字符串 |
| 4 | 用户已被告知操作结果 | 按「输出规范」格式展示结果 |
| 5 | 不可逆操作已获得用户确认 | 回查对话记录中有用户明确的确认消息 |
| 6 | 分支策略合规 | feature 分支未直接 push 到 main/develop；MR 已创建 |
| 7 | 临时资源已清理 | stash 已 pop、临时分支已删除 |
