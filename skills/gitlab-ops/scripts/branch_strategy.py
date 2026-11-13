#!/usr/bin/env python3
"""分支管理策略注册表——解析 / 设置 / 切换各仓库应遵循的分支策略。

策略取值（模型定义、拓扑图与选型判据见 references/workflows.md「分支管理策略」）::

    git-flow        经典 Git Flow：develop 作集成分支
    assembly-flow   装配式 release：无 develop，feature 装配进 release，release→master
    github-flow     单主干：feature 直接 MR 回主干
    none            该项目不适用任何分支策略：分支完全按用户当次意图控制，
                    Agent MUST NOT 自行套用上述任一模型（不开 feature、不定 MR 目标）

用法::

    python branch_strategy.py get [--project GROUP/PROJ]
    python branch_strategy.py set STRATEGY [--project GROUP/PROJ] [--reason TEXT]
    python branch_strategy.py set STRATEGY --default      # 设置未匹配时的兜底策略
    python branch_strategy.py switch STRATEGY [...]       # set 的语义别名
    python branch_strategy.py remove [--project GROUP/PROJ]  # 删登记，回落 default
    python branch_strategy.py list

``none`` 只能作为**项目级**登记值。``--default none`` 表示清空兜底（回到「未登记即
UNSET、必须问用户」），而非「所有未登记项目默认不适用策略」——后者会让缺失配置
静默退化为无约束，故不接受。

配置文件：``<skill-root>/config/settings.yaml``（入库共享；凭据禁止写入）。

退出码：``0`` 已解析 / ``3`` UNSET（Agent MUST 走对话式确认后写入，不得猜） /
``2`` 参数、配置或 git 环境错误。

依赖：PyYAML（``env_check.py`` 会检查；缺失时本脚本以退出码 2 明确报错，不静默降级）。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:  # pragma: no cover - 环境缺失时给出可执行指引
    print("ERROR: 缺少 PyYAML。安装：python -m pip install pyyaml", file=sys.stderr)
    print("       或运行 python scripts/env_check.py --install", file=sys.stderr)
    sys.exit(2)

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_ROOT / "config" / "settings.yaml"

# Windows 控制台默认 GBK，reason 等中文字段会乱码；与凭据模块共用同一套 stdio 设置，
# 避免出现两份各自演化的编码处理。
from config import configure_utf8_stdio

configure_utf8_stdio()

STRATEGIES = ("git-flow", "assembly-flow", "github-flow")
NONE_VALUE = "none"
# 项目级可登记的取值：三种策略 + none（不适用任何策略）
PROJECT_VALUES = STRATEGIES + (NONE_VALUE,)
CLEAR_VALUES = ("none", "null", "")

MINIMAL_HEADER = """\
# gitlab-ops 非敏感配置（入库共享）。凭据禁止写入本文件，只允许在 config/.env。
# branch_strategy 各策略定义与选型判据见 references/workflows.md；解析用 scripts/branch_strategy.py。
# 项目键为归一化路径 group/[subgroup/]project，MUST NOT 用 gitlab_url（SSH/HTTPS 形态不同会失配）。
# 「为什么选这套」写进 reason 字段，不要写行内注释（yaml dump 会丢注释）。

"""

EXIT_UNSET = 3
EXIT_ERROR = 2


def _fail(msg: str) -> None:
    """打印错误到 stderr 并以 EXIT_ERROR 退出。"""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(EXIT_ERROR)


def normalize_project(url: str) -> str | None:
    """把 git remote URL 归一化为 ``group/[subgroup/]project``。

    同时支持 SSH（``git@host:group/proj.git``、``ssh://git@host/group/proj.git``）
    与 HTTPS（``https://host/group/proj.git``）两种形态；本地路径 remote 返回 None。
    """
    u = (url or "").strip()
    if not u or "\\" in u:
        return None

    if "://" in u:
        path = urlparse(u).path
    elif ":" in u:
        path = u.split(":", 1)[1]
    else:
        return None

    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.strip("/") or None


def current_project(repo: Path | None = None) -> str:
    """由当前仓库的 origin remote 推导归一化项目路径。"""
    cwd = str(repo) if repo else None
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=cwd, timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        _fail(f"无法执行 git：{exc}")
    if r.returncode != 0:
        _fail(f"当前目录不是 git 仓库或无 origin remote：{(r.stderr or '').strip()}")
    project = normalize_project(r.stdout)
    if not project:
        _fail(f"无法从 origin remote 归一化项目路径：{r.stdout.strip()}")
    return project


def _header_of(raw: str) -> str:
    """取出文件开头的注释/空行块，用于写回时原样保留。"""
    kept: list[str] = []
    for line in raw.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            kept.append(line)
        else:
            break
    return "".join(kept)


def load_config() -> tuple[dict, str]:
    """读取配置，返回 (data, header)。文件缺失时给出最小骨架。"""
    if not CONFIG_PATH.is_file():
        return (
            {"schema_version": 1, "branch_strategy": {"default": None, "projects": []}},
            MINIMAL_HEADER,
        )
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        _fail(f"{CONFIG_PATH} 解析失败：{exc}")
    if data is None:
        data = {}
    if not isinstance(data, dict):
        _fail(f"{CONFIG_PATH} 顶层必须是映射，实际为 {type(data).__name__}")
    data.setdefault("schema_version", 1)
    bs = data.setdefault("branch_strategy", {})
    if not isinstance(bs, dict):
        _fail("branch_strategy 必须是映射")
    bs.setdefault("default", None)
    if bs.get("projects") is None:
        bs["projects"] = []
    if not isinstance(bs["projects"], list):
        _fail("branch_strategy.projects 必须是列表")
    return data, _header_of(raw)


def save_config(data: dict, header: str) -> None:
    """写回配置：保留原文件头注释块，数据区由 safe_dump 生成（sort_keys=False 保序）。

    用 open() 而非 Path.write_text()：后者的 newline 参数是 Python 3.10+ 才有，
    本 Skill 声明支持 3.8+。
    """
    body = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + body)


def resolve(data: dict, project: str) -> tuple[str | None, str | None]:
    """解析项目策略，返回 (strategy, reason)。精确匹配优先，其次 default。"""
    for entry in data["branch_strategy"]["projects"]:
        if isinstance(entry, dict) and entry.get("project") == project:
            return entry.get("strategy"), entry.get("reason")
    default = data["branch_strategy"].get("default")
    if default:
        return default, None
    return None, None


def cmd_get(args: argparse.Namespace) -> None:
    """输出当前（或指定）仓库的生效策略；未解析时打印 UNSET 并退出 3。"""
    project = args.project or current_project(Path(args.repo) if args.repo else None)
    data, _ = load_config()
    strategy, reason = resolve(data, project)
    if not strategy:
        print("UNSET")
        print(f"# 项目 {project} 未登记分支策略，且 default 为空。", file=sys.stderr)
        print(f"# MUST 对话式确认后写入：python {Path(__file__).name} set <策略> "
              f"--project {project} --reason '<理由>'", file=sys.stderr)
        print(f"# 可选策略：{', '.join(STRATEGIES)}", file=sys.stderr)
        print(f"# 若用户明确表示不适用任何策略：set {NONE_VALUE} --project {project}",
              file=sys.stderr)
        sys.exit(EXIT_UNSET)
    print(strategy)
    if strategy == NONE_VALUE:
        print(f"# 项目 {project} 已显式登记为不适用任何分支策略：", file=sys.stderr)
        print("# 分支与 MR 目标完全按用户当次意图控制，MUST NOT 自行套用 "
              "git-flow / assembly-flow / github-flow。", file=sys.stderr)
    if args.verbose:
        print(f"# project={project}", file=sys.stderr)
        if reason:
            print(f"# reason={reason}", file=sys.stderr)


def cmd_set(args: argparse.Namespace) -> None:
    """写入策略：--default 改兜底，否则按项目 upsert。"""
    strategy = args.strategy
    data, header = load_config()

    if args.default:
        if strategy.lower() in CLEAR_VALUES:
            data["branch_strategy"]["default"] = None
            save_config(data, header)
            print("default 已清空（未匹配项目时将返回 UNSET）")
            return
        if strategy not in STRATEGIES:
            _fail(f"未知策略 '{strategy}'，可选：{', '.join(STRATEGIES)}")
        data["branch_strategy"]["default"] = strategy
        save_config(data, header)
        print(f"default = {strategy}")
        return

    if strategy not in PROJECT_VALUES:
        _fail(f"未知策略 '{strategy}'，可选：{', '.join(PROJECT_VALUES)}"
              f"（none 表示该项目不适用任何分支策略）")

    project = args.project or current_project(Path(args.repo) if args.repo else None)
    projects = data["branch_strategy"]["projects"]
    for entry in projects:
        if isinstance(entry, dict) and entry.get("project") == project:
            entry["strategy"] = strategy
            if args.reason:
                entry["reason"] = args.reason
            elif "reason" not in entry:
                print(f"WARN: {project} 缺少 reason，建议补 --reason 记录选型理由",
                      file=sys.stderr)
            save_config(data, header)
            print(f"{project} = {strategy}" + (f"  ({entry.get('reason')})"
                                              if entry.get("reason") else ""))
            return

    entry = {"project": project, "strategy": strategy}
    if args.reason:
        entry["reason"] = args.reason
    else:
        print(f"WARN: {project} 缺少 reason，建议补 --reason 记录选型理由", file=sys.stderr)
    projects.append(entry)
    save_config(data, header)
    print(f"{project} = {strategy}" + (f"  ({args.reason})" if args.reason else ""))


def cmd_remove(args: argparse.Namespace) -> None:
    """删除某项目的登记，使其回落到 default（未设 default 则回到 UNSET）。"""
    project = args.project or current_project(Path(args.repo) if args.repo else None)
    data, header = load_config()
    projects = data["branch_strategy"]["projects"]
    kept = [e for e in projects
            if not (isinstance(e, dict) and e.get("project") == project)]
    if len(kept) == len(projects):
        print(f"{project} 未登记，无需删除")
        return
    data["branch_strategy"]["projects"] = kept
    save_config(data, header)
    fallback = data["branch_strategy"].get("default")
    print(f"已删除 {project} 的登记"
          + (f"，现回落到 default={fallback}" if fallback else "，现为 UNSET"))


def cmd_list(_args: argparse.Namespace) -> None:
    """列出兜底策略与全部已登记项目。"""
    data, _ = load_config()
    bs = data["branch_strategy"]
    print(f"config: {CONFIG_PATH}")
    print(f"可选策略: {', '.join(STRATEGIES)}")
    print(f"default: {bs.get('default') or '(未设置 → 未登记项目返回 UNSET)'}")
    projects = bs.get("projects") or []
    if not projects:
        print("projects: (空)")
        return
    print(f"projects: {len(projects)} 条")
    for entry in projects:
        if not isinstance(entry, dict):
            print(f"  - (格式异常，已跳过) {entry!r}")
            continue
        reason = entry.get("reason")
        print(f"  - {entry.get('project')}: {entry.get('strategy')}"
              + (f"\n      reason: {reason}" if reason else ""))


def main() -> None:
    """入口：分发 get / set / switch / list 子命令。"""
    parser = argparse.ArgumentParser(
        description="Resolve or record the branch strategy for a repository")
    sub = parser.add_subparsers(dest="command", required=True)

    p_get = sub.add_parser("get", help="解析生效策略（未登记输出 UNSET，退出码 3）")
    p_get.add_argument("--project", help="归一化项目路径，缺省由 origin remote 推导")
    p_get.add_argument("--repo", help="本地仓库路径，缺省为当前目录")
    p_get.add_argument("-v", "--verbose", action="store_true", help="附带 project/reason")
    p_get.set_defaults(func=cmd_get)

    for name, help_text in (("set", "写入策略"), ("switch", "切换策略（set 的别名）")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("strategy", help=f"策略 ID：{', '.join(PROJECT_VALUES)}；"
                                       f"none 作项目级登记表示不适用任何策略，"
                                       f"配合 --default 时表示清空兜底")
        p.add_argument("--project", help="归一化项目路径，缺省由 origin remote 推导")
        p.add_argument("--repo", help="本地仓库路径，缺省为当前目录")
        p.add_argument("--default", action="store_true", help="设置未匹配时的兜底策略")
        p.add_argument("--reason", help="选型理由（写入 reason 字段，dump 不会丢失）")
        p.set_defaults(func=cmd_set)

    p_remove = sub.add_parser("remove", help="删除项目登记，回落到 default")
    p_remove.add_argument("--project", help="归一化项目路径，缺省由 origin remote 推导")
    p_remove.add_argument("--repo", help="本地仓库路径，缺省为当前目录")
    p_remove.set_defaults(func=cmd_remove)

    p_list = sub.add_parser("list", help="列出兜底策略与已登记项目")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
