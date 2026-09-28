"""Tests for REST API endpoints documented across all SKILL files."""

import unittest
import time
from conftest import (
    run, run_ok, api_get, api_post, api_delete,
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT, PROJECT_PATH_ENCODED,
)


class TestProjectAPI(unittest.TestCase):
    def test_get_project_by_id(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}")
        self.assertEqual(status, 200)
        self.assertIn("id", data)
        self.assertIn("name", data)

    def test_get_project_fields(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}")
        self.assertEqual(status, 200)
        for field in ["id", "name", "path_with_namespace", "default_branch",
                       "web_url", "ssh_url_to_repo", "http_url_to_repo"]:
            self.assertIn(field, data, f"Field {field} missing from project response")


class TestMRAPI(unittest.TestCase):
    def test_list_mrs(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?state=all"
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_list_mrs_filter_state(self):
        for state in ["opened", "closed", "merged", "all"]:
            status, data = api_get(
                f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?state={state}"
            )
            self.assertEqual(status, 200, f"state={state} failed")

    def test_mr_diff_via_api(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?state=all&per_page=1"
        )
        if status == 200 and len(data) > 0:
            mr_iid = data[0]["iid"]
            status2, changes = api_get(
                f"/projects/{PROJECT_PATH_ENCODED}/merge_requests/{mr_iid}/changes"
            )
            self.assertEqual(status2, 200)
            self.assertIn("changes", changes)


class TestIssueAPI(unittest.TestCase):
    def test_list_issues(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/issues?state=all"
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_create_and_delete_issue(self):
        title = f"api-test-{int(time.time())}"
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/issues",
            {"title": title},
        )
        self.assertIn(status, [200, 201])
        issue_iid = data["iid"]
        status2, _ = api_delete(
            f"/projects/{PROJECT_PATH_ENCODED}/issues/{issue_iid}"
        )
        self.assertIn(status2, [200, 204])


class TestFileAPI(unittest.TestCase):
    def test_list_repo_tree(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/tree"
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_get_file_content(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/files/README.md"
        )
        if status == 200:
            self.assertIn("file_name", data)
            self.assertIn("content", data)

    def test_list_tree_with_path(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/tree?path=.&recursive=false"
        )
        self.assertEqual(status, 200)


class TestVariableAPI(unittest.TestCase):
    VAR_KEY = "TEST_API_VAR"

    def setUp(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}")

    def tearDown(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}")

    def test_list_variables(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/variables")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_create_get_delete_variable(self):
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/variables",
            {"key": self.VAR_KEY, "value": "api-test-value"},
        )
        self.assertIn(status, [200, 201])

        status2, data2 = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/variables/{self.VAR_KEY}"
        )
        self.assertEqual(status2, 200)
        self.assertEqual(data2["value"], "api-test-value")


class TestWebhookAPI(unittest.TestCase):
    HOOK_URL = "https://httpbin.org/post"

    def test_list_webhooks(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/hooks")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_create_and_delete_webhook(self):
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/hooks",
            {"url": self.HOOK_URL, "push_events": True},
        )
        self.assertIn(status, [200, 201])
        hook_id = data["id"]
        status2, _ = api_delete(
            f"/projects/{PROJECT_PATH_ENCODED}/hooks/{hook_id}"
        )
        self.assertIn(status2, [200, 204])


class TestLabelAPI(unittest.TestCase):
    def test_list_labels(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/labels")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_create_and_delete_label(self):
        name = f"api-test-label-{int(time.time())}"
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/labels",
            {"name": name, "color": "#FF0000"},
        )
        self.assertIn(status, [200, 201])
        status2, _ = api_delete(
            f"/projects/{PROJECT_PATH_ENCODED}/labels/{name}"
        )
        self.assertIn(status2, [200, 204])


class TestPaginationAPI(unittest.TestCase):
    def test_pagination_headers(self):
        """Verify pagination works with per_page and page params."""
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        import json

        url = (
            f"{GITLAB_URL}/api/v4/projects/{PROJECT_PATH_ENCODED}"
            f"/merge_requests?state=all&per_page=1&page=1"
        )
        req = Request(url, headers={"PRIVATE-TOKEN": GITLAB_TOKEN})
        try:
            with urlopen(req, timeout=15) as resp:
                self.assertEqual(resp.status, 200)
                x_total = resp.headers.get("X-Total")
                x_page = resp.headers.get("X-Page")
                self.assertIsNotNone(x_page, "X-Page header should be present")
        except HTTPError as e:
            self.fail(f"Pagination request failed: {e.code}")


class TestBranchAPI(unittest.TestCase):
    def test_list_branches(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches"
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        if len(data) > 0:
            self.assertIn("name", data[0])
            self.assertIn("commit", data[0])

    def test_get_single_branch(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/main"
        )
        if status == 200:
            self.assertIn("name", data)
            self.assertEqual(data["name"], "main")


class TestScheduleAPI(unittest.TestCase):
    def test_list_schedules(self):
        status, data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/pipeline_schedules"
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)


class TestSnippetAPI(unittest.TestCase):
    def test_list_snippets(self):
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}/snippets")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
