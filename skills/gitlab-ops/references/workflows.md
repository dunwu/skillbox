# End-to-End Workflows

## Branch Management Strategies

> **This Skill supports three strategies; there is no "globally unified" strategy.** Which strategy
> each repository follows is registered per-repo in `config/settings.yaml`. The Agent **must** resolve
> it via `scripts/branch_strategy.py get`, and must not infer "the project uniformly adopts X" from
> any section of this document. For unregistered repositories the script returns `UNSET` (exit code 3);
> in that case you **MUST** go through conversational confirmation and then write it in with `set`;
> **do not guess**.

**Strategy quick reference (selection criteria and branch flow at a glance):**

| Strategy ID     | Integration branch | feature branches from | feature merges into                | Release source                        | Selection criteria                                         |
| --------------- | ------------------ | --------------------- | ---------------------------------- | ------------------------------------- | --------------------------------------------------------- |
| `git-flow`      | `develop`          | `develop`             | `develop`                          | `release/*` → `main`                  | Long version iterations, needs a pre-release stabilization period |
| `assembly-flow` | None               | `master`              | `release/<four-part version>` (assembly) | `release/<four-part version>` → `master` | Multiple requirements shipped in one version, may need to drop a single feature and rebuild the release |
| `github-flow`   | None (single trunk) | `master`             | `master` (direct MR)               | `master`                              | Continuous delivery, no pre-release branch                |

### git-flow (for projects with long version iterations)

```
Timeline →

main       ──●──────────────────────●──────────●── (tag v1.0) ──●── (tag v1.1)
            / \                    / \        / \              /
develop  ──●───●──●──●──●──●──●──●───●──●──●───●──●──●──●──●───
            \         /    \           /
feature/A  ──●──●──●─/      \         /
                          \         /
feature/B                  ●──●──●──/

hotfix ──────────────────────────●──/
                                 (based on main; after the fix, merge into main + develop)
```

**Core branches:**

| Branch      | Lifecycle | Purpose                                                        |
| ----------- | --------- | -------------------------------------------------------------- |
| `main`      | Permanent | Production code; accepts merges only; tag on every release     |
| `develop`   | Permanent | Integration branch for the next version                        |
| `feature/*` | Temporary | Created from develop; merged back into develop when done       |
| `release/*` | Temporary | Created from develop; after testing/fixing, merged into main + develop |
| `hotfix/*`  | Temporary | Created from main; after the fix, merged into main + develop   |

**Branch flow rules:**

- **MUST NOT** commit directly on `main` (`main` only accepts merges from release and hotfix)
- **MUST NOT** develop features directly on `develop` (create feature branches from `develop`)
- feature branches **MUST** be created from the latest `develop` and merged back into `develop` when done
- release branches **MUST** be created from `develop`; after tests pass, merge back into `main` (with a tag) and `develop`
- hotfix branches **MUST** be created from `main`; after the fix, merge back into `main` (with a tag) and `develop`
- After merging a feature / release / hotfix, its remote branch **MUST** be deleted

**Naming examples:**

```
feature/JIRA-1234-article-publish
feature/JIRA-5678-author-crud
release/1.5.0
hotfix/JIRA-9999-fix-null-pointer
```

**Git Flow workflow:**

```bash
# 1. Develop a new feature
git checkout -b feature/auth develop
# ... develop ...
git checkout develop
git merge --no-ff feature/auth
git branch -d feature/auth
git push origin --delete feature/auth    # delete the remote branch

# 2. Prepare a release
git checkout -b release/1.0 develop
# ... fix pre-release bugs ...
git checkout main
git merge --no-ff release/1.0
git tag -a v1.0
git checkout develop
git merge --no-ff release/1.0
git branch -d release/1.0
git push origin --delete release/1.0    # delete the remote branch

# 3. Emergency fix
git checkout -b hotfix/1.0.1 main
# ... fix ...
git checkout main
git merge --no-ff hotfix/1.0.1
git tag -a v1.0.1
git checkout develop
git merge --no-ff hotfix/1.0.1
git branch -d hotfix/1.0.1
git push origin --delete hotfix/1.0.1   # delete the remote branch
```

**Selection criteria**: choose `git-flow` when you need `develop` as a long-lived integration branch
spanning versions and want an independent stabilization period before release. If the team needs both
"multiple requirements assembled in parallel into the same version" and "the ability to drop a single
feature and re-release", choose `assembly-flow` instead of `git-flow`.

### github-flow (single trunk)

There is only one long-lived branch; every change goes back to the trunk via MR, and the trunk is
releasable at any time.

```
Timeline →

master  ──●───●─────●───●───●────●── (every merge is releasable; tags are applied afterwards)
           \  ╱    ╲ ╱   ╲ ╱
  feature   ●─●      ●─●     ●─●     ← branched from master; deleted after MR back into master
```

**Core branches:**

| Branch                | Lifecycle | Purpose                                                |
| --------------------- | --------- | ------------------------------------------------------ |
| `master` (or `main`)  | Permanent | The only branch; both integration branch and release source |
| `feature/*` / `fix/*` | Temporary | Branched from the trunk, MR back to the trunk, deleted on merge |

**Branch flow rules:**

- **MUST NOT** create `develop` or `release/*` — there is no integration branch and no pre-release branch
- feature **MUST** be branched from the latest commit on the trunk and merged back into the trunk via MR
- The trunk **MUST** always remain releasable; tagging a release does not depend on a dedicated branch
- After merging, the source branch **MUST** be deleted
- When a release stabilization period is needed, **do not** use this strategy; use `git-flow` or `assembly-flow` instead

**Workflow:**

```bash
git checkout -b feature/short-desc origin/master
# ... develop, commit ...
git push -u origin feature/short-desc
glab mr create --fill --target-branch master --no-editor
glab mr merge <iid> --squash --remove-source-branch
```

**Selection criteria**: choose it when changes are delivered continuously in small steps and there is
no need to assemble requirements per version. Documentation sites, tooling repos, and non-business
code repos are typically a good fit.

### assembly-flow (assembly-style release)

Features do not flow into a long-lived integration branch; instead they are **assembled directly into
the target version branch**; merging the version branch into `master` is the release. There is no
`develop`.

```
Timeline →

master            ──●─────────────────────────●────────●── (every release merge is a release)
                     \                       ╱        ╱
feature/A             ●──●──●──●─────────────╱      ╱     ← branched from master, assembled into release
                         \                ╱      ╱
feature/B                 ●──●──●──●─────╱      ╱      ← another feature of the same version
                                          ╱      ╱
release/13.7.0.2  ──●──●──●──●──●───────╱      ╱       ← assembly container = full master + features participating in this version
                                              ╱
                             release/13.7.0.2′ (rebuilt after dropping a feature)
```

**Core branches:**

| Branch                     | Lifecycle | Purpose                                                                |
| -------------------------- | --------- | ---------------------------------------------------------------------- |
| `master`                   | Permanent | The only long-lived branch; release baseline and the source from which features are branched |
| `feature/*`                | Temporary | Created from `master`; assembled into the `release/*` of its version   |
| `release/<four-part version>` | Temporary | Assembled from the features participating in that version; merged into `master` to release |

**Branch flow rules:**

- **MUST NOT** create or use `develop` — this strategy has no integration branch; introducing `develop` would create two parallel release chains
- feature branches **MUST** be created from `master`; to sync with the trunk, use `git merge origin/master` into the feature, never the reverse
- feature **MUST NOT** MR directly to `master`; it only MRs to its own `release/<four-part version>`
- `release/*` **MUST** only accept features confirmed to participate in that version; at release time, `release` is merged into `master`
- **The way to drop a feature is to rebuild the release**: cut `release/<four-part version>` again from `master`, then re-assemble the retained features one by one. **MUST NOT** use `revert` or `reset` to strip a feature out of an assembled release — the assembly merge commits already produced would remain in history, and the release would no longer be equivalent to "master + retained features"
- A feature belongs to exactly one `release`; cross-version requirements are split into separate features and assembled separately
- After `release` is merged into `master`, that `release` branch and all its feature branches **MUST** be deleted

#### Naming convention (consistent with server-side Push Rules regex)

```bash
feature/<requirement-ID>--<description>      # double-dash separator, e.g. feature/VR261027-342--knowledge-gen
release/<four-part pure number>               # e.g. release/13.7.0.2
```

> **Version format rule (constrains `assembly-flow` only)**: the `release` branch name is always a
> **four-part pure number** (`X.Y.Z.W`, e.g. `13.7.0.2`). The `-SNAPSHOT` / `-RELEASE` suffixes only
> appear in dependency versions in the pom and **never in branch names**. `git-flow`'s `release/*`
> follows the project's own versioning scheme and is not constrained by this rule.

For how this pairs with server-side Push Rules, see gitlab-server-config.md §Branch naming regex
(used with git flow). If that Push Rule is enabled, `fix/*` does not satisfy the double-dash
requirement (in the regex, `fix/.+` is a separate alternative), so under `assembly-flow` defect-fix
branches for requirement-level fixes are carried by `feature/<requirement-ID>--<description>`; only
independent minor fixes use `fix/<description>`.

**Workflow:**

```bash
# 1. Branch a feature from master (name contains requirement ID and double dash)
git checkout -b feature/VR1234-1--short-desc origin/master

# 2. Develop and commit; sync from trunk only by merging into the feature
git fetch origin && git merge origin/master

# 3. After push, open an MR to the owning release (target is not master)
git push -u origin feature/VR1234-1--short-desc
glab mr create --source-branch feature/VR1234-1--short-desc \
  --target-branch release/13.7.0.2 --no-editor

# 4. Release: release → master, tag, clean up temporary branches
glab mr create --source-branch release/13.7.0.2 --target-branch master --no-editor
git tag -a v13.7.0.2 -m "Release 13.7.0.2" && git push origin v13.7.0.2
git push origin --delete release/13.7.0.2

# 5. Drop an already-assembled feature → rebuild the release (do not revert)
git push origin --delete release/13.7.0.2
git checkout -b release/13.7.0.2 origin/master && git push -u origin release/13.7.0.2
# Re-assemble the retained features (one MR each)
```

**Selection criteria**: choose it when one version carries multiple parallel requirements and a
requirement may need to be pulled out and re-released before the release window. The cost is that MRs
must be reopened after a `release` rebuild, and the assembly relationship is expressed by branch
names rather than by history.

## Agent Procedure for Resolving the Branch Strategy

> For any judgment involving branch creation, MR target branch, push target, or release operations,
> you **MUST** resolve the strategy before acting. Until resolution succeeds, you **MUST NOT** guess
> the target branch, nor **MUST** you infer "the project uniformly adopts X" from the wording of any
> section of this document.

```bash
# Resolve inside the target repository (project path is normalized automatically from the origin remote)
python scripts/branch_strategy.py get
```

| Exit code | stdout                                                              | Agent action                                                                                                                                                                                                                     |
| --------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`       | Strategy ID (`git-flow` / `github-flow` / `assembly-flow`)          | Execute according to the flow rules of that strategy's section                                                                                                                                                                   |
| `0`       | `none`                                                              | No strategy applies to this project: control branches entirely per the user's stated intent for the current operation; do not apply any model                                                                                     |
| `3`       | `UNSET`                                                             | **Stop** and go through conversational confirmation: list the three strategies with their criteria → user picks one → write the registration with `set <strategy> --project <path> --reason '<reason>'`; if the user says none of the three applies → `set none`. You **MUST** write back the registration; do not merely answer the current question |
| `2`       | —                                                                   | Parameter/config/git environment problem; fix per the error message and retry; **do not** degrade to guessing                                                                                                                    |

Registration data lives in `config/settings.yaml` (committed and shared; credentials are forbidden);
the key is the normalized project path `group/[subgroup/]project`; **MUST NOT** use `gitlab_url` as
the key. The selection rationale **MUST** be written into the entry's `reason` field, not as an
inline comment (YAML dump would lose comments).

### No strategy applies: register `none`

Which branch strategy to use is **determined solely by the registration in `config/settings.yaml`** —
there is no other basis: not which branches exist in the repository directory, not the examples in
workflows.md, and not self-classification by repo nature.

- Project **already registered** (including `none`) → follow the registration
- Project **not registered** (`get` returns `UNSET`) → you **MUST** proactively ask the user which
  strategy to adopt and write the user's choice back into the registration (`set <strategy>
  --reason '<reason>'`). Do not end after merely answering the current question, leaving the project unregistered
- The user explicitly states that **none of the three strategies applies** → `set none`, meaning
  "no branch strategy applies to this project": branch creation, MR target, and push target are
  executed **entirely per the user's stated intent for the current operation**; the Agent **MUST NOT**
  apply any strategy model on its own (do not proactively suggest creating a feature branch, do not
  set the MR target yourself, do not treat "the trunk must not be committed to directly" as a default premise)

```bash
# Register as "no strategy applies"
python scripts/branch_strategy.py set none --project <group/proj> --reason '<why it does not apply>'
```

`none` and `UNSET` are two different states and must not be conflated:

| State                                                              | Meaning                          | Agent action                                                  |
| ------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------------- |
| `none` (registered; `get` outputs `none`, exit code 0)             | Confirmed: no strategy applies   | Execute per the user's stated intent; do not ask about strategy again |
| `UNSET` (`get` outputs `UNSET`, exit code 3)                       | Never decided                    | **Must** ask and register; guessing is forbidden              |

> `none` can only be a **project-level** registration value. The semantics of `set none --default`
> is "clear the fallback", returning unregistered projects to `UNSET` and requiring the question
> again — it is not "all unregistered projects default to no strategy". This rule must not be
> rewritten: otherwise a missing configuration would silently degrade into an unconstrained state.

## Workflow 1: Feature Branch Development

> `<BASE>` and `<TARGET>` are not fixed values; they are determined by the strategy resolved via
> `scripts/branch_strategy.py get`:
>
> | Strategy        | `<BASE>` (branch from) | `<TARGET>` (MR target)      |
> | --------------- | ---------------------- | --------------------------- |
> | `git-flow`      | `develop`              | `develop`                   |
> | `assembly-flow` | `master`               | `release/<four-part version>` |
> | `github-flow`   | `master`               | `master`                    |

```
1. python scripts/branch_strategy.py get          # resolve the strategy; if UNSET (exit code 3), stop and guide confirmation
2. glab issue create --title "..." --label feature
3. git checkout -b <name per strategy> origin/<BASE>
4. <code, commit>
5. git push -u origin <feature branch>
6. glab mr create --fill --source-branch <feature branch> --target-branch <TARGET> \
     --no-editor --assignee @reviewer --label feature
7. <review, revise, push>
8. glab mr merge <iid> --remove-source-branch     # whether to --squash: see gitlab-mr.md §Merging an MR
9. glab issue close <iid> (automatic if the MR description already has Closes)
```

## Workflow 2: Hotfix

```
1. git checkout -b hotfix/critical-fix main
2. <fix, test>
3. git push -u origin hotfix/critical-fix
4. glab mr create --title "hotfix: ..." --label hotfix,urgent
5. <quick review>
6. glab mr merge <iid> --squash
7. glab release create v1.0.1 --ref main
```

> `hotfix` always branches from `main`/`master` and merges back into the trunk — identical across all
> three strategies; `git-flow` additionally requires syncing back to `develop`.

## Workflow 3: Code Review Automation

```
1. Get MR changes: glab mr diff <iid>
2. Analyze changed files
3. Add line-level comments: glab mr note create <iid> --file X --line Y -m "..."
4. Approve or request changes: /approve or /request_review @author
```

## Workflow 4: CI/CD Monitoring and Fixing

```
1. Check the pipeline: glab ci status
2. Locate the failed job: glab ci trace
3. Analyze the logs
4. Fix locally and push
5. Wait for the pipeline to rerun: glab ci status (confirm it turns green)
6. If it still fails: glab ci retry <pipeline-id>
```

## Workflow 5: Multi-Agent Parallel Development

```
Agent A: git checkout -b feature/auth origin/<BASE>
Agent B: git checkout -b feature/payment origin/<BASE>
Each develops → each opens an MR → reviewed and merged independently
Note: when multiple agents converge on the same <TARGET>, the one merging later must first sync
      the target branch before pushing (git merge origin/<TARGET> or rebase onto origin/<TARGET>)
```

## Workflow 6: Release Process

| Strategy        | Release path                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------------- |
| `git-flow`      | `feature` → `develop` → `release/X.Y.Z` (stabilization period) → `main` + tag → back-merge into `develop` |
| `assembly-flow` | `feature` → `release/<four-part version>` (assembly) → `master` + tag; dropping a requirement means rebuilding the release |
| `github-flow`   | `feature` → `master`; the trunk is releasable as-is, tags are applied afterwards                   |

```bash
# Common wrap-up: after merging into the trunk, tag and clean up temporary branches
git tag -a v1.0.0 -m "Release 1.0.0" && git push origin v1.0.0
glab release create v1.0.0 --ref v1.0.0 --notes-file NOTES.md
git push origin --delete release/1.0.0
```
