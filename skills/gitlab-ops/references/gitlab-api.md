# Advanced REST API Operations

Operations not covered by glab are performed via the REST API. Use `curl` with the `PRIVATE-TOKEN` header.

## Basic Template

```bash
GITLAB_URL="https://gitlab.example.com"
TOKEN="glpat-xxxxx"
PROJECT_ID=123

# GET request
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID" | jq .

# POST request
curl -s --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"title":"New Issue","labels":["bug"]}' \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/issues" | jq .

# PUT request
curl -s --request PUT --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"state_event":"close"}' \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/issues/1" | jq .

# DELETE request
curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/issues/1"
```

## Common API Endpoints

### Projects

```bash
GET    /api/v4/projects                           # List projects
GET    /api/v4/projects/:id                       # Project details
POST   /api/v4/projects                           # Create project
PUT    /api/v4/projects/:id                       # Update project
```

### Merge Requests

```bash
GET    /api/v4/projects/:id/merge_requests         # List MRs
GET    /api/v4/projects/:id/merge_requests/:iid    # MR details
POST   /api/v4/projects/:id/merge_requests         # Create MR
PUT    /api/v4/projects/:id/merge_requests/:iid    # Update MR
POST   /api/v4/projects/:id/merge_requests/:iid/merge  # Merge
```

### Repository Files

```bash
GET    /api/v4/projects/:id/repository/files/:path?ref=main    # Get file
POST   /api/v4/projects/:id/repository/files/:path             # Create file
PUT    /api/v4/projects/:id/repository/files/:path             # Update file
DELETE /api/v4/projects/:id/repository/files/:path             # Delete file
POST   /api/v4/projects/:id/repository/commits                 # Batch commit
```

### Variables

```bash
GET    /api/v4/projects/:id/variables              # List project variables
POST   /api/v4/projects/:id/variables              # Create variable
PUT    /api/v4/projects/:id/variables/:key         # Update variable
DELETE /api/v4/projects/:id/variables/:key         # Delete variable
```

### Webhooks

```bash
GET    /api/v4/projects/:id/hooks                  # List webhooks
POST   /api/v4/projects/:id/hooks                  # Create webhook
PUT    /api/v4/projects/:id/hooks/:hook_id         # Update webhook
DELETE /api/v4/projects/:id/hooks/:hook_id         # Delete webhook
```

## Pagination

```bash
# Default is 20 items per page, max 100
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects?per_page=100&page=2" | jq .

# Use the Link header to iterate through all pages
curl -sI --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects?per_page=100" | grep -i link
```

## Agent Usage Guidelines

- Always parse JSON responses with `jq`
- GET to confirm the target exists before any write operation
- Add sleep intervals between batch operations to avoid rate limiting
- Error response format: `{"message":"error description"}`; the HTTP status code indicates the error type

## Troubleshooting

| HTTP Status Code | Meaning | Action |
|-------------|------|------|
| 400 | Invalid request parameters | Check body format |
| 401 | Unauthenticated | Token is invalid or expired |
| 403 | No permission | Insufficient token scope |
| 404 | Resource not found | Check ID/path |
| 409 | Conflict | Resource already exists or state conflict |
| 429 | Rate limited | Reduce request frequency |
