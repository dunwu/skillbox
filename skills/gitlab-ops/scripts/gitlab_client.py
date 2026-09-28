"""GitLab REST API 共享客户端——自动分页、指数退避重试、类型安全。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GitLabClient:
    """GitLab REST API 客户端，支持自动分页和指数退避重试。"""

    def __init__(self, url: str, token: str, project: str, timeout: int = 30):
        """初始化客户端。

        Args:
            url: GitLab 实例地址（自动去除末尾斜杠）。
            token: Private Access Token。
            project: 项目路径，如 'group/project'。
            timeout: HTTP 请求超时时间（秒）。
        """
        self.url = url.rstrip("/")
        self.token = token
        self.project = project
        self.project_encoded = quote(project, safe="")
        self.timeout = timeout

    def _request(self, method: str, path: str, data: dict | None = None,
                 retries: int = 3) -> tuple[int, Any]:
        """发送 HTTP 请求，5xx 和连接异常自动指数退避重试。"""
        url = f"{self.url}/api/v4{path}"
        headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }

        body = None
        if data is not None:
            body = json.dumps(data).encode()

        for attempt in range(retries):
            try:
                req = Request(url, data=body, method=method, headers=headers)
                with urlopen(req, timeout=self.timeout) as resp:
                    response_body = resp.read().decode()
                    try:
                        return resp.status, json.loads(response_body)
                    except json.JSONDecodeError:
                        return resp.status, response_body

            except HTTPError as e:
                if e.code >= 500 and attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"HTTP {e.code}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                try:
                    return e.code, json.loads(e.read().decode())
                except json.JSONDecodeError:
                    return e.code, e.read().decode()

            except (URLError, TimeoutError) as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Connection error, retrying in {wait}s: {e}")
                    time.sleep(wait)
                    continue
                logger.error(f"Request failed after {retries} attempts: {e}")
                return 0, str(e)

        return 0, "Max retries exceeded"

    def get(self, path: str) -> tuple[int, Any]:
        """发送 GET 请求。"""
        return self._request("GET", path)

    def get_all(self, path: str, per_page: int = 100) -> list[Any]:
        """GET 请求并自动翻页，返回全部结果。"""
        results = []
        page = 1

        while True:
            separator = "&" if "?" in path else "?"
            paginated_path = f"{path}{separator}per_page={per_page}&page={page}"
            status, data = self.get(paginated_path)

            if status != 200 or not isinstance(data, list):
                logger.error(f"Pagination failed at page {page}: HTTP {status}")
                break

            results.extend(data)

            if len(data) < per_page:
                break

            page += 1

        return results

    def put(self, path: str, data: dict) -> tuple[int, Any]:
        """发送 PUT 请求。"""
        return self._request("PUT", path, data)

    def post(self, path: str, data: dict) -> tuple[int, Any]:
        """发送 POST 请求。"""
        return self._request("POST", path, data)

    def delete(self, path: str) -> tuple[int, Any]:
        """发送 DELETE 请求。"""
        return self._request("DELETE", path)
