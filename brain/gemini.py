from __future__ import annotations

from typing import Any

import requests

from .errors import BrainError

BASE = "https://generativelanguage.googleapis.com/v1beta"
_MODEL_CACHE: dict[str, str] = {}


def _resolve_model(cfg: dict[str, Any], api_key: str) -> str:
    configured = str(cfg.get("model", "auto")).strip()
    if configured and configured != "auto":
        return configured

    if api_key in _MODEL_CACHE:
        return _MODEL_CACHE[api_key]

    try:
        response = requests.get(f"{BASE}/models", params={"key": api_key}, timeout=20)
        response.raise_for_status()
        models = response.json().get("models", [])
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"Gemini 模型清單取得失敗：{exc}") from exc

    names = [
        m.get("name", "").split("/")[-1]
        for m in models
        if "generateContent" in (m.get("supportedGenerationMethods") or [])
    ]
    if not names:
        raise BrainError("Gemini 沒有可用的 generateContent 模型")

    def pick(predicate) -> str | None:
        for name in names:
            if predicate(name.lower()):
                return name
        return None

    model = (
        pick(lambda n: "flash" in n and "lite" in n)
        or pick(lambda n: "flash" in n)
        or names[0]
    )
    _MODEL_CACHE[api_key] = model
    return model


def generate(
    system: str,
    user: str,
    cfg: dict[str, Any],
    api_key: str,
) -> str:
    if not api_key:
        raise BrainError("沒有設定 Gemini API key")

    model = _resolve_model(cfg, api_key)
    url = f"{BASE}/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": float(cfg.get("temperature", 0.95)),
            "topP": 0.95,
            "maxOutputTokens": int(cfg.get("max_output_tokens", 800)),
        },
    }

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=int(cfg.get("timeout_seconds", 60)),
        )
    except requests.Timeout as exc:
        raise BrainError("Gemini 逾時") from exc
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"Gemini 連線失敗：{exc}") from exc

    if response.status_code == 429:
        raise BrainError("Gemini 免費額度用完或太頻繁（429）")
    if not response.ok:
        raise BrainError(f"Gemini 回應 {response.status_code}：{response.text[:300]}")

    data = response.json()
    blocked = (data.get("promptFeedback") or {}).get("blockReason")
    if blocked:
        raise BrainError(f"Gemini 擋掉了這個 prompt：{blocked}")

    candidates = data.get("candidates") or []
    if not candidates:
        raise BrainError("Gemini 沒有回傳候選內容")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        finish = candidates[0].get("finishReason", "未知")
        raise BrainError(f"Gemini 回傳空白內容（finishReason={finish}）")
    return text
