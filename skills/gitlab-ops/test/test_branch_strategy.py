"""branch_strategy.py 测试——策略登记、退出码语义、remote 归一化、配置文件保序。

用 import 方式调用命令函数，并把 CONFIG_PATH 重定向到临时文件，
全程不读写入库的 config/settings.yaml。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import branch_strategy as bs  # noqa: E402

HEADER = (
    "# gitlab-ops 非敏感配置（入库共享）。凭据禁止写入本文件，只允许在 config/.env。\n"
    "# 策略定义与选型判据见 workflows.md。\n"
    "\n"
)

BASE_YAML = HEADER + """\
schema_version: 1
branch_strategy:
  default: null
  projects:
  - project: ocp/ocp-biz/ocp
    strategy: assembly-flow
    reason: 多需求同版本发布，需支持剔除单个 feature 后重建 release
  - project: team/docs
    strategy: github-flow
    reason: 知识库仓只有 master，feature 直接 MR 到 master
  - project: team/skill-repo
    strategy: none
    reason: 技能仓不适用任何分支策略
"""


def ns(**kwargs):
    """构造命令函数所需的 argparse.Namespace。"""
    args = dict(project=None, repo=None, default=False, reason=None, verbose=False,
                strategy=None)
    args.update(kwargs)
    return argparse.Namespace(**args)


class StrategyCase(unittest.TestCase):
    """提供临时配置文件与 stdout/stderr 捕获的基类。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = pathlib.Path(self._tmp.name) / "settings.yaml"
        self.config.write_text(BASE_YAML, encoding="utf-8")
        self._orig = bs.CONFIG_PATH
        bs.CONFIG_PATH = self.config
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(setattr, bs, "CONFIG_PATH", self._orig)

    def run_get(self, project, verbose=False):
        """执行 cmd_get，返回 (stdout, stderr, 退出码或 None)。"""
        out, err = io.StringIO(), io.StringIO()
        code = None
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                bs.cmd_get(ns(project=project, verbose=verbose))
        except SystemExit as exc:
            code = exc.code
        return out.getvalue(), err.getvalue(), code

    def run_set(self, strategy, project=None, reason=None, default=False):
        """执行 cmd_set，返回 (stdout, stderr, 退出码或 None)。"""
        out, err = io.StringIO(), io.StringIO()
        code = None
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                bs.cmd_set(ns(strategy=strategy, project=project, reason=reason,
                              default=default))
        except SystemExit as exc:
            code = exc.code
        return out.getvalue(), err.getvalue(), code

    def loaded(self):
        """读取当前配置数据。"""
        return bs.load_config()[0]

    def projects(self):
        """返回已登记的项目名顺序。"""
        return [e["project"] for e in self.loaded()["branch_strategy"]["projects"]]


class TestNormalizeProject(StrategyCase):
    """origin remote URL 归一化为 group/[subgroup/]project。"""

    def test_ssh_and_https_agree(self):
        """同一项目的 SSH 与 HTTPS 形态必须归一到同一个键。"""
        forms = [
            "git@gitlab.example.com:ocp/ocp-biz/ocp.git",
            "https://gitlab.example.com/ocp/ocp-biz/ocp.git",
            "ssh://git@gitlab.example.com/ocp/ocp-biz/ocp.git",
            "https://gitlab.example.com/ocp/ocp-biz/ocp",
        ]
        self.assertEqual({bs.normalize_project(u) for u in forms},
                         {"ocp/ocp-biz/ocp"})

    def test_local_path_returns_none(self):
        """本地路径不是远端项目，返回 None 而非猜测。"""
        self.assertIsNone(bs.normalize_project("/d/code/local/repo"))
        self.assertIsNone(bs.normalize_project(""))


class TestGetSemantics(StrategyCase):
    """get 的三种结果：已登记策略 / none / UNSET。"""

    def test_registered_strategy(self):
        out, _, code = self.run_get("ocp/ocp-biz/ocp")
        self.assertEqual(out.strip(), "assembly-flow")
        self.assertIsNone(code)

    def test_none_is_registered_not_unset(self):
        """none 是已登记状态：退出码 0，且明确告知不得套用任何模型。"""
        out, err, code = self.run_get("team/skill-repo")
        self.assertEqual(out.strip(), "none")
        self.assertIsNone(code)
        self.assertIn("不适用任何分支策略", err)

    def test_unregistered_returns_unset_with_exit_3(self):
        """未登记且 default 为空 → UNSET + 退出码 3，提示必须问用户。"""
        out, err, code = self.run_get("team/unknown")
        self.assertEqual(out.strip(), "UNSET")
        self.assertEqual(code, bs.EXIT_UNSET)
        self.assertIn("MUST", err)
        self.assertIn("set none", err)

    def test_default_fallback(self):
        """default 非空时，未登记项目回落到 default。"""
        data, header = bs.load_config()
        data["branch_strategy"]["default"] = "github-flow"
        bs.save_config(data, header)
        out, _, code = self.run_get("team/unknown")
        self.assertEqual(out.strip(), "github-flow")
        self.assertIsNone(code)

    def test_verbose_shows_reason(self):
        _, err, _ = self.run_get("ocp/ocp-biz/ocp", verbose=True)
        self.assertIn("project=ocp/ocp-biz/ocp", err)
        self.assertIn("reason=", err)


class TestSetSemantics(StrategyCase):
    """set 的登记、覆盖、非法值，以及 none 在项目级与 default 上的不同语义。"""

    def test_set_new_project_appends(self):
        out, _, code = self.run_set("github-flow", project="team/new", reason="新登记")
        self.assertIsNone(code)
        self.assertIn("team/new = github-flow", out)
        entry = [e for e in self.loaded()["branch_strategy"]["projects"]
                 if e["project"] == "team/new"][0]
        self.assertEqual(entry["reason"], "新登记")

    def test_set_existing_preserves_reason_when_omitted(self):
        """改策略但不给 reason 时静默保留原 reason（原 reason 仍是有效语义）。"""
        _, err, code = self.run_set("github-flow", project="ocp/ocp-biz/ocp")
        self.assertIsNone(code)
        self.assertNotIn("WARN", err)
        entry = [e for e in self.loaded()["branch_strategy"]["projects"]
                 if e["project"] == "ocp/ocp-biz/ocp"][0]
        self.assertEqual(entry["strategy"], "github-flow")
        self.assertIn("多需求同版本发布", entry["reason"])

    def test_set_without_reason_on_reasonless_entry_warns(self):
        """条目本就没有 reason 时才 WARN，提示补写选型理由。"""
        data, header = bs.load_config()
        data["branch_strategy"]["projects"].append(
            {"project": "team/no-reason", "strategy": "git-flow"})
        bs.save_config(data, header)
        _, err, code = self.run_set("github-flow", project="team/no-reason")
        self.assertIsNone(code)
        self.assertIn("WARN", err)

    def test_set_none_at_project_level_is_allowed(self):
        """none 可作项目级登记值，表示不适用任何策略。"""
        _, _, code = self.run_set("none", project="ocp/ocp-biz/ocp", reason="工具仓")
        self.assertIsNone(code)
        entry = [e for e in self.loaded()["branch_strategy"]["projects"]
                 if e["project"] == "ocp/ocp-biz/ocp"][0]
        self.assertEqual(entry["strategy"], "none")
        out, _, _ = self.run_get("ocp/ocp-biz/ocp")
        self.assertEqual(out.strip(), "none")

    def test_set_none_as_default_clears_it(self):
        """--default none 是清空兜底，不是把 none 写成兜底策略。

        否则漏配项目会静默退化为「不适用任何策略」，绕过必须询问用户的门禁。
        """
        self.run_set("github-flow", project="ocp/ocp-biz/ocp", reason="x")
        _, _, code = self.run_set("none", default=True)
        self.assertIsNone(code)
        self.assertIsNone(self.loaded()["branch_strategy"]["default"])
        self.assertNotEqual(self.projects(), [])

    def test_set_unknown_strategy_exits_2(self):
        """非法策略名以退出码 2 拒绝，不写文件。"""
        before = self.config.read_text(encoding="utf-8")
        _, err, code = self.run_set("gitlab-flow", project="team/x")
        self.assertEqual(code, bs.EXIT_ERROR)
        self.assertIn("未知策略", err)
        self.assertNotIn("team/x", self.projects())
        self.assertEqual(self.config.read_text(encoding="utf-8"), before)


class TestRemoveAndIntegrity(StrategyCase):
    """remove 回落语义与配置文件写回的完整性。"""

    def test_remove_falls_back_to_unset(self):
        _, _, code = self.run_set("git-flow", project="team/x", reason="临时")
        self.assertIsNone(code)
        data = self.loaded()
        self.assertIn("team/x", self.projects())
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            bs.cmd_remove(ns(project="team/x"))
        self.assertNotIn("team/x", self.projects())
        out, _, code = self.run_get("team/x")
        self.assertEqual(out.strip(), "UNSET")
        self.assertEqual(code, bs.EXIT_UNSET)

    def test_header_comments_survive_write(self):
        """说明块是文档承诺的一部分，写回后必须仍在。"""
        self.run_set("github-flow", project="team/x", reason="写盘")
        self.assertTrue(self.config.read_text(encoding="utf-8").startswith(HEADER))

    def test_existing_entry_order_is_preserved(self):
        """新增登记不得打乱已有条目的相对顺序。"""
        before = self.projects()
        self.run_set("github-flow", project="team/zzz", reason="追加")
        after = self.projects()
        existing = [p for p in before]
        self.assertEqual([p for p in after if p in existing], existing)
        self.assertEqual(after[-1], "team/zzz")

    def test_reason_with_chinese_survives_roundtrip(self):
        """中文 reason 经 dump→load 不失真（Windows 下曾因编码踩过坑）。"""
        self.run_set("git-flow", project="team/cn",
                     reason="剔除单个 feature 后重建 release")
        entry = [e for e in self.loaded()["branch_strategy"]["projects"]
                 if e["project"] == "team/cn"][0]
        self.assertEqual(entry["reason"], "剔除单个 feature 后重建 release")


class TestList(StrategyCase):
    """list 输出登记全貌，供 Agent 与人工核对。"""

    def test_list_shows_default_and_entries(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            bs.cmd_list(ns())
        text = out.getvalue()
        self.assertIn("git-flow, assembly-flow, github-flow", text)
        self.assertIn("default: (未设置", text)
        self.assertIn("team/skill-repo: none", text)


if __name__ == "__main__":
    unittest.main()
