#!/usr/bin/env python3
"""根据已合并 MR 生成发布说明。

用法::

    python release_notes.py [--from REF] [--to REF] [--output FILE]

环境变量:
    GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT（必需）
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from config import require_env
from gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def classify_mr(title: str, labels: list[str]) -> str:
    """根据标签和标题前缀将已合并 MR 分类到发布说明类别。

    优先级：feature > bugfix > docs > chore > Other Changes。
    """
    labels_lower = [l.lower() for l in labels]
    if any(l in labels_lower for l in ["feat", "feature", "enhancement"]):
        return "Features"
    if any(l in labels_lower for l in ["fix", "bug", "bugfix"]):
        return "Bug Fixes"
    if any(l in labels_lower for l in ["docs", "documentation"]):
        return "Documentation"
    if any(l in labels_lower for l in ["chore", "ci", "build"]):
        return "Maintenance"
    if title.lower().startswith("feat"):
        return "Features"
    if title.lower().startswith("fix"):
        return "Bug Fixes"
    return "Other Changes"


def parse_merged_at(raw: str) -> datetime | None:
    """解析 ISO 8601 日期字符串为带时区的 datetime。"""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning("Invalid date format: %s", raw)
        return None


def main() -> None:
    """入口：获取已合并 MR，按类别分组并生成发布说明。"""
    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument("--from", dest="from_ref", default=None,
                        help="Start date (YYYY-MM-DD) or tag")
    parser.add_argument("--to", dest="to_ref", default=None,
                        help="End date (YYYY-MM-DD) or tag")
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    client = GitLabClient(url, token, project)

    mrs = client.get_all(
        "/merge_requests?state=merged&order_by=merged_at&sort=desc"
    )
    if not mrs:
        logger.info("No merged MRs found.")
        return

    if args.from_ref:
        try:
            from_date = datetime.strptime(args.from_ref, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error("Invalid date format: '%s'. Use YYYY-MM-DD.", args.from_ref)
            sys.exit(1)
        filtered = []
        for m in mrs:
            if not m.get("merged_at"):
                continue
            merged_at = parse_merged_at(m["merged_at"])
            if merged_at and merged_at >= from_date:
                filtered.append(m)
        mrs = filtered

    categories: dict[str, list[dict]] = {}
    for mr in mrs:
        cat = classify_mr(mr["title"], mr.get("labels", []))
        categories.setdefault(cat, []).append(mr)

    lines = [f"## Release Notes ({datetime.now().strftime('%Y-%m-%d')})", ""]
    for cat in ["Features", "Bug Fixes", "Documentation", "Maintenance", "Other Changes"]:
        if cat not in categories:
            continue
        lines.append(f"### {cat}")
        for mr in categories[cat]:
            author = mr.get("author", {}).get("username", "?")
            lines.append(f"- {mr['title']} (!{mr['iid']}) @{author}")
        lines.append("")

    output = "\n".join(lines)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        logger.info("Written to %s", args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
