"""scripts/ 目录测试——验证 Python 脚本语法正确且 --help 可正常运行。"""

import os
import subprocess
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def run_script(script_name, args=None):
    """使用占位环境变量运行 scripts/ 下的脚本，返回 (rc, stdout, stderr)。"""
    if args is None:
        args = ["--help"]
    elif isinstance(args, str):
        args = args.split()
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    env = os.environ.copy()
    env.setdefault("GITLAB_URL", "https://placeholder.local")
    env.setdefault("GITLAB_TOKEN", "placeholder-token")
    env.setdefault("GITLAB_PROJECT", "placeholder/project")
    result = subprocess.run(
        ["python", script_path] + args,
        capture_output=True, text=True, timeout=15,
        env=env,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestScriptSyntax(unittest.TestCase):
    """验证所有脚本编译无语法错误。"""

    scripts = [
        "mr_batch_merge.py",
        "issue_triage.py",
        "ci_retry_failed.py",
        "repo_audit.py",
        "release_notes.py",
        "branch_cleanup.py",
        "env_check.py",
    ]

    def test_all_scripts_compile(self):
        """验证 scripts/ 下每个脚本通过 py_compile 编译无语法错误。"""
        for script in self.scripts:
            path = os.path.join(SCRIPTS_DIR, script)
            result = subprocess.run(
                ["python", "-c",
                 f"import py_compile; py_compile.compile(r'{path}', doraise=True)"],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0,
                             f"{script} has syntax errors: {result.stderr}")


class TestMRBatchMerge(unittest.TestCase):
    """mr_batch_merge.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("mr_batch_merge.py")
        self.assertEqual(rc, 0)
        self.assertIn("--label", out)
        self.assertIn("--dry-run", out)
        self.assertIn("--squash", out)


class TestIssueTriage(unittest.TestCase):
    """issue_triage.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("issue_triage.py")
        self.assertEqual(rc, 0)
        self.assertIn("--no-label", out)
        self.assertIn("--assign", out)


class TestCIRetryFailed(unittest.TestCase):
    """ci_retry_failed.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("ci_retry_failed.py")
        self.assertEqual(rc, 0)
        self.assertIn("--ref", out)
        self.assertIn("--dry-run", out)


class TestRepoAudit(unittest.TestCase):
    """repo_audit.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("repo_audit.py")
        self.assertEqual(rc, 0)
        self.assertIn("--output", out)


class TestReleaseNotes(unittest.TestCase):
    """release_notes.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("release_notes.py")
        self.assertEqual(rc, 0)
        self.assertIn("--output", out)


class TestBranchCleanup(unittest.TestCase):
    """branch_cleanup.py 测试。"""

    def test_help(self):
        rc, out, _ = run_script("branch_cleanup.py")
        self.assertEqual(rc, 0)
        self.assertIn("--target", out)
        self.assertIn("--dry-run", out)
        self.assertIn("--remote", out)

    def test_dry_run_local(self):
        """branch_cleanup.py --dry-run 应在任意 git 仓库中正常运行。"""
        rc, out, err = run_script("branch_cleanup.py", "--dry-run")
        self.assertEqual(rc, 0)


class TestEnvCheck(unittest.TestCase):
    """env_check.py 测试——环境前置依赖检查。"""

    def _run_env_check(self, args=None):
        """使用可选参数运行 env_check.py，返回 (rc, stdout, stderr)。"""
        script_path = os.path.join(SCRIPTS_DIR, "env_check.py")
        cmd = ["python", script_path]
        if args:
            if isinstance(args, str):
                args = args.split()
            cmd.extend(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    def test_check_mode(self):
        """默认模式应报告 python3、git、glab 的状态。"""
        rc, out, _ = self._run_env_check()
        self.assertIn("python3", out)
        self.assertIn("git", out)
        self.assertIn("glab", out)

    def test_json_output(self):
        """--json 应生成包含预期字段的有效 JSON。"""
        import json
        rc, out, _ = self._run_env_check("--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("os", data)
        self.assertIn("checks", data)
        self.assertIn("all_ok", data)
        self.assertIn("missing", data)
        self.assertEqual(len(data["checks"]), 3)

    def test_install_mode(self):
        """--install 应无错运行（工具齐全时为空操作）。"""
        rc, out, _ = self._run_env_check("--install")
        self.assertIn("python3", out)
        self.assertIn("git", out)
        self.assertIn("glab", out)


if __name__ == "__main__":
    unittest.main()
