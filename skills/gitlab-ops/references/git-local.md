# Local Git Operations

Covers all purely local git operations that do not depend on the GitLab server.

## Safety Rules (Prerequisites)

### Confirmation Checklist for Irreversible Operations

| Operation | Risk level | Confirmation requirement |
|------|---------|---------|
| `git reset --hard` | High | Explicit user confirmation required; forbidden on uncommitted work |
| `git checkout` / `restore` | Medium | Stash first when there are uncommitted changes |
| `git rebase` (interactive) | Medium | `--no-edit` is forbidden; `-i` is forbidden (requires interactive input) |
| `git branch -D` | Medium | Confirm the branch is merged or the user explicitly wants to discard it |

### General Safety Rules

- Run `git status` before operating to confirm the working tree state
- Before major operations, `git stash -u` or create a backup branch
- In shared worktrees, bare `git stash` is forbidden (use a unique tag)

## Config

### Three-Level Configuration Hierarchy

```
Configuration precedence (high → low):
├── Repo level    .git/config          ← git config <key>
├── User level    ~/.gitconfig          ← git config --global <key>
└── System level  /etc/gitconfig        ← git config --system <key>
```

### Common Configurations

```bash
# User identity (required)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Credential cache (avoid re-entering passwords)
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=3600'  # 1 hour

# Default branch name
git config --global init.defaultBranch main

# Pull strategy
git config --global pull.rebase true     # rebase instead of merge on pull
git config --global fetch.prune true     # auto-prune deleted remote branches on fetch

# Aliases (for efficiency)
git config --global alias.s  status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --graph --oneline --decorate --all -20"
git config --global alias.ds "diff --staged"
git config --global alias.unpushed "log @{u} --oneline"

# View current configuration
git config --list
git config --list --global
git config user.name   # view a specific item
```

### Notes for Agents

- Do not modify `--global` or `--system` configuration in the Agent sandbox; use `--local` (repo level) only
- Credential cache should be disabled in CI environments; inject tokens via environment variables instead

## Clone

### Decision Tree

```
Need to clone?
├── Only need to read diff/log → git clone --depth=1 (shallow, saves bandwidth)
├── Need full history → git clone (full)
├── Huge repo and only need one branch → git clone --single-branch -b <branch>
├── Tight disk space → git clone --filter=blob:none (partial clone)
└── Need submodules → git clone --recurse-submodules
```

### Command Templates

```bash
# Standard clone
git clone <url> [directory]

# Shallow clone (latest snapshot only)
git clone --depth=1 <url>

# Specific branch
git clone --single-branch -b <branch> <url>

# With submodules
git clone --recurse-submodules <url>

# Specific protocol
git clone https://gitlab.example.com/group/project.git
git clone git@gitlab.example.com:group/project.git
```

### Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| Authentication failed | Credentials expired or no permission | Check SSH key or PAT |
| RPC failed; curl 18 | Large file transfer interrupted | `git config http.postBuffer 524288000` |
| shallow update not allowed | Server forbids shallow clones | Drop `--depth` and do a full clone |
| fatal: destination exists | Directory already exists | Delete it or choose another directory |

## Diff

### Decision Tree

```
What difference do you need to see?
├── Working tree vs staging area → git diff (no arguments)
├── Staging area vs HEAD → git diff --cached / --staged
├── Working tree + staging vs HEAD → git diff HEAD
├── Between two branches/commits → git diff <A>..<B>
├── History of changes to a file → git log -p -- <file>
├── One file across two versions → git diff <A>:<file> <B>:<file>
└── Summary statistics of changes → git diff --stat <A>..<B>
```

### Command Templates

```bash
# Unstaged changes
git diff

# Staged changes
git diff --cached

# All changes (unstaged + staged)
git diff HEAD

# Between two refs
git diff main..feature-branch
git diff abc123..def456

# Statistics only
git diff --stat main..HEAD

# One file only
git diff main..HEAD -- path/to/file.java

# Ignore whitespace changes
git diff -w main..HEAD

# Output as a patch file
git diff main..HEAD > changes.patch
```

### Usage Guide for Agents

- diff output can be very long; prefer `--stat` for an overview before drilling down
- In large repos, use `--diff-filter=ACMR` to see only added/modified/renamed files
- Binary files require `--binary` to show differences

## Log

### Decision Tree

```
What history do you need?
├── Last N commits → git log -n <N> --oneline
├── Change history of a file → git log -- <file>
├── Who changed which line → git blame <file>
├── Common ancestor (branch point) of two branches → git merge-base <A> <B>
├── Commits within a time range → git log --since/--after/--until/--before
├── Commits by someone → git log --author=<name>
└── Commits containing a keyword → git log --grep=<keyword>
```

### Command Templates

```bash
# Compact format
git log --oneline -20

# With per-file change statistics
git log --stat -5

# Graphical branch history
git log --oneline --graph --all -30

# Full history of a file (with rename tracking)
git log --follow -- <file>

# Who changed a given line
git blame -L 10,20 -- <file>

# Search commit messages
git log --grep="fix:" --oneline

# All commits between two refs
git log --oneline main..HEAD

# Custom format (Agent-parsing friendly)
git log --format="%H|%an|%ae|%ai|%s" -10
```

### Usage Guide for Agents

- Always use `--format` to output structured data for easy parsing
- Use `--no-merges` to filter out merge commits and see only substantive changes
- In large repos, limit with `-n` to avoid overly long output

## Branch

### Decision Tree

```
Branch operation?
├── List branches → git branch / git branch -a
├── Create without switching → git branch <name>
├── Create and switch → git checkout -b <name> / git switch -c <name>
├── Delete a merged branch → git branch -d <name>
├── Force-delete an unmerged branch → git branch -D <name> (confirmation required)
├── Rename the current branch → git branch -m <new-name>
└── Set upstream tracking → git branch -u origin/<branch>
```

### Naming Conventions

> **Branch naming is not globally uniform; it is determined by the strategy registered for the
> repository** (`python scripts/branch_strategy.py get`). The table below shows only the general
> shape; for each strategy's concrete format, see the corresponding section of workflows.md:
> git-flow → "Naming examples"; assembly-flow → "Naming convention (consistent with server-side
> Push Rules regex)"; github-flow → the branch names inside "Workflow".

```
feature/<ticket>-<short-desc>    # new feature
bugfix/<ticket>-<short-desc>     # bug fix
hotfix/<ticket>-<short-desc>     # urgent fix
release/<version>                # release branch
```

> `assembly-flow` uses `feature/<requirement-ID>--<description>` (**double** dash), matching the
> server-side Push Rules regex `^(feature/.+--.+|fix/.+|release/\d+\.\d+\.\d+|develop|master)$`;
> a single dash would be rejected by that regex. When referencing naming formats across documents,
> you **MUST** state the strategy; do not apply this table generically.

### Branch Maintenance

```bash
# Check whether branches are merged into the current branch
git branch --merged main
git branch --merged HEAD

# List unmerged branches
git branch --no-merged main

# Clean up merged local branches
git branch --merged main | grep -v "main" | xargs git branch -d

# Clean up local tracking branches whose remotes are deleted
git fetch --prune

# Inspect diverging commits between two branches
git log --oneline --left-right main...feature-branch

# Recover from committing to the wrong branch: accidentally committed to main
git branch feature/correct-branch  # create a new branch at current HEAD
git reset --hard HEAD~1            # move main back one commit
git checkout feature/correct-branch # switch to the correct branch
```

## Merge vs Rebase

### Decision Tree

```
Integrating changes from another branch?
├── Need to preserve merge history → git merge
│   ├── Fast-forward suffices → git merge --ff-only
│   └── Keep a merge commit → git merge --no-ff
├── Need linear history → git rebase
│   ├── Rebase onto target → git rebase <target>
│   └── Continue after conflicts → git rebase --continue
├── Undo a merge → git revert <merge-commit> -m 1
└── Unsure → default to merge (safe, does not rewrite history)
```

### Key Rules

- **Do not rebase commits that have been pushed** — rebase rewrites SHAs, and others will hit conflicts when they pull
- Personal branches may be rebased to stay tidy; shared branches use merge
- After resolving conflicts: for merge use `git add` + `git commit`; for rebase use `git add` + `git rebase --continue`

### Advanced Merge Strategies

```bash
# Squash merge: compress all commits of a branch into one
git merge --squash feature-branch
git commit -m "feat: implement XXX feature"
# ⚠️ after squash, all changes are attributed to the author of this single commit; the original
#    authors of the source commits are lost. Do not use this when the source branch contains
#    commits by others — see gitlab-mr.md §The authorship trap of squash

# Keep merge evidence without auto-committing
git merge --no-ff --no-commit feature-branch
# Inspect the merge result → commit manually when satisfied

# Combine multiple unpushed commits (interactive rebase)
# Note: interactive rebase is not supported in the Agent environment; use reset --soft instead
git log --oneline HEAD~5..HEAD  # confirm the commits to combine
git reset --soft HEAD~3          # move back 3 commits, keeping changes staged
git commit -m "combined commit message"
```

## Cherry-pick

Pick specific commits from other branches and apply them to the current branch.

```bash
# Pick a single commit
git cherry-pick abc123

# Pick multiple commits
git cherry-pick abc123 def456 ghi789

# Pick a range (exclusive of the start)
git cherry-pick abc123..def456

# Keep original author information
git cherry-pick --no-commit abc123  # stage without committing; you can edit the message when committing manually

# On conflict
git cherry-pick abc123
# Resolve conflicts → git add → git cherry-pick --continue
# Abort: git cherry-pick --abort
```

### Typical Scenario

```
Scenario: a bug fix lives on a feature branch and also needs to be applied to a hotfix branch
1. git checkout hotfix/urgent
2. git cherry-pick <bugfix-commit-sha>
3. Resolve conflicts (if any) → git cherry-pick --continue
4. git push
```

## Undo and Recovery

### Decision Tree

```
What do you need to undo?
├── Unstage (keep changes) → git reset HEAD <file>
├── Discard working-tree changes → git checkout HEAD -- <file> / git restore <file>
├── Undo the last commit (keep changes staged) → git reset --soft HEAD~1
├── Undo the last commit (keep changes in working tree) → git reset --mixed HEAD~1
├── Undo the last commit (discard all changes) → git reset --hard HEAD~1 (dangerous!)
├── Create a reverse commit (safe, does not rewrite history) → git revert <commit>
├── Undo a merge → git revert <merge-commit> -m 1
├── Undo a rebase/merge → git reset --hard ORIG_HEAD
├── Recover an accidentally deleted commit/branch → git reflog → git reset --hard <sha>
└── Amend the last commit message → git commit --amend -m "new message"
```

### reflog — the Last Safety Net

`git reflog` records every movement of HEAD; even commits that have been reset or branches that have
been deleted can be recovered.

```bash
# View HEAD history
git reflog

# Example output:
# a1b2c3d HEAD@{0}: checkout: moving from feature to main
# e4f5g6h HEAD@{1}: commit: fix: fix login logic
# i7j8k9l HEAD@{2}: checkout: moving from main to feature

# Restore to any historical state
git reset --hard e4f5g6h

# Recover an accidentally deleted branch
git reflog  # find the commit SHA before deletion
git checkout -b recovered-branch <sha>
```

**Key point**: reflog only keeps local operations (90 days by default); it does not track file
content changes and does not record cross-repository operations.

### ORIG_HEAD

Before performing dangerous operations such as merge or rebase, Git saves the original HEAD to
`ORIG_HEAD`.

```bash
# Undo a just-completed rebase or merge
git reset --hard ORIG_HEAD
```

## Stash

### Decision Tree

```
Need to temporarily shelve the working tree?
├── Save everything (including untracked) → git stash -u
├── Save with a description → git stash push -m "description"
├── Save only some files → git stash push -p (interactively select hunks)
├── Restore the most recent stash → git stash pop
├── Restore without deleting → git stash apply
├── Restore a specific stash → git stash pop stash@{2}
└── List stashes → git stash list
```

### Shared Worktree Warning

- A bare `git stash` interferes with others in shared environments
- Safe practice: `git stash push -u -m "unique-tag-$(date +%s)"`; restore using the exact reference

## Staging Area Operations

### Partial Staging

```bash
# Stage selected hunks of a file (interactive mode)
git add -p <file>
# y = stage this hunk, n = skip, s = split, e = edit manually, q = quit

# Stage a new file without tracking its content (mark first, then select)
git add -N <file>
git add -p <file>  # now you can select specific lines

# Swap the staging area and the working tree (staged becomes unstaged and vice versa)
git stash -k       # stash the unstaged part
git reset --hard   # clear the working tree (keep the staging area)
git stash pop      # restore the previously unstaged content
git add -A         # now the previously unstaged content is staged
```

### Staging Operation Decisions

```
What do you want to do?
├── Stage an entire file → git add <file>
├── Stage all changes → git add -A
├── Stage specific lines of a file → git add -p <file>
├── Unstage → git reset HEAD <file>
└── Unstage but keep the changes → git restore --staged <file>
```

## Multiple Remotes

### Push to Multiple Remotes Simultaneously

```bash
# View current remotes
git remote -v

# Add multiple push URLs to the same remote
git remote set-url --add --push origin git@github.com:user/repo.git
git remote set-url --add --push origin git@gitlab.com:user/repo.git

# Verify the configuration
git remote -v
# origin should show two push URLs

# Push to both repositories with a single push
git push origin main
```

### Sync an Upstream Fork

```bash
# Add the upstream repository
git remote add upstream https://gitlab.example.com/original/repo.git

# Fetch upstream updates
git fetch upstream

# Merge into the local branch
git merge upstream/main

# Or rebase
git rebase upstream/main
```

## Commit Conventions

### Angular Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Rules for each part:**

| Part | Rule |
|------|------|
| `type` | **Required**; see the type table below |
| `scope` | Optional; the affected area (module or component name); see the Scope reference |
| `subject` | **Required**; brief description of the change; no more than 50 characters; first letter lowercase; no trailing period |
| `body` | Optional; detailed explanation of why the change was made and its impact |
| `footer` | Optional; Breaking Change marker or linked Issue (e.g. `Closes #123`). When a requirement ID is known, you MUST add `Ref: <requirement-ID>` (e.g. `Ref: VR260924-145`) for traceability |

**type values:**

| type | Meaning | Example |
|------|------|------|
| `feat` | New feature | `feat(biz-author): add article publish workflow` |
| `fix` | Bug fix | `fix(dal): resolve NPE when Redis timeout` |
| `refactor` | Refactoring (no new feature, no bug fix) | `refactor(core): extract ResultCode to enum` |
| `docs` | Documentation changes | `docs: update README for local setup` |
| `style` | Code formatting (no logic impact) | `style: apply uniform indentation` |
| `test` | Test cases | `test(biz-author): add unit tests for service` |
| `chore` | Build/tooling/dependency changes | `chore: upgrade mybatis-plus to 3.5.9` |
| `perf` | Performance optimization | `perf(redis): use pipeline for batch queries` |
| `ci` | CI/CD configuration changes | `ci: add PMD check to pipeline` |
| `build` | Build system | `build: update flatten-maven-plugin config` |
| `revert` | Revert a commit | `revert: revert feat(biz-author): add publish` |

**Scope value rules:**

> The scope must correspond to a **locatable physical or logical partition** of the codebase
> (directory, package, module, layer), with consistent granularity within the same project.

| Pattern | Applicable scenario | Examples |
|------|---------|------|
| Directory/package name | Monolith or monorepo sub-package | `auth`, `payment`, `dal-redis` |
| Architecture layer | Projects with clear layering | `api`, `service`, `repo`, `config` |
| Submodule name | Maven/Gradle multi-module projects | `biz-chat`, `biz-review`, `ocp-bom` |

- Use **nouns**, not verbs (`auth` rather than `login`)
- Seeing the scope should let you locate the corresponding directory or module directly
- Keep granularity uniform within the same project; do not mix module-level and feature-level scopes

**Good examples:**

```
feat(biz-author): add article publish workflow

Implement the article publishing feature, including state machine transitions and notifications.
- Add the ArticlePublishService domain service
- Add the ARTICLE_PUBLISH ResultCode

Ref: VR-123

fix(dal): resolve connection leak in HBase pool

chore: upgrade redis to 4.0.12 in bom
```

**Bad examples:**

```
# ❌ no type prefix
update article service

# ❌ subject capitalized
feat(Biz-Author): Add article publish workflow

# ❌ subject too long and ends with a period
feat(biz-author): implement the article publish workflow feature with state machine and notification.

# ❌ one commit contains multiple unrelated changes
feat: add article publish and fix redis timeout and update readme
```

### Commit Discipline

- **MUST** include exactly one logical change per commit (single responsibility)
- **MUST NOT** commit code that fails to compile or whose tests do not pass
- **MUST NOT** commit files containing sensitive information (keys, passwords, tokens)
- **MUST** ensure all CI pipelines pass before merging an MR

### Commit Rules for Agents

- Confirm the user has explicitly requested a commit before committing (do not commit automatically)
- The commit message must describe "why the change was made", not "what was changed"
- Do not `git add .` unrelated files together; stage files precisely
- Do not include `.env`, credential files, `node_modules`, etc. in commits

## .gitignore

### Common Templates

```bash
# List ignored files
git ls-files --others --ignored --exclude-standard

# Check why a file is ignored
git check-ignore -v <file>
```

```gitignore
# Build artifacts
*.class
*.jar
*.war
target/
build/
dist/

# IDE
.idea/
.vscode/
*.iml
*.swp

# Dependencies
node_modules/
vendor/

# Logs
*.log
logs/

# OS files
.DS_Store
Thumbs.db

# Environment config (contains sensitive information)
.env
.env.local
*.pem
*.key
```

### Rule Notes

```
*.log          # ignore all .log files
/build/        # ignore all directories named build
/dist/         # ignore the dist directory at the root
!important.log # do not ignore this file (negation)
*.tmp          # ignore all .tmp files
```

**Already-tracked files are not ignored by .gitignore**. To stop tracking them:

```bash
git rm -r --cached .
git add .
git commit -m "chore: reapply .gitignore rules"
```

## .gitattributes

Resolves cross-platform LF/CRLF line-ending differences.

```gitattributes
# Default: auto-detect text files; use LF in the working tree
* text=auto eol=lf

# Explicitly mark text files
*.java text
*.js text
*.ts text
*.py text
*.md text
*.xml text
*.yml text
*.json text

# Shell scripts forced to LF
*.sh text eol=lf

# Windows batch files forced to CRLF
*.bat text eol=crlf

# Binary files: no conversion
*.jar binary
*.png binary
*.jpg binary
*.pdf binary
*.zip binary
```

## Git Hooks

### Common Client-Side Hooks

| Hook | Trigger timing | Typical use |
|------|---------|---------|
| `pre-commit` | Before `git commit` runs | lint checks, format validation, tests |
| `prepare-commit-msg` | Before the editor opens | Auto-inject template information |
| `commit-msg` | After the commit message is confirmed | Validate commit message format |
| `post-commit` | After the commit completes | Notifications, logging |
| `pre-push` | Before `git push` runs | Run tests, validate branch protection |

### Configuration Methods

```bash
# Method 1: edit .git/hooks/ directly
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Method 2: use husky (recommended for JS projects)
npm i -D husky
npx husky init
# Edit .husky/pre-commit:
# npm test

# Method 3: specify a hooks directory
git config core.hooksPath .githooks/
```

### Agents and Hooks

- Hooks fire normally when the Agent runs `git commit`
- If a hook causes the commit to fail, analyze the cause, fix it, and retry
- **Do not** skip hooks with `--no-verify` unless the user explicitly asks
- Hooks usually do not run in CI environments (CI has its own check steps)

## Tag

### Command Templates

```bash
# Lightweight tag
git tag v1.0.0

# Annotated tag (recommended)
git tag -a v1.0.0 -m "Release 1.0.0"

# Tag a historical commit
git tag -a v0.9.0 abc123 -m "Release 0.9.0"

# Push tags
git push origin v1.0.0
git push origin --tags

# List tags
git tag -l "v1.*"
```

## General Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| detached HEAD | Checked out a commit instead of a branch | `git switch <branch>` to return to a branch |
| merge conflict | Both sides changed the same spot | Edit manually → `git add` → `git commit`/`rebase --continue` |
| rebase conflict | History conflicts during rebase | Edit manually → `git add` → `git rebase --continue`; abort with `git rebase --abort` |
| fatal: not a git repository | Not in a repository directory | `cd` to the repository root |
| permission denied (publickey) | SSH key not configured | Test with `ssh -T git@host`; check `~/.ssh/` |
| fatal: refusing to merge unrelated histories | The two repositories share no common ancestor | `git merge --allow-unrelated-histories` (use with caution) |
| Accidentally deleted a branch / misused reset | Performed a destructive operation | Find the SHA via `git reflog` → `git reset --hard <sha>` |
| push rejected (non-fast-forward) | The remote has new commits | Retry after `git pull --rebase` |
| push rejected after amend | rebase/amend rewrote an already-pushed SHA | Create a new commit instead of modifying pushed ones; avoid amending pushed commits on shared branches |
| LF/CRLF differences | Inconsistent line endings across platforms | Configure `.gitattributes`; `git config core.autocrlf` |
