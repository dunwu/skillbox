"""Tests for gitlab-issue.md — Issue management commands."""

import unittest
from conftest import run, run_ok, GITLAB_PROJECT


class TestIssueCreate(unittest.TestCase):
    def test_issue_create_help(self):
        rc, out = run_ok("glab issue create --help")
        self.assertTrue(rc)
        for flag in ["--title", "--description", "--label", "--assignee"]:
            self.assertIn(flag, out)


class TestIssueList(unittest.TestCase):
    def test_issue_list(self):
        rc, out = run_ok(f"glab issue list -R {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_issue_list_json(self):
        rc, out = run_ok(f"glab issue list -R {GITLAB_PROJECT} -O json")
        self.assertTrue(rc)
        self.assertTrue(out.startswith("["))


class TestIssueView(unittest.TestCase):
    def test_issue_view_help(self):
        rc, out = run_ok("glab issue view --help")
        self.assertTrue(rc)


class TestIssueUpdate(unittest.TestCase):
    def test_issue_update_help(self):
        rc, out = run_ok("glab issue update --help")
        self.assertTrue(rc)


class TestIssueClose(unittest.TestCase):
    def test_issue_close_help(self):
        rc, out = run_ok("glab issue close --help")
        self.assertTrue(rc)


class TestIssueNote(unittest.TestCase):
    def test_issue_note_help(self):
        rc, out = run_ok("glab issue note --help")
        self.assertTrue(rc)


class TestIssueDelete(unittest.TestCase):
    def test_issue_delete_help(self):
        rc, out = run_ok("glab issue delete --help")
        self.assertTrue(rc)


if __name__ == "__main__":
    unittest.main()
