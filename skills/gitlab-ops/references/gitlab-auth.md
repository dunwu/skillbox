# Authentication and Identity Management

Covers glab login, SSH keys, PATs, and multi-identity isolation.

## Decision tree

```
Authentication issue?
├── First-time login → glab auth login
├── Check the current identity → glab auth status
├── Switch accounts → glab auth logout + glab auth login (glab has no auth switch subcommand)
├── Token expired → log in again
├── SSH key issues → check the ~/.ssh/ configuration
├── Authentication in CI/CD → CI_JOB_TOKEN / environment variables
├── Multi-Agent identity isolation → per-agent env files
```

## Login and status

```bash
# Interactive login (browser OAuth)
glab auth login

# Login with a token
glab auth login --stdin < my-token.txt
echo "$GITLAB_TOKEN" | glab auth login --stdin

# Specify a GitLab instance
glab auth login --hostname gitlab.example.com

# View the current identity
glab auth status
glab auth status --hostname gitlab.example.com

# Switch identity (glab has no auth switch; logout + login is required)
glab auth logout --hostname gitlab.example.com
echo "$NEW_TOKEN" | glab auth login --hostname gitlab.example.com --stdin
```

## SSH key diagnostics

```bash
# Test the SSH connection
ssh -T git@gitlab.example.com

# List registered SSH keys
glab ssh-key list

# JSON output
glab ssh-key list --output json
```

## Personal Access Token (PAT)

```bash
# List tokens
glab token list
```

### Token scopes

| Scope | Capability |
|-------|------|
| `api` | Full API read/write |
| `read_api` | Read-only API |
| `read_user` | Read user information |
| `sudo` | Execute as another user |
| `read_repository` / `write_repository` | Repository operations |

## Authentication in CI/CD

### CI environment (GitLab CI/CD)

```bash
# Automatically injected in CI environments; no configuration needed
$CI_JOB_TOKEN    # Lifetime matches the pipeline; scope is determined by .gitlab-ci.yml
```

### Agent scenarios (local / sandbox)

Credentials **must** be read and written through `scripts/config.py`; the only storage location
is `<skill-base>/config/.env` (see the "Managing credentials via config/.env" section). **Do not**
parse manually with `grep`/`cut`, and don't write the file with `cat > … << EOF` either — that
would expose the token in command text, shell history, and tool logs.

```bash
# Check readiness (exit code 0 = ready / 3 = not configured; output contains lengths only, never credential contents)
python scripts/config.py check
```

The script resolves credentials in the order "process environment variables → `config/.env`",
shared by all GitLab scripts.

It is **forbidden** to read credentials from a `.env` in any other location, and **forbidden** to
pass the token as a command-line argument.

## Managing credentials via config/.env

### File location

**The only valid location**: `<skill-base>/config/.env`

This file **may only be written by `scripts/config.py setup`** (which verifies connectivity before
writing and self-checks `.gitignore` protection afterwards). The sibling `settings.yaml` is
non-sensitive configuration committed and shared in the repo; credentials appearing there are a
violation.

### File format

Each line of `config/.env` is one `KEY=VALUE` pair, following the sibling `config/.env.example`:

```bash
# <skill-base>/config/.env
GITLAB_URL=https://gitlab.vmic.xyz
GITLAB_TOKEN=glpat-xxxxxxxxxxxx
```

`GITLAB_PROJECT` **does not go into this file**: it is not a credential; callers pass it via the
`--project` argument (the test suite specifies it as a constant at the top of `test/conftest.py`
or via the environment variable of the same name).

### Rules

1. **The file is protected by `.gitignore` exclusion, not by "living in the Skill directory"** —
   `config/.env` sits inside the workspace; it isn't committed only because the repository's
   `.gitignore` contains a bare `.env` pattern (matching any level). In a repository without that
   rule, or if you copy this Skill directory elsewhere, that protection **does not exist**:
   `setup` automatically runs `git check-ignore` and prints a `WARN` when there is no match; if you
   see that warning you **MUST** add the rule first
2. **Do not wrap values in quotes** — `GITLAB_TOKEN=glpat-xxx` (not `"glpat-xxx"`)
3. **The token must not be persisted anywhere else** — don't write it into code files, don't print
   it to logs, don't embed it in code
4. **Once committed, treat it as leaked** — once a token is committed, deleting the file does not
   revoke it; `git log --all --full-history -- <path>` can still dig it up. You must immediately
   revoke the PAT in GitLab and issue a new one
5. **Tokens are never passed on the command line** — `setup` offers no `--token <value>` flag; it
   only accepts interactive input (`getpass`, no echo) or reads from pre-existing environment
   variables. Command-line arguments end up in shell history and process lists; once a token
   appears there it must be treated as leaked

### Reading

Reading is done uniformly by `scripts/config.py`, resolving in the order "process environment
variables → `config/.env`"; all other scripts reuse the same entry point:

```bash
# Readiness check (by the Agent before every GitLab operation)
python scripts/config.py check          # exit code 0 = ready / 3 = not configured
```

```python
# Reading values inside a script (all 7 GitLab scripts do this)
from config import require_env
url = require_env("GITLAB_URL")
token = require_env("GITLAB_TOKEN")
```

### Writing and updating

```bash
# Method A: the user runs it in a real terminal (interactive; token is not echoed)
python scripts/config.py setup

# Method B: the user exports environment variables first, then the Agent runs setup to persist them (values never touch the command line)
export GITLAB_URL=... GITLAB_TOKEN=...
python scripts/config.py setup --from-env
```

Both paths verify with `GET /api/v4/user` first; **if verification fails, nothing is written to
disk**, avoiding persisting a credential that doesn't work.

### Handling missing credentials

When `check` returns exit code 3, the Agent **must** proactively guide the user through one of the
methods above, then rerun `check` to confirm readiness.

It is **forbidden** to guide the user into creating a `.env` anywhere else; **forbidden** to write
a real token manually with `cat` or an editor; **forbidden** to fall back to guessed values,
hardcoded values, or skipping authentication when credentials are unavailable.

### Security checklist

| Check | Command |
|--------|------|
| Credentials ready (including connectivity) | `python scripts/config.py check` (exit code 0) |
| `<skill-base>/config/.env` exists with both keys | `check` reports "set + length" item by item, without printing contents |
| **The file is excluded by .gitignore** | `git check-ignore -v "<skill-base>/config/.env"` (`setup` checks this automatically; no output means **unprotected** — add the rule before use) |
| **The file is untracked and absent from history** | `git ls-files <path>` (should be empty); `git log --all --oneline --full-history -- <path>` (should be empty) |
| Template synced for others to reference | `config/.env.example` exists with all-placeholder values |

## Credential caching

Avoid entering username and password on every push/pull.

```bash
# In-memory cache (default 15 minutes)
git config --global credential.helper cache

# Set the timeout (seconds)
git config --global credential.helper 'cache --timeout=3600'  # 1 hour

# macOS Keychain
git config --global credential.helper osxkeychain

# Windows Credential Manager
git config --global credential.helper manager

# Linux Secret Service
git config --global credential.helper libsecret
```

### Notes for Agent environments

- Don't use a credential helper in CI/CD; use `$CI_JOB_TOKEN` or environment variables instead
- In Agent sandboxes, credentials should be injected via environment variables rather than relying
  on a cache
- Avoid `manager` on shared machines (credentials are visible to all users)

## Multi-identity management (Agent scenarios)

```bash
# Pre-check: confirm the current identity
glab auth status

# Remediation steps when the identity doesn't match
# 1. Log out of the current identity
glab auth logout --hostname gitlab.example.com
# 2. Log in again with the correct token
echo "$CORRECT_TOKEN" | glab auth login --hostname gitlab.example.com --stdin
# 3. Verify
glab auth status
```

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| "authentication failed" | Token expired or invalid | Log in again or rotate the token |
| Wrong identity | Multiple accounts mixed up | Check with `glab auth status`; switch via `auth logout` + `auth login` |
| 403 in CI | Insufficient token scope | Check that the token's scopes include the required permissions |
