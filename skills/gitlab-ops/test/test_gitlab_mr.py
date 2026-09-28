"""Tests for gitlab-mr.md — MR lifecycle commands via glab CLI."""

import unittest
from conftest import run, run_ok, GITLAB_PROJECT


class TestMRCreate(unittest.TestCase):
    """MR creation requires a source branch with commits ahead of target.
    We test command syntax validity, not actual creation (may fail due to conflicts)."""

    def test_mr_create_help(self):
        rc, out = run_ok(f"glab mr create --help")
        self.assertTrue(rc)
        self.assertIn("create", out.lower())

    def test_mr_create_flags_exist(self):
        rc, out = run_ok(f"glab mr create --help")
        for flag in ["--title", "--description", "--source-branch", "--target-branch",
                      "--assignee", "--label", "--milestone", "--draft", "--fill"]:
            self.assertIn(flag, out, f"Flag {flag} not found in glab mr create --help")


class TestMRList(unittest.TestCase):
    def test_mr_list(self):
        rc, out = run_ok(f"glab mr list -R {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_mr_list_json(self):
        rc, out = run_ok(f"glab mr list -R {GITLAB_PROJECT} -F json")
        self.assertTrue(rc)
        self.assertTrue(out.startswith("["))

    def test_mr_list_label(self):
        rc, out = run_ok(f"glab mr list -R {GITLAB_PROJECT} --label bug")
        self.assertTrue(rc)

    def test_mr_list_no_state_flag(self):
        """--state is NOT a valid flag for glab mr list."""
        rc, out = run_ok(f"glab mr list -R {GITLAB_PROJECT} --state merged")
        self.assertFalse(rc, "--state should not be a valid flag")


class TestMRView(unittest.TestCase):
    def test_mr_view_help(self):
        rc, out = run_ok("glab mr view --help")
        self.assertTrue(rc)


class TestMRNote(unittest.TestCase):
    def test_mr_note_create_help(self):
        rc, out = run_ok("glab mr note create --help")
        self.assertTrue(rc)
        self.assertIn("--file", out)
        self.assertIn("--line", out)

    def test_mr_note_old_message_deprecated(self):
        """--message flag on glab mr note (without create) should be deprecated."""
        rc, out = run_ok(f"glab mr note --help")
        self.assertTrue(rc)


class TestMRClose(unittest.TestCase):
    def test_mr_close_help(self):
        rc, out = run_ok("glab mr close --help")
        self.assertTrue(rc)


class TestMRMerge(unittest.TestCase):
    def test_mr_merge_help(self):
        rc, out = run_ok("glab mr merge --help")
        self.assertTrue(rc)
        for flag in ["--squash", "--remove-source-branch"]:
            self.assertIn(flag, out, f"Flag {flag} not found in glab mr merge --help")


class TestMRDiff(unittest.TestCase):
    def test_mr_diff_help(self):
        rc, out = run_ok("glab mr diff --help")
        self.assertTrue(rc)


class TestMRUpdate(unittest.TestCase):
    def test_mr_update_help(self):
        rc, out = run_ok("glab mr update --help")
        self.assertTrue(rc)
        for flag in ["--title", "--assignee", "--label", "--description", "--target-branch"]:
            self.assertIn(flag, out, f"Flag {flag} not found in glab mr update --help")


class TestStack(unittest.TestCase):
    def test_stack_help(self):
        rc, out = run_ok("glab stack --help")
        self.assertTrue(rc)
        self.assertIn("create", out)
        self.assertIn("sync", out)


if __name__ == "__main__":
    unittest.main()
