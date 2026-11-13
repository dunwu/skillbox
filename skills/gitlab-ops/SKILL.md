---
name: gitlab-ops
version: 1.0.0
description: >-
  Use for any git or GitLab operation — local git operations
  (clone, diff, log, branch, merge, rebase), GitLab platform workflows
  (Merge Request, CI/CD, Issue, Release, repository management),
  or when you need guidance on git workflow methodology, safety rules,
  or version-control decisions. Covers the glab CLI and the GitLab REST API.
  Trigger words: commit、提交、git add、git status、暂存、
  git push、git pull、git merge、git rebase、git branch、git hook、hooksPath、
  MR、merge request、CI/CD、pipeline、glab、GitLab、
  分支管理、分支策略、该合到哪个分支、目标分支、集成分支、发布分支、
  git flow、trunk-based、分支保护、tag、release、issue、
  git clone、git diff、git log、git stash、cherry-pick、冲突解决、
  branch management、branch strategy、target branch、release branch、
  branch protection、conflict resolution.
---

# gitlab-ops

A complete guide to git and GitLab operations. Covers local git operations, GitLab platform workflows, methodology, and safety rules.

## File Routing

Load the corresponding sub-file based on the operation type:

| Operation Area | Sub-file | Trigger Scenarios |
|---------|--------|---------|
| Local git operations | [references/git-local.md](references/git-local.md) | clone, diff, log, branch, merge, rebase, stash, tag, config, cherry-pick, reflog, .gitignore, .gitattributes, Git Hook, commit conventions |
| Merge Request | [references/gitlab-mr.md](references/gitlab-mr.md) | MR creation, review, merge, merge gates, Stacked MR |
| CI/CD pipelines | [references/gitlab-ci.md](references/gitlab-ci.md) | pipeline viewing, job management, schedule, .gitlab-ci.yml, CI gates, stage orchestration, rules fallback |
| Issue management | [references/gitlab-issue.md](references/gitlab-issue.md) | Issue creation, triage, closing, linking with MRs, Issue templates |
| Repository management | [references/gitlab-repo.md](references/gitlab-repo.md) | project info, fork, archive, branch management |
| Server-side configuration | [references/gitlab-server-config.md](references/gitlab-server-config.md) | branch protection, Push Rules, merge settings, merge gates, mandatory pipelines, MR approval rules, tag protection |
| Authentication & identity | [references/gitlab-auth.md](references/gitlab-auth.md) | login, SSH key, PAT, credential caching, multi-identity management |
| REST API | [references/gitlab-api.md](references/gitlab-api.md) | operations not covered by glab, batch updates, Webhook |
| Other features | [references/gitlab-advanced.md](references/gitlab-advanced.md) | Release, Snippet, Variable, Label, Runner, Package |
| Quick Actions | [references/quick-actions.md](references/quick-actions.md) | slash command cheatsheet (/assign, /label, /merge, etc.) |
| End-to-end workflows | [references/workflows.md](references/workflows.md) | branching strategy selection (git-flow / assembly-flow / github-flow), Git Flow, Feature Branch, Hotfix, Code Review, release process |
| **Branching strategy resolution** | [scripts/branch_strategy.py](scripts/branch_strategy.py) + [config/settings.yaml](config/settings.yaml) | **MUST run `get` before every commit and before cutting branches, setting MR target branches, push targets, or release actions**; never guess when it returns `UNSET` |
| General troubleshooting | [references/troubleshooting.md](references/troubleshooting.md) | authentication failures, git conflicts, glab errors, disaster recovery (reflog/ORIG_HEAD) |
| Script templates | [scripts/](scripts/) | batch operation script templates |
| Test suite | [test/](test/) | **MUST run after changing this Skill**; regression entry point for script behavior and exit codes |

### Verification After Changing This Skill

```bash
# Run from the skill root (four suites that are purely local, requiring no credentials or network)
python -m unittest test.test_scripts test.test_branch_strategy test.test_config test.test_conftest_helpers

# GitLab-dependent suites: you must specify the test project first (not a credential; does not go into .env)
GITLAB_PROJECT=<dedicated test project> python -m unittest discover -s test
```

`test.test_branch_strategy` and `test.test_config` are isolated with temporary files and do not read or write the in-repo `config/settings.yaml` or `config/.env`.
The GitLab-dependent suites (`test_gitlab_*.py`) create real resources such as branches, MRs, and forks on the specified project, so you MUST use a dedicated test project;
capabilities that require the Maintainer role on the project (CI/CD variables, Webhooks, archiving) and merges into protected branches are reported as `skipped` with a reason when permissions are insufficient,
and do not count as regressions — see [test/README.md](test/README.md) for details and how to check for leftovers.

**Red-test disposition is mandatory.** A non-zero exit code is never an "expected failure" and must not be hidden by piping the command into another program. Capture the real exit code and stderr, rerun `python -m unittest <failing-suite> -v`, then classify the failure before touching any script or test:

| Failure signature | Classification and required action |
|---|---|
| `test_scripts` fails and `glab` is unavailable | Environment-blocked, not green. Install `glab` and rerun the suite; meanwhile run the other three local suites separately and report precisely which suite remains blocked. Do not weaken or skip the failing assertion. |
| `repo_audit.py` raises `TypeError: 'type' object is not subscriptable` | Interpreter incompatibility. Rerun with the supported Python version from §First-Run Environment Check; if it still fails on that version, stop and report a script defect with the traceback. |
| A test reader raises `UnicodeDecodeError` mentioning GBK/UTF-8 | Test-harness decoding failure, not a product pass or a product regression. Fix the caller to use the explicit UTF-8 capture rules below, then rerun; do not edit the expected behavior to make the error disappear. |
| Any other failure | Stop and report the failing test, exit code, and stderr. Do not modify scripts, tests, or fixtures unless the user has authorized that separate fix. |

## Safety Rules (Global)

### 🛑 STOP — Irreversible Operation Red Lines

> **🔴 CHECKPOINT: Before performing any operation in the table below, you must pause and confirm with the user. Executing without confirmation = incident.**

The following operations **must** be confirmed by the user before execution:

| Operation | Risk | Requirement |
|------|------|------|
| `git reset --hard` | discards uncommitted changes | user confirmation; back up with `git stash` first |
| `git branch -D` | discards unmerged branches | confirm the branch is disposable |
| `glab mr merge` | merges code | confirm the pipeline has passed and review is complete |
| `glab issue delete` | permanent deletion | user confirmation |
| `glab repo archive` | repository becomes read-only | user confirmation |
| `git clean -fd` | permanently deletes untracked files/dirs | user confirmation; dry-run with `git clean -nd` first |
| `git push --force` | overwrites remote history | user confirmation; prefer `--force-with-lease`; forbidden on shared branches (main/develop) |

### ⚠️ General Safety Rules (Check Before Every Operation)

1. **Check status before operating** — use `git status` to confirm the working tree is clean or stashed
2. **No bare stash in shared worktrees** — use `git stash push -u -m "unique-tag"`
3. **Agent-written tokens never touch disk** — never write them into code files, print them to logs, or embed them in code. **Sole Agent-write exception**: `<skill-base>/config/.env`, which may only be written by `scripts/config.py setup` after connection verification. Treat that file as **unprotected until proven otherwise**: before `setup` writes it, and whenever it already exists, run `git check-ignore -v -- <repo-relative-path-to>/config/.env` from the host repository root. Exit code 1, a negated rule, or an unreadable result means 🛑 STOP before `setup` or any staging while the file exists; exit code 0 must name an effective ignore rule. If the file is absent and no write is planned, unrelated explicit staging does not require this check. When this Skill lives in the target worktree, `git add -A` and `git add .` are always forbidden; stage explicit paths only. Never infer protection from the file's location or from a `setup` warning
4. **Redact secrets** — passwords/tokens appearing in scripts must be scrubbed from logs
5. **GET before write** — for REST API operations, query first to confirm the target exists
6. **Pace batch operations** — avoid triggering GitLab rate limiting (429)

### Master Decision Tree

```
Received a git/GitLab operation request?
├── Involves a commit / cutting a branch / setting an MR target / push target / release?
│   └── Resolve through Step 4 → then follow the subsection for that strategy in references/workflows.md §Branch Management Strategy
├── Purely local operations (no remote involved) → references/git-local.md
├── MR related → references/gitlab-mr.md
├── CI/CD related → references/gitlab-ci.md
├── Issue related → references/gitlab-issue.md
├── Repository management → references/gitlab-repo.md
├── Auth/identity issues → references/gitlab-auth.md
├── Operations not covered by glab → references/gitlab-api.md
├── Release/Snippet/Variable etc. → references/gitlab-advanced.md
├── Need slash commands → references/quick-actions.md
├── End-to-end flows → references/workflows.md
└── Hit an error → references/troubleshooting.md
```

## Agent Main Workflow (Execution Order After Receiving a Request)

> **Execute the following 6 steps in strict order. Skipping any step = violation.**

```
Step 1: Routing
  ├─ Read the user request → match against the "Master Decision Tree" → load the corresponding sub-file
  └─ Spans multiple areas → load multiple sub-files in order

Step 2: Environment gate
  ├─ Purely local read-only op (git diff / log / status / show / blame)? → skip all gates, go straight to Step 6 and execute
  ├─ First non-read-only operation? → run python scripts/env_check.py and record its real exit code
  ├─ Only glab is missing, while every dependency required by the requested local operation passed?
  │   ├─ GitLab operation → 🛑 STOP; install glab or use the credential-safe REST fallback in the failure table
  │   └─ Purely local operation → record "glab unavailable; GitLab operations blocked", skip Step 3, proceed to Step 4
  ├─ Any other required dependency failed? → 🛑 STOP; guide the user through installation (see the failure fallback table)
  └─ Passed → GitLab operations proceed to Step 3; purely local operations skip Step 3 and proceed to Step 4

Step 3: Credential gate (GitLab operations only) — credentials live in config/.env
  ├─ Run python scripts/config.py check
  ├─ Exit code 0 (ready) → readiness confirmed; check exports nothing to the Agent shell → use the credential-safe channel below for glab/curl → proceed to Step 4
  ├─ Exit code 3 (not configured) → 🛑 STOP; guide the user through setup (Method A interactive, preferred; Method B --from-env), then rerun check
  ├─ Setup/check errors → follow "Credential Check (Credential Gate)" below; never skip the gate or improvise credentials
  └─ Red line: tokens MUST NOT appear in command-line arguments, heredocs, file excerpts, or reply text

Step 4: Branching strategy gate (MUST run before every commit and before branches/MRs/pushes/releases) — the strategy is governed entirely by what is registered in settings.yaml
  ├─ Run python scripts/branch_strategy.py get inside the target repository
  ├─ Exit code 0 (prints git-flow / assembly-flow / github-flow)
  │   └─ Go to the subsection for that strategy in references/workflows.md §Branch Management Strategy, and use its transition rules to determine the branch-off source and MR target
  ├─ Exit code 0 (prints none) → no strategy applies to this project: control branches entirely per the user's stated intent for the current task,
  │   MUST NOT apply any model on your own (do not proactively suggest cutting a feature branch, do not pick an MR target yourself)
  ├─ Exit code 3 (UNSET) → 🛑 STOP; do not infer from document wording or existing branches in the repo:
  │   ├─ Present the three strategies (git-flow / assembly-flow / github-flow) and their criteria to the user
  │   ├─ User picks one → python scripts/branch_strategy.py set <strategy> --reason '<reason>' to write the registration
  │   ├─ User says none of the three applies → set none --reason '<reason>' (once registered, do not ask again)
  │   └─ MUST write back the registration; do not leave the project unregistered after answering only the immediate question
  └─ Exit code 2 → environment/argument/configuration error; fix per the error message and retry; never degrade into guessing

Step 5: Status check
  ├─ Run git status → confirm working-tree state
  ├─ Check the current branch: git branch --show-current
  │   └─ Already on a protected trunk (main/master/develop) with uncommitted changes? → 🛑 STOP, ask the user to confirm
  │       whether to commit directly on the trunk or cut a feature branch first (the branch-off source is decided by the strategy from Step 4)
  ├─ Uncommitted changes present? → branch by operation type:
  │   ├─ About to commit → the changes ARE the commit; do NOT stash, proceed to Step 6
  │   └─ About to run an operation needing a clean tree (checkout / rebase / pull / merge) → `git stash push -u -m "tag"` (or commit) first
  └─ Working tree clean → proceed to Step 6

Step 6: Execute the operation
  ├─ Execute per the specific commands in the sub-files
  ├─ Involves an irreversible operation? → 🛑 STOP → confirm with the user → execute only after explicit approval
  └─ Finished → check the exit code → present the result to the user
```

### Quick Reference for Frequent Operations

| Scenario | Command |
|------|------|
| Create a feature branch | `git checkout -b <feature branch name> origin/<BASE>` (`<BASE>` and the naming format are decided by the strategy; see references/workflows.md §Workflow 1) |
| Create an MR non-interactively | `glab mr create --title "feat(scope): title" --description "## Summary" --source-branch <src> --target-branch <TARGET> --no-editor` (`<TARGET>` is decided by the strategy) |
| Check pipeline status | `glab ci status` |
| Merge an MR | `glab mr merge <iid> --remove-source-branch` (whether to add `--squash`: see references/gitlab-mr.md §the squash authorship trap) |
| View a file's diff | `git diff HEAD~1 -- path/to/file` |
| Safely undo local changes | `git stash push -u -m "backup-$(date +%s)"` |

## Additional Tools

Core Python/git/glab/PyYAML requirements are defined only in §First-Run Environment Check.

| Tool | When Needed | Installation |
|------|------|------|
| `curl` | REST fallback when glab is unavailable or insufficient | usually bundled with the OS |
| `jq` | parsing JSON API output | `winget install jqlang.jq` / `brew install jq` / `sudo apt install jq` |
| `ssh` | SSH authentication instead of HTTPS | usually bundled with the OS |

## Interpreter Resolution

Use `python` for the commands in this Skill, but verify the interpreter before the first script invocation:

```bash
python --version
python -c "import sys; print(sys.executable)"
```

1. The printed version must satisfy §First-Run Environment Check, and the printed path must be a real Python installation.
2. Do not assume `python3` is equivalent. On Windows it may be a Microsoft Store alias that prints nothing and exits with code 49; that is a launcher failure, not a script with empty output and not a successful check.
3. If `python3` exhibits that behavior, stop retrying it and run the verified `python` interpreter instead. If `python` is also invalid, follow the installation fallback below.
4. When Python code invokes another script from this Skill, launch it with `sys.executable` so the parent and child use the same interpreter.
5. Never read `$?` after a pipeline and attribute it to the script; run the script directly or capture its own pipeline status (for example, Bash `PIPESTATUS`).

## Script Output and Encoding Conventions

The scripts in this Skill (`config.py`, `branch_strategy.py`, etc.) uniformly set stdout/stderr to **UTF-8**;
prompts and error messages contain Chinese.

> **A script can only guarantee one half — that what it emits is valid UTF-8 bytes; the capturing side must specify the encoding explicitly. The other half cannot be handled by the script.**

On Windows, `subprocess.run(..., text=True)` without an explicit `encoding` decodes
UTF-8 bytes using the locale (GBK); the reader thread raises `UnicodeDecodeError`, and the result is **`stdout` / `stderr` becoming `None`** —
the caller sees no error message at all, only an empty result, which is easily misdiagnosed as "the script produced no output".

```python
# ✅ Correct: specify the encoding explicitly
subprocess.run([sys.executable, script, "check"], capture_output=True,
               text=True, encoding="utf-8", errors="replace")

# ✅ Or capture bytes and decode yourself (consistent across platforms)
raw = subprocess.run([...], capture_output=True).stdout
text = raw.decode("utf-8", errors="replace")

# ❌ Wrong: text=True without an encoding
subprocess.run([...], capture_output=True, text=True)
```

When adding a new script that produces Chinese output, reuse `config.configure_utf8_stdio()`; do not write yet another encoding handler.

## 🔴 CHECKPOINT — First-Run Environment Check

> **🛑 STOP: Before the first non-read-only git/GitLab operation, the Agent must run this check. A failed dependency blocks every operation that needs it; missing `glab` blocks GitLab operations only. Purely local read-only operations are exempt.**

Step 2 is the sole invocation and dependency-routing procedure; this section is the authority for required versions and failure handling.

### Check Items

| Dependency | Minimum Version | Required | Notes |
|------|---------|------|------|
| `python` | **3.9+** | yes | `repo_audit.py` uses runtime-evaluated built-in generic annotations and fails on older interpreters |
| `git` | **2.41+** | yes | local version control (a warning is issued below 2.41) |
| `glab` | any | yes (GitLab operations) | GitLab CLI |
| `PyYAML` | any | yes | required for `branch_strategy.py` to read/write `config/settings.yaml`; when missing, the script fails with exit code 2 instead of silently degrading |

The current `env_check.py` reports Python as `OK` when it can parse any version; it does **not** enforce the 3.9 floor. Independently compare the `python --version` result from §Interpreter Resolution: Python <3.9 means the environment is not ready even when `env_check.py` prints `OK`.

### Handling Check Results

1. **All passed** → continue with the requested operation
2. **Only `glab` failed** → block GitLab operations; a purely local operation may continue only when all of its own dependencies passed, following Step 2
3. **Any other required dependency failed** → stop the dependent operation, report the missing items, and show the install commands
4. **User requests automatic installation** → run `python scripts/env_check.py --install`
5. **Automatic installation failed** → show the manual installation instructions and retry after the user completes them

### Post-Install Verification

After automatic installation completes, rerun Step 2 and confirm that every dependency required by the requested operation passes.

## 🔴 CHECKPOINT — Credential Check (Credential Gate)

> **🛑 STOP: After the environment check passes and before performing GitLab operations, the credential check must pass. Credentials unavailable = perform no GitLab operations.**

The only legitimate location for credentials is **`<skill-base>/config/.env`** (keys: `GITLAB_URL`, `GITLAB_TOKEN`).
All reads and writes are handled by `scripts/config.py` — **do not** parse it manually with `grep`/`cut`, and **do not**
write the file with `cat > … << EOF`; that would expose the token in command text, shell history, and tool logs.

**1. Check whether credentials are ready**

Run the check exactly as shown in Step 3. Exit code 0 means ready; exit code 3 means `GITLAB_URL` or `GITLAB_TOKEN` is missing. Output reports only whether each value is set and its character length, never its contents.

**2. Guide the user to configure when not ready (`setup`)**

`setup` performs, in order: read values → verify via `GET /api/v4/user` → write `config/.env` only on connection-verification success →
self-check that the file is excluded by `.gitignore`. **If connection verification fails, nothing is written**, avoiding stored credentials that don't work. The `.gitignore` self-check runs after the write and only warns; it is not fail-closed, so a warning requires the stop-and-verify procedure in Safety Rule 3 before any staging.

Two ways to supply values; neither passes them on the command line:

| Method | Command | Who Can Run It | Notes |
|------|------|---------|------|
| **A. Interactive (preferred)** | `python scripts/config.py setup` | **The user only**, requires a real terminal | the token is entered via `getpass` and not echoed. The Agent running it on the user's behalf fails due to no input (exit code 2); this is intended protection |
| **B. Persist from environment variables** | `python scripts/config.py setup --from-env` | The Agent may run it | the user first runs `export GITLAB_URL=… GITLAB_TOKEN=…` in their own terminal; the Agent passes only variable names (`--url-var` / `--token-var` can change them) and **never touches the values** |

**3. Use ready credentials without exporting or printing them**

The `check` subcommand loads `config/.env` only into its own Python process. It cannot modify the Agent's shell or any later `glab`/`curl` process.

- For `glab`, the user runs `glab auth login` in their own terminal (its credential store remains user-managed and is never read by the Agent), or starts the Agent with `GITLAB_URL` and `GITLAB_TOKEN` already exported. Never `source` `.env`, parse it with shell commands, or ask the user to paste the token into chat.
- For the REST fallback, run this wrapper **from the Skill root**. `require_env` uses the existing process environment first and `config/.env` second; curl receives the header on stdin through `--config -`, so the token is neither a command-line argument nor written into any new file by the wrapper:

```python
import subprocess
import sys

sys.path.insert(0, "scripts")
from config import require_env

url = require_env("GITLAB_URL").rstrip("/")
token = require_env("GITLAB_TOKEN")
subprocess.run(
    ["curl", "--fail", "--silent", "--show-error",
     "--config", "-", f"{url}/api/v4/user"],
    input=f'header = "PRIVATE-TOKEN: {token}"\n',
    text=True, encoding="utf-8", check=True,
)
```

Save it as a temporary script only when the user authorizes a new file, or execute it through `python -` with the same code on stdin. Replace only the URL and add non-secret curl options for other endpoints in [references/gitlab-api.md](references/gitlab-api.md); do not copy that file's placeholder token assignment as a real value.

**4. Handling Results**

| Symptom | Meaning | Action |
|------|------|------|
| `check` exit code 3 | not configured or a key is empty | follow the `setup` guidance above (prefer method A) |
| `setup` reports `HTTP 401/403` | token invalid, expired, or insufficient scope | follow the PAT remediation rows in §Failure Fallback Table, then run `setup` again |
| `setup` reports `无法连接 / getaddrinfo failed` (unable to connect) | wrong address or network unreachable | verify `GITLAB_URL` (protocol, hostname, no stray spaces) |
| `setup` reports `没有可读输入` (no readable input) | the Agent tried to run an interactive command | have the user run method A themselves, or switch to method B |
| `WARN: … 未被 .gitignore 排除` (not excluded by .gitignore) | the file has already been written but is not proven ignored | stop before any staging; add an effective `.env` ignore rule in the host repository, rerun the `git check-ignore -v` proof in Safety Rule 3, and stage only explicit non-secret paths |

> Whichever path is taken, the token **MUST NOT** appear in command-line arguments, heredocs, file content excerpts, or reply text.
> Once a token has entered version-control history, treat it as compromised: deleting the file does not undo it — immediately revoke the PAT in GitLab
> and issue a new one.

## Failure Fallback Table

> Each failure scenario is handled in three stages: trigger condition → first-line fix → last-resort fallback. Do not skip the fallback step.

| Trigger Condition | First-Line Fix | Last-Resort Fallback |
|---------|---------|-----------|
| `config.py check` exit code 3 (not configured) | guide the user to run `config.py setup` (interactive, by the user themselves) or `setup --from-env` (run by the Agent) → writes `config/.env` | guide the user to issue credentials first: `GitLab → Settings → Access Tokens → create a PAT (api scope)` |
| File exists but `GITLAB_URL` or `GITLAB_TOKEN` is empty | `check` also returns 3 → rerun `setup` to overwrite that key (the script preserves other keys) | guide the user to fill in each item per `config/.env.example`, then rerun `setup` |
| `setup` reports `HTTP 401` | token expired or revoked → rerun `setup` with a new token (the script won't write to disk if verification fails) | follow the PAT issuance procedure in the `check` exit 3 row above |
| `setup` reports `HTTP 403` | insufficient token scope → prompt to check token permissions | follow the PAT issuance procedure in the `check` exit 3 row above |
| `setup` reports connection failure / `getaddrinfo` | check URL spelling and protocol → check network connectivity | rerun `setup` and have the user re-enter the GitLab address |
| `setup` reports `没有可读输入` (no readable input) | the Agent tried to run the interactive entry on the user's behalf — this command requires a human typing live | have the user run it themselves, or switch to `setup --from-env` |
| `setup` reports `WARN: 未被 .gitignore 排除` (not excluded by .gitignore) | the write has already happened: stop all staging, add an effective `.env` rule, then prove it with `git check-ignore -v` per Safety Rule 3 | until ignore protection is proven, perform no `git add`; for future runs prefer credentials already exported by the user instead of persisting again |
| `python3 --version` reports `command not found` | verify `python --version` and its executable path per §Interpreter Resolution → run Step 2 with that interpreter | if no supported real interpreter is available, install Python 3.9+: `winget install Python.Python.3` / `brew install python3` / `sudo apt install python3` |
| `python3` prints nothing and exits with code 49 on Windows | treat it as a Microsoft Store launcher stub, not as script output; verify `python --version` and `python -c "import sys; print(sys.executable)"`, then use that interpreter | if `python` is not a supported real interpreter, install Python and rerun the version/path checks before any Skill script |
| `glab` is missing or reports `command not found` | purely local operations may proceed only per Step 2; for GitLab operations run `winget install glab` / `brew install glab` / download the binary from the GitLab website | for GitLab operations, degrade to pure REST API mode using `curl` + the `PRIVATE-TOKEN` header through the credential-safe channel (see references/gitlab-api.md); never place the token in a command argument |
| `glab auth status` reports `no token configured` | guide the user to run `glab auth login` or set the `GITLAB_TOKEN` environment variable | if the user cannot log in interactively (CI environment), follow the PAT issuance procedure in the `check` exit 3 row above |
| `glab auth status` reports `401 Unauthorized` (token expired) | guide the user to regenerate a PAT in GitLab → run `glab auth login` themselves (interactive; the token is never passed as a command-line argument) | check for multi-identity conflicts: `glab auth status --hostname` to confirm the target hostname is correct |
| `glab mr create` reports `403 Forbidden` | verify PAT permissions per the credential fallback rows above; check whether the protected branch allows this user to push | if using CI `CI_JOB_TOKEN`, confirm the `GITLAB_TOKEN` variable is configured in `.gitlab-ci.yml` with sufficient scope |
| REST API returns `429 Too Many Requests` | wait the number of seconds specified by the `Retry-After` header, then retry | reduce batch-operation concurrency: add a `sleep 1` interval; check whether GitLab global rate limiting was triggered |
| `git clone` times out (>5 minutes) | check network connectivity: `curl -I "$GITLAB_URL"` | try a shallow clone: `git clone --depth 1`; for large repositories, use `--filter=blob:none` for a partial clone |

---

## 🔴 Agent Execution Checkpoint Quick Reference

> **A summary of all mandatory stop points in this Skill. Hitting any one = pause execution and wait for user confirmation or the condition to be met.**

| # | Checkpoint | Trigger Condition | Stop Action |
|---|--------|---------|---------|
| 1 | 🛑 Irreversible operation | about to run `reset --hard` / `branch -D` / `clean -fd` / `push --force` / `mr merge` / `issue delete` / `repo archive` | pause → present the risks to the user → obtain confirmation |
| 2 | 🔴 Environment check | before the first non-read-only git/GitLab operation | apply Step 2 → a failed dependency blocks dependent operations; missing `glab` blocks GitLab operations only, and purely local read-only operations are exempt |
| 3 | 🔴 Credential check | after the environment check passes, before GitLab operations | apply Step 3 and §Credential Check → on exit code 3, proactively guide `setup` (interactive run by the user, or `--from-env` persisted by the Agent) → **forbidden** to read/write `.env` manually or let the token appear in command text |
| 4 | 🔴 Branching strategy gate | before every commit and before cutting a branch / setting an MR target / push target / release | apply Step 4 → on `UNSET` (exit code 3), stop, guide the user to choose, then `set` to write it back (use `set none` when none of the three applies) → **never guess the target branch**; when the output is `none`, control branches per the user's stated intent without applying any model |
| 5 | ⚠️ Pre-operation status | before every write operation (commit/push/merge) | `git status` + `git branch --show-current` to confirm the working tree and current branch |
| 6 | ⚠️ Committing on trunk | currently on `main`/`master`/`develop` and about to commit | pause → confirm "commit directly on trunk" vs. "cut a feature branch first" |
| 7 | ⚠️ Token safety | any operation involving credentials or staging | no token in output, arguments, or code; the sole Agent-written on-disk exception is `config/.env` written by `setup`, and Safety Rule 3's conditional ignore proof must pass before writing it or staging while it exists |

## Agent Anti-Pattern Blacklist

> **The most common mistakes the Agent makes when using this Skill. Hitting any one = stop immediately, correct it, then continue.**

| # | Anti-Pattern | Why It's Wrong | Correct Approach |
|---|--------|---------|---------|
| 1 | **Hardcoding tokens into scripts/config files** | a leaked token = the entire GitLab account is taken over; once committed to a repo it cannot be clawed back | always inject via the environment variable `$GITLAB_TOKEN` or `glab auth login` interactively; reference `$VAR` in scripts |
| 2 | **Bare `git stash` in a shared worktree** | `git stash` without a tag → indistinguishable among multiple people/agents sharing the worktree → applying the wrong stash corrupts code | `git stash push -u -m "agent-unique-tag"` → restore with `git stash apply stash^{/agent-unique-tag}` |
| 3 | **`git push --force` to main/develop** | overwrites others' commits, breaks CI history, irreversible | only `--force-with-lease` to personal feature branches is allowed; force-pushing shared branches is forbidden |
| 4 | **Skipping the environment check or letting a `glab` failure block unrelated local work** | missing dependencies invalidate dependent operations, but `glab` is not needed for a purely local commit | apply Step 2 before the first non-read-only operation; follow its dependency-scoped branches instead of either skipping the check or stopping all local work |
| 5 | **Silently swallowing git's stderr** | git error messages go to stderr; looking only at stdout makes failures look like success (e.g., clone fails but stdout is empty) | always check the exit code `$?`; redirect stderr to a log or show it to the user |
| 6 | **Batch API calls without intervals** | GitLab global rate limiting (default 600 req/min); once 429 is triggered all requests are rejected | add `sleep 1` between batch operations; on 429, read the `Retry-After` header and wait |
| 7 | **Committing directly on main/develop** | violates the branching strategy → MR review becomes a formality → code not verified by CI enters the trunk | resolve Step 4 first; commit on the trunk only when the strategy allows it (e.g., a tools repo directly on `master`) or the user explicitly agrees; otherwise cut a feature branch |
| 8 | **Merging an MR before its pipeline passes** | CI failure = tests not passing / broken build → merging pollutes the trunk | confirm the pipeline is `passed` with `glab ci status` before merging |
| 9 | **Using `subprocess` with `text=True` but no `encoding`** | Windows decodes the script's UTF-8 output as GBK; after the reader thread raises, `stdout`/`stderr` become `None`; the caller misreads "can't read output" as "the script didn't respond", silently losing all diagnostics | explicitly set `encoding="utf-8", errors="replace"`, or capture bytes and decode yourself (see §Script Output and Encoding Conventions) |

## Output Specification

> **After completing an operation, the Agent reports the result to the user in the following format.**

### Successful Operation

```
✅ Operation completed: [operation name]
- Branch: feature/TICKET-123-desc
- Remote: pushed to origin
- MR: !42 created → https://gitlab.example.com/group/project/-/merge_requests/42
```

### Failed Operation

```
❌ Operation failed: [operation name]
- Error: [specific error message, from stderr]
- Cause: [analyzed possible cause]
- Suggested fix: [specific steps from the failure fallback table]
```

### User Confirmation Required

```
⚠️ Confirmation required: about to perform an irreversible operation
- Operation: [specific operation, e.g., git reset --hard]
- Impact: [scope of impact, e.g., 3 uncommitted files will be lost]
- Backup: [backup measures taken, e.g., already stashed]
- Proceed? (y/n)
```

## Scenario Judgment Guide

> **When a user request is ambiguous, judge the intent by the following rules.**

| User Says | Actual Intent | Sub-files to Load | Execution Path |
|--------|---------|-----------|---------|
| "show me what changed" | view the diff | references/git-local.md | `git diff` or `git diff --cached` |
| "commit the code" | commit (confirm whether to push as well) | references/git-local.md + references/workflows.md | resolve Step 4 to confirm the current branch is compliant → `git add` (stage files precisely) → `git commit` (Angular format, single responsibility) → `git push` only when the user explicitly asks |
| "open an MR" | create an MR | references/gitlab-mr.md + references/workflows.md | resolve Step 4 to get `<TARGET>` → confirm the branch is pushed first → `glab mr create --target-branch <TARGET>` → show the MR link |
| "CI is broken" | troubleshoot the pipeline | references/gitlab-ci.md + references/troubleshooting.md | `glab ci status` → `glab ci view` → locate the failed job → analyze the logs |
| "merge this MR" | merge an MR | references/gitlab-mr.md | 🛑 check pipeline status + review status first → user confirmation → `glab mr merge` |
| "create an issue" | create an Issue | references/gitlab-issue.md | collect title/description/labels → `glab issue create` |
| "info about this repo" | view the project | references/gitlab-repo.md | `glab repo view` or the REST API |
| "the token expired" | authentication issue | references/gitlab-auth.md | guide re-login or PAT refresh |

## 🔴 Post-Operation Self-Check Checklist

> **After every operation, check each item. Failing any one = the operation is not complete.**

| # | Check Item | How to Verify |
|---|--------|---------|
| 1 | command exit code is 0 | check `$?` or catch exceptions |
| 2 | remote state matches expectations | `git fetch` + `git status` to confirm no unexpected changes |
| 3 | no token/password leaked into output | check stdout/stderr logs for sensitive strings like `glpat-`, `Bearer` |
| 4 | the user has been informed of the result | present the result per the "Output Specification" format |
| 5 | irreversible operations had user confirmation | look back in the conversation for an explicit confirmation message from the user |
| 6 | branching strategy compliance | before every commit and every operation involving branches/MRs/pushes/releases, Step 4 was resolved (not UNSET); no target branch was guessed on unregistered projects; the feature branch was not pushed directly to a protected trunk; the MR was created with `--target-branch` consistent with the strategy |
| 7 | commit has a single responsibility | this commit contains only one logical change; unrelated changes were split out; the commit body explains "why" rather than listing which lines changed |
| 8 | temporary resources cleaned up | working stashes popped after the operation; a backup stash made before `reset --hard` is NOT popped (it would restore the discarded changes) — keep it or drop it only after user confirmation; temporary branches deleted |
