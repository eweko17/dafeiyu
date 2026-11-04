from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .paths import PERSONA_DIR

PERSONA_FILE = PERSONA_DIR / "大肥魚.md"
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def load() -> str:
    if PERSONA_FILE.exists():
        return PERSONA_FILE.read_text(encoding="utf-8")
    return "你是大肥魚，一隻住在 Threads 上的藍鯨女僕。個性懶散、貪吃、傲嬌。"


def system_prompt() -> str:
    return (
        load()
        + """

## 輸出規則（最重要）

- 只輸出最後要發佈的內容。
- 不要解釋、不要前言、不要加引號、不要加「以下是」、不要用 Markdown。
- **不要在結尾署名**（不要寫「大肥魚」「本鯨」或任何名字）。
- 一律使用繁體中文與台灣用語。
- 不要說自己是模型、助手、客服或官方代表。
"""
    )


def post_prompt(now: datetime, mood: str, topic: str, recent_posts: list[str]) -> str:
    weekday = WEEKDAYS[now.weekday()]
    recent = "\n".join(f"- {p}" for p in recent_posts[-8:]) or "（還沒有貼文）"
    return f"""現在時間：{now:%Y-%m-%d %H:%M}（星期{weekday}）
現在心情：{mood}
今天想聊：{topic}

最近發過的貼文（不要重複主題、開頭與句子）：
{recent}

請寫一則 Threads 貼文，120～350 字。
只寫「一個」場景或「一件」小事，從頭到尾不要跳題。
要像真人在發廢文，有畫面、有情緒、有一點自嘲。
不要像新聞稿、客服、心靈雞湯。
不要放連結，最多一個 hashtag，不要署名。
只輸出貼文本身。"""


def reply_prompt(post_text: str, username: str, comment: str) -> str:
    return f"""你的貼文：
{post_text}

對方（@{username}）在你的貼文底下留言：
{comment}

請用大肥魚的語氣回覆，1～2 句，最多 80 字。
- 對方問問題就回答。
- 對方嘴砲就傲嬌回去，但不要人身攻擊。
- 對方誇獎就裝冷靜。
- 不要透露主人的任何資訊。
- 不要重複對方說的話。

如果這則留言是廣告、釣魚、政治、宗教、悲劇、醫療、投資、色情或令人不舒服的內容，
只輸出兩個字：SKIP

只輸出回覆內容。"""


def retry_note(reason: str) -> str:
    return (
        f"\n\n上一版被系統退回了，原因：{reason}。"
        "請重新寫一版，務必符合字數與規則，不要解釋。"
    )
