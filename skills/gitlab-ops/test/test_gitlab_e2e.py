"""Tests for previously 'untestable' scenarios using the test project.

These tests perform real operations (fork, archive, MR create/merge) on
the configured test project, with full cleanup via REST API.
"""

import unittest
import os
import shutil
import tempfile
import time
from conftest import (
    run, run_ok, api_get, api_post, api_put, api_delete, TempRepo,
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT, GITLAB_NAMESPACE, PROJECT_PATH_ENCODED,
)


def _wait_project_ready(timeout=15):
    """Wait until the project is accessible (not archived/deleting)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, data = api_get(f"/projects/{PROJECT_PATH_ENCODED}")
        if status == 200 and not data.get("archived"):
            return True
        time.sleep(1)
    return False


class TestRepoFork(unittest.TestCase):
    """Fork the test project via REST API, verify, then delete the fork.

    Note: glab repo fork has issues when forking your own project into the
    same namespace. The REST API is more reliable for this edge case.
    """

    FORK_NAME = "git-test-fork-verify"

    def tearDown(self):
        fork_path = f"{GITLAB_NAMESPACE}/{self.FORK_NAME}"
        fork_encoded = fork_path.replace("/", "%2F")
        api_delete(f"/projects/{fork_encoded}")

    def test_fork_via_api(self):
        status, data = api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/fork",
            {"name": self.FORK_NAME, "path": self.FORK_NAME}
        )
        self.assertIn(status, [200, 201], f"Fork failed: {data}")

        fork_path = f"{GITLAB_NAMESPACE}/{self.FORK_NAME}"
        fork_encoded = fork_path.replace("/", "%2F")
        status2, data2 = api_get(f"/projects/{fork_encoded}")
        self.assertEqual(status2, 200, f"Forked project not found: {data2}")
        self.assertFalse(data2.get("archived"))


class TestRepoForkGlab(unittest.TestCase):
    """Test glab repo fork syntax.

    Note: Forking your own project into the same namespace causes conflicts.
    This test verifies the command syntax is correct (--clone=false with equals).
    """

    def test_fork_syntax_help(self):
        rc, out, err = run("glab repo fork --help", check=False)
        self.assertEqual(rc, 0)
        self.assertIn("--clone", out)
        self.assertIn("--name", out)


class TestRepoArchive(unittest.TestCase):
    """Archive the test project via REST API, verify, then unarchive.

    Note: glab repo archive downloads a zip file, it does NOT archive
    (make read-only) a project. Use REST API for archiving.
    """

    def tearDown(self):
        api_post(f"/projects/{PROJECT_PATH_ENCODED}/unarchive", {})
        _wait_project_ready()

    def test_archive_and_unarchive_via_api(self):
        status, data = api_post(f"/projects/{PROJECT_PATH_ENCODED}/archive", {})
        self.assertIn(status, [200, 201], f"Archive failed: {data}")

        status2, data2 = api_get(f"/projects/{PROJECT_PATH_ENCODED}")
        self.assertEqual(status2, 200)
        self.assertTrue(data2.get("archived"), "Project should be archived")

        status3, data3 = api_post(f"/projects/{PROJECT_PATH_ENCODED}/unarchive", {})
        self.assertIn(status3, [200, 201])

        status4, data4 = api_get(f"/projects/{PROJECT_PATH_ENCODED}")
        self.assertEqual(status4, 200)
        self.assertFalse(data4.get("archived"), "Project should be unarchived")


class TestRepoArchiveDownload(unittest.TestCase):
    """Test glab repo archive downloads a zip (not project archiving)."""

    def test_archive_downloads_zip(self):
        import glob

        tmp_dir = tempfile.mkdtemp(prefix="gitlab-ops-archive-test-")
        try:
            rc, out, err = run(
                ["glab", "repo", "archive", GITLAB_PROJECT],
                cwd=tmp_dir, check=False,
            )
            self.assertEqual(rc, 0,
                             f"glab repo archive failed: stdout={out}, stderr={err}")

            zip_files = glob.glob(os.path.join(tmp_dir, "*.zip"))
            self.assertGreater(len(zip_files), 0,
                               "Should have downloaded a zip file")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestMRCreateAndClose(unittest.TestCase):
    """Create a real MR via glab, verify it, then close it.

    Note: glab mr create requires being in a git repo with matching remote.
    """

    BRANCH = "test-mr-create-verify"

    def setUp(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH}")

    def tearDown(self):
        status, mrs = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?source_branch={self.BRANCH}&state=opened"
        )
        if status == 200 and isinstance(mrs, list):
            for mr in mrs:
                api_put(
                    f"/projects/{PROJECT_PATH_ENCODED}/merge_requests/{mr['iid']}",
                    {"state_event": "close"},
                )
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH}")

    def test_mr_create_and_close(self):
        api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches",
            {"branch": self.BRANCH, "ref": "master"},
        )
        api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/commits",
            {
                "branch": self.BRANCH,
                "commit_message": "test: add file for MR verify",
                "actions": [
                    {
                        "action": "create",
                        "file_path": "test-mr-verify.txt",
                        "content": "verify MR create",
                    }
                ],
            },
        )

        with TempRepo() as repo:
            run(f"git remote add origin {GITLAB_URL}/{GITLAB_PROJECT}.git", cwd=repo.dir)
            run(f"git fetch origin {self.BRANCH}", cwd=repo.dir)
            run(f"git checkout -b {self.BRANCH} origin/{self.BRANCH}", cwd=repo.dir)

            rc, out, err = run(
                f'glab mr create '
                f'--source-branch {self.BRANCH} --target-branch master '
                f'--title "test: MR create verify" '
                f'--description "Automated test MR" '
                f'--yes',
                cwd=repo.dir,
                check=False
            )
            self.assertEqual(rc, 0, f"glab mr create failed: stdout={out}, stderr={err}")

        status, mrs = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?source_branch={self.BRANCH}&state=opened"
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(mrs), 0, "MR should exist")
        mr_iid = mrs[0]["iid"]

        status2, _ = api_put(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests/{mr_iid}",
            {"state_event": "close"},
        )
        self.assertIn(status2, [200, 201])


class TestMRCreateAndMerge(unittest.TestCase):
    """Create a real MR, merge it via glab, verify merged state."""

    BRANCH = "test-mr-merge-verify"

    def setUp(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH}")

    def tearDown(self):
        api_delete(f"/projects/{PROJECT_PATH_ENCODED}/repository/branches/{self.BRANCH}")

    def test_mr_create_and_merge(self):
        import time
        unique_id = int(time.time() * 1000) % 100000
        filename = f"test-mr-merge-{unique_id}.txt"

        api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/branches",
            {"branch": self.BRANCH, "ref": "master"},
        )
        api_post(
            f"/projects/{PROJECT_PATH_ENCODED}/repository/commits",
            {
                "branch": self.BRANCH,
                "commit_message": "test: add file for MR merge verify",
                "actions": [
                    {
                        "action": "create",
                        "file_path": filename,
                        "content": f"verify MR merge {unique_id}",
                    }
                ],
            },
        )

        with TempRepo() as repo:
            run(f"git remote add origin {GITLAB_URL}/{GITLAB_PROJECT}.git", cwd=repo.dir)
            run(f"git fetch origin {self.BRANCH}", cwd=repo.dir)
            run(f"git checkout -b {self.BRANCH} origin/{self.BRANCH}", cwd=repo.dir)

            rc, out, err = run(
                f'glab mr create '
                f'--source-branch {self.BRANCH} --target-branch master '
                f'--title "test: MR merge verify" '
                f'--description "Automated test MR for merge" '
                f'--yes',
                cwd=repo.dir,
                check=False
            )
            self.assertEqual(rc, 0, f"glab mr create failed: stdout={out}, stderr={err}")

        status, mrs = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests?source_branch={self.BRANCH}&state=opened"
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(mrs), 0, "MR should exist")
        mr_iid = mrs[0]["iid"]

        rc2, out2, err2 = run(
            f"glab mr merge {mr_iid} -R {GITLAB_PROJECT} --squash --remove-source-branch --yes",
            check=False
        )
        self.assertEqual(rc2, 0, f"glab mr merge failed: stdout={out2}, stderr={err2}")

        status3, mr_data = api_get(
            f"/projects/{PROJECT_PATH_ENCODED}/merge_requests/{mr_iid}"
        )
        self.assertEqual(status3, 200)
        self.assertEqual(mr_data["state"], "merged", "MR should be merged")


class TestRepoTransferHelp(unittest.TestCase):
    """Transfer is too destructive even for test project — verify help only."""

    def test_transfer_target_namespace_flag(self):
        rc, out, err = run("glab repo transfer --help", check=False)
        self.assertEqual(rc, 0)
        self.assertIn("--target-namespace", out)


if __name__ == "__main__":
    unittest.main()
