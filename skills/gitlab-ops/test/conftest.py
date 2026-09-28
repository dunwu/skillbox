"""gitlab-ops Skill 测试共享配置与辅助工具。

必需环境变量（不设默认值——绝不硬编码凭据）:

    GITLAB_URL     — GitLab 实例地址，如 https://gitlab.example.com
    GITLAB_TOKEN   — 具有 api 权限的个人访问令牌
    GITLAB_PROJECT — 项目路径，如 group/project

环境变量在首次访问时延迟校验，确保导入本模块（如测试收集阶段）不会崩溃。
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


def _load_dotenv() -> None:
    """从当前目录的 .env 文件加载 KEY=VALUE 键值对（无第三方依赖）。

    已有环境变量优先于 .env 中的值。
    值的首尾引号（单引号或双引号）会被自动去除。
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()

_config_cache: dict[str, str] = {}


def _load_config() -> dict[str, str]:
    """校验必需环境变量并返回派生配置字典。"""
    if _config_cache:
        return _config_cache
    for key in ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT"):
        if not os.environ.get(key):
            raise RuntimeError(
                f"Environment variable {key} is not set. "
                f"See test/README.md for required variables."
            )
    project = os.environ["GITLAB_PROJECT"]
    parsed = urlparse(os.environ["GITLAB_URL"])
    _config_cache.update({
        "GITLAB_URL": os.environ["GITLAB_URL"],
        "GITLAB_TOKEN": os.environ["GITLAB_TOKEN"],
        "GITLAB_PROJECT": project,
        "PROJECT_PATH_ENCODED": quote(project, safe=""),
        "GITLAB_NAMESPACE": project.split("/")[0],
        "GITLAB_HOST": os.environ.get("GITLAB_HOST") or (parsed.hostname or ""),
    })
    return _config_cache


def __getattr__(name: str) -> str:
    """模块级属性的延迟访问入口，用于配置常量。"""
    if name in ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT",
                "PROJECT_PATH_ENCODED", "GITLAB_NAMESPACE", "GITLAB_HOST"):
        return _load_config()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _glab_env() -> dict[str, str]:
    """构建环境变量字典，确保 glab 可在无 keyring 时认证。"""
    env = os.environ.copy()
    env.setdefault("GITLAB_TOKEN", _load_config()["GITLAB_TOKEN"])
    env.setdefault("GITLAB_HOST", _load_config()["GITLAB_HOST"])
    return env


def run(cmd, cwd=None, check=True, timeout=30):
    """执行命令并返回 (returncode, stdout, stderr)。

    接受字符串（通过 shell 执行）或参数列表（直接执行）。
    """
    if isinstance(cmd, list):
        result = subprocess.run(
            cmd, capture_output=True,
            encoding="utf-8", errors="replace",
            cwd=cwd, timeout=timeout,
            env=_glab_env(),
        )
    else:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            encoding="utf-8", errors="replace",
            cwd=cwd, timeout=timeout,
            env=_glab_env(),
        )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command failed (rc={result.returncode}): {cmd}\n"
            f"stderr: {stderr}"
        )
    return result.returncode, stdout, stderr


def run_ok(cmd, **kwargs):
    """断言命令执行成功，返回 (是否成功, stdout)。"""
    rc, out, _ = run(cmd, check=False, **kwargs)
    return rc == 0, out


def _api_request(method: str, path: str, data: dict | None = None):
    """发送 API 请求，返回 (状态码, 解析后的 JSON 或原始文本)。"""
    cfg = _load_config()
    url = f"{cfg['GITLAB_URL']}/api/v4{path}"
    headers = {"PRIVATE-TOKEN": cfg["GITLAB_TOKEN"]}
    payload = None
    if data is not None:
        payload = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = Request(url, data=payload, method=method, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body


def api_get(path: str):
    """向 GitLab API 发送 GET 请求。"""
    return _api_request("GET", path)


def api_post(path: str, data: dict):
    """向 GitLab API 发送 POST JSON 请求。"""
    return _api_request("POST", path, data)


def api_put(path: str, data: dict):
    """向 GitLab API 发送 PUT JSON 请求。"""
    return _api_request("PUT", path, data)


def api_delete(path: str):
    """向 GitLab API 发送 DELETE 请求。"""
    return _api_request("DELETE", path)


class TempRepo:
    """创建临时 git 仓库，用于测试本地 git 命令。"""

    def __init__(self):
        """创建唯一临时目录作为测试仓库。"""
        self.dir = tempfile.mkdtemp(prefix="gitlab-ops-test-")

    def __enter__(self):
        """初始化 git 仓库并配置默认用户信息，返回自身。"""
        run(["git", "init"], cwd=self.dir)
        run(["git", "config", "user.email", "test@test.com"], cwd=self.dir)
        run(["git", "config", "user.name", "Test"], cwd=self.dir)
        return self

    def __exit__(self, *args):
        """上下文退出时清理临时目录。"""
        shutil.rmtree(self.dir, ignore_errors=True)

    def commit(self, msg: str = "test commit", filename: str | None = None):
        """创建文件、暂存并提交，返回创建的文件名。"""
        if filename is None:
            filename = f"file-{secrets.token_hex(4)}.txt"
        filepath = os.path.join(self.dir, filename)
        with open(filepath, "w") as f:
            f.write(msg + "\n")
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-m", msg], cwd=self.dir)
        return filename
