#!/usr/bin/env python3
"""仓库审计——汇总项目设置、分支、MR 和 CI 状态。

用法::

    python repo_audit.py [--output json|text]

环境变量:
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT（必需）
"""

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def fetch_parallel(client: GitLabClient, paths: dict[str, str]) -> dict[str, object]:
    """并行请求多个 API 路径。"""
    results: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        futures = {pool.submit(client.get, path): key for key, path in paths.items()}
        for future in as_completed(futures):
            key = futures[future]
            status, data = future.result()
            results[key] = data if status == 200 else None
    return results


def main() -> None:
    """入口：并行获取项目元数据并输出审计报告。"""
    parser = argparse.ArgumentParser(description="Repository audit report")
    parser.add_argument("--output", choices=["json", "text"], default="text")
    args = parser.parse_args()

    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    client = GitLabClient(url, token, project)

    status, proj = client.get(f"/projects/{client.project_encoded}")
    if status != 200:
        logger.error("Cannot access project (HTTP %d)", status)
        sys.exit(1)

    data = fetch_parallel(client, {
        "branches": "/repository/branches?per_page=100",
        "mrs": "/merge_requests?state=opened&per_page=100",
        "issues": "/issues?state=opened&per_page=100",
        "pipelines": "/pipelines?per_page=5",
        "schedules": "/pipeline_schedules",
    })

    branches = data.get("branches")
    mrs = data.get("mrs")
    issues = data.get("issues")
    pipelines = data.get("pipelines")
    schedules = data.get("schedules")

    report = {
        "project": {
            "name": proj["name"],
            "path": proj["path_with_namespace"],
            "default_branch": proj["default_branch"],
            "visibility": proj["visibility"],
            "web_url": proj["web_url"],
        },
        "branches": {
            "count": len(branches) if isinstance(branches, list) else 0,
            "names": [b["name"] for b in branches] if isinstance(branches, list) else [],
        },
        "open_mrs": len(mrs) if isinstance(mrs, list) else 0,
        "open_issues": len(issues) if isinstance(issues, list) else 0,
        "schedules": len(schedules) if isinstance(schedules, list) else 0,
    }

    if isinstance(pipelines, list) and pipelines:
        report["latest_pipeline"] = {
            "id": pipelines[0]["id"],
            "status": pipelines[0]["status"],
            "ref": pipelines[0]["ref"],
        }

    if args.output == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        p = report["project"]
        logger.info("=== Audit: %s (%s) ===", p["name"], p["path"])
        logger.info("  Default branch: %s", p["default_branch"])
        logger.info("  Visibility:     %s", p["visibility"])
        logger.info("  URL:            %s", p["web_url"])
        logger.info("  Branches:       %d", report["branches"]["count"])
        logger.info("  Open MRs:       %d", report["open_mrs"])
        logger.info("  Open Issues:    %d", report["open_issues"])
        if "latest_pipeline" in report:
            lp = report["latest_pipeline"]
            logger.info("  Latest Pipeline:  #%d (%s, %s)", lp["id"], lp["status"], lp["ref"])
        logger.info("  Schedules:      %d", report["schedules"])


if __name__ == "__main__":
    main()
