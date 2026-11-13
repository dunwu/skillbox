# Other GitLab Features

Covers Release, Snippet, Variable, Label, Milestone, Runner, Package, Todo, and more.

## Release

```bash
# List releases
glab release list

# Create a release
glab release create v1.0.0 \
  --name "v1.0.0" \
  --notes "$(cat <<'EOF'
## What's Changed
- Add user authentication module
- Fix token refresh issue
EOF
)" \
  --assets-links '[{"name":"binary","url":"https://..."}]'

# View a release
glab release view v1.0.0

# Delete a release
glab release delete v1.0.0
```

## Snippet

```bash
# Create a snippet
glab snippet create main.go --title "sample code"

# View (glab has no snippet list subcommand; list via REST API)
glab snippet view <id>

# List snippets via REST API
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/snippets" | jq .
```

## Variables

```bash
# Project variables
glab variable list
glab variable set DEPLOY_URL "https://staging.example.com"
glab variable set SECRET_KEY "xxx" --masked --protected
glab variable get DEPLOY_URL
glab variable delete DEPLOY_URL

# Group variables
glab variable list -g my-group
glab variable set API_KEY "xxx" -g my-group

# Variable flags
# --masked: hidden in logs
# --protected: only available on protected branches/tags
# --raw: do not expand variable references
```

## Labels

```bash
glab label list
glab label create --name bug --color "#FF0000" --description "bug"
glab label create --name feature --color "#00FF00"
```

## Milestone

```bash
glab milestone list --project group/project
glab milestone list --group my-group
glab milestone create --title "Sprint 25" --start-date 2026-09-22 --due-date 2026-10-03
```

## Runners

```bash
# List project runners
glab runner list

# Register a runner (requires admin)
glab runner register

# Delete a runner
glab runner delete <runner-id>
```

## Packages

```bash
# List project packages
glab packages list

# Delete a package
glab packages delete <package-id>
```

## Todo

```bash
glab todo list
glab todo list --type=MergeRequest
glab todo done 123
glab todo done --all
```

## User Info

```bash
# Current user info (via REST API)
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/user" | jq .
```

## Work Items

glab has no work-item subcommand yet; use the REST API or the GitLab Web UI instead.

```bash
# List work items via REST API (requires GitLab Premium/Ultimate)
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/work_items" | jq .
```
