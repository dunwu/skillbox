# 本地 Git 操作

覆盖所有不依赖 GitLab 服务端的纯本地 git 操作。

## 安全规范（前置）

### 不可逆操作确认清单

| 操作 | 风险等级 | 确认要求 |
|------|---------|---------|
| `git reset --hard` | 高 | 必须用户确认；禁止对未提交工作执行 |
| `git checkout` / `restore` | 中 | 未提交改动时先 stash |
| `git rebase`（交互式） | 中 | 禁止 `--no-edit`；禁止 `-i`（需交互输入） |
| `git branch -D` | 中 | 确认分支已合并或用户明确要丢弃 |

### 通用安全规则

- 操作前 `git status` 确认工作区状态
- 大操作前 `git stash -u` 或创建备份分支
- 共享 worktree 中禁止裸 `git stash`（用唯一 tag）

## Config

### 三级配置体系

```
配置优先级（高→低）：
├── 仓库级  .git/config          ← git config <key>
├── 用户级  ~/.gitconfig          ← git config --global <key>
└── 系统级  /etc/gitconfig        ← git config --system <key>
```

### 常用配置

```bash
# 用户身份（必须）
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# 凭据缓存（避免重复输入密码）
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=3600'  # 1 小时

# 默认分支名
git config --global init.defaultBranch main

# 拉取策略
git config --global pull.rebase true     # pull 时默认 rebase 而非 merge
git config --global fetch.prune true     # fetch 时自动清理已删除的远端分支

# 别名（提升效率）
git config --global alias.s  status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --graph --oneline --decorate --all -20"
git config --global alias.ds "diff --staged"
git config --global alias.unpushed "log @{u} --oneline"

# 查看当前配置
git config --list
git config --list --global
git config user.name   # 查看特定项
```

### Agent 注意

- 不要在 Agent 沙箱中修改 `--global` 或 `--system` 配置，只使用 `--local`（仓库级）
- 凭据缓存在 CI 环境中应禁用，改用环境变量注入 Token

## Clone

### 决策树

```
需要 clone？
├── 只需读 diff/log → git clone --depth=1（shallow，省带宽）
├── 需要完整历史 → git clone（完整）
├── 仓库很大且只需某分支 → git clone --single-branch -b <branch>
├── 磁盘空间紧张 → git clone --filter=blob:none（partial clone）
└── 需要子模块 → git clone --recurse-submodules
```

### 命令模板

```bash
# 标准 clone
git clone <url> [directory]

# Shallow clone（只要最新快照）
git clone --depth=1 <url>

# 指定分支
git clone --single-branch -b <branch> <url>

# 带子模块
git clone --recurse-submodules <url>

# 指定协议
git clone https://gitlab.example.com/group/project.git
git clone git@gitlab.example.com:group/project.git
```

### 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| Authentication failed | 凭据过期或无权限 | 检查 SSH key 或 PAT |
| RPC failed; curl 18 | 大文件传输中断 | `git config http.postBuffer 524288000` |
| shallow update not allowed | 服务端禁止 shallow | 去掉 `--depth`，完整 clone |
| fatal: destination exists | 目录已存在 | 删除或换目录 |

## Diff

### 决策树

```
需要看什么差异？
├── 工作区 vs 暂存区 → git diff（无参数）
├── 暂存区 vs HEAD → git diff --cached / --staged
├── 工作区+暂存 vs HEAD → git diff HEAD
├── 两个分支/commit 之间 → git diff <A>..<B>
├── 某文件的历史变更 → git log -p -- <file>
├── 两个版本的某文件 → git diff <A>:<file> <B>:<file>
└── 统计变更概况 → git diff --stat <A>..<B>
```

### 命令模板

```bash
# 未暂存的变更
git diff

# 已暂存的变更
git diff --cached

# 所有变更（未暂存+已暂存）
git diff HEAD

# 两个 ref 之间
git diff main..feature-branch
git diff abc123..def456

# 只看统计
git diff --stat main..HEAD

# 只看某文件
git diff main..HEAD -- path/to/file.java

# 忽略空白变更
git diff -w main..HEAD

# 输出为 patch 文件
git diff main..HEAD > changes.patch
```

### Agent 使用指南

- diff 输出可能很长，优先用 `--stat` 了解概况再定向查看
- 大仓库用 `--diff-filter=ACMR` 只看新增/修改/重命名
- 二进制文件用 `--binary` 才能看到差异

## Log

### 决策树

```
需要了解什么历史？
├── 最近 N 条提交 → git log -n <N> --oneline
├── 某文件的变更历史 → git log -- <file>
├── 谁改了哪一行 → git blame <file>
├── 两个分支的分叉点 → git merge-base <A> <B>
├── 某段时间内的提交 → git log --since/--after/--until/--before
├── 某人的提交 → git log --author=<name>
└── 包含某关键词的提交 → git log --grep=<keyword>
```

### 命令模板

```bash
# 简洁格式
git log --oneline -20

# 带文件变更统计
git log --stat -5

# 图形化分支历史
git log --oneline --graph --all -30

# 某文件的完整历史（含重命名追踪）
git log --follow -- <file>

# 某行是谁改的
git blame -L 10,20 -- <file>

# 搜索提交消息
git log --grep="fix:" --oneline

# 两个 ref 之间的所有提交
git log --oneline main..HEAD

# 自定义格式（Agent 解析友好）
git log --format="%H|%an|%ae|%ai|%s" -10
```

### Agent 使用指南

- 始终用 `--format` 输出结构化数据便于解析
- `--no-merges` 过滤合并提交，只看实质变更
- 大仓库限制 `-n` 避免输出过长

## Branch

### 决策树

```
分支操作？
├── 查看分支 → git branch / git branch -a
├── 创建不切换 → git branch <name>
├── 创建并切换 → git checkout -b <name> / git switch -c <name>
├── 删除已合并分支 → git branch -d <name>
├── 强制删除未合并 → git branch -D <name>（需确认）
├── 重命名当前分支 → git branch -m <new-name>
└── 设置上游跟踪 → git branch -u origin/<branch>
```

### 命名约定

```
feature/<ticket>-<short-desc>    # 新功能
bugfix/<ticket>-<short-desc>     # 缺陷修复
hotfix/<ticket>-<short-desc>     # 紧急修复
release/<version>                # 发布分支
```

### 分支维护

```bash
# 检查分支是否已合并到当前分支
git branch --merged main
git branch --merged HEAD

# 查看未合并的分支
git branch --no-merged main

# 清理已合并的本地分支
git branch --merged main | grep -v "main" | xargs git branch -d

# 清理远端已删除的本地跟踪分支
git fetch --prune

# 检查两个分支间的差异提交
git log --oneline --left-right main...feature-branch

# 从错误分支恢复：误提交到 main
git branch feature/correct-branch  # 在当前 HEAD 创建新分支
git reset --hard HEAD~1            # main 回退一个提交
git checkout feature/correct-branch # 切到正确的分支
```

## Merge vs Rebase

### 决策树

```
整合其他分支的变更？
├── 需要保留合并历史 → git merge
│   ├── 快进即可 → git merge --ff-only
│   └── 保留合并节点 → git merge --no-ff
├── 需要线性历史 → git rebase
│   ├── 变基到目标 → git rebase <target>
│   └── 继续冲突后 → git rebase --continue
├── 撤销合并 → git revert <merge-commit> -m 1
└── 不确定 → 默认 merge（安全，不改写历史）
```

### 关键规则

- **已推送的提交不要 rebase** — rebase 改写 SHA，push 后别人拉取会冲突
- 个人分支可以 rebase 保持整洁；共享分支用 merge
- 解决冲突后：merge 用 `git add` + `git commit`，rebase 用 `git add` + `git rebase --continue`

### 进阶合并策略

```bash
# Squash merge：将分支所有提交压缩为一个
git merge --squash feature-branch
git commit -m "feat: 实现 XXX 功能"

# 保留合并证据但不自动提交
git merge --no-ff --no-commit feature-branch
# 检查合并结果 → 满意后手动 commit

# 组合多个未推送的提交（交互式 rebase）
# 注意：Agent 环境不支持交互式 rebase，用 reset --soft 替代
git log --oneline HEAD~5..HEAD  # 确认要组合的提交
git reset --soft HEAD~3          # 回退 3 个提交，保留修改在暂存区
git commit -m "合并后的提交消息"
```

## Cherry-pick

从其他分支挑选特定提交应用到当前分支。

```bash
# 挑选单个提交
git cherry-pick abc123

# 挑选多个提交
git cherry-pick abc123 def456 ghi789

# 挑选一个范围（不含起始）
git cherry-pick abc123..def456

# 保留原提交者信息
git cherry-pick --no-commit abc123  # 暂存但不提交，手动 commit 时可改消息

# 遇到冲突
git cherry-pick abc123
# 解决冲突 → git add → git cherry-pick --continue
# 放弃：git cherry-pick --abort
```

### 典型场景

```
场景：bug 修复在 feature 分支，也需要应用到 hotfix 分支
1. git checkout hotfix/urgent
2. git cherry-pick <bugfix-commit-sha>
3. 解决冲突（如有）→ git cherry-pick --continue
4. git push
```

## 撤销与恢复

### 决策树

```
需要撤销什么？
├── 撤销暂存（保留修改） → git reset HEAD <file>
├── 撤销工作区修改 → git checkout HEAD -- <file> / git restore <file>
├── 撤销最近提交（保留修改在暂存区） → git reset --soft HEAD~1
├── 撤销最近提交（保留修改在工作区） → git reset --mixed HEAD~1
├── 撤销最近提交（丢弃所有修改） → git reset --hard HEAD~1（危险！）
├── 创建反向提交（安全，不改写历史） → git revert <commit>
├── 撤销 merge → git revert <merge-commit> -m 1
├── 撤销 rebase/merge → git reset --hard ORIG_HEAD
├── 找回误删的提交/分支 → git reflog → git reset --hard <sha>
└── 修改最近提交消息 → git commit --amend -m "新消息"
```

### reflog — 最后的安全网

`git reflog` 记录 HEAD 的每一次移动，即使提交已被 reset 或分支被删除也能找回。

```bash
# 查看 HEAD 历史
git reflog

# 输出示例：
# a1b2c3d HEAD@{0}: checkout: moving from feature to main
# e4f5g6h HEAD@{1}: commit: fix: 修复登录逻辑
# i7j8k9l HEAD@{2}: checkout: moving from main to feature

# 恢复到任意历史状态
git reset --hard e4f5g6h

# 找回误删分支
git reflog  # 找到删除前的 commit SHA
git checkout -b recovered-branch <sha>
```

**关键**：reflog 只保留本地操作（默认 90 天），不跟踪文件内容变更，不记录跨仓库操作。

### ORIG_HEAD

Git 在执行 merge、rebase 等危险操作前，会将原始 HEAD 保存到 `ORIG_HEAD`。

```bash
# 撤销刚完成的 rebase 或 merge
git reset --hard ORIG_HEAD
```

## Stash

### 决策树

```
需要临时保存工作区？
├── 保存所有（含未跟踪） → git stash -u
├── 保存并附描述 → git stash push -m "描述"
├── 只保存部分文件 → git stash push -p（交互选择 hunk）
├── 恢复最近 stash → git stash pop
├── 恢复但不删除 → git stash apply
├── 恢复指定 stash → git stash pop stash@{2}
└── 查看 stash 列表 → git stash list
```

### 共享 worktree 警告

- 裸 `git stash` 在共享环境会互相干扰
- 安全做法：`git stash push -u -m "unique-tag-$(date +%s)"` 恢复时用精确引用

## 暂存区操作

### 部分暂存

```bash
# 暂存文件的某些 hunk（交互模式）
git add -p <file>
# y = 暂存此 hunk, n = 跳过, s = 拆分, e = 手动编辑, q = 退出

# 暂存新文件但不跟踪内容（先标记再选择）
git add -N <file>
git add -p <file>  # 现在可以选择具体行

# 把暂存区和工作区互换（暂存的变未暂存，未暂存的变暂存）
git stash -k       # stash 未暂存的部分
git reset --hard   # 清除工作区（保留暂存区）
git stash pop      # 恢复之前未暂存的内容
git add -A         # 现在原来的未暂存变成了暂存
```

### 暂存区操作决策

```
想做什么？
├── 暂存整个文件 → git add <file>
├── 暂存所有修改 → git add -A
├── 暂存某文件的某些行 → git add -p <file>
├── 取消暂存 → git reset HEAD <file>
└── 取消暂存但保留修改 → git restore --staged <file>
```

## 多远程仓库

### 同时推送到多个远程

```bash
# 查看当前远程
git remote -v

# 添加多个推送地址到同一远程
git remote set-url --add --push origin git@github.com:user/repo.git
git remote set-url --add --push origin git@gitlab.com:user/repo.git

# 验证配置
git remote -v
# origin 应显示两个 push URL

# 一次 push 同时推送到两个仓库
git push origin main
```

### 同步上游 Fork

```bash
# 添加上游仓库
git remote add upstream https://gitlab.example.com/original/repo.git

# 拉取上游更新
git fetch upstream

# 合并到本地分支
git merge upstream/main

# 或 rebase
git rebase upstream/main
```

## Commit 规范

### Angular Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**各部分规则：**

| 部分 | 规则 |
|------|------|
| `type` | **必填**，见下方类型表 |
| `scope` | 可选，影响范围（模块名或组件名），见 Scope 参考 |
| `subject` | **必填**，简述改动，不超过 50 字符，首字母小写，不加句号 |
| `body` | 可选，详细说明改动原因与影响面 |
| `footer` | 可选，Breaking Change 标记或关联 Issue（如 `Closes #123`） |

**type 类型：**

| type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(biz-author): add article publish workflow` |
| `fix` | 缺陷修复 | `fix(dal): resolve NPE when Redis timeout` |
| `refactor` | 重构（不新增功能、不修复 Bug） | `refactor(core): extract ResultCode to enum` |
| `docs` | 文档变更 | `docs: update README for local setup` |
| `style` | 代码格式（不影响逻辑） | `style: apply uniform indentation` |
| `test` | 测试用例 | `test(biz-author): add unit tests for service` |
| `chore` | 构建/工具/依赖变更 | `chore: upgrade mybatis-plus to 3.5.9` |
| `perf` | 性能优化 | `perf(redis): use pipeline for batch queries` |
| `ci` | CI/CD 配置变更 | `ci: add PMD check to pipeline` |
| `build` | 构建系统 | `build: update flatten-maven-plugin config` |
| `revert` | 回退提交 | `revert: revert feat(biz-author): add publish` |

**Scope 取值规则：**

> Scope 必须对应代码库中一个**可定位的物理或逻辑分区**（目录、包、模块、层），且同一项目内粒度一致。

| 模式 | 适用场景 | 示例 |
|------|---------|------|
| 目录/包名 | 单体或 monorepo 子包 | `auth`、`payment`、`dal-redis` |
| 架构层 | 分层明确的项目 | `api`、`service`、`repo`、`config` |
| 子模块名 | Maven/Gradle 多模块 | `biz-chat`、`biz-review`、`ocp-bom` |

- 用**名词**，不用动词（`auth` 而非 `login`）
- 看到 scope 应能直接定位到对应目录或模块
- 同一项目内粒度统一，不混用模块级和功能级

**正确示例：**

```
feat(biz-author): add article publish workflow

实现文章发布功能，包含状态机流转和消息通知。
- 新增 ArticlePublishService 领域服务
- 新增 ARTICLE_PUBLISH ResultCode

fix(dal): resolve connection leak in HBase pool

chore: upgrade redis to 4.0.12 in bom
```

**错误示例：**

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

### 提交纪律

- **MUST** 一次提交只包含一个逻辑改动（单一职责）
- **MUST NOT** 提交编译失败或测试未通过的代码
- **MUST NOT** 提交包含敏感信息（密钥、密码、Token）的文件
- **MUST** 在合并 MR 前确保 CI 流水线全部通过

### Agent 提交规则

- 提交前确认用户明确要求（不要自动提交）
- 提交消息必须描述「为什么改」而非「改了什么」
- 不要把不相关文件一起 `git add .`，按文件精确暂存
- 不要把 `.env`、凭据文件、`node_modules` 等纳入提交

## .gitignore

### 常用模板

```bash
# 查看被忽略的文件
git ls-files --others --ignored --exclude-standard

# 检查某文件为何被忽略
git check-ignore -v <file>
```

```gitignore
# 编译产物
*.class
*.jar
*.war
target/
build/
dist/

# IDE
.idea/
.vscode/
*.iml
*.swp

# 依赖
node_modules/
vendor/

# 日志
*.log
logs/

# 系统文件
.DS_Store
Thumbs.db

# 环境配置（含敏感信息）
.env
.env.local
*.pem
*.key
```

### 规则说明

```
*.log          # 忽略所有 .log 文件
/build/        # 忽略所有名为 build 的目录
/dist/         # 忽略根目录下的 dist 目录
!important.log # 不忽略此文件（取反）
*.tmp          # 忽略所有 .tmp 文件
```

**已跟踪文件不会被 .gitignore 忽略**。如需停止跟踪：

```bash
git rm -r --cached .
git add .
git commit -m "chore: 重新应用 .gitignore 规则"
```

## .gitattributes

解决跨平台 LF/CRLF 行尾差异。

```gitattributes
# 默认：自动检测文本文件，工作区使用 LF
* text=auto eol=lf

# 明确标记文本文件
*.java text
*.js text
*.ts text
*.py text
*.md text
*.xml text
*.yml text
*.json text

# Shell 脚本强制 LF
*.sh text eol=lf

# Windows 批处理强制 CRLF
*.bat text eol=crlf

# 二进制文件不转换
*.jar binary
*.png binary
*.jpg binary
*.pdf binary
*.zip binary
```

## Git Hooks

### 常用客户端 Hook

| Hook | 触发时机 | 典型用途 |
|------|---------|---------|
| `pre-commit` | `git commit` 执行前 | lint 检查、格式校验、测试 |
| `prepare-commit-msg` | 编辑器打开前 | 自动注入模板信息 |
| `commit-msg` | 提交消息确认后 | 校验 commit message 格式 |
| `post-commit` | 提交完成后 | 通知、日志 |
| `pre-push` | `git push` 执行前 | 运行测试、校验分支保护 |

### 配置方式

```bash
# 方式 1：直接编辑 .git/hooks/
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 方式 2：使用 husky（JS 项目推荐）
npm i -D husky
npx husky init
# 编辑 .husky/pre-commit:
# npm test

# 方式 3：指定 hooks 目录
git config core.hooksPath .githooks/
```

### Agent 与 Hooks

- Agent 执行 `git commit` 时 hooks 会正常触发
- 如果 hook 导致提交失败，分析失败原因并修复后重试
- **不要** 用 `--no-verify` 跳过 hooks，除非用户明确要求
- CI 环境中 hooks 通常不执行（CI 有自己的检查步骤）

## Tag

### 命令模板

```bash
# 轻量标签
git tag v1.0.0

# 附注标签（推荐）
git tag -a v1.0.0 -m "Release 1.0.0"

# 给历史提交打标签
git tag -a v0.9.0 abc123 -m "Release 0.9.0"

# 推送标签
git push origin v1.0.0
git push origin --tags

# 列出标签
git tag -l "v1.*"
```

## 通用故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| detached HEAD | checkout 了 commit 而非分支 | `git switch <branch>` 回到分支 |
| merge conflict | 两边改了同一处 | 手动编辑 → `git add` → `git commit`/`rebase --continue` |
| rebase conflict | 变基时历史冲突 | 手动编辑 → `git add` → `git rebase --continue`；放弃用 `git rebase --abort` |
| fatal: not a git repository | 不在仓库目录 | `cd` 到仓库根目录 |
| permission denied (publickey) | SSH key 未配置 | `ssh -T git@host` 测试；检查 `~/.ssh/` |
| fatal: refusing to merge unrelated histories | 两个仓库无共同祖先 | `git merge --allow-unrelated-histories`（谨慎） |
| 误删分支/误 reset | 执行了破坏性操作 | `git reflog` 找到 SHA → `git reset --hard <sha>` |
| push 被拒（non-fast-forward） | 远端有新提交 | `git pull --rebase` 后重试 |
| amend 后 push 被拒 | rebase/amend 改写了已推送的 SHA | 创建新提交而非修改已推送提交；共享分支避免 amend 已推送提交 |
| LF/CRLF 差异 | 跨平台行尾不一致 | 配置 `.gitattributes`；`git config core.autocrlf` |
