# GitLab Server-Side Configuration

Covers GitLab project-level server-side configuration: branch protection, Push Rules, merge
settings, MR approval rules, and tag protection. All operations are done through the REST API;
glab CLI has no corresponding subcommands.

## Decision tree

```
Server-side configuration?
├── Branch protection rules (push/merge permissions, force push) → §Branch protection
├── Commit message regex validation → §Push Rules
├── Merge behavior (squash, discussions, pipeline) → §Project merge settings
├── MR approval rules (approver count, approval rules) → §MR approval rules
├── Tag protection (prevent deletion/overwrite) → §Tag protection
└── Full initial configuration for a new project → §OCP project configuration example
```

## General API template

glab's `-f` flag does not support bracket syntax for complex JSON fields (e.g.
`push_access_levels[0][access_level]`). Two approaches are recommended:

```bash
# Method 1: glab api + --input (JSON file)
echo '{"name":"develop","allow_force_push":false,"push_access_levels":[{"access_level":40}]}' > /tmp/body.json
glab api "projects/:id/protected_branches" -X POST --input /tmp/body.json

# Method 2: curl + PRIVATE-TOKEN (most reliable, no JSON serialization issues)
GITLAB_TOKEN=$(glab config get token -h gitlab.vmic.xyz)
# Note: if the token is stored in the keyring, the above command may return empty; use Method 1 instead
curl -s -X POST "https://gitlab.vmic.xyz/api/v4/projects/:id/protected_branches" \
  -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"develop","allow_force_push":false,"push_access_levels":[{"access_level":40}]}'
```

### Getting the project ID

```bash
# Get the project ID via URL-encoded path
glab api "projects/group%2Fproject" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
```

### Access level reference

| Value | Role | Description |
|----|------|------|
| 0  | No access | No permissions |
| 20 | Reporter | Can view code, cannot push |
| 30 | Developer | Can push to non-protected branches |
| 40 | Maintainer | Can push to protected branches and merge MRs |
| 60 | Admin | Administrator |

## Branch protection

### API endpoints

| Operation | Method | Endpoint |
|------|------|------|
| List all protected branches | GET | `/projects/:id/protected_branches` |
| View a single protected branch | GET | `/projects/:id/protected_branches/:name` |
| Create a protection rule | POST | `/projects/:id/protected_branches` |
| Update a protection rule | PUT | `/projects/:id/protected_branches/:name` |
| Delete a protection rule | DELETE | `/projects/:id/protected_branches/:name` |

### Creating a protection rule

```bash
# JSON body field reference:
# name              — branch name (supports wildcards such as release/*)
# allow_force_push  — whether force push is allowed (recommended: false)
# push_access_levels  — roles allowed to push directly
# merge_access_levels — roles allowed to merge via MR

glab api "projects/:id/protected_branches" -X POST --input <(cat <<'EOF'
{
  "name": "master",
  "allow_force_push": false,
  "push_access_levels": [{"access_level": 40}],
  "merge_access_levels": [{"access_level": 30}]
}
EOF
)
```

### OCP branch protection configuration

Per the team's git flow strategy, the protection rules for the two trunk branches:

```bash
# master: only Maintainers may push; Developer+ may merge MRs
glab api "projects/:id/protected_branches" -X POST --input <(cat <<'EOF'
{"name":"master","allow_force_push":false,"push_access_levels":[{"access_level":40}],"merge_access_levels":[{"access_level":30}]}
EOF
)

# develop: same as above
glab api "projects/:id/protected_branches" -X POST --input <(cat <<'EOF'
{"name":"develop","allow_force_push":false,"push_access_levels":[{"access_level":40}],"merge_access_levels":[{"access_level":30}]}
EOF
)
```

### Wildcard protection

```bash
# Protect all release branches
{"name":"release/*","allow_force_push":false,"push_access_levels":[{"access_level":40}],"merge_access_levels":[{"access_level":30}]}
```

## Push Rules

> **Prerequisite**: the Push Rules API requires GitLab Premium/Ultimate. The Free tier returns 404.

### API endpoints

| Operation | Method | Endpoint |
|------|------|------|
| View push rules | GET | `/projects/:id/push_rule` |
| Create/update push rules | PUT | `/projects/:id/push_rule` |

### OCP commit message regex

```bash
# Format: <type>(<scope>): <subject> or <type>: <subject>
# type ∈ feat|fix|refactor|docs|chore|test|perf|ci|build|revert

glab api "projects/:id/push_rule" -X PUT --input <(cat <<'EOF'
{
  "commit_message_regex": "^(feat|fix|refactor|docs|chore|test|perf|ci|build|revert)(\\(.+\\))?: .+",
  "commit_message_negative_regex": "^(Merge|Initial commit|Revert)"
}
EOF
)
```

`commit_message_negative_regex` excludes merge commits and revert commits (these are generated
automatically by git and are not subject to the team's conventions).

### Other available Push Rules fields

| Field | Description |
|------|------|
| `commit_message_regex` | Regex the commit message must match |
| `commit_message_negative_regex` | Regex the commit message must not match |
| `branch_name_regex` | Regex branch names must match |
| `author_email_regex` | Regex the author email must match |
| `member_check` | Only project members may push (no external contributors) |
| `prevent_secrets` | Reject commits containing secrets/passwords |
| `max_file_size` | Maximum size of a single file (KB) |

### Branch naming regex (for git flow)

```json
{
  "branch_name_regex": "^(feature/.+--.+|fix/.+|release/\\d+\\.\\d+\\.\\d+\\.\\d+|develop|master)$"
}
```

Matches the team's branch conventions: `feature/<requirement-ID>--<description>`,
`fix/<description>`, `release/<four-segment version>`, `develop`, `master`.

> A `release` branch name is **always four segments of pure digits** (e.g. `release/13.7.0.2`).
> The `-SNAPSHOT` / `-RELEASE` suffixes exist only in dependency versions inside the pom —
> **they never go into branch names**. A suffixed branch name would fail the regex above and be
> misread by the CI version-parsing logic.

## Project merge settings

### API endpoint

```
PUT /projects/:id
```

### Configurable fields

| Field | Type | Description |
|------|------|------|
| `merge_method` | string | Merge method: `merge` (merge commit) / `rebase_merge` / `ff` (fast-forward) |
| `squash_option` | string | Squash option: `default_off` (no squash by default) / `default_on` / `enabled` / `disabled` |
| `only_allow_merge_if_all_discussions_are_resolved` | bool | All discussions must be resolved before merging |
| `only_allow_merge_if_pipeline_succeeds` | bool | The pipeline must succeed before merging |
| `merge_requests_author_approval` | bool | Whether the MR author may approve their own MR |
| `merge_requests_disable_committers_api` | bool | Whether to disable the committers API |

### OCP recommended configuration

```bash
glab api "projects/:id" -X PUT --input <(cat <<'EOF'
{
  "merge_method": "merge",
  "squash_option": "default_off",
  "only_allow_merge_if_all_discussions_are_resolved": true,
  "only_allow_merge_if_pipeline_succeeds": true,
  "merge_requests_author_approval": false
}
EOF
)
```

## MR approval rules

> **Prerequisite**: the MR Approval Rules API requires GitLab Premium/Ultimate.

### API endpoints

| Operation | Method | Endpoint |
|------|------|------|
| View approval rules | GET | `/projects/:id/approval_rules` |
| Create an approval rule | POST | `/projects/:id/approval_rules` |
| Update an approval rule | PUT | `/projects/:id/approval_rules/:rule_id` |
| Delete an approval rule | DELETE | `/projects/:id/approval_rules/:rule_id` |

### Creating an approval rule

```bash
# Require at least 1 approver, with a designated approver group
glab api "projects/:id/approval_rules" -X POST --input <(cat <<'EOF'
{
  "name": "Architecture team approval",
  "approvals_required": 1,
  "rule_type": "regular",
  "user_ids": [],
  "group_ids": [89460]
}
EOF
)
```

### Project-level approval settings

```bash
# Set the project-wide approval count (applies to all MRs)
glab api "projects/:id/approvals" -X POST -f approvals_required=1
```

## Tag protection

Prevents important tags from being deleted or overwritten by force push.

### API endpoints

| Operation | Method | Endpoint |
|------|------|------|
| List protected tags | GET | `/projects/:id/protected_tags` |
| Protect a tag | POST | `/projects/:id/protected_tags` |
| Unprotect a tag | DELETE | `/projects/:id/protected_tags/:name` |

### Protecting release tags

```bash
# Protect all semantic-version tags
glab api "projects/:id/protected_tags" -X POST --input <(cat <<'EOF'
{"name":"v*.*.*","create_access_levels":[{"access_level":40}]}
EOF
)
```

## OCP project configuration example

The complete initialization script for a new project (using ocp-workflow-test as an example):

```bash
PROJECT="ocp%2Focp-workflow-test"

# 1. Create the develop branch
glab api "projects/$PROJECT/repository/branches" -X POST \
  -f branch=develop -f ref=master

# 2. Protect master
glab api "projects/$PROJECT/protected_branches" -X POST --input <(cat <<'EOF'
{"name":"master","allow_force_push":false,"push_access_levels":[{"access_level":40}],"merge_access_levels":[{"access_level":30}]}
EOF
)

# 3. Protect develop
glab api "projects/$PROJECT/protected_branches" -X POST --input <(cat <<'EOF'
{"name":"develop","allow_force_push":false,"push_access_levels":[{"access_level":40}],"merge_access_levels":[{"access_level":30}]}
EOF
)

# 4. Merge settings (pipeline must succeed + discussions must be resolved + no author self-approval)
glab api "projects/$PROJECT" -X PUT --input <(cat <<'EOF'
{"merge_method":"merge","squash_option":"default_off","only_allow_merge_if_all_discussions_are_resolved":true,"only_allow_merge_if_pipeline_succeeds":true,"merge_requests_author_approval":false}
EOF
)

# 5. Push Rules (requires Premium)
glab api "projects/$PROJECT/push_rule" -X PUT --input <(cat <<'EOF'
{"commit_message_regex":"^(feat|fix|refactor|docs|chore|test|perf|ci|build|revert)(\\(.+\\))?: .+","commit_message_negative_regex":"^(Merge|Initial commit|Revert)","branch_name_regex":"^(feature/.+--.+|fix/.+|release/\\d+\\.\\d+\\.\\d+\\.\\d+|develop|master)$"}
EOF
)
```

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| PUT protected_branches returns 404 | Some GitLab versions don't support PUT updates | DELETE first, then POST to recreate |
| Push Rules API returns 404 | Requires a Premium/Ultimate license | Use a client-side hook instead (prepare-commit-msg) |
| `--input` returns 415 Content-Type | glab doesn't set Content-Type automatically | Add `-H "Content-Type: application/json"` or switch to curl |
| merge_access_levels has no effect | glab `-f` can't properly pass nested JSON arrays | Use `--input` with a JSON file |
| Process substitution `<()` fails on Windows | Git Bash doesn't support /proc fd | Use a temp file: `echo '...' > /tmp/body.json && ... --input /tmp/body.json` |
