# gitlab-ops Skill Test Suite

This directory contains the automated tests for the gitlab-ops Skill, covering every git command, glab subcommand, and GitLab REST API documented in the SKILL docs.

## Requirements

- Python 3.9+
- git installed and on PATH
- [glab CLI](https://gitlab.com/gitlab-org/cli) installed (`glab --version` must work)
- A GitLab project available for testing, plus an Access Token

## Credentials and Test Project

The tests **provide no credential defaults**, so that credentials are never committed with the code.

| Variable | Description | Source |
|------|------|------|
| `GITLAB_URL` | GitLab instance URL | Environment variable, or `<skill-root>/config/.env` |
| `GITLAB_TOKEN` | Personal Access Token (requires `api` scope) | Same as above |
| `GITLAB_PROJECT` | Test project path (`namespace/project`) | Environment variable, or the `GITLAB_PROJECT` constant at the top of `test/conftest.py` |

> `GITLAB_URL` / `GITLAB_TOKEN` are read from exactly the same location as the Skill itself
> (both `scripts/config.py` and `test/conftest.py` point to `<skill-root>/config/.env`); there is no second credentials file.
> `GITLAB_PROJECT` is not a credential, so it **does not go into `.env`**.

### Configuration

**Option 1: Write to `config/.env` via the Skill's credential entry point (recommended)**

```bash
# 在 skill 根目录，检查是否就绪（退出码 0 就绪 / 3 未配置）
python scripts/config.py check

# 未就绪时录入：交互式，token 不回显，需真实终端
python scripts/config.py setup

# 或由用户先导出环境变量、再让 Agent 代跑落盘（值不经过命令行）
python scripts/config.py setup --from-env
```

`setup` verifies the connection before writing to disk, and self-checks that the file is excluded by `.gitignore`.

**Option 2: Set environment variables directly (takes precedence over `.env`)**

```bash
# Linux / macOS
export GITLAB_URL=https://gitlab.example.com
export GITLAB_TOKEN=glpat-xxxxxxxx
export GITLAB_PROJECT=mygroup/myproject

# Windows PowerShell
$env:GITLAB_URL="https://gitlab.example.com"
$env:GITLAB_TOKEN="glpat-xxxxxxxx"
$env:GITLAB_PROJECT="mygroup/myproject"
```

**If the test project is not specified**, any test that depends on GitLab will fail with a clear error on first access, telling you where to set it —
this suite ships with no real project ID; please point it at a test project you are comfortable letting it create and merge MRs in.

> `config/.env` is protected by the bare pattern `.env` in the repository's `.gitignore`, not by its directory location;
> after moving to a different repository, re-confirm the protection is in effect (`git check-ignore -v config/.env` should produce output).

## Running Tests

```bash
# 进入 test 目录
cd test

# 运行全部测试
python -m unittest discover -v

# 运行单个测试文件
python -m unittest test_gitlab_repo -v

# 运行单个测试类
python -m unittest test_gitlab_repo.TestRepoView -v

# 运行单个测试方法
python -m unittest test_gitlab_repo.TestRepoView.test_repo_view_current -v
```

You can also run from the skill root (without `cd test`) using the package form — this is the style given in the routing table of SKILL.md:

```bash
python -m unittest test.test_scripts test.test_branch_strategy test.test_config
python -m unittest test.test_gitlab_mr.TestMRList -v
```

Both entry points work; `test/__init__.py` adds this directory to `sys.path` (so modules use the flat form `from conftest import ...`).

## Test File Overview

### test_git_local.py — Local Git Commands (references/git-local.md)

Verifies every local git command documented in `references/git-local.md`.

| Scenario | What is verified |
|------|---------|
| Global config | `git config --global` read/write |
| Repo init | `git init` |
| Clone | `git clone`, `git clone --depth 1` (shallow clone) |
| Branch | `git branch`, `git checkout -b`, `git switch`, `git branch -d/-D` (including force-deleting an unmerged branch) |
| Commit | `git commit`, `git commit --amend` |
| Stash | `git stash`, `git stash pop`, `git stash list`, `git stash push -m` (with message), `git stash -u` (including untracked files) |
| Remote | `git remote add/list` |
| Tag | `git tag`, `git tag -a` |
| diff / log | `git diff` (staged), `git diff` (unstaged working-tree changes), `git diff A..B` (cross-branch comparison), `git diff --stat`, `git log --oneline` |
| cherry-pick | `git cherry-pick` (single), `git cherry-pick` (multiple consecutive commits) |
| merge / rebase | `git merge` (default), `git merge --no-ff` (forced merge commit), `git merge --ff-only` (fast-forward only), `git rebase` |
| revert | `git revert HEAD` (safe rollback, creates an inverse commit) |
| reset | `git reset --soft` (keeps the staging area), `git reset --hard` (discards all changes) |
| reflog / disaster recovery | `git reflog`, recovering a deleted branch via its reflog SHA |
| .gitignore | Rule syntax validation |
| .gitattributes | Rule syntax validation |

> Everything runs in a local temporary repository; no GitLab connection is needed (but the environment variables must exist).

### test_gitlab_auth.py — Authentication and Identity (references/gitlab-auth.md)

| Scenario | What is verified |
|------|---------|
| auth login | `--help` output contains `--hostname`, `--stdin` |
| auth status | Query current authentication status |
| auth status --hostname | Query for a specific hostname |
| auth switch | Verify the `switch` subcommand **does not exist** (use logout + login instead) |
| auth logout | `--help` output contains `--hostname` |
| ssh-key | `--help` validation for list / add / get / delete |
| token | `--help` validation for create / list / revoke |
| credential helper | git credential helper configuration validation |

### test_gitlab_repo.py — Repository Management (references/gitlab-repo.md)

| Scenario | What is verified |
|------|---------|
| repo view | View current project, a specified project, JSON output |
| repo browse | Verify the `browse` subcommand **does not exist** |
| repo fork | `--help` validation, confirming the `--name` and `--clone` flags |
| repo archive | `--help` validation (this command downloads a zip; it does **not** archive the project) |
| repo transfer | `--help` validation of the `--target-namespace` flag |
| Branch REST API | Create/list/delete branches via the REST API |

### test_gitlab_mr.py — Merge Requests (references/gitlab-mr.md)

| Scenario | What is verified |
|------|---------|
| mr create | `--help` validation of `--title`, `--source-branch`, `--fill`, and other flags |
| mr list | `--help` validation of `--state`, `--label`, and other filter flags |
| mr view | `--help` validation |
| mr merge | `--help` validation of `--squash` and `--remove-source-branch` flags |
| mr close | `--help` validation (**no** `--comment` flag) |
| mr note | `--help` validation of the `create` subcommand |
| mr diff | `--help` validation |
| mr approve | `--help` validation |
| mr rebase | `--help` validation |
| Branch management | Branch operations via the REST API |

### test_gitlab_issue.py — Issue Management (references/gitlab-issue.md)

| Scenario | What is verified |
|------|---------|
| issue create | `--help` validation of `--title`, `--label`, `--assignee`, and other flags |
| issue list | `--help` validation of filter flags; verify `--state opened` **does not exist** (opened is the default) |
| issue view | `--help` validation |
| issue close | `--help` validation (**no** `--comment` flag) |
| issue note | `--help` validation |
| issue update | `--help` validation |
| issue delete | `--help` validation (**no** `--yes` flag) |
| issue CRUD | Full create/query/update/close/delete flow via the REST API |

### test_gitlab_ci.py — CI/CD Pipelines (references/gitlab-ci.md)

| Scenario | What is verified |
|------|---------|
| ci status | `--help` validation |
| ci list | `--help` validation of `--scope` and `--ref` filters |
| ci view | `--help` validation |
| ci get | `--help` validation of the `--pipeline-id` flag (**not** a positional argument) |
| ci trace | `--help` validation |
| ci retry | `--help` validation that the argument is a job-id (**not** a pipeline-id) |
| ci cancel | `--help` validation of the `pipeline` subcommand usage |
| ci trigger | `--help` validation (triggers a manual job; **not** `--branch`) |
| schedule | `--help` validation for list / create / update / delete |

### test_gitlab_advanced.py — Other Features (references/gitlab-advanced.md)

| Scenario | What is verified |
|------|---------|
| release | `--help` validation for list / create / view / delete |
| snippet | `--help` validation for create / view |
| variable | `--help` validation for list / set / get / delete |
| label | `--help` validation for list / create |
| milestone | `--help` validation of `--project` / `--group` flags for list (**no** `view` subcommand) |
| runner | `--help` validation for list |
| packages | `--help` validation for list |
| todo | `--help` validation for list / done |

### test_gitlab_api.py — General REST API Patterns (references/gitlab-api.md)

| Scenario | What is verified |
|------|---------|
| Auth header | `PRIVATE-TOKEN` header authentication |
| Pagination | `?page=1&per_page=5` parameters |
| Sorting | `?order_by=created_at&sort=desc` parameters |
| Search | `?search=keyword` parameter |
| CRUD | GET request for project information |

### test_gitlab_e2e.py — End-to-End Scenarios

Verifies scenarios previously marked as "untestable", performing real operations against the test project and cleaning up afterwards.

| Scenario | What is verified |
|------|---------|
| Fork (REST API) | Fork a project via the API, verify, then delete |
| Fork (glab syntax) | Verify the `glab repo fork --help` flags are correct |
| Archive/unarchive | Via the REST API: archive → verify archived → unarchive → verify restored |
| Download archive | `glab repo archive` downloads a zip file (not project archival) |
| MR create + close | `glab mr create` in a temporary git repo, verify via API, then close |
| MR create + merge | `glab mr create` in a temporary git repo, merge with `glab mr merge --squash` |
| Transfer syntax | Verify the `--target-namespace` flag exists |

### test_scripts.py — Helper Scripts

Verifies that the Python scripts under `scripts/` are syntactically correct and that `--help` is executable.

| Script | What is verified |
|------|---------|
| branch_cleanup.py | Syntax + `--help` + `--dry-run` |
| ci_retry_failed.py | Syntax + `--help` |
| env_check.py | Syntax + `--help` |
| issue_triage.py | Syntax + `--help` |
| mr_batch_merge.py | Syntax + `--help` |
| release_notes.py | Syntax + `--help` |
| repo_audit.py | Syntax + `--help` |

### test_config.py — Credential Read/Write (scripts/config.py)

Purely local; never touches GitLab. Uses a temporary directory as a stand-in for the skill root, covering
the path constraints of `config/.env`, resolution order, `check` exit codes (0 ready / 2 environment error / 3 not configured),
**no token fragment ever echoed on any path**, no write to disk when validation fails (fail-closed),
`_write_env` preserving unrelated keys without producing duplicates, and output bytes being UTF-8 decodable with no BOM.

### test_branch_strategy.py — Branch Strategy Resolution (scripts/branch_strategy.py)

Purely local. Covers SSH/HTTPS remote normalization, local paths returning None,
`none` meaning "registered as not applicable" rather than "not registered", exit code 3 when unregistered,
default-strategy fallback, unknown strategy exiting 2 without writing to disk, write-back preserving header comments and existing entry order, and round-tripping a Chinese `reason`.

### test_conftest_helpers.py — The Test Suite's Own Resolution Logic

Purely local, zero network (permission checks use mocks; cross-process cases import `conftest` in a subprocess).
Pins down three spots that genuinely broke before: the `GITLAB_PROJECT` environment variable not being shadowed by the module constant,
credential resolution not requiring the test project, and the three tiers of `require_role` ("skip when insufficient / pass when sufficient / do not pass when the role cannot be determined").

## Cautions

### Test Project Requirements

- The e2e tests (`test_gitlab_e2e.py`) perform real operations on the project (creating branches, MRs, forks, archiving, etc.). Make sure you use a **dedicated test project**; do not run against production projects.
- The token needs the following scope: `api` (full API access).
- A full pass requires **Maintainer (access_level 40) or Owner on the test project**. Lower-privilege tokens (e.g. group bots are often Developer/30) are not treated as regressions; instead, tests are skipped per the table below:

| Capability | Required role | Behavior when insufficient |
|------|---------|-------------|
| CI/CD variable add/delete/query (the actual calls in `test_gitlab_api.TestVariableAPI` and `test_gitlab_advanced.TestVariable`) | Maintainer | `skipped：管理 CI/CD 变量 需要 access_level >= 40…` (managing CI/CD variables requires access_level >= 40…) |
| Project Webhooks (`test_gitlab_api.TestWebhookAPI`) | Maintainer | `skipped：管理项目 Webhook…` (managing project webhooks…) |
| Archive/unarchive (`test_gitlab_e2e.TestRepoArchive`) | Maintainer | `skipped：归档项目…` (archiving the project…) |
| Merging an MR into a protected branch (`test_gitlab_e2e.TestMRCreateAndMerge`) | Determined by branch protection and approval rules, not by role | Reads server-side `user.can_merge`; when `false`, `skipped：当前令牌对 master 无合并权限…` (current token has no merge permission on master…) |

- When the role cannot be determined (the API did not return `permissions`), tests **do not skip** — the real request is allowed to fail so the problem surfaces, avoiding "silent skips" that would mask permission failures.
- The skip decision for the merge case can only read the server-side `user.can_merge`, and `can_merge` only exists once a real MR exists,
  so `TestMRCreateAndMerge` **still leaves behind a closed test MR** in low-privilege environments (the source branch is deleted by `tearDown`, and GitLab closes it automatically).
  This is a known cost, not a residue bug.
- Hard-deleting an issue (`DELETE /issues/:iid`) requires Admin; a Developer token gets `403`, and the failure leaves behind an opened issue; therefore `TestIssueAPI` only does create → `PUT state_event=close`.
- The decision logic itself is self-verified by `test_conftest_helpers.py` (purely local, zero network, with injected negative controls).

### Residue Check

After running project-dependent tests, use read-only endpoints to confirm no resources were left behind (forks are especially easy to miss — see below):

```bash
python - <<'PY'
# 在技能根目录执行；GITLAB_PROJECT 必须已指定
import sys; sys.path.insert(0, "test")
import conftest as c
P = c._load_config()["PROJECT_PATH_ENCODED"]
for name, path in [("branches", "/repository/branches?per_page=100"),
                   ("opened MR", "/merge_requests?state=opened"),
                   ("opened issues", "/issues?state=opened"),
                   ("labels", "/labels?per_page=100"),
                   ("milestones", "/milestones?per_page=50"),
                   ("forks", "/forks")]:
    status, data = c.api_get(f"/projects/{P}{path}")
    print(f"{name:<15} http={status} n={len(data) if isinstance(data, list) else data}")
PY
```

### glab Authentication

- Tests inject authentication via the `GITLAB_TOKEN` environment variable and do not rely on glab's keyring.
- `_glab_env()` in `conftest.py` automatically injects the token into the subprocess environment.

### Known Behaviors

- `glab repo archive` downloads the repository as a zip; it does **not** set the project to read-only. Project archival requires the REST API.
- The `--clone` and `--remote` flags of `glab repo fork` must be joined with `=` (e.g. `--clone=false`); spaces are not accepted.
- `glab mr create` must be run inside a git repository directory, and the repository's remote must match the GitLab host.
- The MR/Issue close API uses `PUT` + `state_event: "close"`; there is no `POST .../close` endpoint.
- `glab mr close` has no `--comment` flag; add a comment first with `glab mr note create`.
- On Windows, glab output is UTF-8; Python subprocess must specify `encoding="utf-8", errors="replace"`.

### Cleanup

- Every e2e test has a `tearDown` that cleans up the branches, MRs, forks, and other resources it created.
- **A fork lands in the namespace of the identity performing the fork, not in the source project's namespace**.
  Building the path from the source project's first segment (e.g. `ocp/git-test-fork-verify`) returns 404, so `tearDown` would be deleting a non-existent project,
  leaking one repository on every run. `TestRepoFork` locates and deletes the fork using the `id` from the `POST /fork` response,
  with retry-waiting for the asynchronous import.
- If an interrupted test leaves residual data, delete it manually:
  - Branches: GitLab project page → Repository → Branches
  - MRs: GitLab closes them automatically when the source branch is deleted; no manual action needed
  - Issues: Developer can only close; hard deletion requires Admin
  - Forks: `GET /projects/:id/forks` to get the fork's `id`, then `DELETE /projects/<fork_id>`
    (`DELETE /projects/:id/forks/<fork_id>` is not a valid endpoint and returns 404)
