# Merge Request 全生命周期

覆盖 MR 从创建到合并/关闭的完整生命周期。

## 决策树：何时创建 MR？

```
准备创建 MR？
├── 功能开发完成 → 直接创建 MR
├── 需要早期反馈 → 创建 Draft MR（glab mr create --draft）
├── 多个小改动依赖 → 考虑 Stacked MR（glab stack）
└── 还没开始写代码 → 先创建分支，不要急着开 MR
```

## 创建 MR

### 命令模板

```bash
# 交互式创建（推荐首次使用）
glab mr create

# 非交互式（Agent/CI 场景）
glab mr create \
  --title "feat(xxx): 新增用户认证" \
  --description "$(cat <<'EOF'
## Summary
- 实现 OAuth2 认证流程
- 添加 JWT token 刷新机制

## Test plan
- [ ] 单元测试通过
- [ ] 集成测试覆盖
EOF
)" \
  --source-branch feature/auth \
  --target-branch develop \
  --assignee @reviewer1 \
  --reviewer @reviewer2 \
  --label backend,security \
  --milestone "Sprint 24"

# Draft MR
glab mr create --draft --title "WIP: auth flow"

# 复用 commit message 填充
glab mr create --fill

# 指定仓库
glab mr create -R group/project
```

### MR 描述模板

Agent 创建 MR 时应遵循的结构化描述格式：

```markdown
## Summary
<1-3 行概述变更目的>

## Changes
- <具体变更 1>
- <具体变更 2>

## Test plan
- [ ] <验证步骤 1>
- [ ] <验证步骤 2>

## Screenshots (if UI)
<截图或 "N/A">
```

## 查看与列出 MR

```bash
# 列出当前分支的 MR
glab mr view

# 列出所有打开的 MR
glab mr list

# 按条件过滤
glab mr list --author @user
glab mr list --label backend
glab mr list --milestone "Sprint 24"
glab mr list --state merged
glab mr list --state closed

# JSON 输出（Agent 解析）
glab mr list --output json
glab mr list -F json

# 查看特定 MR
glab mr view 123
glab mr view 123 --comments
```

## 审查与协作

### Quick Actions（在 MR 评论中使用）

```
/assign @user              # 指定负责人
/unassign @user            # 取消指定
/reassign @user            # 重新指定
/label ~backend ~security  # 添加标签
/unlabel ~wip              # 移除标签
/milestone %"Sprint 24"    # 设置里程碑
/cc @user                  # 抄送
/merge                     # 合并（需权限）
/approve                   # 批准
/unapprove                 # 取消批准
```

详见 [quick-actions.md](quick-actions.md)。

### 添加评论

```bash
# 普通评论
glab mr note 123 --message "LGTM, 但建议加个空值检查"

# 行级评论（代码评审）
glab mr note 123 --message "这里可能 NPE" \
  --filename src/main/java/Auth.java --line 42
```

## 更新 MR

```bash
# 推送新提交自动更新 MR（分支已关联）
git push origin feature/auth

# 修改 MR 元数据
glab mr update 123 --title "新标题"
glab mr update 123 --assignee @new-reviewer
glab mr update 123 --label backend,urgent
glab mr update 123 --description "新的描述"

# 修改目标分支
glab mr update 123 --target-branch main
```

## 合并 MR

### 决策树

```
如何合并？
├── 标准合并（保留所有提交） → --merge
├── 快进合并（线性历史） → --squash（推荐用于功能分支）
├── 变基后合并 → --rebase
└── 合并后删除分支 → --squash --remove-source-branch
```

```bash
# Squash 合并（推荐，保持历史整洁）
glab mr merge 123 --squash

# 标准合并
glab mr merge 123 --merge

# 合并后删除源分支
glab mr merge 123 --squash --remove-source-branch

# 指定合并提交消息
glab mr merge 123 --squash --squash-message "feat(auth): add OAuth2"

# 设置合并时间（CI 通过后自动合并）
glab mr merge 123 --merge-when-pipeline-succeeds
```

## 关闭 MR

```bash
# 关闭单个 MR
glab mr close 123

# 关闭多个 MR
glab mr close 1 2 3

# 关闭指定仓库的 MR
glab mr close 123 -R group/project

# 附评论后关闭（先评论再关闭）
glab mr note create 123 -m "被 MR #456 替代"
glab mr close 123
```

## Stacked MR（堆叠合并请求）

```bash
# 创建 stack
glab stack create feature-stack

# 基于 commit 范围推断 layers
glab stack infer main..HEAD

# 同步推送所有 layers
glab stack sync

# 变基到最新 main
glab stack sync --update-base

# 只推送不开 MR
glab stack sync --skip-mr-creation

# 带元数据提交
glab stack sync --assignee @owner --reviewer @reviewer --label backend

# 追加改动到当前 layer
glab stack amend

# 只改 commit message
glab stack amend --reword -m "updated message"

# 导航
glab stack next / prev / first / last
glab stack move
glab stack switch              # 交互式选择
glab stack switch stack-name   # 直接切换
```

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| MR 创建失败 "source branch not found" | 分支未推送 | `git push -u origin <branch>` |
| merge conflict | 目标分支有新提交 | `git rebase <target>` 后 push |
| pipeline blocks merge | CI 未通过 | 检查 pipeline 日志，修复后重跑 |
| "cannot force push" | 保护分支不允许 force push | 用普通 push 或联系管理员 |
| MR 显示 outdated | 目标分支已更新 | rebase 或 merge 目标分支 |
