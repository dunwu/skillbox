# Quick Actions Reference

Used in MR/Issue comments to perform status changes in bulk.

## Common to Issues / MRs

| Quick Action | Effect |
|-------------|------|
| `/assign @user` | Assign a user |
| `/unassign` | Remove assignee |
| `/reassign @user` | Reassign |
| `/label ~label1 ~label2` | Add labels |
| `/unlabel ~label1` | Remove a label |
| `/relabel ~label1 ~label2` | Replace all labels |
| `/milestone %"Sprint 24"` | Set milestone |
| `/cc @user1 @user2` | CC notification |
| `/duplicate #123` | Mark as a duplicate of #123 |
| `/move to group/project` | Move to another project |

## MR Only

| Quick Action | Effect |
|-------------|------|
| `/merge` | Merge the MR |
| `/approve` | Approve the MR |
| `/unapprove` | Revoke approval |
| `/request_review @user` | Request a review |

## Close / Reopen

| Quick Action | Effect |
|-------------|------|
| `/close` | Close Issue/MR |
| `/reopen` | Reopen Issue/MR |

## Time Tracking

| Quick Action | Effect |
|-------------|------|
| `/estimate 2h` | Set a time estimate |
| `/spend 1h` | Log time spent |
| `/time_estimate 3h` | Update the estimate |

## Agent Use Cases

- Bulk assignment: loop through the glab comment API to write Quick Actions
- One-shot post-review MR actions: `/approve` + `/merge` in two separate comments
- Avoid multiple API calls: combine multiple Quick Actions in a single comment
