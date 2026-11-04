"""切換大肥魚的大腦。

- 筆電：Ollama 為主、Gemini 備援
- 手機（Termux）／GitHub Actions：沒有 Ollama，改成 Gemini

用法：
    python scripts/switch_brain.py           # 切換成 Gemini
    python scripts/switch_brain.py ollama    # 切換回 Ollama
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "gemini").strip().lower()
    if not CONFIG.exists():
        print(f"找不到 {CONFIG}")
        return 1

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    brain = data.setdefault("brain", {})

    if mode == "gemini":
        brain["primary"] = "gemini"
        brain["fallback"] = ""
        message = "已切換成 Gemini（雲端／手機用）。記得要有 Gemini API key。"
    elif mode == "ollama":
        brain["primary"] = "ollama"
        brain["fallback"] = "gemini"
        message = "已切換成 Ollama（筆電用），Gemini 當備援。"
    else:
        print("用法：python scripts/switch_brain.py [gemini|ollama]")
        return 1

    CONFIG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
