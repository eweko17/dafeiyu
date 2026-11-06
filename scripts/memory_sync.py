#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大肥魚：手機 ↔ 筆電 記憶同步

兩邊共用一個「私密 GitHub Gist」當共同記憶抽屜：
  - 手機 PWA 直接讀寫這個 Gist
  - 筆電把 Gist 跟桌寵的 memory.json 合併

用法：
  python scripts/memory_sync.py            同步一次
  python scripts/memory_sync.py --watch    每 60 秒同步一次（常駐）
  python scripts/memory_sync.py --status   看目前設定與狀態
  python scripts/memory_sync.py --wipe     清空兩邊記憶

設定檔（第一次用 --setup 或直接編輯）：
  %USERPROFILE%\\.dsh\\dafeiyu-sync.json
  {"token": "ghp_...", "gist_id": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    print("缺少 requests，請先執行：.venv\\Scripts\\pip install requests")
    raise SystemExit(1)

API = "https://api.github.com"
GIST_FILE = "dafeiyu-memory.json"
MAX_MSGS = 400
LOCK_PORT = 49731

HOME = Path.home()
CONFIG = HOME / ".dsh" / "dafeiyu-sync.json"
PET_MEMORY = HOME / ".dsh" / "dsh-pet" / "memory.json"
LOG_FILE = HOME / ".dsh" / "dafeiyu-sync.log"


# ---------------------------------------------------------------- 基本工具


def now_text() -> str:
    return datetime.now().strftime("%m/%d %H:%M:%S")


def log(message: str, quiet: bool = False) -> None:
    line = f"{now_text()} {message}"
    if not quiet:
        print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 512 * 1024:
            LOG_FILE.write_text("", encoding="utf-8")
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_config() -> dict[str, Any]:
    if not CONFIG.exists():
        return {}
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data: dict[str, Any]) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- 訊息格式


def msg_key(m: dict[str, Any]) -> str:
    return f"{m.get('role', '')}|{int(m.get('ts') or 0)}|{m.get('text', '')}"


def to_common(raw: Any, src: str) -> dict[str, Any] | None:
    """桌寵的 {content} 與手機的 {text} 統一成 {text}。"""
    if not isinstance(raw, dict):
        return None
    role = raw.get("role")
    if role not in ("user", "assistant"):
        return None

    data = dict(raw)
    text = data.pop("text", None)
    if not isinstance(text, str):
        text = data.get("content")
    data.pop("content", None)
    if not isinstance(text, str) or not text.strip():
        return None

    data["role"] = role
    data["text"] = text
    data["ts"] = int(data.get("ts") or 0)
    if not isinstance(data.get("src"), str):
        data["src"] = src
    return data


def to_pet(common: dict[str, Any]) -> dict[str, Any]:
    """還原成桌寵記憶的格式。"""
    data = dict(common)
    data.pop("src", None)
    text = data.pop("text", "")
    data["content"] = text
    data["ts"] = int(data.get("ts") or 0)
    return data


def merge(local: list[dict], remote: list[dict], cleared_at: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in list(local) + list(remote):
        if not item:
            continue
        if cleared_at and int(item.get("ts") or 0) <= cleared_at:
            continue
        key = msg_key(item)
        old = seen.get(key)
        if old is None:
            seen[key] = item
        else:
            merged = dict(old)
            for k, v in item.items():
                if v not in (None, "", []):
                    merged[k] = v
            seen[key] = merged
    ordered = sorted(seen.values(), key=lambda m: int(m.get("ts") or 0))
    return ordered[-MAX_MSGS:]


# ---------------------------------------------------------------- 桌寵記憶


def read_pet() -> list[dict]:
    if not PET_MEMORY.exists():
        return []
    try:
        data = json.loads(PET_MEMORY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entry = (
        data.get("main", {}).get("main", {})
        if isinstance(data.get("main"), dict)
        else {}
    )
    messages = entry.get("messages") if isinstance(entry, dict) else None
    if not isinstance(messages, list):
        return []
    out = []
    for raw in messages:
        item = to_common(raw, "pc")
        if item:
            out.append(item)
    return out


def write_pet(messages: list[dict]) -> None:
    data: dict[str, Any] = {}
    if PET_MEMORY.exists():
        try:
            loaded = json.loads(PET_MEMORY.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            data = {}

    bucket = data.get("main")
    if not isinstance(bucket, dict):
        bucket = data["main"] = {}
    entry = bucket.get("main")
    if not isinstance(entry, dict):
        entry = bucket["main"] = {}
    entry["messages"] = [to_pet(m) for m in messages]

    atomic_write(
        PET_MEMORY, json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )


# ---------------------------------------------------------------- Gist


def headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def friendly(status: int) -> str:
    if status == 401:
        return "GitHub 金鑰不對（401）"
    if status == 403:
        return "金鑰沒有 gist 權限（403）"
    if status == 404:
        return "找不到記憶抽屜（404），確認 gist_id"
    if status == 422:
        return "內容格式被拒絕（422）"
    return f"GitHub 回應 {status}"


def read_remote(token: str, gist_id: str) -> dict[str, Any]:
    res = requests.get(f"{API}/gists/{gist_id}", headers=headers(token), timeout=25)
    if res.status_code != 200:
        raise RuntimeError(friendly(res.status_code))
    data = res.json()
    files = data.get("files") or {}
    info = files.get(GIST_FILE)
    empty = {"messages": [], "summary": "", "summaryTs": 0, "clearedAt": 0, "raw": ""}
    if not isinstance(info, dict):
        return empty

    content = info.get("content") or ""
    if info.get("truncated") and info.get("raw_url"):
        raw = requests.get(info["raw_url"], timeout=25)
        if raw.ok:
            content = raw.text
    if not content.strip():
        return empty
    try:
        parsed = json.loads(content)
    except ValueError:
        return dict(empty, raw=content)
    if not isinstance(parsed, dict):
        return dict(empty, raw=content)
    messages = parsed.get("messages")
    clean = []
    if isinstance(messages, list):
        for raw in messages:
            item = to_common(raw, "phone")
            if item:
                clean.append(item)
    return {
        "messages": clean,
        "summary": parsed.get("summary") if isinstance(parsed.get("summary"), str) else "",
        "summaryTs": int(parsed.get("summaryTs") or 0),
        "clearedAt": int(parsed.get("clearedAt") or 0),
        "raw": content,
    }


def canonical(payload: dict[str, Any]) -> str:
    body = {
        "version": 1,
        "summary": payload.get("summary") or "",
        "summaryTs": int(payload.get("summaryTs") or 0),
        "clearedAt": int(payload.get("clearedAt") or 0),
        "messages": [
            {
                "role": m.get("role"),
                "text": m.get("text"),
                "ts": int(m.get("ts") or 0),
                "src": m.get("src") or "pc",
                **({"meme": m["meme"]} if m.get("meme") else {}),
            }
            for m in payload.get("messages") or []
        ],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_remote(token: str, gist_id: str, payload: dict[str, Any]) -> None:
    body = {
        "files": {
            GIST_FILE: {
                "content": json.dumps(
                    {
                        "version": 1,
                        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "summary": payload.get("summary") or "",
                        "summaryTs": int(payload.get("summaryTs") or 0),
                        "clearedAt": int(payload.get("clearedAt") or 0),
                        "messages": json.loads(canonical(payload))["messages"],
                    },
                    ensure_ascii=False,
                    indent=1,
                )
            }
        }
    }
    res = requests.patch(
        f"{API}/gists/{gist_id}", headers=headers(token), json=body, timeout=25
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(friendly(res.status_code))


# ---------------------------------------------------------------- 同步


def sync_once(quiet: bool = False) -> bool:
    config = load_config()
    token = str(config.get("token") or "").strip()
    gist_id = str(config.get("gist_id") or "").strip()

    if not token or not gist_id:
        if not quiet:
            log("還沒設定同步。請把 token 與 gist_id 寫進 " + str(CONFIG))
        return False

    try:
        remote = read_remote(token, gist_id)
        local = read_pet()

        cleared_at = max(int(config.get("cleared_at") or 0), remote["clearedAt"])
        if cleared_at != int(config.get("cleared_at") or 0):
            config["cleared_at"] = cleared_at
            save_config(config)

        merged = merge(local, remote["messages"], cleared_at)

        payload = {
            "summary": remote["summary"],
            "summaryTs": remote["summaryTs"],
            "clearedAt": cleared_at,
            "messages": merged,
        }

        # 桌寵記憶只有在真的變了才寫，避免一直改檔案
        if canonical({"messages": local}) != canonical({"messages": merged}):
            write_pet(merged)

        # 雲端只有在內容不同才 PATCH，避免製造一堆修訂版本
        remote_canon = canonical(
            {
                "messages": remote["messages"],
                "summary": remote["summary"],
                "summaryTs": remote["summaryTs"],
                "clearedAt": remote["clearedAt"],
            }
        )
        if remote_canon != canonical(payload):
            write_remote(token, gist_id, payload)

        config["last_sync"] = datetime.now().astimezone().isoformat(timespec="seconds")
        config["last_count"] = len(merged)
        save_config(config)
        log(f"同步完成：{len(merged)} 則（本機 {len(local)}、雲端 {len(remote['messages'])}）", quiet)
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"同步失敗：{exc}", quiet)
        return False


def watch(interval: int) -> None:
    guard = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        guard.bind(("127.0.0.1", LOCK_PORT))
        guard.listen(1)
    except OSError:
        log("已經有一個同步程式在跑了，這次不重複啟動。")
        return

    log(f"記憶同步常駐啟動，每 {interval} 秒一次。")
    try:
        while True:
            sync_once(quiet=True)
            time.sleep(max(15, interval))
    except KeyboardInterrupt:
        log("記憶同步結束。")
    finally:
        guard.close()


def show_status() -> None:
    config = load_config()
    token = str(config.get("token") or "")
    print(f"設定檔：{CONFIG}")
    print(f"金鑰：{'有（' + token[:4] + '…）' if token else '沒有'}")
    print(f"抽屜 ID：{config.get('gist_id') or '沒有'}")
    print(f"上次同步：{config.get('last_sync') or '從未'}")
    print(f"上次則數：{config.get('last_count') or 0}")
    print(f"桌寵記憶：{PET_MEMORY}（{len(read_pet())} 則）")
    print(f"清除時間點：{config.get('cleared_at') or 0}")


def main() -> int:
    parser = argparse.ArgumentParser(description="大肥魚記憶同步")
    parser.add_argument("--watch", action="store_true", help="常駐，每 N 秒同步")
    parser.add_argument("--interval", type=int, default=60, help="常駐間隔秒數")
    parser.add_argument("--status", action="store_true", help="顯示狀態")
    parser.add_argument("--wipe", action="store_true", help="清空兩邊記憶")
    parser.add_argument("--set-token", help="寫入 GitHub token")
    parser.add_argument("--set-gist", help="寫入 Gist ID")
    args = parser.parse_args()

    if args.set_token or args.set_gist:
        config = load_config()
        if args.set_token:
            config["token"] = args.set_token.strip()
        if args.set_gist:
            config["gist_id"] = args.set_gist.strip()
        save_config(config)
        print(f"已寫入 {CONFIG}")
        return 0

    if args.status:
        show_status()
        return 0

    if args.wipe:
        config = load_config()
        config["cleared_at"] = int(time.time() * 1000)
        save_config(config)
        write_pet([])
        ok = sync_once()
        print("兩邊記憶都清掉了。" if ok else "本機清掉了，但雲端同步失敗，稍後再試。")
        return 0 if ok else 1

    if args.watch:
        watch(args.interval)
        return 0

    return 0 if sync_once() else 1


if __name__ == "__main__":
    raise SystemExit(main())
