"""脚本共享配置——GitLab 凭据的唯一读写入口。

凭据唯一合法位置：``<skill-root>/config/.env``

三级加载顺序（先命中先用）：

    1. 进程环境变量
    2. ``<skill-root>/config/.env``
    3. 引导配置 —— 由 ``check`` / ``setup`` 子命令驱动，见下方 CLI

同目录的 ``config/settings.yaml`` 是**入库共享的非敏感配置**（分支策略等）；
凭据禁止写进那里，反之亦然。

CLI::

    python config.py check                     # 是否就绪；退出码 0 就绪 / 3 未配置
    python config.py setup                     # 交互式录入并写入（需真实终端，Agent 代跑无效）
    python config.py setup --from-env          # 从已存在的环境变量取值并写入
    python config.py setup --from-env --url-var MY_URL --token-var MY_TOKEN

退出码：``0`` 成功 / ``2`` 校验或写入失败 / ``3`` 凭据未配置（需要引导）。

安全约束：本模块的任何输出**都不打印 token 内容**，只报告是否存在与长度。
``setup`` 不接受 ``--token <值>`` 这类命令行参数——命令行参数会进入 shell history、
进程列表与调用方的日志，凭据一经出现在那里就应视为已泄露。
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import urllib.error
import urllib.request

EXIT_READY = 0
EXIT_ERROR = 2
EXIT_UNSET = 3


def configure_utf8_stdio() -> None:
    """把本进程的 stdout/stderr 固定为 UTF-8。

    为什么需要：Windows 控制台默认 GBK，含中文的提示会乱码；更麻烦的是父进程用
    ``subprocess.run(..., text=True)`` 捕获时同样按 locale(GBK) 解码本脚本输出的
    UTF-8 字节，reader 线程抛 ``UnicodeDecodeError`` 后 stdout/stderr 直接变成
    ``None``——调用方看不到任何错误信息。

    本函数只解决「输出侧是合法 UTF-8」这一半；**捕获方仍必须显式传
    ``encoding="utf-8"``**，否则问题在父进程侧、脚本无法替代。

    模块导入时自动执行一次；不 import 本模块的脚本（如 env_check.py）若无中文输出
    则无需调用。
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


configure_utf8_stdio()

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(SKILL_ROOT, "config", ".env")

REQUIRED_KEYS = ("GITLAB_URL", "GITLAB_TOKEN")

_dotenv_loaded = False


def env_file_path() -> str:
    """凭据文件的唯一路径：``<skill-root>/config/.env``。"""
    return ENV_PATH


def _load_dotenv() -> None:
    """解析 config/.env 并注入 os.environ（仅首次调用生效）。

    格式：每行 ``KEY=VALUE``，忽略空行与 ``#`` 注释行。
    已存在的环境变量不被覆盖——环境变量优先级高于 .env。
    """
    global _dotenv_loaded
    _dotenv_loaded = True

    if not os.path.isfile(ENV_PATH):
        return

    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value.strip()


def resolve(key: str) -> str | None:
    """按「环境变量 → config/.env」顺序取一个键的值。"""
    val = os.environ.get(key)
    if val:
        return val
    if not _dotenv_loaded:
        _load_dotenv()
        val = os.environ.get(key)
        if val:
            return val
    return os.environ.get(key)


def _guide(missing: list[str]) -> None:
    """打印缺失凭据的引导指引（不含任何凭据内容）。"""
    print(f"ERROR: 缺少必需的配置项: {', '.join(missing)}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"凭据唯一合法位置：{ENV_PATH}", file=sys.stderr)
    print(file=sys.stderr)
    print("两种补齐方式（任选其一）：", file=sys.stderr)
    print("  A. 在你自己的终端运行（需要交互输入，Agent 代跑无效）：", file=sys.stderr)
    print(f"     python {os.path.join(SKILL_ROOT, 'scripts', 'config.py')} setup",
          file=sys.stderr)
    print("  B. 先导出环境变量，再让 Agent 落盘（值不经过命令行）：", file=sys.stderr)
    print("     export GITLAB_URL=... GITLAB_TOKEN=...   # Windows 用 set", file=sys.stderr)
    print(f"     python {os.path.join(SKILL_ROOT, 'scripts', 'config.py')} setup --from-env",
          file=sys.stderr)


# ── 供其他脚本复用的旧接口（签名与行为保持兼容）──────────────────────────

def require_env(key: str) -> str:
    """获取必需配置项，按「环境变量 → config/.env → 引导」三级解析。"""
    val = resolve(key)
    if val:
        return val
    _guide([key])
    sys.exit(1)


def get_gitlab_config() -> tuple[str, str]:
    """读取 GitLab 凭据，返回 ``(url, token)``。

    项目路径不在此处配置：由各调用方通过 ``--project`` 参数传入。
    """
    missing = [k for k in REQUIRED_KEYS if not resolve(k)]
    if missing:
        _guide(missing)
        sys.exit(1)
    return os.environ["GITLAB_URL"], os.environ["GITLAB_TOKEN"]


# ── 凭据落盘与自检 ─────────────────────────────────────────────────────

def _verify_connection(url: str, token: str) -> tuple[bool, str]:
    """用 GET /api/v4/user 验证凭据，返回 (是否可用, 说明)。"""
    api = url.rstrip("/") + "/api/v4/user"
    req = urllib.request.Request(api, headers={"PRIVATE-TOKEN": token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            return True, f"HTTP {resp.status}，用户 {body.get('username', '?')}"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"HTTP {exc.code}：token 无效、已过期或 scope 不足（需 api）"
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"无法连接：{exc.reason}（检查 GITLAB_URL 拼写与网络）"
    except (TimeoutError, OSError) as exc:
        return False, f"连接失败：{exc}"


def _warn_if_not_ignored() -> None:
    """确认凭据文件被 .gitignore 排除；未排除时给出必须补规则的警告。"""
    try:
        r = subprocess.run(["git", "check-ignore", "-q", "--", ENV_PATH],
                           cwd=SKILL_ROOT, capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"WARN: 无法执行 git check-ignore 验证保护：{exc}", file=sys.stderr)
        return
    if r.returncode != 0:
        print(f"WARN: {ENV_PATH} 未被 .gitignore 排除！写入真实凭据前必须补规则，"
              "否则一次 `git add` 就会把 token 提交进仓库。", file=sys.stderr)
        return
    print(f"[ok] 已被 .gitignore 排除：{ENV_PATH}")


def _write_env(values: dict[str, str]) -> None:
    """写入 config/.env：保留文件中已有的其他键，只更新给定键。"""
    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)

    lines: list[str] = []
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f]

    remaining = dict(values)
    out: list[str] = []
    for ln in lines:
        key = ln.split("=", 1)[0].strip() if "=" in ln else ""
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(ln)
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    with open(ENV_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")

    try:
        os.chmod(ENV_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 0600；Windows 上为尽力而为
    except OSError:
        pass
    print(f"[ok] 已写入 {ENV_PATH}")


def _mask(key: str, value: str) -> str:
    """脱敏描述一个键：只显示长度，不显示任何内容字符。"""
    return f"{key}: 已设置（{len(value)} 字符）" if value else f"{key}: 空"


def _read_interactively() -> tuple[str, str]:
    """从终端采集 (url, token)。

    可靠性说明：Windows / Git Bash 下把 stdin 重定向到 ``/dev/null`` 时
    ``isatty()`` 仍可能返回 True，所以不能只靠 tty 判断——真正的兜底是捕获
    ``EOFError``（输入流耗尽即视为"没有人在旁边输入"，通常是 Agent 代跑）。
    """
    if not sys.stdin.isatty():
        print("ERROR: 交互式录入需要真实终端，当前 stdin 不是 tty。", file=sys.stderr)
        print("       Agent 代跑会失败——请由用户在自己的终端执行本命令，"
              "或先导出环境变量后用 `setup --from-env`。", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    try:
        url = input("GitLab 地址（如 https://gitlab.example.com）：").strip()
        try:
            # getpass 而非 input：input() 会让 token 在终端回显，被旁人看到或被录屏捕获
            import getpass
            token = getpass.getpass(
                "GitLab Personal Access Token（需 api scope，输入不回显）：").strip()
        except (ImportError, OSError) as exc:
            # 仅当 getpass 本身不可用时才降级；EOFError 不在这里吞，交给外层统一处理
            print(f"WARN: 无法隐藏回显（{type(exc).__name__}），改用普通输入——"
                  "请确认周围无人可看到你的屏幕。", file=sys.stderr)
            token = input("GitLab Personal Access Token（需 api scope）：").strip()
    except (EOFError, KeyboardInterrupt):
        _abort_no_input()   # 内部 sys.exit，不会返回
        raise               # 仅为可读性标明不可达，实际不会执行

    return url, token


def _abort_no_input() -> None:
    """输入流耗尽：判定为无人交互（多为 Agent 代跑），给出可执行的替代路径。"""
    print("ERROR: 没有可读输入（stdin 已耗尽）——本命令需要人当场输入凭据。",
          file=sys.stderr)
    print("请改用下列任一方式：", file=sys.stderr)
    print("  A. 用户在自己的终端直接运行：python scripts/config.py setup", file=sys.stderr)
    print("  B. 用户导出环境变量后，Agent 代跑落盘（值不经过命令行）：", file=sys.stderr)
    print("     python scripts/config.py setup --from-env", file=sys.stderr)
    sys.exit(EXIT_ERROR)


# ── CLI 子命令 ─────────────────────────────────────────────────────────

def cmd_check(_args: argparse.Namespace) -> None:
    """报告凭据是否就绪；未就绪时退出码 3，调用方据此触发引导。"""
    _load_dotenv()
    missing = [k for k in REQUIRED_KEYS if not os.environ.get(k)]
    print(f"凭据文件：{ENV_PATH}"
          + ("" if os.path.isfile(ENV_PATH) else "（不存在）"))
    for key in REQUIRED_KEYS:
        print("  " + _mask(key, os.environ.get(key, "")))
    if missing:
        print(f"UNSET: 缺少 {', '.join(missing)}", file=sys.stderr)
        _guide(missing)
        sys.exit(EXIT_UNSET)
    print("[ok] 凭据就绪")
    sys.exit(EXIT_READY)


def cmd_setup(args: argparse.Namespace) -> None:
    """采集凭据 → 验证连接 → 写入 config/.env → 自检 gitignore。

    取值来源二选一，都**不经命令行传值**：
      --from-env      从已存在的环境变量读取（Agent 可代跑）
      默认（交互式）  input() 提示，需真实终端（Agent 代跑无效）
    """
    if args.from_env:
        url = os.environ.get(args.url_var, "").strip()
        token = os.environ.get(args.token_var, "").strip()
        if not url or not token:
            print(f"ERROR: 环境变量 {args.url_var} / {args.token_var} 未设置或为空。"
                  " 请先在你的终端导出它们，或改用交互式 setup。", file=sys.stderr)
            sys.exit(EXIT_ERROR)
    else:
        url, token = _read_interactively()

    if not url.startswith(("http://", "https://")):
        print(f"ERROR: GITLAB_URL 看起来不是合法地址：{url}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    if not token:
        print("ERROR: token 为空。", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    ok, detail = _verify_connection(url, token)
    if not ok:
        print(f"ERROR: 连接验证失败：{detail}", file=sys.stderr)
        print("未写入任何文件。请确认地址与 token 后重试。", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    print(f"[ok] 连接验证通过：{detail}")

    _write_env({"GITLAB_URL": url, "GITLAB_TOKEN": token})
    _warn_if_not_ignored()
    print("提醒：该文件含敏感凭据，不要粘贴到日志、issue 或对话中。")


def main() -> None:
    """入口：分发 check / setup 子命令。"""
    parser = argparse.ArgumentParser(
        description="GitLab 凭据读写——唯一位置 <skill-root>/config/.env")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="凭据是否就绪（未就绪退出码 3）")
    p_check.set_defaults(func=cmd_check)

    p_setup = sub.add_parser("setup", help="采集凭据、验证连接并写入 config/.env")
    p_setup.add_argument("--from-env", action="store_true",
                         help="从环境变量取值（Agent 可代跑；默认走交互式，需真实终端）")
    p_setup.add_argument("--url-var", default="GITLAB_URL",
                         help="配合 --from-env：URL 所在变量名（只传名字，不传值）")
    p_setup.add_argument("--token-var", default="GITLAB_TOKEN",
                         help="配合 --from-env：token 所在变量名（只传名字，不传值）")
    p_setup.set_defaults(func=cmd_setup)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
