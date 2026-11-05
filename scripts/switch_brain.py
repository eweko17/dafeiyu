"""切換大肥魚的大腦。

- 筆電：Ollama 為主、Gemini 備援
- 手機（Termux）／GitHub Actions：沒有 Ollama，改成雲端模型
  - 有 Gemini key：Gemini 為主，Groq 備援
  - 只有 Groq key：Groq 為主
  - 兩個都有：Gemini 為主、Groq 備援（Gemini 掛掉自動換手）

用法：
    python scripts/switch_brain.py           # 切成雲端（自動看有哪些 key）
    python scripts/switch_brain.py ollama    # 切換回 Ollama
    python scripts/switch_brain.py gemini    # 強制 Gemini
    python scripts/switch_brain.py groq      # 強制 Groq
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
SECRETS = ROOT / "state" / "secrets.json"


def _keys() -> tuple[bool, bool]:
    if not SECRETS.exists():
        return False, False
    try:
        data = json.loads(SECRETS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, False
    return (
        bool(str(data.get("gemini_api_key", "")).strip()),
        bool(str(data.get("groq_api_key", "")).strip()),
    )


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "cloud").strip().lower()
    if not CONFIG.exists():
        print(f"找不到 {CONFIG}")
        return 1

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    brain = data.setdefault("brain", {})
    has_gemini, has_groq = _keys()

    if mode in ("cloud", "auto", "gemini"):
        if mode == "gemini":
            brain["primary"] = "gemini"
            brain["fallback"] = "groq" if has_groq else ""
            message = "已切換成 Gemini（雲端），Groq 當備援。"
        elif has_groq and has_gemini:
            # GitHub Actions 是資料中心 IP，Gemini 免費層一定 403，
            # 放進備援只會在 log 裡多一段紅字，所以直接不用它。
            brain["primary"] = "groq"
            brain["fallback"] = ""
            message = "已切換成 Groq（雲端）。Gemini 在 GitHub 上會被擋，暫不列入備援。"
        elif has_groq:
            brain["primary"] = "groq"
            brain["fallback"] = ""
            message = "已切換成 Groq（雲端）。"
        else:
            brain["primary"] = "gemini"
            brain["fallback"] = ""
            message = "已切換成 Gemini，但沒有偵測到任何雲端 API key。"
    elif mode == "groq":
        brain["primary"] = "groq"
        brain["fallback"] = "gemini" if has_gemini else ""
        message = "已切換成 Groq（雲端）。"
    elif mode == "ollama":
        brain["primary"] = "ollama"
        brain["fallback"] = "groq" if has_groq else ("gemini" if has_gemini else "")
        message = "已切換成 Ollama（筆電用），雲端模型當備援。"
    else:
        print("用法：python scripts/switch_brain.py [cloud|ollama|gemini|groq]")
        return 1

    CONFIG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
