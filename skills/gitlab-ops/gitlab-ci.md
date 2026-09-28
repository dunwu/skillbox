# CI/CD 流水线

覆盖 GitLab CI/CD 流水线的全生命周期操作。

## 决策树

```
需要做什么 CI/CD 操作？
├── 查看当前 pipeline 状态 → glab ci status / glab ci view
├── 查看某次 pipeline 详情 → glab ci get <id>
├── 查看 job 日志 → glab ci trace
├── 重试失败的 job → glab ci retry
├── 取消运行中的 pipeline → glab ci cancel
├── 手动触发 pipeline → glab ci trigger
├── 管理定时 pipeline → glab schedule
└── 编写/修改 .gitlab-ci.yml → 参见编写规范章节
```

## Pipeline 查看

```bash
# 实时状态面板（交互式）
glab ci status

# 可视化查看（浏览器）
glab ci view

# 查看特定 pipeline
glab ci get --pipeline-id <id>
glab ci get --pipeline-id <id> --output json

# 列出 pipeline
glab ci list
glab ci list --scope finished
glab ci list --scope running
glab ci list --ref main

# JSON 输出（Agent 解析）
glab ci list --output json
```

## Job 操作

```bash
# 查看 job 日志（实时跟踪）
glab ci trace

# 查看特定 job 日志
glab ci trace <job-id>

# 列出 pipeline 的所有 job（glab 无 ci list --pipeline-id，通过 REST API）
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/pipelines/<id>/jobs" | jq .

# 查看 job 详情（通过 REST API）
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://$GITLAB_HOST/api/v4/projects/$PROJECT_ID/jobs/<job-id>" | jq .
```

## Pipeline 控制

```bash
# 重试失败的 job（交互式选择）
glab ci retry

# 重试指定 job
glab ci retry <job-id>
glab ci retry <job-name> --branch main

# 取消运行中的 pipeline
glab ci cancel pipeline <pipeline-id>

# 取消运行中的 job
glab ci cancel job <job-id>

# 触发手动 job
glab ci trigger <job-name> --branch main

# 通过 pipeline trigger 触发（需预先在 GitLab 创建 trigger token）
glab ci run-trig

# 删除 pipeline
glab ci delete <pipeline-id>
```

## 定时 Pipeline（Schedule）

```bash
# 列出定时任务
glab schedule list
glab schedule list --output json

# 创建定时任务
glab schedule create \
  --description "每日构建" \
  --ref main \
  --cron "0 2 * * *"

# 带变量
glab schedule create \
  --ref main \
  --cron "0 6 * * 1" \
  --variable "DEPLOY_ENV:staging"

# 更新
glab schedule update <schedule-id> --cron "0 3 * * *"

# 删除
glab schedule delete <schedule-id>
```

### Schedule 变量注意事项

- 变量 key 在创建前会校验，空 key 被拒绝
- 确认 `--variable <key>:<value>` 格式正确再执行

## .gitlab-ci.yml 编写规范

### 最小结构

```yaml
stages:
  - build
  - test
  - deploy

build-job:
  stage: build
  script:
    - echo "Building..."
    - mvn clean package -DskipTests

test-job:
  stage: test
  script:
    - mvn test

deploy-job:
  stage: deploy
  script:
    - echo "Deploying..."
  environment: production
  when: manual
  only:
    - main
```

### 常用模式

```yaml
# 缓存依赖
cache:
  key: "${CI_COMMIT_REF_SLUG}"
  paths:
    - .m2/repository/
    - node_modules/

# 模板复用（include）
include:
  - template: Security/SAST.gitlab-ci.yml
  - project: 'group/ci-templates'
    file: '/templates/maven.yml'

# 规则控制（替代 only/except）
rules:
  - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    changes:
      - src/**/*
  - if: '$CI_COMMIT_BRANCH == "main"'

# 手动触发
deploy-prod:
  stage: deploy
  script: ./deploy.sh
  when: manual
  environment:
    name: production
    url: https://app.example.com

# 并行矩阵
test:
  parallel:
    matrix:
      - JAVA_VERSION: ['17', '21']
        DB: ['mysql', 'postgres']
```

### 预定义变量（常用）

| 变量 | 含义 |
|------|------|
| `$CI_COMMIT_SHA` | 当前提交 SHA |
| `$CI_COMMIT_BRANCH` | 分支名（非 MR 时） |
| `$CI_MERGE_REQUEST_IID` | MR 编号 |
| `$CI_PIPELINE_ID` | Pipeline ID |
| `$CI_JOB_NAME` | 当前 Job 名称 |
| `$CI_PROJECT_PATH` | 项目路径（group/project） |
| `$CI_REGISTRY` | 容器镜像仓库地址 |
| `$CI_DEFAULT_BRANCH` | 默认分支名 |

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| pipeline stuck | 等待手动触发的 job | `glab ci view` 找到手动 job 并触发 |
| job failed 但日志为空 | Runner 问题 | 检查 Runner 状态；重试 job |
| "no matching job" | rules 不匹配 | 检查 rules 条件和变量 |
| schedule 不执行 | 未启用或 Runner 不可用 | `glab schedule list` 检查 active 状态 |
| cache miss | key 不匹配 | 统一 cache key 策略 |
| include 模板找不到 | 路径错误或权限不足 | 确认模板路径和 token 权限 |
