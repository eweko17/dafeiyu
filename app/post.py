from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from brain import router
from threads_api import ThreadsError, make_client

from . import persona, state, textutil

log = logging.getLogger("dafeiyu.post")

MOODS = [
    "剛睡醒，還有點呆",
    "吃飽了，心情很好",
    "被主人派工作，有點不甘願",
    "想睡但不能睡",
    "摸魚被發現，心虛",
    "今天特別聰明（自認為）",
    "莫名有點 emo",
    "很想吃宵夜",
    "尾巴很蓬，心情不錯",
    "被叫胖，正在生氣",
]

TOPICS = [
    "白飯與 Token 的關係",
    "上班摸魚的一百種姿勢",
    "主人又派了奇怪的工作",
    "減肥失敗的第 N 天",
    "伺服器繁忙的時候我在幹嘛",
    "捷運上看到的人類",
    "超商新的微波食品",
    "颱風天要不要囤白飯",
    "AI 新聞看得似懂非懂",
    "週末的計畫（睡覺）",
    "被叫胖的應對方式",
    "深夜睡不著的時候",
    "珍奶要不要加珍珠",
    "開會時靈魂出竅",
    "今天學到的新詞",
    "如果不用工作想做什麼",
    "冷氣與棉被的拉扯",
    "手機電量剩 3% 的焦慮",
]


def _now(config: dict[str, Any]) -> datetime:
    try:
        return datetime.now(ZoneInfo(str(config.get("timezone", "Asia/Taipei"))))
    except ZoneInfoNotFoundError:
        return datetime.now()


def _choose_topic(data: dict[str, Any], cooldown: int) -> str:
    recent = {p.get("topic") for p in data.get("posts", [])[-cooldown:]}
    pool = [t for t in TOPICS if t not in recent] or TOPICS
    return random.choice(pool)


def _validate(text: str, config: dict[str, Any]) -> str | None:
    posting = config.get("posting", {})
    minimum = int(posting.get("min_chars", 100))
    maximum = int(posting.get("max_chars", 380))
    blocked = config.get("safety", {}).get("blocked_keywords", [])

    if not text:
        return "內容是空的"
    if textutil.is_too_short(text, minimum):
        return f"內容太短（少於 {minimum} 字）"
    if len(text) > maximum:
        return f"內容太長（超過 {maximum} 字）"
    hit = textutil.contains_blocked(text, blocked)
    if hit:
        return f"命中禁用詞「{hit}」"
    if textutil.looks_like_refusal(text):
        return "模型在道歉或拒絕，不像大肥魚"
    return None


def _generate_once(
    config: dict[str, Any],
    secrets: dict[str, Any],
    now: datetime,
    mood: str,
    topic: str,
    recent: list[str],
    extra: str = "",
) -> tuple[str, str]:
    system = persona.system_prompt()
    user = persona.post_prompt(now, mood, topic, recent) + extra
    raw, provider = router.generate(system, user, config, secrets)
    text = textutil.clean(textutil.to_traditional(raw))
    text = textutil.limit_hashtags(text, 1)
    text = textutil.fit(text, int(config.get("posting", {}).get("max_chars", 380)))
    return text, provider


def create_post(
    config: dict[str, Any],
    secrets: dict[str, Any],
    *,
    slot: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    posting = config.get("posting", {})
    if not posting.get("enabled", True):
        log.info("發文功能已關閉（posting.enabled=false）")
        return {"skipped": True, "reason": "disabled"}

    data = state.load()
    max_per_day = int(posting.get("max_per_day", 3))
    if data["daily"].get("posts", 0) >= max_per_day:
        log.info("今天已發 %s 篇，達到上限 %s", data["daily"]["posts"], max_per_day)
        return {"skipped": True, "reason": "daily_limit"}

    now = _now(config)
    mood = random.choice(MOODS)
    topic = _choose_topic(data, int(posting.get("topic_cooldown_posts", 6)))
    recent = [str(p.get("text", "")) for p in data.get("posts", [])[-8:]]

    log.info("開始生成貼文（slot=%s, 心情=%s, 主題=%s）", slot, mood, topic)
    attempts = int(posting.get("max_retries", 2)) + 1
    text = ""
    provider = ""
    problem = ""

    for attempt in range(1, attempts + 1):
        extra = persona.retry_note(problem) if problem else ""
        try:
            text, provider = _generate_once(
                config, secrets, now, mood, topic, recent, extra
            )
        except Exception as exc:  # noqa: BLE001
            problem = f"生成失敗：{exc}"
            log.warning("第 %s 次生成失敗：%s", attempt, exc)
            # 連線／金鑰這類問題重試同一個 prompt 沒有意義，直接停。
            break

        problem = _validate(text, config) or ""
        if not problem:
            break
        log.warning("第 %s 次內容不合格：%s", attempt, problem)

    if problem:
        log.error("生成失敗，最後原因：%s", problem)
        return {"skipped": True, "reason": problem}

    if dry_run:
        log.info("（dry-run）以下是要發的內容：\n%s", text)
        return {
            "dry_run": True,
            "text": text,
            "provider": provider,
            "mood": mood,
            "topic": topic,
        }

    try:
        client = make_client(config, secrets)
        media_id = client.post_text(text)
    except ThreadsError as exc:
        log.error("發文失敗：%s", exc)
        return {"skipped": True, "reason": f"threads_error: {exc}"}

    with state.transaction() as fresh:
        fresh["posts"].append(
            {
                "id": media_id,
                "text": text,
                "topic": topic,
                "mood": mood,
                "provider": provider,
                "ts": time.time(),
                "iso": now.isoformat(),
            }
        )
        fresh["daily"]["posts"] = int(fresh["daily"].get("posts", 0)) + 1
        fresh["last_post_at"] = time.time()

    log.info("已發文：%s（%s, %s）", media_id, provider, topic)
    return {
        "id": media_id,
        "text": text,
        "provider": provider,
        "mood": mood,
        "topic": topic,
    }
