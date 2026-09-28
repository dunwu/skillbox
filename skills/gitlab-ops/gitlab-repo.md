# 仓库管理

覆盖 GitLab 项目/仓库的管理操作。

## 决策树

```
仓库操作？
├── 查看项目信息 → glab repo view
├── 克隆 → 参见 git-local.md Clone 章节
├── 创建项目 → glab repo create（需管理员权限）
├── Fork → glab repo fork
├── 下载仓库归档（zip/tar） → glab repo archive
├── 归档项目（设为只读） → REST API POST /projects/:id/archive
├── 查看/管理分支 → REST API /api/v4/projects/:id/repository/branches（glab 无分支子命令）
├── 查看/管理标签 → glab release（标签管理在 git-local.md）
```

## 项目信息

```bash
# 查看项目详情
glab repo view
glab repo view group/project

# JSON 输出（Agent 解析）
glab repo view group/project --output json
```

## Fork

```bash
# Fork 到当前用户命名空间
glab repo fork

# Fork 指定仓库
glab repo fork namespace/repo

# Fork 并 clone
glab repo fork namespace/repo --clone

# Fork 但不 clone（注意用 = 连接）
glab repo fork namespace/repo --clone=false

# 指定 fork 后的项目名
glab repo fork namespace/repo --name=my-fork-name

# 设置 upstream remote
glab repo fork namespace/repo --remote
```

## 下载仓库归档（zip/tar）

`glab repo archive` 下载仓库的压缩包，**不会**将项目设为只读。

```bash
# 下载仓库 zip（默认下载到当前目录）
glab repo archive group/project

# 指定下载目录
glab repo archive group/project /tmp/backup

# 指定格式（tar.gz）
glab repo archive group/project --format=tar.gz

# 指定 commit SHA
glab repo archive group/project --sha=abc123
```

## 归档项目（设为只读，REST API）

将项目设为只读状态，需通过 REST API 操作。

```bash
# 归档项目（设为只读）
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/archive"

# 取消归档
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/unarchive"

# 检查项目是否已归档
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID" | jq '.archived'
```

## 分支管理（REST API）

glab 没有分支子命令，分支操作通过 REST API 完成。

```bash
# 列出分支
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/repository/branches" | jq .

# 创建分支
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"branch":"feature/x","ref":"main"}' \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/repository/branches" | jq .

# 删除分支
curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/repository/branches/feature/x"
```

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| "project not found" | 路径错误或无权限 | 确认 `group/project` 格式 |
| fork 失败 "already exists" | 已 fork 过 | 删除旧 fork 或用其他命名空间 |
| `glab repo archive` 没有归档项目 | 该命令只下载 zip，不改变项目状态 | 归档项目需使用 REST API `POST /projects/:id/archive` |
| 归档后无法取消 | Web UI 操作不可逆 | 取消归档需通过 REST API `POST /projects/:id/unarchive` |
