# Merge Request Lifecycle

Covers the complete MR lifecycle from creation to merge/close.

## Decision tree: when to create an MR?

```
Ready to create an MR?
├── Feature development complete → create the MR directly
├── Need early feedback → create a Draft MR (glab mr create --draft)
├── Multiple dependent small changes → consider Stacked MRs (glab stack)
└── Haven't started coding yet → create the branch first; don't rush to open an MR
```

## Creating an MR

### Command templates

```bash
# Interactive creation (recommended for first-time use)
glab mr create

# Non-interactive (Agent/CI scenarios)
glab mr create \
  --title "feat(xxx): add user authentication" \
  --description "$(cat <<'EOF'
## Summary
- Implement the OAuth2 authentication flow
- Add a JWT token refresh mechanism

## Test plan
- [ ] Unit tests pass
- [ ] Integration test coverage
EOF
)" \
  --source-branch feature/auth \
  --target-branch "<TARGET>" \
  --assignee @reviewer1 \
  --reviewer @reviewer2 \
  --label backend,security \
  --milestone "Sprint 24"

# Draft MR
glab mr create --draft --title "WIP: auth flow"

# Fill from commit messages
glab mr create --fill

# Specify a repository
glab mr create -R group/project
```

> **`<TARGET>` is not a fixed value.** It is determined by the branch strategy registered for the
> repository: `git-flow` → `develop`; `assembly-flow` → `release/<four-segment version>`
> (e.g. `release/13.7.0.2`); `github-flow` → `master`. Before creating an MR you **MUST** first
> resolve it with `python scripts/branch_strategy.py get`. When it is unregistered (`UNSET`),
> never guess — confirm conversationally. See
> [workflows.md](workflows.md) §Agent Procedure for Resolving the Branch Strategy.

### MR description template

The structured description format the Agent should follow when creating an MR:

```markdown
## Summary
<1-3 lines summarizing the purpose of the change>

## Changes
- <specific change 1>
- <specific change 2>

## Test plan
- [ ] <verification step 1>
- [ ] <verification step 2>

## Screenshots (if UI)
<screenshot or "N/A">
```

## Viewing and listing MRs

```bash
# View the MR for the current branch
glab mr view

# List all open MRs
glab mr list

# Filter by criteria
glab mr list --author @user
glab mr list --label backend
glab mr list --milestone "Sprint 24"
glab mr list --state merged
glab mr list --state closed

# JSON output (for Agent parsing)
glab mr list --output json
glab mr list -F json

# View a specific MR
glab mr view 123
glab mr view 123 --comments
```

## Review and collaboration

### Quick Actions (used in MR comments)

```
/assign @user              # Assign an assignee
/unassign @user            # Remove the assignment
/reassign @user            # Reassign
/label ~backend ~security  # Add labels
/unlabel ~wip              # Remove a label
/milestone %"Sprint 24"    # Set a milestone
/cc @user                  # CC a user
/merge                     # Merge (requires permission)
/approve                   # Approve
/unapprove                 # Revoke approval
```

See [quick-actions.md](quick-actions.md) for details.

### Adding comments

```bash
# Regular comment
glab mr note 123 --message "LGTM, but suggest adding a null check"

# Line-level comment (code review)
glab mr note 123 --message "Possible NPE here" \
  --filename src/main/java/Auth.java --line 42
```

## Updating an MR

```bash
# Pushing new commits automatically updates the MR (branch already linked)
git push origin feature/auth

# Modify MR metadata
glab mr update 123 --title "New title"
glab mr update 123 --assignee @new-reviewer
glab mr update 123 --label backend,urgent
glab mr update 123 --description "New description"

# Change the target branch
glab mr update 123 --target-branch main
```

## Merge gate prerequisites

For the merge button to light up (`detailed_merge_status=mergeable`), all of the following checks
must pass. The first five are determined by project settings or the MR's own state; if any of them
fails, the merge button is greyed out and the error is shown directly in the UI.

| Check | Trigger condition | Project field | How to fix |
|--------|---------|---------|--------|
| Pipeline must succeed | When the project has `only_allow_merge_if_pipeline_succeeds=true` and the head_pipeline status of the latest commit ≠ `success` | `only_allow_merge_if_pipeline_succeeds` | Fix CI, retry, or push again to trigger a new pipeline |
| All discussions resolved | When the project has `only_allow_merge_if_all_discussions_are_resolved=true` and a discussion with `resolved=false` exists | `only_allow_merge_if_all_discussions_are_resolved` | Click "Resolve discussion" on the MR comment, or use the Quick Action `/resolve` |
| Approval count met | The project or approval rules require N approvers and there aren't enough yet | approval rules (Premium) | Get enough approvers |
| Not Draft / WIP | The MR title starts with `Draft:` / `WIP:`, or "Convert to Draft" was clicked in the UI | — | `glab mr update <iid> --ready` |
| No merge conflict | The source and target branches conflict | — | `git rebase origin/<target>` locally, or merge and push again |
| Protected target branch allows you to merge | The target branch is protected and `merge_access_levels` doesn't include your role | protected branches | Ask someone with permission to merge it, or adjust the protection rules |

### Programmatic checks

```bash
# Get the MR's overall status (GitLab 14+)
glab api "projects/:id/merge_requests/<iid>" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('detailed_merge_status:', d.get('detailed_merge_status'))   # mergeable / blocked / pipeline / discussions / draft / conflicts / approvals / author_approval
print('has_conflicts:', d.get('has_conflicts'))
print('pipeline:', (d.get('head_pipeline') or {}).get('status'))"

# Check whether the project enforces "pipeline must succeed"
glab api "projects/:id" | python3 -c "import sys,json; d=json.load(sys.stdin); print('pipeline gate:', d['only_allow_merge_if_pipeline_succeeds'])"

# Toggling project gates: see gitlab-server-config.md §Project merge settings
```

> The settings and default-value conventions for these gate fields live in
> [gitlab-server-config.md](gitlab-server-config.md) §Project merge settings; this section
> only explains "why the merge is blocked".

## Merging an MR

### The three merge methods

| Method | Effect | History shape | Author of each commit |
|------|------|---------|-------------------|
| `--merge` | Creates a merge commit; all source-branch commits enter the target branch | A merge node with divergence | **Fully preserved** |
| `--squash` | All source-branch commits are squashed into **one new commit** on the target branch | Linear; one change, one commit | **All become the MR author** |
| `--rebase` | Replays the source-branch commits one by one onto the tip of the target branch, then fast-forwards | Linear; each commit kept | Original author preserved (SHA changes) |

> **`--squash` is not a "fast-forward merge"**: it discards the entire commit history of the
> source branch and produces one brand-new commit. A true fast-forward corresponds to
> `merge_method: ff` and creates no new commit. Don't confuse the two.

### Decision tree

```
How to merge?
├── Source branch contains others' commits and their attribution must be preserved → --merge or --rebase (do NOT use --squash)
├── Source branch has only your own scratch commits (WIP/typo/debug) and you want a clean history → --squash
├── Need a linear history with each commit meaningful on its own → --rebase
├── Need to preserve branch structure and merge evidence → --merge
└── Unsure → --merge (most conservative, loses no information) + --remove-source-branch
```

> **Relationship between merge methods and project settings**: `squash_option` controls whether
> squash is available on the MR page (`default_off` / `default_on` / `enabled` / `disabled`), and
> `merge_method` controls the base merge shape (`merge` / `rebase_merge` / `ff`). Both settings
> are covered in [gitlab-server-config.md](gitlab-server-config.md) §Project merge settings.
> When the server sets `squash_option` to `default_off`, the Agent **MUST NOT** override it with
> `--squash`.

### ⚠️ The authorship trap of squash

For the new commit produced by `--squash`, both `author` and `committer` are **the MR author**.
The original authors of the source commits only leave a trace as `(cherry picked from commit
<sha>)` lines at the end of the squash message.

Consequences:
- GitLab contribution statistics (contributions graph) credit all of that work to the MR author
- `git blame` on the target branch points to the MR author; the original authors become untraceable
- If the squashed commit ever needs to be reverted, every unrelated change bundled into it gets
  reverted along with it

You **MUST** check the authorship of the source branch before merging:

```bash
git log --format='%an <%ae>' origin/<TARGET>..<SOURCE> | sort | uniq -c | sort -rn
```

When two or more authors appear, you **MUST NOT** use `--squash` — use `--merge` or `--rebase`
instead, or ask the original authors to split their commits into separate MRs first.

> Likewise, when **multiple unrelated logical changes are mixed into a single commit** (e.g.
> bumping a dependency version together with business-code changes), squash locks them under the
> same author and a revert cannot separate them. Such changes should be split at commit time per
> the single-responsibility rule in [git-local.md](git-local.md) §Commit discipline, rather
> than patched up at merge time.

```bash
# Standard merge (keeps all commits and original authors)
glab mr merge 123 --merge --remove-source-branch

# Squash merge (only when the source branch is entirely your own commits)
glab mr merge 123 --squash --remove-source-branch

# Rebase merge (linear history, keeps each commit)
glab mr merge 123 --rebase --remove-source-branch

# Specify the squash commit message
glab mr merge 123 --squash --squash-message "feat(auth): add OAuth2"

# Merge automatically once CI passes
glab mr merge 123 --merge-when-pipeline-succeeds
```

## Closing an MR

```bash
# Close a single MR
glab mr close 123

# Close multiple MRs
glab mr close 1 2 3

# Close an MR in a specific repository
glab mr close 123 -R group/project

# Close with a comment (comment first, then close)
glab mr note create 123 -m "Superseded by MR #456"
glab mr close 123
```

## Stacked MRs

```bash
# Create a stack
glab stack create feature-stack

# Infer layers from a commit range
glab stack infer main..HEAD

# Sync and push all layers
glab stack sync

# Rebase onto the latest main
glab stack sync --update-base

# Push only, without opening MRs
glab stack sync --skip-mr-creation

# Sync with metadata
glab stack sync --assignee @owner --reviewer @reviewer --label backend

# Amend changes into the current layer
glab stack amend

# Change only the commit message
glab stack amend --reword -m "updated message"

# Navigation
glab stack next / prev / first / last
glab stack move
glab stack switch              # Interactive selection
glab stack switch stack-name   # Switch directly
```

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| MR creation fails with "source branch not found" | Branch not pushed | `git push -u origin <branch>` |
| merge conflict | The target branch has new commits | `git rebase <target>` then push |
| pipeline blocks merge | CI not passing | Check the pipeline logs, fix and rerun |
| "cannot force push" | The protected branch disallows force push | Use a normal push or contact an admin |
| MR shows outdated | The target branch has moved on | Rebase onto or merge the target branch |
