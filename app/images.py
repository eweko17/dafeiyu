"""貼文配圖：使用「大肥魚表情包」的現成圖片（不再每次 AI 產圖）。

流程：
  貼文文字 → 從 docs/memes/memes.json 的表情包清單挑 1～2 張
  → 用 GitHub Pages 的公開網址交給 Threads（單張用 IMAGE、兩張用 CAROUSEL）

圖片是專案內建的靜態檔案，行為穩定、不用等產圖，也没有第三方產圖服務。
舊的 Pollinations AI 產圖保留成備用模式（config 的 images.mode = "pollinations"）。
"""

from __future__ import annotations

import json
import logging
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any

import requests

from brain import router

from . import persona, textutil
from .paths import ROOT

log = logging.getLogger("dafeiyu.images")

DEFAULT_MANIFEST = "docs/memes/memes.json"
DEFAULT_BASE_URL = "https://eweko17.github.io/dafeiyu/memes/"
DEFAULT_ALT_PREFIX = "大肥魚表情包："

_MANIFEST_CACHE: dict[str, list[dict[str, Any]]] = {}

# --------------------------------------------------------------------------
# 表情包（預設模式）
# --------------------------------------------------------------------------


def enabled(config: dict[str, Any]) -> bool:
    return bool((config.get("images") or {}).get("enabled", False))


def _manifest_path(config: dict[str, Any]) -> Path:
    raw = str((config.get("images") or {}).get("manifest") or DEFAULT_MANIFEST)
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _load_manifest(config: dict[str, Any]) -> list[dict[str, Any]]:
    """讀表情包清單；檔案不存在或格式壞掉就回空清單（貼文改純文字）。"""
    cfg = config.get("images") or {}
    path = _manifest_path(config)
    key = str(path)
    if key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[key]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("讀不到表情包清單（%s）：%s", path, exc)
        _MANIFEST_CACHE[key] = []
        return []

    base = str(cfg.get("base_url") or data.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    items: list[dict[str, Any]] = []
    for raw_item in data.get("items") or []:
        if not isinstance(raw_item, dict):
            continue
        filename = str(raw_item.get("file") or "").strip()
        if not filename:
            continue
        if not (path.parent / filename).is_file():
            log.warning("表情包檔案不存在，略過：%s", path.parent / filename)
            continue
        items.append(
            {
                "id": str(raw_item.get("id") or Path(filename).stem),
                "desc": str(raw_item.get("desc") or "").strip(),
                "tags": [str(t) for t in (raw_item.get("tags") or []) if str(t)],
                "url": f"{base}/{urllib.parse.quote(filename)}",
            }
        )

    if not items:
        log.warning("表情包清單是空的：%s", path)
    _MANIFEST_CACHE[key] = items
    return items


def _score(item: dict[str, Any], haystack: str) -> int:
    return sum(1 for tag in item.get("tags", []) if tag and tag in haystack)


def _select_memes(
    config: dict[str, Any],
    post_text: str,
    topic: str,
    mood: str,
) -> list[dict[str, Any]]:
    cfg = config.get("images") or {}
    max_per_post = int(cfg.get("max_per_post", 2))
    max_per_post = max(0, min(2, max_per_post))
    if max_per_post == 0:
        return []

    items = _load_manifest(config)
    if not items:
        return []

    haystack = "\n".join([post_text or "", topic or "", mood or ""])
    hits = [(item, _score(item, haystack)) for item in items]
    hits = [(item, score) for item, score in hits if score > 0]

    if hits:
        # 分數高的優先；同分隨機，避免每次都同一張
        hits.sort(key=lambda pair: (-pair[1], random.random()))
        chosen = [item for item, _ in hits[:max_per_post]]
    else:
        # 完全沒有關鍵字命中時，只放一張，避免兩張都文不對題
        chosen = [random.choice(items)]

    alt_prefix = str(cfg.get("alt_prefix") or DEFAULT_ALT_PREFIX)
    result: list[dict[str, Any]] = []
    for item in chosen:
        alt = f"{alt_prefix}{item['desc']}".strip()
        result.append(
            {
                "url": item["url"],
                "alt": alt[:900],
                "meme": item["id"],
                "desc": item["desc"],
            }
        )

    log.info(
        "配圖：%s",
        "、".join(str(image["meme"]) for image in result) or "（無）",
    )
    return result


# --------------------------------------------------------------------------
# 舊的 Pollinations AI 產圖（備用模式）
# --------------------------------------------------------------------------

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


def _prepare_pollinations(
    config: dict[str, Any],
    secrets: dict[str, Any],
    post_text: str,
    topic: str,
    mood: str,
) -> dict[str, Any] | None:
    """回傳 {"url", "alt", "scene"}；做不出來就回 None（改成純文字發）。"""
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


# --------------------------------------------------------------------------
# 對外入口
# --------------------------------------------------------------------------


def prepare(
    config: dict[str, Any],
    secrets: dict[str, Any],
    post_text: str,
    topic: str,
    mood: str,
) -> list[dict[str, Any]]:
    """回傳 0～2 張圖片的清單（空清單 = 純文字發）。"""
    if not enabled(config):
        return []

    cfg = config.get("images") or {}
    mode = str(cfg.get("mode") or "memes").strip().lower()
    if mode == "pollinations":
        image = _prepare_pollinations(config, secrets, post_text, topic, mood)
        return [image] if image else []

    return _select_memes(config, post_text, topic, mood)
