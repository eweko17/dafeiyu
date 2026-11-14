from __future__ import annotations

import logging
import re
import time
from typing import Any

from brain import router
from threads_api import ThreadsError, make_client

from . import persona, state, textutil

log = logging.getLogger("dafeiyu.replies")

BOT_HINTS = re.compile(r"(大肥魚|大肥鱼|肥魚|肥鱼|小飛鯨|小飞鲸|鯨魚娘|鲸鱼娘)")


def _is_probably_another_fish(username: str, text: str) -> bool:
    return bool(BOT_HINTS.search(username or "")) and ("本鯨" in text or "本鲸" in text)


def _recent_replies_to(data: dict[str, Any], username: str) -> int:
    cutoff = time.time() - 86400
    count = 0
    for item in data.get("replied", {}).values():
        if item.get("username") == username and item.get("ts", 0) >= cutoff:
            count += 1
    return count


# 留言樹最多往下追幾層（貼文 → 留言 → 回覆 → 回覆的回覆…）。
# 對方回她、她再回、對方又回，會一層一層往下長；追太淺就會「聊到第二輪就停住」。
MAX_REPLY_DEPTH = 10
# 每篇貼文每輪最多打幾次 /replies，避免爆量或撞到 API 速率限制。
MAX_REPLY_CALLS = 40
# 每篇貼文每輪最多收幾則留言（含各層）。
MAX_COMMENTS = 400


def _collect_comments(client: Any, post_id: str) -> list[dict[str, Any]]:
    """抓貼文底下的整棵留言樹（含留言的回覆、回覆再回覆…）。

    Threads 的 /replies 只回「直接掛在這個 id 底下」的留言，所以要用 BFS 逐層往下：
    貼文底下是第 1 層，留言底下是第 2 層，她回完對方再回就是第 3 層……
    舊版只追到第 2 層，所以別人回在她的回覆下面時，那一則永遠看不到，
    她就會停在那裡不講話。
    """
    top = client.replies(post_id)

    seen: set[str] = set()
    collected: list[dict[str, Any]] = []
    queue: list[tuple[str, int]] = []

    for item in top:
        item_id = str(item.get("id", ""))
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        collected.append(item)
        if item.get("has_replies") and MAX_REPLY_DEPTH >= 2:
            queue.append((item_id, 2))

    calls = 0
    while queue and calls < MAX_REPLY_CALLS and len(collected) < MAX_COMMENTS:
        parent_id, depth = queue.pop(0)
        calls += 1
        try:
            children = client.replies(parent_id)
        except ThreadsError as exc:
            log.warning("讀取留言 %s 的子回覆失敗：%s", parent_id, exc)
            continue
        for child in children:
            child_id = str(child.get("id", ""))
            if not child_id or child_id in seen:
                continue
            seen.add(child_id)
            collected.append(child)
            if child.get("has_replies") and depth + 1 <= MAX_REPLY_DEPTH:
                queue.append((child_id, depth + 1))

    if queue:
        log.info(
            "留言樹還有 %s 個分支沒追完（本輪已抓 %s 則、呼叫 %s 次），下一輪會再抓",
            len(queue),
            len(collected),
            calls,
        )

    return collected


def _looks_unfinished(text: str) -> bool:
    """模型偶爾會講到一半就斷掉，這種回覆發出去很奇怪。"""
    t = text.strip()
    if not t:
        return True
    if t.count("（") != t.count("）") or t.count("(") != t.count(")"):
        return True
    return t.endswith(("，", ",", "、", "…", "（", "(", "：", ":"))


def generate_reply_text(
    config: dict[str, Any],
    secrets: dict[str, Any],
    user_prompt: str,
    *,
    max_chars: int,
) -> tuple[str, str] | None:
    """把 prompt 丟給模型，回傳（整理過的文字, provider）；不想回就回 None。"""
    system = persona.system_prompt()
    blocked = config.get("safety", {}).get("blocked_keywords", [])

    for attempt in range(2):
        raw, provider = router.generate(system, user_prompt, config, secrets)
        cleaned = textutil.clean(textutil.to_traditional(raw))

        head = cleaned.strip()
        if re.match(r"^skip", head, re.IGNORECASE):
            return None
        # 模型偶爾會先亂寫一段、最後才補上 SKIP；只要出現就當作不想回。
        if re.search(r"(?:^|\s)skip\b", cleaned, re.IGNORECASE):
            log.info("模型輸出含 SKIP，跳過")
            return None

        cleaned = textutil.fit(cleaned, max_chars)
        if not cleaned:
            return None

        # 講到一半就斷掉就再產一次；第二次還是一樣才勉強收尾。
        if attempt == 0 and _looks_unfinished(cleaned):
            log.info("回覆被截斷（%s），重新產生一次", cleaned[-6:])
            continue

        cleaned = cleaned.rstrip("，,、…：: ")
        if cleaned and cleaned[-1] not in "。！？!?）)」":
            cleaned += "。"

        if textutil.contains_blocked(cleaned, blocked):
            return None

        return cleaned, provider

    return None


def _generate_reply(
    config: dict[str, Any],
    secrets: dict[str, Any],
    post_text: str,
    username: str,
    comment: str,
    person: dict[str, Any] | None = None,
) -> tuple[str, str] | None:
    user = persona.reply_prompt(post_text, username, comment, person)
    max_chars = int(config.get("replies", {}).get("max_chars", 80))
    return generate_reply_text(config, secrets, user, max_chars=max_chars)


def remember_person(
    data: dict[str, Any], username: str, said: str, reply: str
) -> None:
    """更新「對這個人的記憶」：見過幾次、說過什麼、上次怎麼回。"""
    now = time.time()
    people = data.setdefault("people", {})
    person = people.get(username)
    if not isinstance(person, dict):
        person = {"first_seen": now, "count": 0, "said": []}
    person["count"] = int(person.get("count", 0)) + 1
    person["last_seen"] = now
    history = [str(x) for x in (person.get("said") or []) if x]
    history.append(said[:80])
    person["said"] = history[-6:]
    person["last_reply"] = reply
    person["last_reply_ts"] = now
    people[username] = person


def run_replies(
    config: dict[str, Any],
    secrets: dict[str, Any],
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> int:
    replies_cfg = config.get("replies", {})
    if not replies_cfg.get("enabled", True):
        log.info("回覆功能已關閉（replies.enabled=false）")
        return 0

    client = make_client(config, secrets)
    me = client.me()
    my_username = str(me.get("username", ""))

    data = state.load()
    max_per_day = int(replies_cfg.get("max_per_day", 100))
    max_per_run = int(limit or replies_cfg.get("max_per_run", 8))
    min_interval = int(replies_cfg.get("min_interval_seconds", 4))
    poll_days = int(replies_cfg.get("poll_days", 7))
    blocked = config.get("safety", {}).get("blocked_keywords", [])
    # 完全不想再回的人：帳號放進 safety.blocked_usernames（不分大小寫、不用加 @）。
    blocked_users = {
        str(u).strip().lstrip("@").lower()
        for u in (config.get("safety", {}).get("blocked_usernames") or [])
        if str(u).strip()
    }
    # 同一個人一天最多回幾則；0 = 不限（預設），這樣對方一直回就一直聊。
    per_person_cap = int(replies_cfg.get("max_per_person_per_day", 0) or 0)

    done_today = int(data["daily"].get("replies", 0))
    if done_today >= max_per_day:
        log.info("今天已回 %s 則，達到上限 %s", done_today, max_per_day)
        return 0

    cutoff = time.time() - poll_days * 86400
    posts = [p for p in data.get("posts", []) if p.get("ts", 0) >= cutoff]
    replied_count = 0

    for post in reversed(posts):
        if replied_count >= max_per_run or done_today >= max_per_day:
            break

        try:
            comments = _collect_comments(client, str(post["id"]))
        except ThreadsError as exc:
            log.warning("讀取貼文 %s 的留言失敗：%s", post.get("id"), exc)
            if exc.code == 10:
                log.error("權限不足，請確認 token 有 threads_read_replies")
                break
            # code 100 / subcode 33＝這則貼文已經不存在（或不再公開）。
            # 留在名單裡只會每輪都撞一次，直接移掉。
            if exc.code == 100 and exc.subcode == 33:
                gone_id = str(post.get("id", ""))
                with state.transaction() as fresh:
                    fresh["posts"] = [
                        p for p in fresh.get("posts", []) if str(p.get("id", "")) != gone_id
                    ]
                data = state.load()
                log.info("貼文 %s 已不存在，從回覆名單移除", gone_id)
            continue

        # 這一串留言的 id，用來判斷某則留言是不是回在這串裡面。
        thread_ids = {str(c.get("id", "")) for c in comments}
        thread_ids.discard("")

        for comment in comments:
            if replied_count >= max_per_run or done_today >= max_per_day:
                break

            comment_id = str(comment.get("id", ""))
            username = str(comment.get("username", ""))
            body = textutil.clean(str(comment.get("text", "")))
            # Threads API 的 replied_to 有時候是字串，有時候是 {"id": "..."}。
            parent_raw = comment.get("replied_to")
            if isinstance(parent_raw, dict):
                parent_id = str(parent_raw.get("id", ""))
            else:
                parent_id = str(parent_raw or "")

            if not comment_id or not body:
                continue
            if comment_id in data.get("replied", {}) or comment_id in data.get("skipped", {}):
                continue
            if username == my_username:
                continue
            # 只回「這篇貼文底下」的留言，包含留言再底下的討論串。
            if parent_id != str(post["id"]) and parent_id not in thread_ids:
                continue
            if _is_probably_another_fish(username, body):
                log.info("跳過另一隻大肥魚：@%s", username)
                continue
            if username.lstrip("@").lower() in blocked_users:
                log.info("跳過封鎖名單裡的 @%s", username)
                continue
            if per_person_cap > 0 and _recent_replies_to(data, username) >= per_person_cap:
                log.info(
                    "今天已經回過 @%s %s 次（上限 %s），先跳過",
                    username,
                    per_person_cap,
                    per_person_cap,
                )
                continue

            hit = textutil.contains_blocked(body, blocked)
            if hit:
                log.info("跳過 @%s 的留言（命中「%s」）", username, hit)
                with state.transaction() as fresh:
                    fresh["skipped"][comment_id] = {
                        "reason": f"blocked:{hit}",
                        "username": username,
                        "ts": time.time(),
                    }
                data = state.load()
                continue

            try:
                generated = _generate_reply(
                    config,
                    secrets,
                    str(post.get("text", "")),
                    username,
                    body,
                    (data.get("people") or {}).get(username),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("生成回覆失敗（@%s）：%s", username, exc)
                continue

            if not generated:
                log.info("模型選擇不回覆 @%s", username)
                with state.transaction() as fresh:
                    fresh["skipped"][comment_id] = {
                        "reason": "model_skip",
                        "username": username,
                        "ts": time.time(),
                    }
                data = state.load()
                continue

            reply_text, provider = generated
            if dry_run:
                print(f"[dry-run] @{username}：{body}\n  → {reply_text}")
            else:
                try:
                    reply_id = client.post_text(reply_text, reply_to_id=comment_id)
                except ThreadsError as exc:
                    log.warning("回覆 @%s 失敗：%s", username, exc)
                    if exc.code == 10:
                        log.error("權限不足，請確認 token 有 threads_content_publish")
                        return replied_count
                    continue

                with state.transaction() as fresh:
                    fresh["replied"][comment_id] = {
                        "reply_id": reply_id,
                        "username": username,
                        "text": reply_text,
                        "provider": provider,
                        "ts": time.time(),
                    }
                    fresh["daily"]["replies"] = int(fresh["daily"].get("replies", 0)) + 1
                    fresh["last_reply_at"] = time.time()
                    remember_person(fresh, username, body, reply_text)
                data = state.load()
                log.info("已回覆 @%s：%s", username, reply_text)

            replied_count += 1
            done_today += 1
            if not dry_run:
                time.sleep(min_interval)

    log.info("本輪回覆 %s 則（今日累計 %s）", replied_count, done_today)
    return replied_count
