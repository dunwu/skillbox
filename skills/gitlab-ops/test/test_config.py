"""scripts/config.py 测试——凭据路径唯一性、脱敏输出、fail-closed 写盘。

所有用例把 config.ENV_PATH 重定向到临时文件，**绝不读写真实的 config/.env**
（那里面是可用凭据）。同时清掉进程内已有的 GITLAB_* 环境变量，避免继承值干扰。
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import config  # noqa: E402


class ConfigCase(unittest.TestCase):
    """提供临时 ENV_PATH、隔离环境变量与输出捕获的基类。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.env_file = os.path.join(self._tmp.name, "config", ".env")
        self._orig_env_path = config.ENV_PATH
        self._orig_loaded = config._dotenv_loaded
        config.ENV_PATH = self.env_file
        config._dotenv_loaded = False
        self._saved = {}
        for key in ("GITLAB_URL", "GITLAB_TOKEN"):
            self._saved[key] = os.environ.pop(key, None)
        self.addCleanup(self._restore)
        self.addCleanup(self._tmp.cleanup)

    def _restore(self):
        config.ENV_PATH = self._orig_env_path
        config._dotenv_loaded = self._orig_loaded
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def run_cmd(self, func, *args):
        """执行子命令，返回 (stdout, stderr, 退出码或 None)。"""
        out, err = io.StringIO(), io.StringIO()
        code = None
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                func(*args)
        except SystemExit as exc:
            code = exc.code
        return out.getvalue(), err.getvalue(), code


class TestCredentialPath(ConfigCase):
    """凭据位置必须是 <skill-root>/config/.env。"""

    def test_env_path_is_config_dir(self):
        """路径落在 config/ 下，与 settings.yaml 同目录，不在 scripts/ 或 test/。"""
        real = pathlib.Path(config.env_file_path()).resolve()
        skill_root = real.parent.parent
        self.assertEqual(real.parent.name, "config")
        self.assertEqual(real.name, ".env")
        self.assertEqual(real, skill_root / "config" / ".env")

    def test_no_stale_scripts_env_reference_in_code(self):
        """源码里不得再出现 scripts/.env 或 test/.env 作为凭据路径。"""
        for py in SCRIPTS_DIR.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            self.assertNotIn("scripts/.env", text, f"{py.name} 仍指向 scripts/.env")


class TestResolutionOrder(ConfigCase):
    """解析顺序：环境变量优先于 config/.env。"""

    def test_env_var_wins(self):
        os.environ["GITLAB_URL"] = "https://from-env-var.example"
        os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write("GITLAB_URL=https://from-file.example\nGITLAB_TOKEN=t\n")
        self.assertEqual(config.resolve("GITLAB_URL"), "https://from-env-var.example")

    def test_file_fills_when_env_absent(self):
        os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write("GITLAB_URL=https://from-file.example\nGITLAB_TOKEN=t\n")
        self.assertEqual(config.resolve("GITLAB_URL"), "https://from-file.example")
        self.assertEqual(config.resolve("GITLAB_TOKEN"), "t")

    def test_quoted_value_unwrapped(self):
        """历史 .env 可能带引号；解析时应剥除（与既有行为一致）。"""
        os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write('GITLAB_TOKEN="glpat-quoted"\n')
        self.assertEqual(config.resolve("GITLAB_TOKEN"), "glpat-quoted")

    def test_missing_file_yields_none(self):
        self.assertIsNone(config.resolve("GITLAB_URL"))


class TestCheckCommand(ConfigCase):
    """check 的退出码语义与脱敏。"""

    def test_unset_returns_exit_3(self):
        _, err, code = self.run_cmd(config.cmd_check, None)
        self.assertEqual(code, config.EXIT_UNSET)
        self.assertIn("UNSET", err)

    def test_ready_returns_exit_0(self):
        os.environ["GITLAB_URL"] = "https://x.example"
        os.environ["GITLAB_TOKEN"] = "a-secret-token-value"
        out, _, code = self.run_cmd(config.cmd_check, None)
        self.assertEqual(code, config.EXIT_READY)
        self.assertIn("凭据就绪", out)

    def test_check_never_prints_the_token(self):
        """脱敏是硬要求：输出里不得出现 token 的任何片段。"""
        os.environ["GITLAB_URL"] = "https://x.example"
        os.environ["GITLAB_TOKEN"] = "glpat-SUPERSECRET-DO-NOT-LEAK"
        out, err, _ = self.run_cmd(config.cmd_check, None)
        combined = out + err
        self.assertNotIn("SUPERSECRET", combined)
        self.assertNotIn("glpat-", combined)
        self.assertIn("已设置", combined)   # 只报告存在与长度


class TestSetupFailClosed(ConfigCase):
    """setup 必须 fail-closed：任一环节不过都不写盘。"""

    def test_from_env_missing_vars_does_not_write(self):
        ns = mock.MagicMock(from_env=True, url_var="GITLAB_URL",
                            token_var="GITLAB_TOKEN")
        _, err, code = self.run_cmd(config.cmd_setup, ns)
        self.assertEqual(code, config.EXIT_ERROR)
        self.assertFalse(os.path.exists(self.env_file), "凭据缺失时不得创建文件")

    def test_from_env_unreachable_url_does_not_write(self):
        """.invalid 是 RFC 保留 TLD，解析必然失败——验证「验证不过不写盘」。"""
        os.environ["GITLAB_URL"] = "https://gitlab-for-test.invalid"
        os.environ["GITLAB_TOKEN"] = "any-token"
        ns = mock.MagicMock(from_env=True, url_var="GITLAB_URL",
                            token_var="GITLAB_TOKEN")
        _, err, code = self.run_cmd(config.cmd_setup, ns)
        self.assertEqual(code, config.EXIT_ERROR)
        self.assertFalse(os.path.exists(self.env_file), "连接验证失败仍写盘 = fail-open")
        self.assertIn("未写入任何文件", err)

    def test_from_env_rejects_non_http_url(self):
        os.environ["GITLAB_URL"] = "gitlab.example.com"   # 缺协议
        os.environ["GITLAB_TOKEN"] = "any-token"
        ns = mock.MagicMock(from_env=True, url_var="GITLAB_URL",
                            token_var="GITLAB_TOKEN")
        _, _, code = self.run_cmd(config.cmd_setup, ns)
        self.assertEqual(code, config.EXIT_ERROR)
        self.assertFalse(os.path.exists(self.env_file))

    def test_setup_without_source_never_writes_real_file(self):
        """子进程验证：既拒绝无 tty 代跑，也不改动真实凭据文件。

        本用例走的是未 patch 的真实路径，所以额外断言 mtime 不变——
        一旦写盘逻辑退化为 fail-open，这条会先炸，而不是把凭据文件覆盖掉。
        """
        real = pathlib.Path(config.env_file_path()).resolve()
        mtime_before = real.stat().st_mtime if real.exists() else None
        script = str(SCRIPTS_DIR / "config.py")
        # 必须显式 encoding：config.py 输出 UTF-8，而 Windows 下 text=True 默认按 GBK 解码，
        # reader 线程会抛 UnicodeDecodeError 并使 stdout/stderr 变成 None
        proc = subprocess.run([sys.executable, script, "setup"],
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=60)
        self.assertEqual(proc.returncode, config.EXIT_ERROR)
        combined = (proc.stdout or "") + (proc.stderr or "")
        self.assertIn("没有可读输入", combined)
        mtime_after = real.stat().st_mtime if real.exists() else None
        self.assertEqual(mtime_after, mtime_before, "真实凭据文件被改动了")


class TestWriteEnvIntegrity(ConfigCase):
    """_write_env 的合并语义与文件属性。"""

    def test_preserves_other_keys(self):
        os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write("OTHER_SETTING=keep-me\nGITLAB_URL=https://old.example\n")
        config._write_env({"GITLAB_URL": "https://new.example",
                           "GITLAB_TOKEN": "tok"})
        text = pathlib.Path(self.env_file).read_text(encoding="utf-8")
        self.assertIn("OTHER_SETTING=keep-me", text)   # 不得丢失无关键
        self.assertIn("GITLAB_URL=https://new.example", text)
        self.assertIn("GITLAB_TOKEN=tok", text)
        self.assertNotIn("https://old.example", text)  # 旧值被替换而非追加重复

    def test_no_duplicate_keys_after_rewrite(self):
        config._write_env({"GITLAB_URL": "https://a.example", "GITLAB_TOKEN": "t1"})
        config._write_env({"GITLAB_TOKEN": "t2"})
        text = pathlib.Path(self.env_file).read_text(encoding="utf-8")
        self.assertEqual(text.count("GITLAB_TOKEN="), 1)

    def test_written_values_are_readable_back(self):
        config._write_env({"GITLAB_URL": "https://b.example", "GITLAB_TOKEN": "t9"})
        os.environ.pop("GITLAB_URL", None)
        os.environ.pop("GITLAB_TOKEN", None)
        config._dotenv_loaded = False
        self.assertEqual(config.resolve("GITLAB_URL"), "https://b.example")


class TestRealConfigEnvUntouched(ConfigCase):
    """守住最硬的一条：测试期间真实凭据文件不得被改动。"""

    def test_repo_config_env_not_modified(self):
        real = pathlib.Path(config.env_file_path()).resolve()
        # env_file_path() 返回真实路径（本类只 patch 了 ENV_PATH 常量）
        stat_before = real.stat().st_mtime if real.exists() else None
        ns = mock.MagicMock(from_env=True, url_var="GITLAB_URL",
                            token_var="GITLAB_TOKEN")
        os.environ["GITLAB_URL"] = "https://gitlab-for-test.invalid"
        os.environ["GITLAB_TOKEN"] = "x"
        self.run_cmd(config.cmd_setup, ns)      # 写向临时路径，且验证会失败
        self.assertEqual(real.stat().st_mtime if real.exists() else None, stat_before)
        self.assertEqual(config.env_file_path(), str(real))


class TestUtf8Output(unittest.TestCase):
    """脚本侧契约：含中文的输出必须是合法 UTF-8 字节。

    这条用**字节捕获**断言，跨平台一致——不依赖测试机的 locale。
    调用方那半（显式 encoding="utf-8"）见 SKILL.md §脚本输出与编码约定。
    """

    SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"

    def _run_bytes(self, script, *args):
        return subprocess.run([sys.executable, str(self.SCRIPTS / script), *args],
                              capture_output=True, timeout=60)

    def test_config_check_output_decodes_as_utf8(self):
        proc = self._run_bytes("config.py", "check")
        text = proc.stdout.decode("utf-8")          # 非 UTF-8 会在此抛错
        self.assertIn("凭据", text)                  # 确认确实输出了中文

    def test_branch_strategy_unset_hint_decodes_as_utf8(self):
        """未登记时的 MUST 指引是本 Skill 的关键约束，不能被编码问题吞掉。"""
        proc = self._run_bytes("branch_strategy.py", "get", "--project", "zzz/not-registered")
        self.assertEqual(proc.returncode, 3)
        err = proc.stderr.decode("utf-8")
        self.assertIn("MUST", err)
        self.assertIn("未登记分支策略", err)

    def test_no_bom_in_output(self):
        """输出不应带 BOM——带 BOM 会让下游 JSON/键值解析首行错位。"""
        proc = self._run_bytes("config.py", "check")
        self.assertFalse(proc.stdout.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
