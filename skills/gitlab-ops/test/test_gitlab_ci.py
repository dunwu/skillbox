"""Tests for gitlab-ci.md — CI/CD pipeline commands."""

import unittest
from conftest import run, run_ok, GITLAB_PROJECT


class TestCIStatus(unittest.TestCase):
    def test_ci_status_help(self):
        rc, out = run_ok("glab ci status --help")
        self.assertTrue(rc)


class TestCIView(unittest.TestCase):
    def test_ci_view_help(self):
        rc, out = run_ok("glab ci view --help")
        self.assertTrue(rc)


class TestCIGet(unittest.TestCase):
    def test_ci_get_help(self):
        rc, out = run_ok("glab ci get --help")
        self.assertTrue(rc)


class TestCIList(unittest.TestCase):
    def test_ci_list(self):
        rc, out = run_ok(f"glab ci list -R {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_ci_list_json(self):
        rc, out = run_ok(f"glab ci list -R {GITLAB_PROJECT} -F json")
        self.assertTrue(rc)

    def test_ci_list_ref(self):
        rc, out = run_ok(f"glab ci list -R {GITLAB_PROJECT} --ref master")
        self.assertTrue(rc)

    def test_ci_list_scope(self):
        """--scope is the correct flag (not --state)."""
        rc, out = run_ok(f"glab ci list -R {GITLAB_PROJECT} --scope finished")
        self.assertTrue(rc)

    def test_ci_list_state_invalid(self):
        """--state is NOT a valid flag for glab ci list."""
        rc, out = run_ok(f"glab ci list -R {GITLAB_PROJECT} --state failed")
        self.assertFalse(rc, "--state should not be a valid flag for ci list")


class TestCITrace(unittest.TestCase):
    def test_ci_trace_help(self):
        rc, out = run_ok("glab ci trace --help")
        self.assertTrue(rc)


class TestCIRetry(unittest.TestCase):
    def test_ci_retry_help(self):
        rc, out = run_ok("glab ci retry --help")
        self.assertTrue(rc)


class TestCICancel(unittest.TestCase):
    def test_ci_cancel_help(self):
        rc, out = run_ok("glab ci cancel --help")
        self.assertTrue(rc)


class TestCITrigger(unittest.TestCase):
    def test_ci_trigger_help(self):
        rc, out = run_ok("glab ci trigger --help")
        self.assertTrue(rc)
        self.assertIn("--branch", out)


class TestCIDelete(unittest.TestCase):
    def test_ci_delete_help(self):
        rc, out = run_ok("glab ci delete --help")
        self.assertTrue(rc)


class TestJobView(unittest.TestCase):
    def test_job_view_not_exist(self):
        """glab job view is NOT a real subcommand — glab silently shows parent help."""
        rc, out = run_ok("glab job view --help")
        self.assertTrue(rc)
        self.assertNotIn("view", out.split("COMMANDS")[1] if "COMMANDS" in out else "",
                         "view should not be listed as a job subcommand")

    def test_job_subcommands(self):
        rc, out = run_ok("glab job --help")
        self.assertTrue(rc)
        self.assertIn("artifact", out)
        commands_section = out.split("COMMANDS")[1] if "COMMANDS" in out else out
        self.assertNotIn("view", commands_section)


class TestSchedule(unittest.TestCase):
    def test_schedule_list(self):
        rc, out = run_ok(f"glab schedule list -R {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_schedule_create_help(self):
        rc, out = run_ok("glab schedule create --help")
        self.assertTrue(rc)
        for flag in ["--cron", "--description", "--ref", "--variable"]:
            self.assertIn(flag, out)

    def test_schedule_create_no_cron_syntax(self):
        """--cron-syntax is NOT a valid flag."""
        rc, out = run_ok("glab schedule create --help")
        self.assertNotIn("cron-syntax", out)


if __name__ == "__main__":
    unittest.main()
