"""测试套件自身的解析逻辑（conftest）的自证用例。

全部为本地用例：不访问 GitLab，权限判定用 mock 注入。
覆盖今天实跑暴露的三类缺陷——
1) 模块常量遮蔽 PEP 562 延迟解析，导致 GITLAB_PROJECT 环境变量丢失；
2) 凭据与测试项目耦合，只断言 CLI 参数的用例也被迫要求指定项目；
3) 角色门禁 require_role 的分档行为。

从技能根目录或 test/ 目录运行均可（test/__init__.py 已把本目录加入 sys.path）：

    python -m unittest test.test_conftest_helpers
"""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess
import sys
import unittest
from unittest import mock

TEST_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import conftest  # noqa: E402


def _run_probe(source: str, extra_env: dict) -> subprocess.CompletedProcess:
    """在干净子进程里导入 conftest 并执行 source，返回结果。

    用子进程而非 importlib.reload：conftest 的解析发生在导入时，
    而 reload 会让同进程内其他模块持有新旧两份函数，污染后续用例。
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT")}
    env.update(extra_env)
    env["PYTHONPATH"] = str(TEST_DIR)
    return subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True, encoding="utf-8", errors="replace", env=env,
    )


class TestProjectResolution(unittest.TestCase):
    """GITLAB_PROJECT 必须能从环境变量注入，常量不得遮蔽它。"""

    BASE_ENV = {"GITLAB_URL": "https://gitlab.example.com",
                "GITLAB_TOKEN": "glpat-fake"}

    def test_env_overrides_constant(self):
        proc = _run_probe(
            "import conftest; print(conftest.GITLAB_PROJECT)",
            {**self.BASE_ENV, "GITLAB_PROJECT": "group/from-env"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "group/from-env")

    def test_config_reflects_env_project(self):
        proc = _run_probe(
            "import conftest; print(conftest._load_config()['PROJECT_PATH_ENCODED'])",
            {**self.BASE_ENV, "GITLAB_PROJECT": "grp/sub/proj"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "grp%2Fsub%2Fproj")

    def test_missing_project_fails_with_guidance(self):
        proc = _run_probe(
            "import conftest\n"
            "try:\n"
            "    conftest._load_config()\n"
            "    print('NO-ERROR')\n"
            "except RuntimeError as e:\n"
            "    print('ERR', e)\n",
            dict(self.BASE_ENV),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("GITLAB_PROJECT", proc.stdout)
        self.assertNotIn("NO-ERROR", proc.stdout, "未指定项目却通过 = fail-open")


class TestCredentialDecoupling(unittest.TestCase):
    """只需要凭据的用例不应被迫要求测试项目。"""

    def test_credentials_resolve_without_project(self):
        proc = _run_probe(
            "import conftest; c = conftest._load_credentials(); "
            "print(c['GITLAB_HOST'], 'GITLAB_PROJECT' in c)",
            {"GITLAB_URL": "https://gitlab.example.com", "GITLAB_TOKEN": "glpat-fake"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "gitlab.example.com False")

    def test_glab_env_works_without_project(self):
        proc = _run_probe(
            "import conftest; e = conftest._glab_env(); "
            "print(bool(e['GITLAB_TOKEN']), e['GITLAB_HOST'])",
            {"GITLAB_URL": "https://gitlab.example.com", "GITLAB_TOKEN": "glpat-fake"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "True gitlab.example.com")

    def test_missing_credentials_fail_closed(self):
        # 显式置空，避免本机 config/.env 里的真实凭据被 _load_dotenv 补上而使断言失真
        proc = _run_probe(
            "import conftest\n"
            "try:\n"
            "    conftest._load_credentials(); print('NO-ERROR')\n"
            "except RuntimeError as e:\n"
            "    print('ERR', str(e)[:60])\n",
            {"GITLAB_URL": "https://gitlab.example.com", "GITLAB_TOKEN": ""},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("GITLAB_TOKEN", proc.stdout)
        self.assertNotIn("NO-ERROR", proc.stdout)


class TestTempRepoCleanup(unittest.TestCase):
    """commit 后 git 把 object 文件写成只读，`rmtree(ignore_errors=True)` 会静默泄漏。"""

    def test_repo_dir_removed_after_context(self):
        repo = conftest.TempRepo()
        repo.__enter__()
        try:
            repo.commit("c1")
            repo.commit("c2")
            files = [p for p in pathlib.Path(repo.dir).rglob("*") if p.is_file()]
            readonly = [
                p for p in files
                if p.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
            ] if os.name == "nt" else []
        finally:
            repo.__exit__(None, None, None)
        self.assertFalse(pathlib.Path(repo.dir).exists(),
                         "TempRepo 目录仍在 = 泄漏（本机已累积过 574 个）")
        if os.name == "nt":
            # 判别性前提：样本里必须真有只读文件，否则这条用例证明不了任何事
            self.assertTrue(readonly, "样本无只读对象，用例失去判别力")


class TestRequireRole(unittest.TestCase):
    """require_role 的三档行为：不足跳过、足够放行、取不到角色不跳过。"""

    def setUp(self):
        patcher = mock.patch.object(
            conftest, "_load_config",
            return_value={"GITLAB_PROJECT": "grp/proj", "PROJECT_PATH_ENCODED": "grp%2Fproj"},
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.case = mock.Mock()

    def _call(self, level: int) -> None:
        with mock.patch.object(conftest, "project_access_level", return_value=level):
            conftest.require_role(self.case, 40, "管理 CI/CD 变量")

    def test_insufficient_role_skips_with_reason(self):
        self._call(30)
        self.case.skipTest.assert_called_once()
        reason = self.case.skipTest.call_args[0][0]
        self.assertIn("管理 CI/CD 变量", reason)
        self.assertIn("40", reason)
        self.assertIn("30", reason)

    def test_sufficient_role_does_not_skip(self):
        for level in (40, 50):
            with self.subTest(level=level):
                self.case.reset_mock()
                self._call(level)
                self.case.skipTest.assert_not_called()

    def test_unknown_role_does_not_skip(self):
        """角色取不到时必须放行，让真实请求以失败暴露问题，而不是静默跳过。"""
        self._call(-1)
        self.case.skipTest.assert_not_called()


class TestRealSkipException(unittest.TestCase):
    """mock 断言之外，再用真实 unittest 机制验证 skipTest 确实生效。"""

    def test_skip_is_raised(self):
        class Probe(unittest.TestCase):
            def runTest(self):
                pass

        with mock.patch.object(conftest, "_load_config",
                               return_value={"GITLAB_PROJECT": "grp/proj"}), \
             mock.patch.object(conftest, "project_access_level", return_value=20):
            with self.assertRaises(unittest.SkipTest):
                conftest.require_role(Probe(), 40, "归档项目")


if __name__ == "__main__":
    unittest.main()
