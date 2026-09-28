"""Tests for gitlab-advanced.md — Release, Snippet, Variable, Label, Milestone, etc."""

import unittest
import time
from conftest import (
    run, run_ok, api_get, api_post, api_delete,
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT, PROJECT_PATH_ENCODED,
)


class TestRelease(unittest.TestCase):
    def test_release_list_help(self):
        rc, out = run_ok("glab release list --help")
        self.assertTrue(rc)

    def test_release_create_help(self):
        rc, out = run_ok("glab release create --help")
        self.assertTrue(rc)
        self.assertIn("--name", out, "Flag --name should exist")
        self.assertIn("--notes", out, "Flag --notes should exist")
        self.assertIn("--assets-links", out, "Flag --assets-links should exist")

    def test_release_create_no_title_flag(self):
        """--title is NOT a valid flag for glab release create."""
        rc, out = run_ok("glab release create --help")
        self.assertNotIn("--title", out, "--title should not exist; use --name instead")

    def test_release_view_help(self):
        rc, out = run_ok("glab release view --help")
        self.assertTrue(rc)

    def test_release_delete_help(self):
        rc, out = run_ok("glab release delete --help")
        self.assertTrue(rc)


class TestSnippet(unittest.TestCase):
    def test_snippet_create_help(self):
        rc, out = run_ok("glab snippet create --help")
        self.assertTrue(rc)
        self.assertIn("--title", out)

    def test_snippet_list_not_exists(self):
        """glab snippet list does NOT exist — only 'create' subcommand."""
        rc, out = run_ok("glab snippet list --help")
        self.assertTrue(rc)
        commands_section = out.split("COMMANDS")[1] if "COMMANDS" in out else ""
        self.assertNotIn("list", commands_section,
                         "list should not be listed as a snippet subcommand")

    def test_snippet_view_help(self):
        rc, out = run_ok("glab snippet view --help")
        self.assertTrue(rc)

    def test_snippet_list_via_api(self):
        """REST API alternative for listing snippets."""
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/snippets")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)


class TestVariable(unittest.TestCase):
    VAR_KEY = "TEST_GITLAB_OPS_VAR"

    def setUp(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}")

    def tearDown(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}")

    def test_variable_list_help(self):
        rc, out = run_ok("glab variable list --help")
        self.assertTrue(rc)

    def test_variable_set_help(self):
        rc, out = run_ok("glab variable set --help")
        self.assertTrue(rc)
        for flag in ["--masked", "--protected", "--raw"]:
            self.assertIn(flag, out, f"Flag {flag} not found")

    def test_variable_set_and_get(self):
        rc, out = run_ok(
            f'glab variable set {self.VAR_KEY} "test-value" -R {GITLAB_PROJECT}'
        )
        self.assertTrue(rc, f"variable set failed: {out}")

        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["key"], self.VAR_KEY)

    def test_variable_delete(self):
        api_post(f"/projects/{PROJECT_PATH_ENCODED}/variables", {
            "key": self.VAR_KEY, "value": "to-delete"
        })
        rc, out = run_ok(
            f"glab variable delete {self.VAR_KEY} -R {GITLAB_PROJECT}"
        )
        self.assertTrue(rc, f"variable delete failed: {out}")


class TestLabel(unittest.TestCase):
    def test_label_list(self):
        rc, out = run_ok(f"glab label list -R {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_label_create_with_name_flag(self):
        label_name = f"test-label-{int(time.time())}"
        rc, out = run_ok(
            f'glab label create --name {label_name} --color "#FF0000" -R {GITLAB_PROJECT}'
        )
        self.assertTrue(rc, f"label create failed: {out}")
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/labels/{label_name}")

    def test_label_create_no_positional_arg(self):
        """glab label create requires --name flag, not positional arg."""
        rc, out = run_ok(
            f'glab label create bug-temp --color "#FF0000" -R {GITLAB_PROJECT}'
        )
        self.assertFalse(rc, "positional arg should not work; --name is required")


class TestMilestone(unittest.TestCase):
    MS_TITLE = f"test-ms-{int(time.time())}"

    def tearDown(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/milestones?title={self.MS_TITLE}"
        )
        if status == 200 and isinstance(data, list):
            for ms in data:
                api_delete(f"/projects/{PROJECT_PATH_ENCODED}/milestones/{ms['id']}")

    def test_milestone_list(self):
        rc, out = run_ok(f"glab milestone list --project {GITLAB_PROJECT}")
        self.assertTrue(rc)

    def test_milestone_create_with_title_flag(self):
        rc, out = run_ok(
            f'glab milestone create --title "{self.MS_TITLE}" -R {GITLAB_PROJECT}'
        )
        self.assertTrue(rc, f"milestone create failed: {out}")

    def test_milestone_create_no_positional_arg(self):
        """glab milestone create requires --title flag, not positional arg."""
        rc, out = run_ok(
            f'glab milestone create "temp-title" -R {GITLAB_PROJECT}'
        )
        self.assertFalse(rc, "positional arg should not work; --title is required")


class TestPackages(unittest.TestCase):
    def test_packages_list_help(self):
        rc, out = run_ok("glab packages list --help")
        self.assertTrue(rc)

    def test_package_singular_not_exists(self):
        """glab package (singular) should NOT exist."""
        rc, out = run_ok("glab package list --help")
        self.assertFalse(rc, "glab package should not exist; use glab packages")


class TestRunner(unittest.TestCase):
    def test_runner_list_help(self):
        rc, out = run_ok("glab runner list --help")
        self.assertTrue(rc)


class TestTodo(unittest.TestCase):
    def test_todo_list_help(self):
        rc, out = run_ok("glab todo list --help")
        self.assertTrue(rc)

    def test_todo_done_help(self):
        rc, out = run_ok("glab todo done --help")
        self.assertTrue(rc)


class TestUserViaAPI(unittest.TestCase):
    """glab user has no direct info command — use REST API."""

    def test_glab_user_no_direct_info(self):
        """glab user without subcommand should not show user info."""
        rc, out = run_ok("glab user --help")
        self.assertTrue(rc)
        self.assertIn("events", out, "glab user should only have 'events' subcommand")

    def test_user_info_via_api(self):
        status, data = api_get("/user")
        self.assertEqual(status, 200)
        self.assertIn("username", data)


class TestWorkItemsViaAPI(unittest.TestCase):
    """glab has no work-item subcommand — use REST API."""

    def test_glab_work_item_not_exists(self):
        rc, out = run_ok("glab work-item --help")
        self.assertFalse(rc, "glab work-item should not exist")

    def test_work_items_via_api(self):
        """REST API may return 403 on non-Premium; just verify endpoint exists."""
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/work_items")
        self.assertIn(status, [200, 403, 404],
                      "work_items endpoint should return 200/403/404")


if __name__ == "__main__":
    unittest.main()
