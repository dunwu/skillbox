# General Troubleshooting

## Identity and Authentication

| Symptom | Troubleshooting Steps |
|------|---------|
| 401 on all operations | `glab auth status` → Token expired → log in again |
| SSH 403 | `ssh -T git@host` → check `~/.ssh/config` → confirm the key is registered |
| Operation shows the wrong user | `glab auth status` → `auth switch` or log in again |
| 403 in CI | Check the `$CI_JOB_TOKEN` scope → use a PAT instead |

## Git Operations

| Symptom | Troubleshooting Steps |
|------|---------|
| merge conflict | `git status` to see conflicted files → resolve manually → `git add` → commit / rebase --continue |
| detached HEAD | `git branch` to see current state → `git switch <branch>` to go back |
| push rejected after rebase | Protected branches do not allow history rewrites → use merge instead of force push |
| "refusing to merge unrelated histories" | Confirm the merge is really needed → `--allow-unrelated-histories` |
| large pack failed | Repository too large → `git clone --depth=1` or `--filter=blob:none` |
| Accidentally deleted a branch | `git reflog` to find the SHA → `git checkout -b <name> <sha>` |
| Accidental reset --hard | `git reflog` to find the SHA before the reset → `git reset --hard <sha>` |
| Messed up a rebase/merge | `git reset --hard ORIG_HEAD` to return to the pre-operation state |
| Pulled the wrong branch / merged incorrectly | `git reflog` to find the HEAD before the operation → `git reset --hard <sha>` |
| Lost content after amend | `git reflog` to find the SHA before the amend → `git reset --hard <sha>` |

## glab CLI

| Symptom | Troubleshooting Steps |
|------|---------|
| command not found | Install: refer to the official glab installation docs |
| "project not found" | Check the `-R group/project` format → confirm access permission |
| JSON parse failure | Check whether `--output json` is supported → verify with `jq` |
| Operation timed out | Network issue → check proxy settings → retry |

## Disaster Recovery Manual

### Scenario 1: Accidentally Deleted a Branch

```bash
# 1. Check the reflog to find the commit before deletion
git reflog
# Example output:
# 4e3cd85 HEAD@{1}: commit: add login feature
# 69204cd HEAD@{2}: checkout: moving from my-branch to main

# 2. Restore the branch from the SHA
git checkout -b my-branch 4e3cd85

# 3. Verify the restored content
git log --oneline -5
```

### Scenario 2: Accidentally Ran reset --hard

```bash
# 1. Find the state before the reset in the reflog
git reflog
# a1b2c3d HEAD@{0}: reset: moving to HEAD~3
# e4f5g6h HEAD@{1}: commit: third commit
# i7j8k9l HEAD@{2}: commit: second commit
# m0n1o2p HEAD@{3}: commit: first commit

# 2. Restore to the state before the reset
git reset --hard e4f5g6h
```

### Scenario 3: Failed rebase/merge

```bash
# Method 1: use ORIG_HEAD (saved automatically by Git)
git reset --hard ORIG_HEAD

# Method 2: use the reflog to find the HEAD before the operation
git reflog
git reset --hard <sha-before-operation>
```

### Scenario 4: Committed to the Wrong Branch

```bash
# 1. Create a new branch on the current branch (without switching)
git branch correct-branch

# 2. Roll back the current branch
git reset --hard HEAD~1

# 3. Switch to the correct branch
git checkout correct-branch
```

### Scenario 5: Cherry-Pick Commits Across Branches

```bash
# Pick a specific commit from another branch
git cherry-pick <commit-sha>

# If there are conflicts
# Resolve the conflicts → git add → git cherry-pick --continue
# Abort → git cherry-pick --abort
```

### Recovering a Deleted Tag

```bash
# 1. Find unreachable tag objects
git fsck --unreachable | grep tag

# 2. Restore with update-ref
git update-ref refs/tags/<tag-name> <hash>
```

### Key Principles

- **The reflog is the last safety net**; entries are kept for 90 days by default
- The reflog only records local HEAD movements, not file content changes
- `ORIG_HEAD` is set automatically before operations like merge, rebase, and pull
- Recover as early as possible; reflog entries may be cleaned up by GC over time
