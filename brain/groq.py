from __future__ import annotations

from typing import Any

import requests

from .errors import BrainError

BASE = "https://api.groq.com/openai/v1"
_MODEL_CACHE: dict[str, str] = {}

# 這些不是聊天模型，挑選時要跳過。
_SKIP = ("whisper", "tts", "guard", "embed", "moderation", "rerank")

# 越前面的越優先。先挑「一般指令模型」，
# 推理型模型（gpt-oss / qwen3）放後面，因為它們常把 token 花在思考上。
_PREFER = (
    "gpt-oss-120b",
    "qwen3.8-27b",
    "gpt-oss-20b",
    "qwen3-32b",
    "qwen-2.5-32b",
)

_MAX_TOKENS_CAP = 4096


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def list_models(api_key: str, timeout: int = 20) -> list[str]:
    if not api_key:
        raise BrainError("沒有設定 Groq API key")
    try:
        response = requests.get(
            f"{BASE}/models", headers=_headers(api_key), timeout=timeout
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"Groq 模型清單取得失敗：{exc}") from exc

    data = response.json()
    return [
        m.get("id", "")
        for m in data.get("data", [])
        if m.get("id") and not any(s in m["id"].lower() for s in _SKIP)
    ]


def _resolve_model(cfg: dict[str, Any], api_key: str) -> str:
    configured = str(cfg.get("model", "auto")).strip()
    if configured and configured != "auto":
        return configured

    if api_key in _MODEL_CACHE:
        return _MODEL_CACHE[api_key]

    names = list_models(api_key)
    if not names:
        raise BrainError("Groq 沒有可用的聊天模型")

    lowered = {name.lower(): name for name in names}
    picked = ""
    for want in _PREFER:
        for low, real in lowered.items():
            if want in low:
                picked = real
                break
        if picked:
            break
    if not picked:
        picked = names[0]

    _MODEL_CACHE[api_key] = picked
    return picked


def _post(
    model: str,
    messages: list[dict[str, str]],
    cfg: dict[str, Any],
    api_key: str,
    max_tokens: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.95)),
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        response = requests.post(
            f"{BASE}/chat/completions",
            headers=_headers(api_key),
            json=payload,
            timeout=int(cfg.get("timeout_seconds", 60)),
        )
    except requests.Timeout as exc:
        raise BrainError("Groq 逾時") from exc
    except Exception as exc:  # noqa: BLE001
        raise BrainError(f"Groq 連線失敗：{exc}") from exc

    if response.status_code == 401:
        raise BrainError("Groq API key 無效（401）")
    if response.status_code == 429:
        raise BrainError("Groq 免費額度用完或太頻繁（429）")
    if not response.ok:
        raise BrainError(f"Groq 回應 {response.status_code}：{response.text[:300]}")

    return response.json()


def generate(
    system: str,
    user: str,
    cfg: dict[str, Any],
    api_key: str,
) -> str:
    if not api_key:
        raise BrainError("沒有設定 Groq API key")

    model = _resolve_model(cfg, api_key)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    max_tokens = int(cfg.get("max_output_tokens", 800))
    last_reason = ""

    # 推理型模型有時會把 token 全花在「思考」，content 就變空的或講到一半。
    # 遇到沒講完就加大上限重試。
    for _ in range(3):
        data = _post(model, messages, cfg, api_key, max_tokens)
        choices = data.get("choices") or []
        if not choices:
            raise BrainError("Groq 沒有回傳內容")

        choice = choices[0]
        message = choice.get("message") or {}
        text = (message.get("content") or "").strip()
        finish = str(choice.get("finish_reason", "未知"))

        if text and finish != "length":
            return text

        thinking = (message.get("reasoning") or "").strip()
        last_reason = f"finish_reason={finish}"
        if thinking:
            last_reason += f"，思考了 {len(thinking)} 字"

        if finish == "length" and max_tokens < _MAX_TOKENS_CAP:
            # 已經有內容但被截斷，也算失敗，放大後重寫一次。
            max_tokens = min(max_tokens * 3, _MAX_TOKENS_CAP)
            continue
        if text:
            return text
        break

    raise BrainError(f"Groq 回傳空白內容（{last_reason}）")


def health(cfg: dict[str, Any], api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "未設定 API key"
    try:
        names = list_models(api_key)
    except BrainError as exc:
        return False, str(exc)

    configured = str(cfg.get("model", "auto")).strip()
    if configured and configured != "auto":
        if configured in names:
            return True, f"Groq 正常，模型 {configured} 可用"
        return True, f"Groq 正常，但清單裡沒有 {configured}（會自動挑）"
    return True, f"Groq 正常，{len(names)} 個模型可用"
