# Repository Management

Covers management operations for GitLab projects/repositories.

## Decision Tree

```
Repository operation?
├── View project info → glab repo view
├── Clone → see the Clone section in git-local.md
├── Create project → glab repo create (requires admin privileges)
├── Fork → glab repo fork
├── Download repo archive (zip/tar) → glab repo archive
├── Archive project (set read-only) → REST API POST /projects/:id/archive
├── View/manage branches → REST API /api/v4/projects/:id/repository/branches (glab has no branch subcommand)
├── View/manage tags → glab release (tag management in git-local.md)
```

## Project Info

```bash
# View project details
glab repo view
glab repo view group/project

# JSON output (for Agent parsing)
glab repo view group/project --output json
```

## Fork

```bash
# Fork to the current user's namespace
glab repo fork

# Fork a specific repository
glab repo fork namespace/repo

# Fork and clone
glab repo fork namespace/repo --clone

# Fork without cloning (note the = sign)
glab repo fork namespace/repo --clone=false

# Specify the forked project name
glab repo fork namespace/repo --name=my-fork-name

# Set up the upstream remote
glab repo fork namespace/repo --remote
```

## Downloading Repository Archives (zip/tar)

`glab repo archive` downloads an archive of the repository and does **not** set the project to read-only.

```bash
# Download repo zip (downloads to the current directory by default)
glab repo archive group/project

# Specify a download directory
glab repo archive group/project /tmp/backup

# Specify the format (tar.gz)
glab repo archive group/project --format=tar.gz

# Specify a commit SHA
glab repo archive group/project --sha=abc123
```

## Archiving a Project (Set Read-Only, REST API)

Setting a project to read-only requires the REST API.

```bash
# Archive a project (set read-only)
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/archive"

# Unarchive
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/unarchive"

# Check whether a project is archived
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID" | jq '.archived'
```

## Branch Management (REST API)

glab has no branch subcommand; branch operations are performed via the REST API.

```bash
# List branches
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/repository/branches" | jq .

# Create a branch
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"branch":"feature/x","ref":"main"}' \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/repository/branches" | jq .

# Delete a branch
curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/repository/branches/feature/x"
```

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| "project not found" | Wrong path or no permission | Confirm the `group/project` format |
| Fork failed with "already exists" | Already forked before | Delete the old fork or use another namespace |
| `glab repo archive` did not archive the project | The command only downloads a zip; it does not change project state | Archiving requires the REST API `POST /projects/:id/archive` |
| Cannot unarchive after archiving | The Web UI operation is irreversible | Unarchive via the REST API `POST /projects/:id/unarchive` |
