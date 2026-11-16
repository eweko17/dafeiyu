from __future__ import annotations

import argparse
import logging
import random
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from brain import router
from threads_api import make_client

from . import config as config_mod
from . import logging_setup, persona, state
from .console import setup_console
from . import discover as discover_mod
from . import post as post_mod
from . import replies as replies_mod
from .doctor import run as doctor_run
from .setup_wizard import run as setup_run

log = logging.getLogger("dafeiyu.cli")


def _load() -> tuple[dict[str, Any], dict[str, Any]]:
    return config_mod.load_config(), config_mod.load_secrets()


def cmd_post(args: argparse.Namespace) -> int:
    cfg, secrets = _load()
    result = post_mod.create_post(
        cfg, secrets, slot=args.slot, dry_run=args.dry_run
    )
    if result.get("dry_run"):
        print("\n--- 預覽（沒有發出去）---\n")
        print(result["text"])
        print(f"\n[provider: {result['provider']} / 心情: {result['mood']} / 主題: {result['topic']}]")
    elif result.get("skipped"):
        reason = str(result.get("reason"))
        print(f"沒有發文：{reason}")
        # 「今天額度滿了」「功能關閉」是正常狀況，不算失敗；
        # 模型完全掛掉、或 Threads API 出錯，才讓排程顯示紅字。
        if reason.startswith("生成失敗") or reason.startswith("threads_error"):
            return 1
        return 0
    else:
        print(f"已發文：{result.get('id')}")
    return 0


def cmd_replies(args: argparse.Namespace) -> int:
    cfg, secrets = _load()
    count = replies_mod.run_replies(
        cfg, secrets, dry_run=args.dry_run, limit=args.limit
    )
    print(f"本輪回覆 {count} 則")
    return 0


def cmd_test_brain(args: argparse.Namespace) -> int:
    cfg, secrets = _load()
    prompt = args.prompt or "用大肥魚的語氣說一句話，20 字以內。"
    text, provider = router.generate(
        persona.system_prompt(), prompt, cfg, secrets
    )
    print(f"[provider: {provider}]")
    print(text)
    return 0


def cmd_quota(_: argparse.Namespace) -> int:
    cfg, secrets = _load()
    client = make_client(cfg, secrets)
    limit = client.publishing_limit()
    print(f"發文：{limit.get('quota_usage')} / {limit.get('config', {}).get('quota_total')}")
    print(f"回覆：{limit.get('reply_quota_usage')} / {limit.get('reply_config', {}).get('quota_total')}")
    return 0


def cmd_refresh(_: argparse.Namespace) -> int:
    cfg, secrets = _load()
    client = make_client(cfg, secrets)
    body = client.refresh_token()
    secrets["threads_token"] = body["access_token"]
    config_mod.save_secrets(secrets)
    days = int(body.get("expires_in", 0)) / 86400
    print(f"Token 已更新，約 {days:.0f} 天後到期。")
    return 0


def _now_local(cfg: dict[str, Any]) -> datetime:
    try:
        return datetime.now(ZoneInfo(str(cfg.get("timezone", "Asia/Taipei"))))
    except ZoneInfoNotFoundError:
        return datetime.now()


def _parse_hhmm(text: Any) -> int | None:
    """'09:30' → 570（分鐘）；格式不對回 None。"""
    try:
        hour, minute = (int(part) for part in str(text).split(":", 1))
    except (ValueError, TypeError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def _random_slots(cfg: dict[str, Any], count: int, day: str) -> list[str]:
    """替這一天抽 count 個時間點。

    種子用日期，所以同一天不管重算幾次都一樣；實際結果也會存進 state，
    下一輪直接沿用，不會每 10 分鐘就換一次時間。
    """
    posting = cfg.get("posting", {})
    window = posting.get("random_window") or ["08:00", "23:00"]
    start = _parse_hhmm(window[0]) if len(window) > 0 else None
    end = _parse_hhmm(window[1]) if len(window) > 1 else None
    start = 8 * 60 if start is None else start
    end = 23 * 60 if end is None else end
    if end <= start:
        start, end = 8 * 60, 23 * 60

    gap = max(0, int(posting.get("min_gap_minutes", 90) or 0))
    rng = random.Random(f"{day}|{count}")

    picks: list[int] = []
    for _ in range(400):
        candidate = sorted(rng.randrange(start, end) for _ in range(count))
        if all(b - a >= gap for a, b in zip(candidate, candidate[1:])):
            picks = candidate
            break
    if not picks:
        # 窗口真的太窄塞不下，就平均分（至少不會全部撞在一起）
        span = end - start
        picks = [start + int(span * i / count) for i in range(count)]
    return [f"{minute // 60:02d}:{minute % 60:02d}" for minute in picks]


def _ensure_slots(cfg: dict[str, Any], now: datetime) -> list[str]:
    """今天的發文時間。固定模式讀 config；隨機模式抽一次並存進 state。"""
    posting = cfg.get("posting", {})
    max_per_day = int(posting.get("max_per_day", 3))
    if not posting.get("random_slots"):
        return [str(slot) for slot in (posting.get("slots") or [])]

    day = now.date().isoformat()
    data = state.load()
    saved = data.get("schedule") or {}
    times = [str(t) for t in (saved.get("times") or [])]
    if saved.get("date") == day and len(times) == max_per_day:
        return times

    times = _random_slots(cfg, max_per_day, day)
    with state.transaction() as fresh:
        current = fresh.get("schedule") or {}
        current_times = [str(t) for t in (current.get("times") or [])]
        if current.get("date") == day and len(current_times) == max_per_day:
            # 另一輪剛好先寫進去了，照它的
            times = current_times
        else:
            fresh["schedule"] = {"date": day, "times": times, "fired": []}
    return times


def _mark_slot(
    now: datetime, slot: int, slots: list[str], *, fired: bool = True
) -> None:
    """記下這個時段已經發過（或發失敗要放回去重試）。

    只靠「今天已發幾篇」判斷會有一個問題：如果前面有時段被跳過，
    後面同一個時段在 40 分鐘內會被每一輪重複觸發，變成短時間連發。
    """
    day = now.date().isoformat()
    with state.transaction() as fresh:
        saved = fresh.get("schedule") or {}
        if saved.get("date") != day or [
            str(t) for t in (saved.get("times") or [])
        ] != [str(t) for t in slots]:
            saved = {"date": day, "times": list(slots), "fired": []}
        done = {int(x) for x in (saved.get("fired") or [])}
        if fired:
            done.add(int(slot))
        else:
            done.discard(int(slot))
        saved["fired"] = sorted(done)
        fresh["schedule"] = saved


def _due_slot(
    cfg: dict[str, Any],
    data: dict[str, Any],
    now: datetime,
    slots: list[str] | None = None,
) -> int | None:
    """現在該發第幾篇？不是發文時間就回 None。

    判斷方式：離某個 slot 不超過「提前 10 分、延後 40 分」，
    而且今天發的篇數還不到那個 slot 的編號。
    延後 40 分是給 GitHub 排程的延遲留空間。
    """
    posting = cfg.get("posting", {})
    if slots is None:
        slots = posting.get("slots") or []
    posted = int((data.get("daily") or {}).get("posts", 0))
    max_per_day = int(posting.get("max_per_day", 3))
    if posted >= max_per_day:
        return None

    # 今天已經觸發過的時段就不要再發一次。
    saved = data.get("schedule") or {}
    done: set[int] = set()
    if saved.get("date") == now.date().isoformat() and [
        str(t) for t in (saved.get("times") or [])
    ] == [str(t) for t in slots]:
        done = {int(x) for x in (saved.get("fired") or [])}

    for index, hhmm in enumerate(slots, start=1):
        if index in done:
            continue
        slot_minutes = _parse_hhmm(hhmm)
        if slot_minutes is None:
            continue
        slot_time = now.replace(
            hour=slot_minutes // 60, minute=slot_minutes % 60, second=0, microsecond=0
        )
        minutes = (now - slot_time).total_seconds() / 60
        if -10 <= minutes <= 40 and posted < index:
            return index
    return None


def cmd_auto(_: argparse.Namespace) -> int:
    """雲端排程用：時間到了就發文，順便回覆留言。"""
    cfg, secrets = _load()
    now = _now_local(cfg)
    slots = _ensure_slots(cfg, now)
    data = state.load()
    posted = int((data.get("daily") or {}).get("posts", 0))
    max_per_day = int(cfg.get("posting", {}).get("max_per_day", 3))

    rc = 0
    slot = _due_slot(cfg, data, now, slots)
    if slot is not None:
        print(
            f"現在 {now:%H:%M}，輪到第 {slot} 篇（今天已發 {posted}/{max_per_day}；"
            f"今日排程 {'、'.join(slots)}）。"
        )
        # 先記下來，避免同一時段在 40 分鐘內被每一輪重複觸發。
        _mark_slot(now, slot, slots)
        result = post_mod.create_post(cfg, secrets, slot=slot)
        if result.get("dry_run"):
            print(result.get("text", ""))
        elif result.get("skipped"):
            reason = str(result.get("reason"))
            print(f"沒有發文：{reason}")
            if reason.startswith("生成失敗") or reason.startswith("threads_error"):
                # 真的失敗才放回去，下一輪（還在時間窗內）再試一次。
                _mark_slot(now, slot, slots, fired=False)
                rc = 1
        else:
            print(f"已發文：{result.get('id')}")
    else:
        print(f"現在 {now:%H:%M}，不是發文時間（今天已發 {posted}/{max_per_day}）。")

    count = replies_mod.run_replies(cfg, secrets)
    print(f"本輪回覆 {count} 則")

    if discover_mod.enabled(cfg):
        try:
            found = discover_mod.run_discover(cfg, secrets)
            print(f"本輪主動回覆 {found} 則")
        except discover_mod.DiscoverUnavailable as exc:
            print(f"主動回覆先跳過：\n{exc}")
    return rc


def cmd_discover(args: argparse.Namespace) -> int:
    cfg, secrets = _load()
    try:
        found = discover_mod.run_discover(
            cfg,
            secrets,
            dry_run=args.dry_run,
            limit=args.limit,
            keyword=args.keyword,
        )
    except discover_mod.DiscoverUnavailable as exc:
        print(f"\n{exc}\n")
        return 2
    print(f"本輪主動回覆 {found} 則")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    data = state.load()
    print(f"今天：發文 {data['daily'].get('posts', 0)} 篇，回覆 {data['daily'].get('replies', 0)} 則")
    print(f"今天主動回覆：{data['daily'].get('discover', 0)} 則")
    print(f"歷史貼文：{len(data.get('posts', []))} 篇")
    print(f"回覆紀錄：{len(data.get('replied', {}))} 則")
    print(f"認識的人：{len(data.get('people', {}))} 位")
    if data.get("posts"):
        last = data["posts"][-1]
        print(f"最近一篇：{last.get('iso')} / {last.get('topic')}")
        print(last.get("text", "")[:120])
    return 0


def cmd_people(_: argparse.Namespace) -> int:
    data = state.load()
    people = data.get("people") or {}
    if not people:
        print("還沒有認識任何人；等有人來貼文留言，就會自動記住他。")
        return 0
    items = sorted(
        people.items(), key=lambda kv: kv[1].get("last_seen", 0), reverse=True
    )
    for name, person in items:
        when = datetime.fromtimestamp(person.get("last_seen", 0)).strftime("%m/%d %H:%M")
        print(f"@{name}｜見過 {person.get('count', 0)} 次｜最後 {when}")
        said = [s for s in (person.get("said") or []) if s][-3:]
        if said:
            print("   他說過：" + "／".join(said))
        if person.get("last_reply"):
            print("   上次回：" + str(person["last_reply"]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="大肥魚", description="大肥魚 Threads 機器人")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="設定 Threads token 與 Gemini key")
    sub.add_parser("doctor", help="健康檢查")
    sub.add_parser("status", help="看今天的進度")
    sub.add_parser("people", help="看大肥魚記得哪些人")
    sub.add_parser("auto", help="自動判斷現在要發文還是回覆（雲端排程用）")

    p_post = sub.add_parser("post", help="發一篇貼文")
    p_post.add_argument("--dry-run", action="store_true", help="只生成，不發佈")
    p_post.add_argument("--slot", type=int, default=None, help="排程槽位（僅記錄用）")

    p_reply = sub.add_parser("replies", help="回覆自己貼文底下的新留言")
    p_reply.add_argument("--dry-run", action="store_true")
    p_reply.add_argument("--limit", type=int, default=None)

    p_disc = sub.add_parser(
        "discover", help="搜尋公開貼文並主動回覆（需 threads_keyword_search）"
    )
    p_disc.add_argument("--dry-run", action="store_true")
    p_disc.add_argument("--limit", type=int, default=None)
    p_disc.add_argument("--keyword", default=None, help="只搜這個關鍵字")

    p_brain = sub.add_parser("test-brain", help="測試本機／雲端模型")
    p_brain.add_argument("--prompt", default=None)

    sub.add_parser("quota", help="查今日 API 額度")
    sub.add_parser("refresh-token", help="更新 Threads token（60 天一次）")
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_console()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "doctor":
        logging_setup.setup(verbose=args.verbose)

    try:
        if args.command == "setup":
            return setup_run()
        if args.command == "doctor":
            return doctor_run()
        if args.command == "post":
            return cmd_post(args)
        if args.command == "replies":
            return cmd_replies(args)
        if args.command == "discover":
            return cmd_discover(args)
        if args.command == "test-brain":
            return cmd_test_brain(args)
        if args.command == "quota":
            return cmd_quota(args)
        if args.command == "refresh-token":
            return cmd_refresh(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "people":
            return cmd_people(args)
        if args.command == "auto":
            return cmd_auto(args)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:  # noqa: BLE001
        log.exception("執行失敗")
        print(f"\n失敗：{exc}")
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
