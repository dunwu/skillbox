#!/usr/bin/env python3
"""Environment prerequisite check for gitlab-ops Skill.

Checks: python3, Git >= 2.41, glab CLI.
Reports missing or outdated tools and offers auto-install guidance.

Usage:
    python env_check.py              # check only
    python env_check.py --install    # attempt auto-install for missing tools
    python env_check.py --json       # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from typing import Any

MIN_GIT_VERSION = (2, 41, 0)

GLAB_DOWNLOAD_URL = (
    "https://gitlab.com/gitlab-org/cli/-/releases/permalink/latest"
    "/downloads/glab_linux_amd64.tar.gz"
)


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """以列表参数安全执行命令，返回 (returncode, stdout, stderr)。"""
    try:
        r = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return -1, "", "timeout or not found"


def _parse_version(text: str) -> tuple[int, ...] | None:
    """从版本字符串（如 '2.52.0'）中提取 (major, minor, patch)。"""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def _os_family() -> str:
    """返回当前操作系统族：'windows'、'macos' 或 'linux'。"""
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return "linux"


def _has_command(cmd: str) -> bool:
    """检查命令是否存在于 PATH 中。"""
    if _os_family() == "windows":
        rc, _, _ = _run(["where", cmd])
    else:
        rc, _, _ = _run([cmd, "--version"])
    return rc == 0


def check_python() -> dict[str, Any]:
    """检查 python3 是否可用，返回检测结果字典。"""
    for cmd in ["python3", "python"]:
        rc, out, _ = _run([cmd, "--version"])
        if rc == 0 and out:
            ver = _parse_version(out)
            if ver:
                return {
                    "name": "python3", "ok": True,
                    "version": ".".join(str(v) for v in ver), "cmd": cmd,
                }
    return {"name": "python3", "ok": False, "version": None, "cmd": None}


def check_git() -> dict[str, Any]:
    """检查 git 是否可用且版本 >= MIN_GIT_VERSION。"""
    rc, out, _ = _run(["git", "--version"])
    if rc != 0:
        return {"name": "git", "ok": False, "version": None, "min_version": None, "too_old": False}
    ver = _parse_version(out)
    if ver is None:
        return {"name": "git", "ok": False, "version": None, "min_version": None, "too_old": False}
    ver_str = ".".join(str(v) for v in ver)
    min_str = ".".join(str(v) for v in MIN_GIT_VERSION)
    too_old = ver < MIN_GIT_VERSION
    return {
        "name": "git", "ok": not too_old,
        "version": ver_str, "min_version": min_str, "too_old": too_old,
    }


def check_glab() -> dict[str, Any]:
    """检查 glab CLI 是否可用。"""
    rc, out, _ = _run(["glab", "version"])
    if rc != 0:
        return {"name": "glab", "ok": False, "version": None}
    ver = _parse_version(out)
    ver_str = ".".join(str(v) for v in ver) if ver else out
    return {"name": "glab", "ok": True, "version": ver_str}


def install_instructions(name: str, os_family: str) -> list[str]:
    """返回缺失工具的人工安装指引（按操作系统区分）。"""
    table = {
        ("python3", "windows"): [
            "winget install Python.Python.3.12",
            "# or download from https://www.python.org/downloads/",
        ],
        ("python3", "macos"): [
            "brew install python@3.12",
            "# or download from https://www.python.org/downloads/",
        ],
        ("python3", "linux"): [
            "sudo apt install python3   # Debian/Ubuntu",
            "sudo dnf install python3   # Fedora/RHEL",
            "sudo pacman -S python      # Arch",
        ],
        ("git", "windows"): [
            "winget install Git.Git",
            "# or download from https://git-scm.com/download/win",
        ],
        ("git", "macos"): [
            "brew install git",
            "# or: xcode-select --install",
        ],
        ("git", "linux"): [
            "sudo apt install git   # Debian/Ubuntu",
            "sudo dnf install git   # Fedora/RHEL",
            "sudo pacman -S git     # Arch",
        ],
        ("glab", "windows"): [
            "winget install GitLab.GLab",
            "# or: scoop install glab",
        ],
        ("glab", "macos"): [
            "brew install glab",
        ],
        ("glab", "linux"): [
            f"# See {GLAB_DOWNLOAD_URL}",
            "# Download, verify checksum, then extract to /usr/local/bin",
        ],
    }
    return table.get((name, os_family), ["Manual install required — check official docs."])


def auto_install(name: str, os_family: str) -> tuple[bool, str]:
    """尝试自动安装缺失工具，返回 (是否成功, 结果消息)。"""
    commands: dict[tuple[str, str], list[str]] = {
        ("python3", "windows"): ["winget", "install", "Python.Python.3.12",
                                 "--accept-source-agreements", "--accept-package-agreements"],
        ("python3", "macos"): ["brew", "install", "python@3.12"],
        ("python3", "linux"): ["sudo", "apt", "install", "-y", "python3"],
        ("git", "windows"): ["winget", "install", "Git.Git",
                             "--accept-source-agreements", "--accept-package-agreements"],
        ("git", "macos"): ["brew", "install", "git"],
        ("git", "linux"): ["sudo", "apt", "install", "-y", "git"],
        ("glab", "windows"): ["winget", "install", "GitLab.GLab",
                              "--accept-source-agreements", "--accept-package-agreements"],
        ("glab", "macos"): ["brew", "install", "glab"],
    }
    cmd = commands.get((name, os_family))
    if not cmd:
        return False, f"No auto-install for {name} on {os_family}. Install manually."
    rc, out, err = _run(cmd, timeout=120)
    if rc == 0:
        return True, f"{name} installed successfully."
    return False, f"Install failed (rc={rc}): {err or out}"


def main() -> None:
    """入口：检查前置依赖，可选自动安装缺失工具。"""
    parser = argparse.ArgumentParser(description="gitlab-ops environment check")
    parser.add_argument("--install", action="store_true",
                        help="attempt auto-install missing tools")
    parser.add_argument("--json", action="store_true",
                        help="output as JSON")
    args = parser.parse_args()

    os_family = _os_family()
    checks = [check_python(), check_git(), check_glab()]

    missing = [c for c in checks if not c["ok"]]
    outdated = [c for c in checks if c.get("too_old")]

    if args.json:
        result = {
            "os": os_family,
            "checks": checks,
            "all_ok": len(missing) == 0 and len(outdated) == 0,
            "missing": [c["name"] for c in missing],
            "outdated": [c["name"] for c in outdated],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["all_ok"] else 1)

    print(f"OS: {os_family} ({platform.system()} {platform.release()})")
    print()

    all_ok = True
    for c in checks:
        if c["ok"]:
            print(f"  [OK]   {c['name']} {c.get('version', '')}")
        elif c.get("too_old"):
            print(f"  [WARN] {c['name']} {c['version']} < {c['min_version']} (too old)")
            all_ok = False
        else:
            print(f"  [FAIL] {c['name']} not found")
            all_ok = False

    print()

    if all_ok:
        print("All prerequisites satisfied.")
        sys.exit(0)

    targets = missing + outdated
    names = [c["name"] for c in targets]
    print(f"Missing or outdated: {', '.join(names)}")
    print()

    if args.install:
        for c in targets:
            name = c["name"]
            print(f"Installing {name}...")
            ok, msg = auto_install(name, os_family)
            print(f"  {msg}")
            if not ok:
                for line in install_instructions(name, os_family):
                    print(f"    {line}")
            print()
    else:
        print("Install instructions:")
        print()
        for c in targets:
            name = c["name"]
            print(f"  {name}:")
            for line in install_instructions(name, os_family):
                print(f"    {line}")
            print()
        print("Re-run with --install to attempt auto-install.")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
