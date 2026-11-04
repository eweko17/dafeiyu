from __future__ import annotations

from typing import Any

import requests

from .errors import BrainError


def _base(cfg: dict[str, Any]) -> str:
    return str(cfg.get("base_url", "http://127.0.0.1:11434")).rstrip("/")


def list_models(cfg: dict[str, Any], timeout: int = 5) -> list[str]:
    try:
        response = requests.get(f"{_base(cfg)}/api/tags", timeout=timeout)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"連不到 Ollama：{exc}") from exc
    data = response.json()
    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]


def health(cfg: dict[str, Any]) -> tuple[bool, str]:
    try:
        models = list_models(cfg)
    except BrainError as exc:
        return False, str(exc)

    wanted = cfg.get("model", "qwen3:4b")
    if wanted in models:
        return True, f"Ollama 正常，模型 {wanted} 已安裝"
    return False, f"Ollama 正常，但找不到模型 {wanted}（現有：{', '.join(models) or '無'}）"


def generate(system: str, user: str, cfg: dict[str, Any]) -> str:
    payload: dict[str, Any] = {
        "model": cfg.get("model", "qwen3:4b"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {
            "temperature": float(cfg.get("temperature", 0.9)),
            "top_p": 0.95,
            "num_predict": int(cfg.get("num_predict", 600)),
        },
    }
    if cfg.get("think") is False:
        payload["think"] = False
    # 用完就卸載模型，避免文書機被吃記憶體。
    payload["keep_alive"] = str(cfg.get("keep_alive", "2m"))

    url = f"{_base(cfg)}/api/chat"
    timeout = int(cfg.get("timeout_seconds", 240))

    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        raise BrainError(f"Ollama 逾時（{timeout} 秒），可能模型太大或筆電太忙") from exc
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"Ollama 連線失敗：{exc}") from exc

    # 舊版 Ollama 不認得 think 參數時，拆掉再試一次。
    if response.status_code == 400 and "think" in response.text.lower():
        payload.pop("think", None)
        response = requests.post(url, json=payload, timeout=timeout)

    if response.status_code == 404:
        raise BrainError(
            f"Ollama 找不到模型 {payload['model']}，請先執行：ollama pull {payload['model']}"
        )
    if not response.ok:
        raise BrainError(f"Ollama 回應 {response.status_code}：{response.text[:300]}")

    data = response.json()
    message = data.get("message") or {}
    text = (message.get("content") or "").strip()
    thinking = (message.get("thinking") or "").strip()
    if not text and thinking:
        raise BrainError(
            f"模型 {payload['model']} 把內容都放進「思考」欄位了，"
            "請改用非思考型模型（例如 qwen2.5:3b-instruct）"
        )
    if not text:
        raise BrainError("Ollama 回傳空白內容")
    return text
