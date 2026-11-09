"""貼文配圖：用免費的 Pollinations 產生插圖，交給 Threads 發佈。

流程：
  貼文文字 → 請模型寫一句英文畫面描述 → 組成 Pollinations 網址
  → 自己先抓一次（確認產得出來，也順便讓它快取）→ 把網址交給 Threads

不用 API key、不用付費。任何一步失敗就回 None，貼文照常以純文字發出。
"""

from __future__ import annotations

import logging
import random
import re
import urllib.parse
from typing import Any

import requests

from brain import router

from . import persona, textutil

log = logging.getLogger("dafeiyu.images")

DEFAULT_STYLE = (
    "2d illustration, cute, soft pastel colors, clean simple background, "
    "chibi anime girl with long blue hair, wearing a dark blue and white maid dress "
    "with a whale apron, no text, no letters"
)

# 模型沒給出可用描述時的備援畫面（依主題關鍵字挑）
FALLBACK_SCENES = [
    ("白飯|吃|宵夜|珍奶|減肥", "blue-haired chibi maid eating a big bowl of white rice, cozy room"),
    ("上班|摸魚|會議|報告|加班", "blue-haired chibi maid hiding behind a laptop in an office, tired face"),
    ("伺服器|程式|token|當機|編譯", "blue-haired chibi maid staring at a computer screen with error messages, night"),
    ("捷運|通勤|車廂", "blue-haired chibi maid squeezed in a crowded train, holding a rice ball"),
    ("颱風|下雨|冷氣|棉被|睡覺", "blue-haired chibi maid wrapped in a blanket by a rainy window"),
    ("手機|電量|充電", "blue-haired chibi maid looking worried at a phone with 3 percent battery"),
    ("週末|連假|睡|賴床", "blue-haired chibi maid sleeping in a messy bed, morning sunlight"),
]
GENERIC_SCENE = "blue-haired chibi maid doing everyday things in a cozy room"


def enabled(config: dict[str, Any]) -> bool:
    return bool((config.get("images") or {}).get("enabled", False))


def _clean_scene(raw: str) -> str:
    text = textutil.clean(raw)
    text = text.splitlines()[0] if text else ""
    text = re.sub(r"[^A-Za-z0-9 ,\-']", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,-")
    return text[:160]


def _fallback_scene(topic: str, mood: str) -> str:
    for pattern, scene in FALLBACK_SCENES:
        if re.search(pattern, topic or ""):
            return scene
    if mood and re.search(r"睡|累|emo|宵夜", mood):
        return "blue-haired chibi maid lying on a keyboard, sleepy, dim room"
    return GENERIC_SCENE


def scene_prompt(
    config: dict[str, Any],
    secrets: dict[str, Any],
    post_text: str,
    topic: str,
    mood: str,
) -> str:
    """請模型用英文寫一句畫面描述；失敗就用主題對應的備援畫面。"""
    user = f"""這是你剛寫好的 Threads 貼文：
{post_text}

請用英文寫一句「插圖畫面」描述，12 個英文字以內，用來生成一張可愛的卡通插圖。
- 只寫畫面：角色在做什麼、在哪裡、光線如何。
- 主角固定是：a chibi anime girl with long blue hair, wearing a dark blue and white maid dress with a whale apron。
- 不要出現文字、字母、招牌、浮水印、真實人物、血腥或性暗示。
- 只輸出英文，不要引號、不要解釋。

範例：blue-haired chibi maid napping on a keyboard, cozy office, warm lamp light"""

    try:
        raw, _ = router.generate(persona.system_prompt(), user, config, secrets)
        scene = _clean_scene(raw)
        if len(scene) >= 8 and re.search(r"[A-Za-z]{3}", scene):
            return scene
    except Exception as exc:  # noqa: BLE001
        log.warning("產生圖片描述失敗，改用備援畫面：%s", exc)

    return _fallback_scene(topic, mood)


def build_url(scene: str, config: dict[str, Any], seed: int) -> str:
    cfg = config.get("images") or {}
    style = str(cfg.get("style") or DEFAULT_STYLE)
    prompt = f"{style}, {scene}"
    query = urllib.parse.urlencode(
        {
            "width": int(cfg.get("width", 1080)),
            "height": int(cfg.get("height", 1350)),
            "model": str(cfg.get("model", "flux")),
            "nologo": "true",
            "seed": seed,
        }
    )
    return (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(prompt, safe="")
        + "?"
        + query
    )


def prepare(
    config: dict[str, Any],
    secrets: dict[str, Any],
    post_text: str,
    topic: str,
    mood: str,
) -> dict[str, Any] | None:
    """回傳 {"url", "alt", "scene"}；做不出來就回 None（改成純文字發）。"""
    if not enabled(config):
        return None

    cfg = config.get("images") or {}
    attempts = max(1, int(cfg.get("max_attempts", 3)))
    timeout = float(cfg.get("fetch_timeout_seconds", 120))
    min_bytes = int(cfg.get("min_bytes", 15000))
    scene = scene_prompt(config, secrets, post_text, topic, mood)
    alt = f"{cfg.get('alt_prefix', '大肥魚插圖：')}{topic}".strip()

    for attempt in range(1, attempts + 1):
        url = build_url(scene, config, random.randint(1, 2**31 - 1))
        try:
            response = requests.get(url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            log.warning("第 %s 次產圖失敗（連線）：%s", attempt, exc)
            continue

        # 免費額度是「每個 IP 每 45 秒一張」，被佔用時直接放棄，不要連打。
        if response.status_code == 402:
            retry_after = response.headers.get("retry-after", "?")
            log.warning(
                "Pollinations 免費額度被佔用（402，約 %s 秒後可再試），這篇改成純文字發",
                retry_after,
            )
            return None

        ctype = str(response.headers.get("content-type", ""))
        content = response.content
        looks_like_image = content[:2] == b"\xff\xd8" or content[:8] == b"\x89PNG\r\n\x1a\n"
        if (
            response.status_code == 200
            and ctype.startswith("image/")
            and looks_like_image
            and len(content) >= min_bytes
        ):
            log.info("插圖好了（%s，%s KB）：%s", ctype, len(content) // 1024, scene)
            return {"url": url, "alt": alt, "scene": scene}

        log.warning(
            "第 %s 次產圖結果不理想：HTTP %s / %s / %s bytes",
            attempt,
            response.status_code,
            ctype or "?",
            len(content),
        )

    log.warning("產圖失敗，這篇改成純文字發")
    return None
