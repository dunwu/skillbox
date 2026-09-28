# Quick Actions 速查

在 MR/Issue 评论中使用，批量执行状态变更。

## Issue / MR 通用

| Quick Action | 效果 |
|-------------|------|
| `/assign @user` | 指定负责人 |
| `/unassign` | 取消指定 |
| `/reassign @user` | 重新指定 |
| `/label ~label1 ~label2` | 添加标签 |
| `/unlabel ~label1` | 移除标签 |
| `/relabel ~label1 ~label2` | 替换全部标签 |
| `/milestone %"Sprint 24"` | 设置里程碑 |
| `/cc @user1 @user2` | 抄送通知 |
| `/duplicate #123` | 标记为 #123 的重复 |
| `/move to group/project` | 移动到其他项目 |

## MR 专用

| Quick Action | 效果 |
|-------------|------|
| `/merge` | 合并 MR |
| `/approve` | 批准 MR |
| `/unapprove` | 取消批准 |
| `/request_review @user` | 请求审查 |

## 关闭/重开

| Quick Action | 效果 |
|-------------|------|
| `/close` | 关闭 Issue/MR |
| `/reopen` | 重开 Issue/MR |

## 时间追踪

| Quick Action | 效果 |
|-------------|------|
| `/estimate 2h` | 预估时间 |
| `/spend 1h` | 记录已花时间 |
| `/time_estimate 3h` | 修改预估 |

## Agent 使用场景

- 批量分配：循环调用 glab 评论 API 写入 Quick Action
- MR 审查后一键操作：`/approve` + `/merge` 在两条评论中
- 避免多次 API 调用：一条评论中可组合多个 Quick Action
