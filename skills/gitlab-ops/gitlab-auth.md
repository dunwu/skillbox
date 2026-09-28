# 认证与身份管理

覆盖 glab 登录、SSH key、PAT、多身份隔离。

## 决策树

```
认证问题？
├── 首次登录 → glab auth login
├── 检查当前身份 → glab auth status
├── 切换账号 → glab auth logout + glab auth login（glab 无 auth switch 子命令）
├── Token 过期 → 重新 login
├── SSH key 问题 → 检查 ~/.ssh/ 配置
├── CI/CD 中的认证 → CI_JOB_TOKEN / 环境变量
├── 多 Agent 身份隔离 → per-agent env 文件
```

## 登录与状态

```bash
# 交互式登录（浏览器 OAuth）
glab auth login

# Token 方式登录
glab auth login --stdin < my-token.txt
echo "$GITLAB_TOKEN" | glab auth login --stdin

# 指定 GitLab 实例
glab auth login --hostname gitlab.example.com

# 查看当前身份
glab auth status
glab auth status --hostname gitlab.example.com

# 切换身份（glab 无 auth switch，需 logout + login）
glab auth logout --hostname gitlab.example.com
echo "$NEW_TOKEN" | glab auth login --hostname gitlab.example.com --stdin
```

## SSH Key 诊断

```bash
# 测试 SSH 连接
ssh -T git@gitlab.example.com

# 查看已注册的 SSH key
glab ssh-key list

# JSON 输出
glab ssh-key list --output json
```

## Personal Access Token（PAT）

```bash
# 列出 Token
glab token list
```

### Token 作用域

| Scope | 能力 |
|-------|------|
| `api` | 完整 API 读写 |
| `read_api` | 只读 API |
| `read_user` | 读取用户信息 |
| `sudo` | 以其他用户身份执行 |
| `read_repository` / `write_repository` | 仓库操作 |

## CI/CD 中的认证

```bash
# CI 环境自动注入
$CI_JOB_TOKEN    # 自动可用，生命周期同 pipeline

# 手动配置（Agent 场景）
export GITLAB_TOKEN="glpat-xxxxx"
export GITLAB_HOST="gitlab.example.com"

# 多 Agent 身份隔离
# 每个 Agent 独立 env 文件
source .env.agent-alpha
glab auth status  # 验证身份正确
```

## 通过 .env 文件配置环境变量

### 文件格式

在项目根目录或用户主目录创建 `.env` 文件，每行一个 `KEY=VALUE`：

```bash
# .env 示例
GITLAB_TOKEN=glpat-xxxxxxxxxxxx
GITLAB_HOST=gitlab.xxx.xxx
GITLAB_USER=username
```

### 规则

1. **`.env` 必须加入 `.gitignore`** — Token 一旦 commit 到仓库无法撤回
2. **不要使用引号包裹值** — `GITLAB_TOKEN=glpat-xxx`（不是 `"glpat-xxx"`）
3. **不要提交 `.env`** — 只提交 `.env.example`（占位符，无真实值）

### 加载方式

```bash
# Linux / macOS / Git Bash
set -a
source .env
set +a

# 验证
echo $GITLAB_TOKEN
glab auth status
```

```powershell
# Windows CMD
for /f "tokens=1,2 delims==" %a in (.env) do set %a=%b

# Windows PowerShell
Get-Content .env | ForEach-Object {
    if ($_ -match "^(.+?)=(.*)$") { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "User") }
}
# 需重新打开终端生效，或手动刷新当前会话：
$env:GITLAB_TOKEN = [Environment]::GetEnvironmentVariable("GITLAB_TOKEN", "User")
```

### .env.example 模板

提交到仓库供团队成员参考：

```bash
# .env.example — 复制为 .env 后填入真实值
GITLAB_TOKEN=glpat-your-token-here
GITLAB_HOST=gitlab.example.com
GITLAB_USER=your-username
```

### 多环境 / 多身份

```bash
# 不同 GitLab 实例使用不同 env 文件
source .env.gitlab-work    # 工作实例
source .env.gitlab-personal # 个人实例

# 验证当前身份
glab auth status --hostname $GITLAB_HOST
```

### 安全检查清单

| 检查项 | 命令 |
|--------|------|
| `.env` 已在 `.gitignore` 中 | `git check-ignore .env`（应返回路径） |
| `.env` 未被跟踪 | `git ls-files .env`（应无输出） |
| `.env` 未出现在历史中 | `git log --all --full-history -- .env`（应无输出） |

## 凭据缓存

避免每次 push/pull 都输入用户名密码。

```bash
# 内存缓存（默认 15 分钟）
git config --global credential.helper cache

# 设置超时时间（秒）
git config --global credential.helper 'cache --timeout=3600'  # 1 小时

# macOS 钥匙串
git config --global credential.helper osxkeychain

# Windows 凭据管理器
git config --global credential.helper manager

# Linux Secret Service
git config --global credential.helper libsecret
```

### Agent 环境注意

- CI/CD 中不要使用 credential helper，改用 `$CI_JOB_TOKEN` 或环境变量
- Agent 沙箱中凭据应通过环境变量注入，不依赖缓存
- 共享机器上避免使用 `manager`（凭据对所有用户可见）

## 多身份管理（Agent 场景）

```bash
# 预检：确认当前身份
glab auth status

# 身份不匹配时的修复步骤
# 1. 退出当前身份
glab auth logout --hostname gitlab.example.com
# 2. 用正确 Token 重新登录
echo "$CORRECT_TOKEN" | glab auth login --hostname gitlab.example.com --stdin
# 3. 验证
glab auth status
```

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| "authentication failed" | Token 过期或无效 | 重新 login 或轮换 Token |
| 身份不对 | 多账号混淆 | `glab auth status` 检查；`auth logout` + `auth login` 切换 |
| CI 中 403 | Token scope 不足 | 检查 Token 的 scopes 是否包含所需权限 |
