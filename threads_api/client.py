from __future__ import annotations

import time
from typing import Any

import requests

DEFAULT_BASE = "https://graph.threads.net/v1.0"


class ThreadsError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        subcode: int | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.http_status = http_status


class ThreadsClient:
    def __init__(
        self,
        token: str,
        user_id: str,
        *,
        api_base: str = DEFAULT_BASE,
        is_made_with_ai: bool = True,
        publish_retries: int = 6,
        publish_retry_seconds: int = 3,
        timeout: int = 30,
    ) -> None:
        self.token = token.strip()
        self.user_id = str(user_id).strip()
        self.api_base = api_base.rstrip("/")
        self.is_made_with_ai = is_made_with_ai
        self.publish_retries = publish_retries
        self.publish_retry_seconds = publish_retry_seconds
        self.timeout = timeout

    # ------------------------------------------------------------------ 基本呼叫
    def _call(self, method: str, path: str, **params: Any) -> dict[str, Any]:
        url = f"{self.api_base}/{path.lstrip('/')}"
        params["access_token"] = self.token

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=self.timeout)
            else:
                response = requests.request(method, url, data=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise ThreadsError(f"Threads API 逾時：{url}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ThreadsError(f"Threads API 連線失敗：{exc}") from exc

        try:
            body = response.json()
        except ValueError:
            body = {}

        if not response.ok or "error" in body:
            error = body.get("error") or {}
            if isinstance(error, str):
                message = error
                code = subcode = None
            else:
                message = error.get("message") or response.text[:300]
                code = error.get("code")
                subcode = error.get("error_subcode")
            raise ThreadsError(
                message,
                code=code,
                subcode=subcode,
                http_status=response.status_code,
            )

        return body

    # ------------------------------------------------------------------ 帳號
    def me(self) -> dict[str, Any]:
        return self._call("GET", "me", fields="id,username")

    def publishing_limit(self) -> dict[str, Any]:
        body = self._call(
            "GET",
            f"{self.user_id}/threads_publishing_limit",
            fields="quota_usage,config,reply_quota_usage,reply_config",
        )
        data = body.get("data") or []
        return data[0] if data else {}

    # ------------------------------------------------------------------ 發文
    def create_text(self, text: str, reply_to_id: str | None = None) -> str:
        payload: dict[str, Any] = {
            "media_type": "TEXT",
            "text": text,
            "is_made_with_ai": "true" if self.is_made_with_ai else "false",
        }
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        return str(self._call("POST", f"{self.user_id}/threads", **payload)["id"])

    def publish(self, creation_id: str) -> str:
        return str(
            self._call(
                "POST",
                f"{self.user_id}/threads_publish",
                creation_id=creation_id,
            )["id"]
        )

    def post_text(self, text: str, reply_to_id: str | None = None) -> str:
        creation_id = self.create_text(text, reply_to_id=reply_to_id)
        last_error: ThreadsError | None = None

        for attempt in range(self.publish_retries):
            try:
                return self.publish(creation_id)
            except ThreadsError as exc:
                last_error = exc
                retryable = (
                    exc.http_status in (500, 502, 503, 504)
                    or "not ready" in str(exc).lower()
                    or "unknown" in str(exc).lower()
                    or "try again" in str(exc).lower()
                )
                if not retryable:
                    raise
                time.sleep(self.publish_retry_seconds * (attempt + 1))

        raise last_error or ThreadsError("發佈失敗，原因不明")

    # ------------------------------------------------------------------ 留言
    def replies(self, media_id: str, limit: int = 50) -> list[dict[str, Any]]:
        body = self._call(
            "GET",
            f"{media_id}/replies",
            fields="id,text,username,timestamp,replied_to,is_reply,has_replies",
            reverse="false",
            limit=limit,
        )
        return list(body.get("data") or [])

    # ------------------------------------------------------------------ Token
    def refresh_token(self) -> dict[str, Any]:
        response = requests.get(
            "https://graph.threads.net/refresh_access_token",
            params={"grant_type": "th_refresh_token", "access_token": self.token},
            timeout=self.timeout,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok or "access_token" not in body:
            raise ThreadsError(f"Token 更新失敗：{body or response.text[:300]}")
        return body


def make_client(config: dict[str, Any], secrets: dict[str, Any]) -> ThreadsClient:
    token = str(secrets.get("threads_token", "")).strip()
    user_id = str(secrets.get("threads_user_id", "")).strip()
    if not token or not user_id:
        raise ThreadsError("尚未設定 Threads token 或 user id，請先執行：py -m app.cli setup")

    threads_cfg = config.get("threads", {})
    return ThreadsClient(
        token,
        user_id,
        api_base=str(threads_cfg.get("api_base", DEFAULT_BASE)),
        is_made_with_ai=bool(threads_cfg.get("is_made_with_ai", True)),
        publish_retries=int(threads_cfg.get("publish_retries", 6)),
        publish_retry_seconds=int(threads_cfg.get("publish_retry_seconds", 3)),
    )
