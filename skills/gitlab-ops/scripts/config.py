"""脚本共享配置——从环境变量读取 GitLab 连接参数。"""

import os
import sys


def require_env(key: str) -> str:
    """获取必需的环境变量，缺失时打印错误并退出。"""
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: {key} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return val


def get_gitlab_config() -> tuple[str, str, str]:
    """从环境变量读取 GitLab 配置，返回 (url, token, project)。"""
    url = require_env("GITLAB_URL")
    token = require_env("GITLAB_TOKEN")
    project = require_env("GITLAB_PROJECT")
    return url, token, project
