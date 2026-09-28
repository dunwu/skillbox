# 通用故障排查

## 身份与认证

| 现象 | 排查步骤 |
|------|---------|
| 所有操作 401 | `glab auth status` → Token 过期 → 重新 login |
| SSH 403 | `ssh -T git@host` → 检查 `~/.ssh/config` → 确认 key 已注册 |
| 操作显示错误用户 | `glab auth status` → `auth switch` 或重新 login |
| CI 中 403 | 检查 `$CI_JOB_TOKEN` scope → 用 PAT 替代 |

## Git 操作

| 现象 | 排查步骤 |
|------|---------|
| merge conflict | `git status` 看冲突文件 → 手动解决 → `git add` → commit/rebase --continue |
| detached HEAD | `git branch` 看当前状态 → `git switch <branch>` 回去 |
| rebase 后 push 被拒 | 保护分支不允许改写历史 → 用 merge 代替 force push |
| "refusing to merge unrelated histories" | 确认是否真的需要合并 → `--allow-unrelated-histories` |
| large pack failed | 仓库太大 → `git clone --depth=1` 或 `--filter=blob:none` |
| 误删分支 | `git reflog` 找到 SHA → `git checkout -b <name> <sha>` |
| 误 reset --hard | `git reflog` 找到 reset 前的 SHA → `git reset --hard <sha>` |
| rebase/merge 搞砸了 | `git reset --hard ORIG_HEAD` 回到操作前 |
| 拉错分支/合并错误 | `git reflog` 找到操作前 HEAD → `git reset --hard <sha>` |
| amend 后丢失内容 | `git reflog` 找 amend 前的 SHA → `git reset --hard <sha>` |

## glab CLI

| 现象 | 排查步骤 |
|------|---------|
| command not found | 安装：参考 glab 官方安装文档 |
| "project not found" | 检查 `-R group/project` 格式 → 确认有访问权限 |
| JSON 解析失败 | 检查 `--output json` 是否被支持 → 用 `jq` 验证 |
| 操作超时 | 网络问题 → 检查代理配置 → 重试 |

## 灾难恢复手册

### 场景 1：误删分支

```bash
# 1. 查看 reflog 找到删除前的提交
git reflog
# 输出示例：
# 4e3cd85 HEAD@{1}: commit: 添加登录功能
# 69204cd HEAD@{2}: checkout: moving from my-branch to main

# 2. 从 SHA 恢复分支
git checkout -b my-branch 4e3cd85

# 3. 验证恢复的内容
git log --oneline -5
```

### 场景 2：误执行 reset --hard

```bash
# 1. reflog 找到 reset 前的状态
git reflog
# a1b2c3d HEAD@{0}: reset: moving to HEAD~3
# e4f5g6h HEAD@{1}: commit: 第三个提交
# i7j8k9l HEAD@{2}: commit: 第二个提交
# m0n1o2p HEAD@{3}: commit: 第一个提交

# 2. 恢复到 reset 前的状态
git reset --hard e4f5g6h
```

### 场景 3：rebase/merge 失败

```bash
# 方法 1：用 ORIG_HEAD（Git 自动保存）
git reset --hard ORIG_HEAD

# 方法 2：用 reflog 找到操作前的 HEAD
git reflog
git reset --hard <sha-before-operation>
```

### 场景 4：提交到了错误的分支

```bash
# 1. 在当前分支创建新分支（不切换）
git branch correct-branch

# 2. 当前分支回退
git reset --hard HEAD~1

# 3. 切到正确的分支
git checkout correct-branch
```

### 场景 5：需要跨分支挑选提交

```bash
# 从其他分支挑选特定提交
git cherry-pick <commit-sha>

# 如果冲突
# 解决冲突 → git add → git cherry-pick --continue
# 放弃 → git cherry-pick --abort
```

### 恢复已删除的 Tag

```bash
# 1. 查找不可达的 tag 对象
git fsck --unreachable | grep tag

# 2. 用 update-ref 恢复
git update-ref refs/tags/<tag-name> <hash>
```

### 关键原则

- **reflog 是最后的安全网**，默认保留 90 天
- reflog 只记录本地 HEAD 移动，不跟踪文件内容变更
- `ORIG_HEAD` 在 merge、rebase、pull 等操作前自动设置
- 恢复操作越早越好，时间越长 reflog 条目可能被 GC 清理
