from __future__ import annotations

import re

try:  # 簡體轉繁體（台灣慣用詞）
    from opencc import OpenCC

    _cc = OpenCC("s2twp")
except Exception:  # pragma: no cover - 沒裝就原樣輸出
    _cc = None


# 模型偶爾會挑錯字或用了中國用語。這裡只放「改了不會壞」的對照，
# 在簡繁轉換後再套一次，貼文和回覆都會用到。
_TYPOS = {
    # 錯字
    "喂進": "餵進",
    "喂給": "餵給",
    "喂食": "餵食",
    "喂養": "餵養",
    "喂牠": "餵牠",
    "因該": "應該",
    "以經": "已經",
    "一只": "一隻",
    "兩只": "兩隻",
    "三只": "三隻",
    "幾只": "幾隻",
    # 中國用語 → 台灣用語
    "信息": "訊息",
    "打車": "叫車",
    "視頻": "影片",
    "軟件": "軟體",
    "硬件": "硬體",
    "硬盤": "硬碟",
    "內存": "記憶體",
    "網絡": "網路",
    "打印": "列印",
    "默認": "預設",
    "屏幕": "螢幕",
    "鼠標": "滑鼠",
    "短信": "簡訊",
    "博客": "部落格",
    "文件夾": "資料夾",
}


def to_traditional(text: str) -> str:
    t = _cc.convert(text) if _cc else text
    for wrong, right in _TYPOS.items():
        t = t.replace(wrong, right)
    return t


def clean(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", t)
    t = re.sub(r"\n?```\s*$", "", t)
    t = re.sub(r"^\s*以下是[^\n]{0,20}[:：]\s*", "", t)
    t = re.sub(r"^\s*(貼文|回覆|輸出|內容)[:：]\s*", "", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*(?:大肥魚|大肥鯨|本鯨)\s*[:：]\s*", "", t)
    t = t.strip().strip('"').strip("“”").strip("「」").strip("『』")
    # 模型很愛在結尾署名，這裡直接砍掉。
    t = re.sub(
        r"(?:\r?\n)+\s*(?:[—–\-]{1,2}\s*)?(?:大肥魚|大肥鯨|本鯨|鯨魚娘)\s*[。！!]?\s*$",
        "",
        t,
    )
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # 括號動作統一用全形，看起來比較一致：「(甩尾巴)」→「（甩尾巴）」
    t = re.sub(r"\(([^\x00-\x7f]{1,12})\)", r"（\1）", t)
    return t.strip()


def fit(text: str, limit: int) -> str:
    """在 limit 字內找一個句尾收掉，真的找不到才硬切。"""
    if len(text) <= limit:
        return text

    window = text[:limit]
    for punct in ("。", "！", "？", "!", "?", "；", ";", "\n"):
        idx = window.rfind(punct)
        if idx >= int(limit * 0.45):
            return text[: idx + 1].strip()

    return window.rstrip("，,、 　") + "。"


def limit_hashtags(text: str, max_n: int = 1) -> str:
    tags = re.findall(r"#[^\s#]+", text)
    if len(tags) <= max_n:
        return text
    for tag in tags[max_n:]:
        text = text.replace(tag, "")
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def contains_blocked(text: str, blocked: list[str]) -> str | None:
    """回傳命中的第一個關鍵字，沒有就回 None。"""
    lowered = (text or "").lower()
    for word in blocked:
        if word.lower() in lowered:
            return word
    return None


def is_too_short(text: str, minimum: int) -> bool:
    return len(re.sub(r"\s", "", text)) < minimum


def looks_like_refusal(text: str) -> bool:
    markers = (
        "抱歉，我不能",
        "很抱歉，我無法",
        "作為一個 AI",
        "身為一個 AI 語言模型",
        "我無法協助",
    )
    return any(m in text for m in markers)
