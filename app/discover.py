"""主動去回覆陌生人的公開貼文。

流程：關鍵字搜尋公開貼文 → 篩掉不該回的 → 生成一句話 → 用 reply_to_id 回覆。

這個功能需要 Meta 的 `threads_keyword_search` 進階權限（App Review）。
沒通過前，API 會回 400 / code 10，這裡會直接停下來並說明原因，
不會亂發、也不會讓排程一直噴錯。
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any

from threads_api import ThreadsError, make_client

from . import persona, state, textutil
from . import replies as replies_mod

log = logging.getLogger("dafeiyu.discover")

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


class DiscoverUnavailable(RuntimeError):
    """權限還沒開，或這個 App 還不能搜尋公開貼文。"""


def enabled(config: dict[str, Any]) -> bool:
    return bool((config.get("discover") or {}).get("enabled", False))


def _parse_ts(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _person_seen_recently(
    data: dict[str, Any], username: str, cooldown_days: float
) -> bool:
    if cooldown_days <= 0:
        return False
    person = (data.get("people") or {}).get(username)
    if not isinstance(person, dict):
        return False
    last = float(person.get("last_seen", 0) or 0)
    return bool(last) and (time.time() - last) < cooldown_days * 86400


def _search(client: Any, keyword: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return client.search_posts(
            keyword,
            search_type=str(cfg.get("search_type", "RECENT")).upper(),
            limit=int(cfg.get("limit", 25)),
        )
    except ThreadsError as exc:
        if exc.code == 10:
            raise DiscoverUnavailable(
                "Meta 還沒給這個 App「threads_keyword_search」權限。\n"
                "這是 App Review 的審核項目，不是程式壞掉：\n"
                "  1. 到 developers.facebook.com → 你的 App → App Review\n"
                "  2. 申請 threads_keyword_search 的進階存取\n"
                "  3. 通過後把 config.json 的 discover.enabled 改成 true\n"
                "申請資料在 docs/app-review/。"
            ) from exc
        raise


def run_discover(
    config: dict[str, Any],
    secrets: dict[str, Any],
    *,
    dry_run: bool = False,
    limit: int | None = None,
    keyword: str | None = None,
) -> int:
    """跑一輪主動回覆，回傳這一輪回了幾則。"""
    cfg = config.get("discover") or {}
    client = make_client(config, secrets)
    me = client.me()
    my_username = str(me.get("username", ""))

    data = state.load()
    max_per_day = int(cfg.get("max_per_day", 3))
    done_today = int(data["daily"].get("discover", 0))
    if done_today >= max_per_day:
        log.info("今天已主動回 %s 則，達到上限 %s", done_today, max_per_day)
        return 0

    max_per_run = int(limit or cfg.get("max_per_run", 2))
    keywords = (
        [keyword]
        if keyword
        else [str(k).strip() for k in (cfg.get("keywords") or []) if str(k).strip()]
    )
    if not keywords:
        log.warning("discover.keywords 是空的，沒有東西可搜")
        return 0

    min_age = float(cfg.get("min_age_minutes", 10)) * 60
    max_age = float(cfg.get("max_age_hours", 12)) * 3600
    min_chars = int(cfg.get("min_chars", 12))
    reply_chars = int(cfg.get("reply_max_chars", 50))
    cooldown_days = float(cfg.get("same_user_cooldown_days", 7))
    min_interval = float(cfg.get("min_interval_seconds", 30))
    require_cjk = bool(cfg.get("require_cjk", True))
    allow_replies = bool(cfg.get("allow_replies", False))
    blocked = config.get("safety", {}).get("blocked_keywords", [])

    now = time.time()
    seen: set[str] = set()
    handled_users: set[str] = set()
    count = 0

    for kw in keywords:
        if count >= max_per_run or done_today >= max_per_day:
            break

        posts = _search(client, kw, cfg)
        log.info("搜尋「%s」→ %s 篇", kw, len(posts))

        for post in posts:
            if count >= max_per_run or done_today >= max_per_day:
                break

            post_id = str(post.get("id", ""))
            username = str(post.get("username", ""))
            text = textutil.clean(str(post.get("text", "")))

            if not post_id or post_id in seen:
                continue
            seen.add(post_id)

            if username == my_username:
                continue
            if post_id in data.get("replied", {}) or post_id in data.get("skipped", {}):
                continue
            if len(text) < min_chars:
                continue
            if require_cjk and len(CJK.findall(text)) < 6:
                continue
            if post.get("is_reply") and not allow_replies:
                continue
            if cfg.get("skip_quote_posts") and post.get("is_quote_post"):
                continue

            created = _parse_ts(post.get("timestamp"))
            if created:
                age = now - created
                if age < min_age:
                    continue
                if age > max_age:
                    continue

            if _person_seen_recently(data, username, cooldown_days):
                log.info("跳過 @%s（最近才聊過）", username)
                continue
            if username in handled_users:
                log.info("跳過 @%s（這一輪已經回過他）", username)
                continue

            hit = textutil.contains_blocked(text, blocked)
            if hit:
                log.info("跳過 @%s 的貼文（命中「%s」）", username, hit)
                with state.transaction() as fresh:
                    fresh["skipped"][post_id] = {
                        "reason": f"blocked:{hit}",
                        "username": username,
                        "ts": time.time(),
                        "source": "discover",
                    }
                data = state.load()
                continue

            person = (data.get("people") or {}).get(username)
            prompt = persona.stranger_reply_prompt(text, username, person)
            try:
                generated = replies_mod.generate_reply_text(
                    config, secrets, prompt, max_chars=reply_chars
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("生成留言失敗（@%s）：%s", username, exc)
                continue

            if not generated:
                log.info("模型選擇不回 @%s", username)
                with state.transaction() as fresh:
                    fresh["skipped"][post_id] = {
                        "reason": "model_skip",
                        "username": username,
                        "ts": time.time(),
                        "source": "discover",
                    }
                data = state.load()
                continue

            reply_text, provider = generated

            if dry_run:
                print(f"[dry-run] @{username}：{text[:60]}")
                print(f"  → {reply_text}")
            else:
                try:
                    reply_id = client.post_text(reply_text, reply_to_id=post_id)
                except ThreadsError as exc:
                    log.warning("回覆 @%s 失敗：%s", username, exc)
                    if exc.code == 10:
                        log.error("權限不足：回覆公開貼文需要 threads_content_publish")
                        return count
                    continue

                with state.transaction() as fresh:
                    fresh["replied"][post_id] = {
                        "reply_id": reply_id,
                        "username": username,
                        "text": reply_text,
                        "provider": provider,
                        "ts": time.time(),
                        "source": "discover",
                        "permalink": str(post.get("permalink", "")),
                    }
                    fresh["daily"]["discover"] = (
                        int(fresh["daily"].get("discover", 0)) + 1
                    )
                    fresh["last_discover_at"] = time.time()
                    replies_mod.remember_person(fresh, username, text, reply_text)
                data = state.load()
                log.info("已主動回覆 @%s：%s", username, reply_text)

            count += 1
            done_today += 1
            handled_users.add(username)
            if not dry_run:
                time.sleep(min_interval)

    log.info("本輪主動回覆 %s 則（今日累計 %s）", count, done_today)
    return count
