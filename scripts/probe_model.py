from __future__ import annotations

import json
import time

import requests

BASE = "http://127.0.0.1:11434/api/chat"
PROMPT = "用大肥魚的語氣說一句話，20 字以內。只輸出那句話。"


def probe(label: str, payload: dict) -> None:
    t0 = time.time()
    response = requests.post(BASE, json=payload, timeout=300)
    dt = time.time() - t0
    print(f"--- {label} ---")
    print("status:", response.status_code, f"{dt:.1f}s")
    if response.status_code != 200:
        print("body:", response.text[:400])
        return
    data = response.json()
    message = data.get("message") or {}
    print("keys:", list(message.keys()))
    print("thinking:", repr((message.get("thinking") or "")[:60]))
    print("content:", repr((message.get("content") or "")[:300]))
    print("eval_count:", data.get("eval_count"), "done:", data.get("done_reason"))
    print()


def main() -> None:
    base = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": False,
        "options": {"num_predict": 120, "temperature": 0.9},
    }
    probe("think=False", {**base, "think": False})
    probe("think=True", {**base, "think": True})
    probe("no think field", base)

    print("=== 模型資訊 ===")
    info = requests.post(
        "http://127.0.0.1:11434/api/show", json={"model": "qwen3:4b"}, timeout=60
    ).json()
    print("family:", (info.get("details") or {}).get("family"))
    print("parameter_size:", (info.get("details") or {}).get("parameter_size"))
    template = info.get("template") or ""
    print("template 前 600 字：")
    print(template[:600])


if __name__ == "__main__":
    main()
