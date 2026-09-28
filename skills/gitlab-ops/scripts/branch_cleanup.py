#!/usr/bin/env python3
"""清理已合并的本地分支——列出并可选删除已合入目标分支的分支。

用法::

    python branch_cleanup.py [--target BRANCH] [--dry-run] [--remote]

本脚本操作当前目录下的本地 git 仓库。
使用 ``--remote`` 时通过 GitLab API 清理远端分支。

环境变量（--remote 模式必需）:
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")


def run_git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """以列表参数安全执行 git 命令（不使用 shell，防止注入）。"""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=cwd, timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_branch_list(output: str) -> list[str]:
    """解析 git branch 输出，正确处理 '* ' 前缀。"""
    branches = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("* "):
            line = line[2:]
        if line:
            branches.append(line)
    return branches


def get_protected_branches(client: GitLabClient) -> set[str]:
    """从 GitLab API 获取受保护分支名称集合。"""
    status, data = client.get(f"/projects/{client.project_encoded}/protected_branches")
    if status == 200 and isinstance(data, list):
        return {b["name"] for b in data}
    return {"main", "master", "develop"}


def main() -> None:
    """入口：列出并可选删除已合并分支（本地或远端）。"""
    parser = argparse.ArgumentParser(description="Clean up merged branches")
    parser.add_argument("--target", default="main",
                        help="Target branch (default: main)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List branches without deleting")
    parser.add_argument("--remote", action="store_true",
                        help="Clean remote branches via GitLab API")
    args = parser.parse_args()

    if args.remote:
        url = require_env("GITLAB_URL")
        token = require_env("GITLAB_TOKEN")
        project = require_env("GITLAB_PROJECT")
        client = GitLabClient(url, token, project)

        status, branches = client.get(
            f"/repository/branches?merged={args.target}"
        )
        if status != 200 or not isinstance(branches, list):
            logger.error("Cannot list branches (HTTP %d)", status)
            sys.exit(1)

        protected = get_protected_branches(client)
        to_delete = [b for b in branches if b["name"] not in protected]

        if not to_delete:
            logger.info("No merged remote branches to clean (target: %s)", args.target)
            return

        logger.info("Found %d merged remote branch(es):", len(to_delete))
        for b in to_delete:
            logger.info("  %s", b["name"])

        if args.dry_run:
            logger.info("\n[DRY RUN] No branches deleted.")
            return

        deleted = 0
        for b in to_delete:
            from urllib.parse import quote
            name_encoded = quote(b["name"], safe="")
            st, _ = client.delete(
                f"/projects/{client.project_encoded}/repository/branches/{name_encoded}"
            )
            if st in (200, 204):
                deleted += 1
                logger.info("  Deleted: %s", b["name"])
            else:
                logger.info("  Failed:  %s (HTTP %d)", b["name"], st)
        logger.info("\nDone: %d branch(es) deleted", deleted)
    else:
        rc, out, _ = run_git(["branch", "--merged", args.target])
        if rc != 0:
            logger.error("git branch --merged failed")
            sys.exit(1)

        protected = {"main", "master", "develop", args.target}
        branches = parse_branch_list(out)
        to_delete = [b for b in branches if b not in protected]

        if not to_delete:
            logger.info("No merged local branches to clean (target: %s)", args.target)
            return

        logger.info("Found %d merged local branch(es):", len(to_delete))
        for b in to_delete:
            logger.info("  %s", b)

        if args.dry_run:
            logger.info("\n[DRY RUN] No branches deleted.")
            return

        deleted = 0
        for b in to_delete:
            if not BRANCH_NAME_RE.match(b):
                logger.warning("  Skipping unsafe branch name: %s", b)
                continue
            rc, _, err = run_git(["branch", "-d", b])
            if rc == 0:
                deleted += 1
                logger.info("  Deleted: %s", b)
            else:
                logger.info("  Failed:  %s (%s)", b, err)
        logger.info("\nDone: %d branch(es) deleted", deleted)


if __name__ == "__main__":
    main()
