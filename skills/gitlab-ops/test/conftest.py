"""gitlab-ops Skill 测试共享配置与辅助工具。

凭据来源与 Skill 主体一致，**不设默认值——绝不硬编码凭据**：

    GITLAB_URL     — GitLab 实例地址，如 https://gitlab.example.com
    GITLAB_TOKEN   — 具有 api 权限的个人访问令牌
    以上两项按「进程环境变量 → <skill-root>/config/.env」顺序解析；
    未配置时先跑 `python scripts/config.py setup` 补齐（见 SKILL.md §认证门禁）。

    GITLAB_PROJECT — 测试项目路径，如 group/project。它不是凭据，故**不进 .env**，
    在本文件（测试套件的初始化入口）或环境变量中指定：导入时取环境变量
    ``GITLAB_PROJECT``，未设置则取下方 GITLAB_PROJECT 常量的值。

环境变量在首次访问时延迟校验，确保导入本模块（如测试收集阶段）不会崩溃。
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import stat
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

# 测试项目路径：在此填写，或用同名环境变量覆盖（环境变量优先）。
# 形如 "group/project" 或 "group/subgroup/project"。本文件不预置任何真实项目 ID，
# 留空时依赖 GitLab 的用例会在首次访问时明确报错并提示到此处填写。
GITLAB_PROJECT = os.environ.get("GITLAB_PROJECT", "")


def _load_dotenv() -> None:
    """从 ``<skill-root>/config/.env`` 加载 KEY=VALUE 键值对（无第三方依赖）。

    路径与 scripts/config.py 保持一致：测试与 Skill 主体共用同一份凭据，
    避免「Skill 读 config/.env、测试读 test/.env」的双轨漂移。
    已有环境变量优先于 .env 中的值。
    值的首尾引号（单引号或双引号）会被自动去除。
    """
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(skill_root, "config", ".env")
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
_credentials_cache: dict[str, str] = {}


def _load_credentials() -> dict[str, str]:
    """校验凭据（URL / TOKEN）并派生主机名——不含测试项目。

    只做 CLI 参数断言、或只需要主机名的用例走这条路径，
    避免「没指定测试项目就连 GITLAB_HOST 都取不到」。
    """
    if _credentials_cache:
        return _credentials_cache
    for key in ("GITLAB_URL", "GITLAB_TOKEN"):
        if not os.environ.get(key):
            raise RuntimeError(
                f"Environment variable {key} is not set. "
                f"它应来自进程环境变量或 <skill-root>/config/.env；"
                f"未配置时先运行 `python scripts/config.py setup` 补齐。"
            )
    _credentials_cache.update({
        "GITLAB_URL": os.environ["GITLAB_URL"],
        "GITLAB_TOKEN": os.environ["GITLAB_TOKEN"],
        "GITLAB_HOST": urlparse(os.environ["GITLAB_URL"]).hostname or "",
    })
    return _credentials_cache


def _load_config() -> dict[str, str]:
    """校验凭据与测试项目，返回派生配置字典。"""
    if _config_cache:
        return _config_cache
    cfg = dict(_load_credentials())
    # GITLAB_PROJECT 不是凭据，不进 .env：常量在导入时取环境变量，未设置时取本文件填写值
    project = GITLAB_PROJECT
    if not project:
        raise RuntimeError(
            "测试项目未指定：请设置环境变量 GITLAB_PROJECT，"
            "或在本文件顶部的 GITLAB_PROJECT 常量中填写 \"group/project\"。"
        )
    cfg.update({
        "GITLAB_PROJECT": project,
        "PROJECT_PATH_ENCODED": quote(project, safe=""),
    })
    _config_cache.update(cfg)
    return _config_cache


def __getattr__(name: str) -> str:
    """模块级属性的延迟访问入口，用于配置常量。

    凭据类属性不要求已指定测试项目。
    """
    if name in ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_HOST"):
        return _load_credentials()[name]
    if name in ("GITLAB_PROJECT", "PROJECT_PATH_ENCODED"):
        return _load_config()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _glab_env() -> dict[str, str]:
    """构建环境变量字典，确保 glab 可在无 keyring 时认证。"""
    env = os.environ.copy()
    creds = _load_credentials()
    env.setdefault("GITLAB_TOKEN", creds["GITLAB_TOKEN"])
    env.setdefault("GITLAB_HOST", creds["GITLAB_HOST"])
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
    """执行命令，返回 (是否成功, stdout)——不抛异常。

    正向用例配 `assertTrue(rc)`，负向用例（断言某参数不被支持）配 `assertFalse(rc)`，
    因此这里不能断言失败。代价是失败信息只剩 "False is not true"；需要看 stderr 时，
    用 `run(cmd, check=False)` 拿三元组自行断言。
    """
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


_role_cache: "dict[str, int]" = {}


def project_access_level() -> int:
    """当前令牌在测试项目上的最高角色数值；取不到返回 -1。

    GitLab 角色：10 Guest / 20 Reporter / 30 Developer / 40 Maintainer / 50 Owner。
    """
    if not _role_cache:
        cfg = _load_config()
        status, data = api_get(f"/projects/{cfg['PROJECT_PATH_ENCODED']}")
        level = -1
        if status == 200 and isinstance(data, dict):
            perms = data.get("permissions") or {}
            levels = [
                (perms.get(k) or {}).get("access_level")
                for k in ("project_access", "group_access")
            ]
            levels = [x for x in levels if isinstance(x, int)]
            level = max(levels) if levels else -1
        _role_cache["level"] = level
    return _role_cache["level"]


def require_role(case, min_level: int, capability: str) -> None:
    """角色不足时跳过用例并说明原因，而不是记成失败。

    这些能力受服务端角色门禁（如 CI/CD 变量、Webhook、归档需 Maintainer），
    用低权限令牌跑测试套件时应当是「未执行」而非「回归」。
    取不到角色时不跳过，让真实的权限问题仍以失败暴露。
    """
    level = project_access_level()
    if 0 <= level < min_level:
        cfg = _load_config()
        case.skipTest(
            f"{capability} 需要 access_level >= {min_level}，"
            f"当前令牌在 {cfg['GITLAB_PROJECT']} 上为 {level}；"
            f"换 Maintainer 令牌后本用例才会执行"
        )


def _remove_readonly(func, path, exc_info):
    """清掉只读位后重试删除。

    git 把 object 文件写成只读，Windows 上 `rmtree` 会抛 PermissionError；
    用 `ignore_errors=True` 会把失败静默吞掉，每个跑过 commit 的用例都泄漏一个临时仓库。
    """
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def remove_tree(path: str) -> None:
    """删除目录树，能破 Windows 只读位；删不掉时抛错而不是静默泄漏。"""
    shutil.rmtree(path, onerror=_remove_readonly)


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
        remove_tree(self.dir)

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
