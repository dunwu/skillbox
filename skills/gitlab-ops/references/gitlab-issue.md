# Issue Management

Covers creating, viewing, updating, and closing Issues, plus linking them to MRs.

## Decision Tree

```
Issue operation?
├── Create Issue → glab issue create
├── List Issues → glab issue list (supports filters)
├── View details → glab issue view <id>
├── Update status/metadata → glab issue update
├── Close/reopen → glab issue close / reopen
├── Add comment → glab issue note
├── Delete → glab issue delete (irreversible, confirm first)
├── Link MR → write "Closes #123" in the MR description
└── Batch operations → script loop + glab issue update
```

## Creating Issues

```bash
# Interactive
glab issue create

# Non-interactive
glab issue create \
  --title "fix(auth): Token not refreshed after expiry" \
  --description "$(cat <<'EOF'
## Problem Description
The user's Token is not automatically refreshed after expiry, resulting in 401.

## Steps to Reproduce
1. Wait for the Token to expire
2. Make an API request

## Expected Behavior
Automatically refresh the Token and retry the request.

## Actual Behavior
Returns 401 Unauthorized.
EOF
)" \
  --label bug,critical \
  --assignee @developer \
  --milestone "Sprint 24"

# Specify a repository
glab issue create -R group/project --title "..."
```

## Viewing and Listing

```bash
# List open Issues (default)
glab issue list

# Filter by criteria
glab issue list --label bug
glab issue list --assignee @user
glab issue list --milestone "Sprint 24"
glab issue list --author @user
glab issue list --search "token refresh"

# Closed / all
glab issue list --closed
glab issue list --all

# JSON output
glab issue list --output json

# View details
glab issue view 123
glab issue view 123 --comments
```

## Updating and Status Changes

```bash
# Modify metadata
glab issue update 123 --title "new title"
glab issue update 123 --label bug,high
glab issue update 123 --assignee @new-dev

# Close / reopen
glab issue close 123
glab issue reopen 123

# Close with a comment (add the comment first, then close)
glab issue note 123 --message "fixed in MR #456"
glab issue close 123

# Add a comment
glab issue note 123 --message "located at AuthFilter.java:87"

# Delete (irreversible)
glab issue delete 123
```

## Linking Issues to MRs

- Writing `Closes #123` or `Fixes #123` in the MR description automatically closes the Issue after merge
- Multiple Issues: `Closes #123, Closes #456`
- Cross-project: `Closes group/other-project#789`

## Issue Templates

Configure Issue templates in the repository to guide reporters into providing complete information.

### Directory Structure

```
project-root/
└── .gitlab/
    └── issue_templates/
        ├── Bug.md          # Bug template
        ├── Feature.md      # Feature request template
        └── Question.md     # Question template
```

When creating an Issue, GitLab offers a template dropdown in the description box.

### Bug Template Example

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

### Feature Template Example

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

### Setting a Default Template

```bash
# Create Default.md under .gitlab/issue_templates/
# When creating a new Issue, Default.md is used if no template is selected
```

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| "issue not found" | Wrong ID or no permission | Confirm the Issue IID and project |
| Creation failed with "title is too short" | Title is empty | Provide a valid title |
| Label does not exist | Label not created yet | Run `glab label create` first or remove the label |
