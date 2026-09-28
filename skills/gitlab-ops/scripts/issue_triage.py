#!/usr/bin/env python3
"""分拣开放 Issue——列出、打标签并可选指派。

用法::

    python issue_triage.py [--no-label] [--assign USERNAME]

环境变量:
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT（必需）
"""

from __future__ import annotations

import argparse
import logging
import sys

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def resolve_user_id(client: GitLabClient, username: str) -> int | None:
    """将用户名解析为 GitLab 用户 ID。"""
    status, users = client.get(f"/users?username={username}")
    if status == 200 and isinstance(users, list) and users:
        return users[0]["id"]
    return None


def main() -> None:
    """入口：列出开放 Issue，可选过滤无标签项并批量指派。"""
    parser = argparse.ArgumentParser(description="Triage open issues")
    parser.add_argument("--no-label", action="store_true",
                        help="Only show issues without labels")
    parser.add_argument("--assign", help="Assign all listed issues to username")
    args = parser.parse_args()

    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    client = GitLabClient(url, token, project)

    issues = client.get_all("/issues?state=opened")

    if args.no_label:
        issues = [i for i in issues if not i.get("labels")]

    if not issues:
        logger.info("No issues to triage.")
        return

    logger.info("%-6s %-50s %-20s %s", "IID", "Title", "Labels", "Author")
    logger.info("-" * 100)
    for issue in issues:
        labels = ", ".join(issue.get("labels", [])) or "(none)"
        author = issue.get("author", {}).get("username", "?")
        logger.info("#%-5d %-50s %-20s %s", issue["iid"], issue["title"], labels, author)

    if args.assign:
        user_id = resolve_user_id(client, args.assign)
        if user_id is None:
            logger.error("User '%s' not found", args.assign)
            sys.exit(1)

        logger.info("\nAssigning %d issue(s) to @%s...", len(issues), args.assign)
        for issue in issues:
            iid = issue["iid"]
            status, _ = client.put(
                f"/projects/{client.project_encoded}/issues/{iid}",
                {"assignee_ids": [user_id]},
            )
            tag = "OK" if status == 200 else f"FAIL (HTTP {status})"
            logger.info("  #%d: %s", iid, tag)


if __name__ == "__main__":
    main()
