"""Tests for git-local.md — all local git commands."""

import os
import unittest
from conftest import run, TempRepo


class TestGitConfig(unittest.TestCase):
    def test_config_set_and_get(self):
        with TempRepo() as repo:
            run('git config user.email "a@b.com"', cwd=repo.dir)
            rc, out, _ = run('git config user.email', cwd=repo.dir, check=False)
            self.assertEqual(out, "a@b.com")

    def test_config_list(self):
        with TempRepo() as repo:
            rc, out, _ = run("git config --list", cwd=repo.dir, check=False)
            self.assertIn("user.email", out)


class TestGitClone(unittest.TestCase):
    def test_clone_local(self):
        with TempRepo() as src:
            src.commit("init")
            dest = src.dir + "-clone"
            rc, out, _ = run(f"git clone {src.dir} {dest}", check=False)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isdir(os.path.join(dest, ".git")))
            import shutil
            shutil.rmtree(dest, ignore_errors=True)


class TestGitDiff(unittest.TestCase):
    def test_diff_staged(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "new.txt")
            with open(filepath, "w") as f:
                f.write("hello\n")
            run("git add new.txt", cwd=repo.dir)
            rc, out, _ = run("git diff --cached", cwd=repo.dir, check=False)
            self.assertIn("+hello", out)

    def test_diff_stat(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "stat.txt")
            with open(filepath, "w") as f:
                f.write("data\n")
            run("git add stat.txt", cwd=repo.dir)
            run('git commit -m "add stat"', cwd=repo.dir)
            rc, out, _ = run("git diff --stat HEAD~1..HEAD", cwd=repo.dir, check=False)
            self.assertIn("stat.txt", out)

    def test_diff_unstaged(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "tracked.txt")
            with open(filepath, "w") as f:
                f.write("original\n")
            run("git add tracked.txt", cwd=repo.dir)
            run('git commit -m "add tracked"', cwd=repo.dir)
            with open(filepath, "w") as f:
                f.write("modified\n")
            rc, out, _ = run("git diff", cwd=repo.dir, check=False)
            self.assertIn("-original", out)
            self.assertIn("+modified", out)

    def test_diff_between_branches(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b feature", cwd=repo.dir)
            filepath = os.path.join(repo.dir, "feat.txt")
            with open(filepath, "w") as f:
                f.write("feature content\n")
            run("git add feat.txt", cwd=repo.dir)
            run('git commit -m "add feat"', cwd=repo.dir)
            run("git checkout master", cwd=repo.dir)
            rc, out, _ = run("git diff master..feature", cwd=repo.dir, check=False)
            self.assertIn("+feature content", out)


class TestGitLog(unittest.TestCase):
    def test_log_oneline(self):
        with TempRepo() as repo:
            repo.commit("first")
            repo.commit("second")
            rc, out, _ = run("git log --oneline", cwd=repo.dir, check=False)
            self.assertIn("second", out)
            self.assertIn("first", out)

    def test_log_graph(self):
        with TempRepo() as repo:
            repo.commit("init")
            rc, out, _ = run("git log --oneline --graph", cwd=repo.dir, check=False)
            self.assertIn("init", out)


class TestGitBranch(unittest.TestCase):
    def test_create_and_list(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git branch feature/x", cwd=repo.dir)
            rc, out, _ = run("git branch", cwd=repo.dir, check=False)
            self.assertIn("feature/x", out)

    def test_delete(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git branch tmp", cwd=repo.dir)
            run("git branch -d tmp", cwd=repo.dir)
            rc, out, _ = run("git branch", cwd=repo.dir, check=False)
            self.assertNotIn("tmp", out)

    def test_rename(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git branch old-name", cwd=repo.dir)
            run("git branch -m old-name new-name", cwd=repo.dir)
            rc, out, _ = run("git branch", cwd=repo.dir, check=False)
            self.assertIn("new-name", out)
            self.assertNotIn("old-name", out)

    def test_force_delete_unmerged(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b unmerged", cwd=repo.dir)
            repo.commit("divergent work")
            run("git checkout master", cwd=repo.dir)
            rc, _, err = run("git branch -d unmerged", cwd=repo.dir, check=False)
            self.assertNotEqual(rc, 0, "-d should fail on unmerged branch")
            run("git branch -D unmerged", cwd=repo.dir)
            rc, out, _ = run("git branch", cwd=repo.dir, check=False)
            self.assertNotIn("unmerged", out)


class TestGitMergeRebase(unittest.TestCase):
    def test_merge(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b feature", cwd=repo.dir)
            repo.commit("feature work")
            run("git checkout master", cwd=repo.dir)
            rc, out, _ = run("git merge feature", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0)

    def test_merge_no_ff(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b feature", cwd=repo.dir)
            repo.commit("feature work")
            run("git checkout master", cwd=repo.dir)
            rc, _, err = run('git merge --no-ff feature -m "merge no-ff"', cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"merge --no-ff failed: {err}")
            rc, out, _ = run("git log --oneline --graph", cwd=repo.dir, check=False)
            self.assertIn("merge no-ff", out)

    def test_merge_ff_only(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b feature", cwd=repo.dir)
            repo.commit("feature work")
            run("git checkout master", cwd=repo.dir)
            rc, _, err = run("git merge --ff-only feature", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"merge --ff-only failed: {err}")
            rc, out, _ = run("git log --oneline", cwd=repo.dir, check=False)
            self.assertIn("feature work", out)

    def test_rebase(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b feature", cwd=repo.dir)
            repo.commit("feature work")
            run("git checkout master", cwd=repo.dir)
            repo.commit("master work")
            run("git checkout feature", cwd=repo.dir)
            rc, out, _ = run("git rebase master", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0)

    def test_revert(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "revert-me.txt")
            with open(filepath, "w") as f:
                f.write("bad change\n")
            run("git add revert-me.txt", cwd=repo.dir)
            run('git commit -m "bad change"', cwd=repo.dir)
            rc, _, err = run("git revert HEAD --no-edit", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"revert failed: {err}")
            rc, out, _ = run("git log --oneline -1", cwd=repo.dir, check=False)
            self.assertIn("Revert", out)
            self.assertFalse(os.path.exists(filepath))


class TestGitCherryPick(unittest.TestCase):
    def test_cherry_pick(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b source", cwd=repo.dir)
            repo.commit("pick me")
            rc, sha, _ = run("git rev-parse HEAD", cwd=repo.dir, check=False)
            run("git checkout master", cwd=repo.dir)
            rc, out, err = run(f"git cherry-pick {sha}", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"cherry-pick failed: {err}")

    def test_cherry_pick_multiple(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b source", cwd=repo.dir)
            repo.commit("first pick")
            repo.commit("second pick")
            rc, sha2, _ = run("git rev-parse HEAD", cwd=repo.dir, check=False)
            rc, sha1, _ = run("git rev-parse HEAD~1", cwd=repo.dir, check=False)
            run("git checkout master", cwd=repo.dir)
            rc, _, err = run(f"git cherry-pick {sha1} {sha2}", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"cherry-pick multiple failed: {err}")
            rc, out, _ = run("git log --oneline", cwd=repo.dir, check=False)
            self.assertIn("first pick", out)
            self.assertIn("second pick", out)


class TestGitStash(unittest.TestCase):
    def test_stash_and_pop(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "stashed.txt")
            with open(filepath, "w") as f:
                f.write("stash me\n")
            run("git add stashed.txt", cwd=repo.dir)
            run('git commit -m "add stashed"', cwd=repo.dir)
            with open(filepath, "w") as f:
                f.write("modified\n")
            run("git stash", cwd=repo.dir)
            rc, out, _ = run("git stash list", cwd=repo.dir, check=False)
            self.assertIn("stash@{0}", out)
            run("git stash pop", cwd=repo.dir)
            with open(filepath) as f:
                self.assertEqual(f.read().strip(), "modified")

    def test_stash_with_message(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "msg.txt")
            with open(filepath, "w") as f:
                f.write("tracked\n")
            run("git add msg.txt", cwd=repo.dir)
            run('git commit -m "add msg"', cwd=repo.dir)
            with open(filepath, "w") as f:
                f.write("wip change\n")
            run('git stash push -m "my wip"', cwd=repo.dir)
            rc, out, _ = run("git stash list", cwd=repo.dir, check=False)
            self.assertIn("my wip", out)

    def test_stash_untracked(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "untracked.txt")
            with open(filepath, "w") as f:
                f.write("untracked content\n")
            run("git stash -u", cwd=repo.dir)
            self.assertFalse(os.path.exists(filepath))
            run("git stash pop", cwd=repo.dir)
            with open(filepath) as f:
                self.assertEqual(f.read().strip(), "untracked content")


class TestGitReflog(unittest.TestCase):
    def test_reflog_exists(self):
        with TempRepo() as repo:
            repo.commit("init")
            repo.commit("second")
            rc, out, _ = run("git reflog", cwd=repo.dir, check=False)
            self.assertIn("HEAD@{0}", out)

    def test_recover_deleted_branch(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git checkout -b doomed", cwd=repo.dir)
            repo.commit("important work")
            rc, sha, _ = run("git rev-parse HEAD", cwd=repo.dir, check=False)
            run("git checkout master", cwd=repo.dir)
            run("git branch -D doomed", cwd=repo.dir)
            rc, out, _ = run("git reflog", cwd=repo.dir, check=False)
            self.assertIn(sha[:7], out)
            rc, _, err = run(f"git branch recovered {sha}", cwd=repo.dir, check=False)
            self.assertEqual(rc, 0, f"recover failed: {err}")
            rc, out, _ = run("git branch", cwd=repo.dir, check=False)
            self.assertIn("recovered", out)


class TestGitTag(unittest.TestCase):
    def test_create_and_list(self):
        with TempRepo() as repo:
            repo.commit("init")
            run("git tag v1.0", cwd=repo.dir)
            rc, out, _ = run("git tag", cwd=repo.dir, check=False)
            self.assertIn("v1.0", out)

    def test_annotated_tag(self):
        with TempRepo() as repo:
            repo.commit("init")
            run('git tag -a v2.0 -m "release v2.0"', cwd=repo.dir)
            rc, out, _ = run("git tag -n", cwd=repo.dir, check=False)
            self.assertIn("v2.0", out)


class TestGitReset(unittest.TestCase):
    def test_soft_reset(self):
        with TempRepo() as repo:
            repo.commit("init")
            repo.commit("undo me")
            run("git reset --soft HEAD~1", cwd=repo.dir)
            rc, out, _ = run("git log --oneline", cwd=repo.dir, check=False)
            self.assertNotIn("undo me", out)
            rc, out, _ = run("git diff --cached --name-only", cwd=repo.dir, check=False)
            self.assertTrue(len(out) > 0)

    def test_hard_reset(self):
        with TempRepo() as repo:
            repo.commit("init")
            filepath = os.path.join(repo.dir, "discard.txt")
            with open(filepath, "w") as f:
                f.write("goodbye\n")
            run("git add discard.txt", cwd=repo.dir)
            run('git commit -m "add discard"', cwd=repo.dir)
            repo.commit("another commit")
            run("git reset --hard HEAD~2", cwd=repo.dir)
            rc, out, _ = run("git log --oneline", cwd=repo.dir, check=False)
            self.assertNotIn("add discard", out)
            self.assertNotIn("another commit", out)
            self.assertFalse(os.path.exists(filepath))


class TestGitIgnore(unittest.TestCase):
    def test_gitignore(self):
        with TempRepo() as repo:
            filepath = os.path.join(repo.dir, ".gitignore")
            with open(filepath, "w") as f:
                f.write("*.log\n")
            run("git add .gitignore", cwd=repo.dir)
            run('git commit -m "add gitignore"', cwd=repo.dir)
            logpath = os.path.join(repo.dir, "test.log")
            with open(logpath, "w") as f:
                f.write("log\n")
            run("git add -A", cwd=repo.dir)
            rc, out, _ = run("git status --short", cwd=repo.dir, check=False)
            self.assertNotIn("test.log", out)


class TestGitCommitConvention(unittest.TestCase):
    def test_conventional_commit(self):
        with TempRepo() as repo:
            repo.commit("feat(auth): add login")
            rc, out, _ = run("git log --oneline -1", cwd=repo.dir, check=False)
            self.assertIn("feat(auth): add login", out)


if __name__ == "__main__":
    unittest.main()
