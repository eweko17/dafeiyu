from __future__ import annotations

from typing import Any

from . import gemini, groq, ollama
from .errors import BrainError


def _order(cfg: dict[str, Any], prefer: str | None) -> list[str]:
    brain_cfg = cfg.get("brain", {})
    names: list[str] = []
    for name in (prefer, brain_cfg.get("primary"), brain_cfg.get("fallback")):
        if name and name not in names:
            names.append(name)
    return names


def generate(
    system: str,
    user: str,
    cfg: dict[str, Any],
    secrets: dict[str, Any],
    prefer: str | None = None,
) -> tuple[str, str]:
    """回傳 (文字, 使用的 provider)。主要模型失敗時自動換備援。"""
    errors: list[str] = []
    brain_cfg = cfg.get("brain", {})

    for name in _order(cfg, prefer):
        try:
            if name == "ollama":
                text = ollama.generate(system, user, brain_cfg.get("ollama", {}))
            elif name == "gemini":
                text = gemini.generate(
                    system,
                    user,
                    brain_cfg.get("gemini", {}),
                    str(secrets.get("gemini_api_key", "")).strip(),
                )
            elif name == "groq":
                text = groq.generate(
                    system,
                    user,
                    brain_cfg.get("groq", {}),
                    str(secrets.get("groq_api_key", "")).strip(),
                )
            else:
                raise BrainError(f"未知的大腦：{name}")
            return text, name
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")

    raise BrainError("所有大腦都失敗了 → " + " ｜ ".join(errors))


def health(cfg: dict[str, Any], secrets: dict[str, Any]) -> list[tuple[str, bool, str]]:
    brain_cfg = cfg.get("brain", {})
    results: list[tuple[str, bool, str]] = []

    ok, message = ollama.health(brain_cfg.get("ollama", {}))
    results.append(("Ollama（本機）", ok, message))

    key = str(secrets.get("gemini_api_key", "")).strip()
    if key:
        results.append(("Gemini（雲端）", True, "已設定 API key"))
    else:
        results.append(("Gemini（雲端）", False, "未設定 API key"))

    groq_key = str(secrets.get("groq_api_key", "")).strip()
    ok, message = groq.health(brain_cfg.get("groq", {}), groq_key)
    results.append(("Groq（雲端）", ok, message))

    return results
