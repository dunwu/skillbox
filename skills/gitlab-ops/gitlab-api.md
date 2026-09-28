# REST API 高级操作

glab 未覆盖的操作通过 REST API 完成。使用 `curl` + `PRIVATE-TOKEN` 头。

## 基础模板

```bash
GITLAB_HOST="gitlab.example.com"
TOKEN="glpat-xxxxx"
PROJECT_ID=123

# GET 请求
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID" | jq .

# POST 请求
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"title":"New Issue","labels":["bug"]}' \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/issues" | jq .

# PUT 请求
curl -s --request PUT --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"state_event":"close"}' \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/issues/1" | jq .

# DELETE 请求
curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/issues/1"
```

## 常用 API 端点

### 项目

```bash
GET    /api/v4/projects                           # 列出项目
GET    /api/v4/projects/:id                       # 项目详情
POST   /api/v4/projects                           # 创建项目
PUT    /api/v4/projects/:id                       # 更新项目
```

### 合并请求

```bash
GET    /api/v4/projects/:id/merge_requests         # 列出 MR
GET    /api/v4/projects/:id/merge_requests/:iid    # MR 详情
POST   /api/v4/projects/:id/merge_requests         # 创建 MR
PUT    /api/v4/projects/:id/merge_requests/:iid    # 更新 MR
POST   /api/v4/projects/:id/merge_requests/:iid/merge  # 合并
```

### 仓库文件

```bash
GET    /api/v4/projects/:id/repository/files/:path?ref=main    # 获取文件
POST   /api/v4/projects/:id/repository/files/:path             # 创建文件
PUT    /api/v4/projects/:id/repository/files/:path             # 更新文件
DELETE /api/v4/projects/:id/repository/files/:path             # 删除文件
POST   /api/v4/projects/:id/repository/commits                 # 批量提交
```

### 变量

```bash
GET    /api/v4/projects/:id/variables              # 列出项目变量
POST   /api/v4/projects/:id/variables              # 创建变量
PUT    /api/v4/projects/:id/variables/:key         # 更新变量
DELETE /api/v4/projects/:id/variables/:key         # 删除变量
```

### Webhook

```bash
GET    /api/v4/projects/:id/hooks                  # 列出 Webhook
POST   /api/v4/projects/:id/hooks                  # 创建 Webhook
PUT    /api/v4/projects/:id/hooks/:hook_id         # 更新 Webhook
DELETE /api/v4/projects/:id/hooks/:hook_id         # 删除 Webhook
```

## 分页

```bash
# 默认每页 20 条，最大 100
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects?per_page=100&page=2" | jq .

# 使用 Link header 遍历所有页
curl -sI --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects?per_page=100" | grep -i link
```

## Agent 使用指南

- 始终用 `jq` 解析 JSON 响应
- 写操作前先 GET 确认目标存在
- 批量操作加 sleep 间隔，避免触发限流
- 错误响应格式：`{"message":"error description"}`，HTTP 状态码标识错误类型

## 故障排查

| HTTP 状态码 | 含义 | 处理 |
|-------------|------|------|
| 400 | 请求参数错误 | 检查 body 格式 |
| 401 | 未认证 | Token 无效或过期 |
| 403 | 无权限 | Token scope 不足 |
| 404 | 资源不存在 | 检查 ID/路径 |
| 409 | 冲突 | 资源已存在或状态冲突 |
| 429 | 限流 | 降低请求频率 |
