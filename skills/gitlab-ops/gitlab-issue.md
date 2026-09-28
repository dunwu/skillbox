# Issue 管理

覆盖 Issue 的创建、查看、更新、关闭及与 MR 的关联。

## 决策树

```
Issue 操作？
├── 创建 Issue → glab issue create
├── 列出 Issue → glab issue list（支持过滤）
├── 查看详情 → glab issue view <id>
├── 更新状态/元数据 → glab issue update
├── 关闭/重开 → glab issue close / reopen
├── 添加评论 → glab issue note
├── 删除 → glab issue delete（不可逆，需确认）
├── 链接 MR → 在 MR 描述中写 "Closes #123"
└── 批量操作 → 脚本循环 + glab issue update
```

## 创建 Issue

```bash
# 交互式
glab issue create

# 非交互式
glab issue create \
  --title "fix(auth): Token 过期未刷新" \
  --description "$(cat <<'EOF'
## 问题描述
用户 Token 过期后未自动刷新，导致 401。

## 复现步骤
1. 等待 Token 过期
2. 发起 API 请求

## 期望行为
自动刷新 Token 并重试请求。

## 实际行为
返回 401 Unauthorized。
EOF
)" \
  --label bug,critical \
  --assignee @developer \
  --milestone "Sprint 24"

# 指定仓库
glab issue create -R group/project --title "..."
```

## 查看与列出

```bash
# 列出打开的 Issue（默认）
glab issue list

# 按条件过滤
glab issue list --label bug
glab issue list --assignee @user
glab issue list --milestone "Sprint 24"
glab issue list --author @user
glab issue list --search "token refresh"

# 已关闭/全部
glab issue list --closed
glab issue list --all

# JSON 输出
glab issue list --output json

# 查看详情
glab issue view 123
glab issue view 123 --comments
```

## 更新与状态变更

```bash
# 修改元数据
glab issue update 123 --title "新标题"
glab issue update 123 --label bug,high
glab issue update 123 --assignee @new-dev

# 关闭/重开
glab issue close 123
glab issue reopen 123

# 关闭时附评论（先添加评论，再关闭）
glab issue note 123 --message "已在 MR #456 中修复"
glab issue close 123

# 添加评论
glab issue note 123 --message "已定位到 AuthFilter.java:87"

# 删除（不可逆）
glab issue delete 123
```

## Issue 与 MR 关联

- MR 描述中写 `Closes #123` 或 `Fixes #123`，合并后自动关闭 Issue
- 多个 Issue：`Closes #123, Closes #456`
- 跨项目：`Closes group/other-project#789`

## Issue 模板

在仓库中配置 Issue 模板，引导提问者提供完整信息。

### 目录结构

```
项目根目录/
└── .gitlab/
    └── issue_templates/
        ├── Bug.md          # 缺陷模板
        ├── Feature.md      # 功能需求模板
        └── Question.md     # 咨询模板
```

创建 Issue 时，GitLab 会在描述框中提供模板下拉选择。

### Bug 模板示例

```markdown
## 问题描述
<!-- 清晰简洁地描述问题 -->

## 复现步骤
1. 打开 '...'
2. 点击 '...'
3. 观察到 '...'

## 期望行为
<!-- 描述期望的结果 -->

## 实际行为
<!-- 描述实际发生的情况 -->

## 环境信息
- 版本：[e.g. v1.2.0]
- 浏览器/系统：[e.g. Chrome 120 / Windows 11]

## 日志/截图
<!-- 附上相关日志或截图 -->

## 标签
/label ~bug
```

### Feature 模板示例

```markdown
## 需求描述
<!-- 作为 [角色]，我希望 [功能]，以便 [价值] -->

## 验收标准
- [ ] 条件 1
- [ ] 条件 2

## 设计参考
<!-- 附上设计稿或原型链接 -->

## 标签
/label ~feature
```

### 指定默认模板

```bash
# 在 .gitlab/issue_templates/ 中创建 Default.md
# 新建 Issue 时如果没有选择模板，将使用 Default.md
```

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| "issue not found" | ID 错误或无权限 | 确认 Issue IID 和项目 |
| 创建失败 "title is too short" | 标题为空 | 提供有效标题 |
| label 不存在 | 标签未创建 | 先 `glab label create` 或去掉该标签 |
