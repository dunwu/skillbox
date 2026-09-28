# 其他 GitLab 功能

覆盖 Release、Snippet、Variable、Label、Milestone、Runner、Package、Todo 等。

## Release（发布）

```bash
# 列出 Release
glab release list

# 创建 Release
glab release create v1.0.0 \
  --name "v1.0.0" \
  --notes "$(cat <<'EOF'
## What's Changed
- 新增用户认证模块
- 修复 Token 刷新问题
EOF
)" \
  --assets-links '[{"name":"binary","url":"https://..."}]'

# 查看 Release
glab release view v1.0.0

# 删除 Release
glab release delete v1.0.0
```

## Snippet（代码片段）

```bash
# 创建 Snippet
glab snippet create main.go --title "示例代码"

# 查看（glab 无 snippet list 子命令，通过 REST API 列出）
glab snippet view <id>

# REST API 列出 Snippet
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/snippets" | jq .
```

## Variable（变量管理）

```bash
# 项目变量
glab variable list
glab variable set DEPLOY_URL "https://staging.example.com"
glab variable set SECRET_KEY "xxx" --masked --protected
glab variable get DEPLOY_URL
glab variable delete DEPLOY_URL

# 组变量
glab variable list -g my-group
glab variable set API_KEY "xxx" -g my-group

# 环境变量类型
# --masked: 日志中隐藏
# --protected: 仅保护分支/标签可用
# --raw: 不展开变量引用
```

## Label（标签管理）

```bash
glab label list
glab label create --name bug --color "#FF0000" --description "缺陷"
glab label create --name feature --color "#00FF00"
```

## Milestone（里程碑）

```bash
glab milestone list --project group/project
glab milestone list --group my-group
glab milestone create --title "Sprint 25" --start-date 2026-09-22 --due-date 2026-10-03
```

## Runner（CI Runner 管理）

```bash
# 列出项目 Runner
glab runner list

# 注册 Runner（需 admin）
glab runner register

# 删除 Runner
glab runner delete <runner-id>
```

## Package（包管理）

```bash
# 列出项目包
glab packages list

# 删除包
glab packages delete <package-id>
```

## Todo（待办）

```bash
glab todo list
glab todo list --type=MergeRequest
glab todo done 123
glab todo done --all
```

## User（用户信息）

```bash
# 当前用户信息（通过 REST API）
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/user" | jq .
```

## Work Items

glab 暂无 work-item 子命令，通过 REST API 或 GitLab Web UI 操作。

```bash
# REST API 列出工作项（需 GitLab Premium/Ultimate）
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/work_items" | jq .
```
