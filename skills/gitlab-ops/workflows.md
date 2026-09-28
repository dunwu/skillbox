# 端到端工作流

## 分支管理策略

### Git Flow（适合版本迭代较长的项目）

```
时间线 →

main       ──●──────────────────────●──────────●── (tag v1.0) ──●── (tag v1.1)
            / \                    / \        / \              /
develop  ──●───●──●──●──●──●──●──●───●──●──●───●──●──●──●──●───
            \         /    \           /
feature/A  ──●──●──●─/      \         /
                          \         /
feature/B                  ●──●──●──/
                               
hotfix ──────────────────────────●──/
                                 (基于 main，修复后合入 main + develop)
```

**核心分支：**

| 分支 | 生命周期 | 用途 |
|------|---------|------|
| `main` | 永久 | 生产环境代码，只接受 merge，每次发布打 tag |
| `develop` | 永久 | 下一个版本的集成分支 |
| `feature/*` | 临时 | 从 develop 创建，完成后 merge 回 develop |
| `release/*` | 临时 | 从 develop 创建，测试修复后 merge 到 main + develop |
| `hotfix/*` | 临时 | 从 main 创建，修复后 merge 到 main + develop |

**分支流转规则：**

- **MUST NOT** 直接在 `main` 上提交代码（`main` 仅接受 release 和 hotfix 合并）
- **MUST NOT** 直接在 `develop` 上开发功能（从 `develop` 创建 feature 分支）
- feature 分支 **MUST** 从最新的 `develop` 创建，开发完成后合并回 `develop`
- release 分支 **MUST** 从 `develop` 创建，测试通过后合并回 `main`（打 tag）和 `develop`
- hotfix 分支 **MUST** 从 `main` 创建，修复完成后合并回 `main`（打 tag）和 `develop`
- feature / release / hotfix 合并后 **MUST** 删除远程分支

**命名示例：**

```
feature/JIRA-1234-article-publish
feature/JIRA-5678-author-crud
release/1.5.0
hotfix/JIRA-9999-fix-null-pointer
```

**Git Flow 工作流：**

```bash
# 1. 开发新功能
git checkout -b feature/auth develop
# ... 开发 ...
git checkout develop
git merge --no-ff feature/auth
git branch -d feature/auth
git push origin --delete feature/auth    # 删除远程分支

# 2. 准备发布
git checkout -b release/1.0 develop
# ... 修复发布前 bug ...
git checkout main
git merge --no-ff release/1.0
git tag -a v1.0
git checkout develop
git merge --no-ff release/1.0
git branch -d release/1.0
git push origin --delete release/1.0    # 删除远程分支

# 3. 紧急修复
git checkout -b hotfix/1.0.1 main
# ... 修复 ...
git checkout main
git merge --no-ff hotfix/1.0.1
git tag -a v1.0.1
git checkout develop
git merge --no-ff hotfix/1.0.1
git branch -d hotfix/1.0.1
git push origin --delete hotfix/1.0.1   # 删除远程分支
```

### GitHub Flow（适合持续部署的简单项目）

```
时间线 →

main  ──●──●─────●─────────●──────●──────●──
         \       /         /      /      /
feature   ●──●──●   ●──●──●  ●──●/  ●──●/
                                   
          (所有分支基于 main，完成后 MR 合入 main)
```

**规则：**

1. `main` 始终可部署
2. 从 `main` 创建描述性分支
3. 频繁推送到远端（备份 + 协作）
4. 通过 MR 发起讨论和审查
5. 只有 `main` 接受合并
6. 合并后立即部署

**选择建议：**

```
项目特征？
├── 版本周期长、需要 release 分支、多版本并行维护 → Git Flow
├── 持续部署、迭代快、团队小 → GitHub Flow
└── 不确定 → GitHub Flow（更简单，MR 驱动）
```

## 工作流 1：Feature Branch 开发

```
1. glab issue create --title "..." --label feature
2. git checkout -b feature/TICKET-123-desc main
3. <编码、提交>
4. git push -u origin feature/TICKET-123-desc
5. glab mr create --fill --assignee @reviewer --label feature
6. <审查、修改、push>
7. glab mr merge <iid> --squash --remove-source-branch
8. glab issue close <iid>（如果 MR 描述中已有 Closes 则自动）
```

## 工作流 2：Hotfix

```
1. git checkout -b hotfix/critical-fix main
2. <修复、测试>
3. git push -u origin hotfix/critical-fix
4. glab mr create --title "hotfix: ..." --label hotfix,urgent
5. <快速审查>
6. glab mr merge <iid> --squash
7. glab release create v1.0.1 --ref main
```

## 工作流 3：Code Review 自动化

```
1. 获取 MR 变更：glab mr diff <iid>
2. 分析变更文件
3. 添加行级评论：glab mr note create <iid> --file X --line Y -m "..."
4. 批准或请求修改：/approve 或 /request_review @author
```

## 工作流 4：CI/CD 监控与修复

```
1. 检查 pipeline：glab ci status
2. 定位失败 job：glab ci trace
3. 分析日志
4. 本地修复并 push
5. 等待 pipeline 重跑：glab ci status（确认变绿）
6. 如仍失败：glab ci retry <pipeline-id>
```

## 工作流 5：多 Agent 并行开发

```
Agent A: git checkout -b feature/auth
Agent B: git checkout -b feature/payment
各自开发 → 各自 MR → 独立审查合并
注意：共享 main 分支时，后合并者需 rebase
```

## 工作流 6：发布流程

```
1. glab mr create feature → develop（集成）
2. 测试通过后 develop → main
3. glab release create v1.0.0 --ref main --notes "..."
4. glab tag 已在 release 时自动创建
```
