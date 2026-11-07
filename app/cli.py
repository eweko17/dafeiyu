from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from brain import router
from threads_api import make_client

from . import config as config_mod
from . import logging_setup, persona, state
from .console import setup_console
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


def _due_slot(cfg: dict[str, Any], data: dict[str, Any], now: datetime) -> int | None:
    """現在該發第幾篇？不是發文時間就回 None。

    判斷方式：離某個 slot 不超過「提前 10 分、延後 40 分」，
    而且今天發的篇數還不到那個 slot 的編號。
    延後 40 分是給 GitHub 排程的延遲留空間。
    """
    posting = cfg.get("posting", {})
    slots = posting.get("slots") or []
    posted = int((data.get("daily") or {}).get("posts", 0))
    max_per_day = int(posting.get("max_per_day", 3))
    if posted >= max_per_day:
        return None

    for index, hhmm in enumerate(slots, start=1):
        try:
            hour, minute = (int(part) for part in str(hhmm).split(":", 1))
        except ValueError:
            continue
        slot_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        minutes = (now - slot_time).total_seconds() / 60
        if -10 <= minutes <= 40 and posted < index:
            return index
    return None


def cmd_auto(_: argparse.Namespace) -> int:
    """雲端排程用：時間到了就發文，順便回覆留言。"""
    cfg, secrets = _load()
    now = _now_local(cfg)
    data = state.load()
    posted = int((data.get("daily") or {}).get("posts", 0))
    max_per_day = int(cfg.get("posting", {}).get("max_per_day", 3))

    rc = 0
    slot = _due_slot(cfg, data, now)
    if slot is not None:
        print(f"現在 {now:%H:%M}，輪到第 {slot} 篇（今天已發 {posted}/{max_per_day}）。")
        result = post_mod.create_post(cfg, secrets, slot=slot)
        if result.get("dry_run"):
            print(result.get("text", ""))
        elif result.get("skipped"):
            reason = str(result.get("reason"))
            print(f"沒有發文：{reason}")
            if reason.startswith("生成失敗") or reason.startswith("threads_error"):
                rc = 1
        else:
            print(f"已發文：{result.get('id')}")
    else:
        print(f"現在 {now:%H:%M}，不是發文時間（今天已發 {posted}/{max_per_day}）。")

    count = replies_mod.run_replies(cfg, secrets)
    print(f"本輪回覆 {count} 則")
    return rc


def cmd_status(_: argparse.Namespace) -> int:
    data = state.load()
    print(f"今天：發文 {data['daily'].get('posts', 0)} 篇，回覆 {data['daily'].get('replies', 0)} 則")
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
