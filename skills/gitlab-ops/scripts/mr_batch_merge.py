#!/usr/bin/env python3
"""批量合并开放 MR——合并所有匹配可选过滤条件的开放 MR。

用法::

    python mr_batch_merge.py [--label LABEL] [--author AUTHOR] [--dry-run]

环境变量:
    GITLAB_URL      GitLab 实例地址（必需）
    GITLAB_TOKEN    个人访问令牌（必需）
    GITLAB_PROJECT  项目路径，如 group/project（必需）
"""

import argparse
import logging
import subprocess
import sys

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def merge_mr(client: GitLabClient, iid: int, squash: bool, remove_source: bool) -> bool:
    """通过 REST API 合并单个 MR。"""
    data: dict = {}
    if squash:
        data["squash"] = True
    if remove_source:
        data["should_remove_source_branch"] = True
    status, _ = client.put(
        f"/projects/{client.project_encoded}/merge_requests/{iid}/merge",
        data,
    )
    return status == 200


def main() -> None:
    """入口：列出开放 MR 并可选批量合并。"""
    parser = argparse.ArgumentParser(description="Batch merge open MRs")
    parser.add_argument("--label", help="Filter by label")
    parser.add_argument("--author", help="Filter by author username")
    parser.add_argument("--dry-run", action="store_true", help="List MRs without merging")
    parser.add_argument("--squash", action="store_true", help="Use squash merge")
    parser.add_argument("--remove-source", action="store_true", help="Delete source branch after merge")
    args = parser.parse_args()

    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    client = GitLabClient(url, token, project)

    query = "/merge_requests?state=opened"
    if args.label:
        query += f"&labels={args.label}"
    if args.author:
        query += f"&author_username={args.author}"

    mrs = client.get_all(query)
    if not mrs:
        logger.info("No open MRs found.")
        return

    logger.info("Found %d open MR(s):", len(mrs))
    for mr in mrs:
        logger.info("  !%d: %s", mr["iid"], mr["title"])

    if args.dry_run:
        logger.info("\n[DRY RUN] No merges performed.")
        return

    merged, failed = 0, 0
    for mr in mrs:
        iid = mr["iid"]
        logger.info("\nMerging !%d...", iid)
        if merge_mr(client, iid, args.squash, args.remove_source):
            merged += 1
            logger.info("  OK: !%d merged", iid)
        else:
            failed += 1
            logger.info("  FAIL: !%d", iid)

    logger.info("\nDone: %d merged, %d failed", merged, failed)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
