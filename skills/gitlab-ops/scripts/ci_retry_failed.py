#!/usr/bin/env python3
"""重试失败的 CI 任务——查找近期流水线中的失败任务并重试。

用法::

    python ci_retry_failed.py [--ref BRANCH] [--max-pipelines N] [--dry-run]

环境变量:
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT（必需）
"""

import argparse
import logging
import subprocess
import sys

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """入口：查找失败的流水线并通过 glab CLI 重试失败任务。"""
    parser = argparse.ArgumentParser(description="Retry failed CI jobs")
    parser.add_argument("--ref", default="main", help="Branch ref (default: main)")
    parser.add_argument("--max-pipelines", type=int, default=5,
                        help="Max pipelines to scan (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List failed jobs without retrying")
    args = parser.parse_args()

    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    client = GitLabClient(url, token, project)

    status, pipelines = client.get(
        f"/pipelines?ref={args.ref}&status=failed&per_page={args.max_pipelines}"
    )
    if status != 200 or not isinstance(pipelines, list) or not pipelines:
        logger.info("No failed pipelines found for ref '%s'.", args.ref)
        return

    logger.info("Found %d failed pipeline(s):", len(pipelines))
    retried = 0
    for pipeline in pipelines:
        pid = pipeline["id"]
        logger.info("\nPipeline #%d (%s, %s)", pid, pipeline["ref"], pipeline["created_at"])

        status2, jobs = client.get(f"/pipelines/{pid}/jobs?scope=failed")
        if status2 != 200 or not isinstance(jobs, list):
            logger.info("  Could not list jobs: HTTP %d", status2)
            continue

        for job in jobs:
            logger.info("  Job #%d: %s (%s)", job["id"], job["name"], job["stage"])

        if args.dry_run:
            continue

        result = subprocess.run(
            ["glab", "ci", "retry", str(pid), "-R", project],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            retried += 1
            logger.info("  Retried pipeline #%d", pid)
        else:
            logger.info("  Failed to retry #%d: %s", pid, result.stderr.strip())

    logger.info("\nDone: %d pipeline(s) retried", retried)


if __name__ == "__main__":
    main()
