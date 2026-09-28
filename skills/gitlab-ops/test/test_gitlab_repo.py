"""Tests for gitlab-repo.md — repo management commands and REST API alternatives."""

import unittest
from conftest import (
    run, run_ok, api_get, api_post, api_delete,
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT, PROJECT_PATH_ENCODED,
)


class TestRepoView(unittest.TestCase):
    def test_repo_view_help(self):
        rc, out = run_ok("glab repo view --help")
        self.assertTrue(rc)
        self.assertIn("view", out.lower())

    def test_repo_view_current(self):
        """glab repo view with positional repo arg shows project info."""
        rc, out = run_ok(f"glab repo view {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_repo_view_json_output(self):
        """glab repo view supports -F json for JSON output."""
        rc, out = run_ok(f"glab repo view {GITLAB_PROJECT} -F json")
        self.assertTrue(rc)


class TestRepoBrowse(unittest.TestCase):
    def test_repo_browse_not_exist(self):
        """glab repo browse does NOT exist — use 'glab repo view' or web URL."""
        rc, out = run_ok("glab repo browse --help")
        self.assertTrue(rc)
        commands_section = out.split("COMMANDS")[1] if "COMMANDS" in out else ""
        self.assertNotIn("browse", commands_section,
                         "browse should not be listed as a repo subcommand")


class TestRepoFork(unittest.TestCase):
    def test_repo_fork_help(self):
        rc, out = run_ok("glab repo fork --help")
        self.assertTrue(rc)
        for flag in ["--clone", "--remote"]:
            self.assertIn(flag, out, f"Flag {flag} not found in glab repo fork --help")

    def test_repo_fork_no_namespace_flag(self):
        """--namespace is NOT a valid flag for glab repo fork."""
        rc, out = run_ok("glab repo fork --help")
        self.assertNotIn("--namespace", out,
                         "--namespace should not exist; use positional arg instead")


class TestRepoArchive(unittest.TestCase):
    def test_repo_archive_help(self):
        rc, out = run_ok("glab repo archive --help")
        self.assertTrue(rc)


class TestRepoTransfer(unittest.TestCase):
    def test_repo_transfer_help(self):
        rc, out = run_ok("glab repo transfer --help")
        self.assertTrue(rc)
        self.assertIn("--target-namespace", out)


class TestBranchRESTAPI(unittest.TestCase):
    """glab has no branch subcommand — verify REST API alternatives."""

    BRANCH_CREATE = "test-branch-repo-md"
    BRANCH_DELETE = "test-branch-del-repo-md"

    def setUp(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH_CREATE}")
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH_DELETE}")

    def tearDown(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH_CREATE}")
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH_DELETE}")

    def test_list_branches_api(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_create_branch_api(self):
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches",
            {"branch": self.BRANCH_CREATE, "ref": "master"},
        )
        self.assertIn(status, [200, 201], f"Create branch failed: {data}")
        self.assertEqual(data["name"], self.BRANCH_CREATE)

    def test_delete_branch_api(self):
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches",
            {"branch": self.BRANCH_DELETE, "ref": "master"},
        )
        self.assertIn(status, [200, 201], f"Create branch failed: {data}")
        status, _ = api_delete(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH_DELETE}"
        )
        self.assertIn(status, [200, 204])


class TestGlabBranchNotExists(unittest.TestCase):
    """Verify that glab branch subcommand does NOT exist."""

    def test_glab_branch_not_found(self):
        rc, out = run_ok("glab branch --help")
        self.assertFalse(rc, "glab branch should not exist as a subcommand")


if __name__ == "__main__":
    unittest.main()
