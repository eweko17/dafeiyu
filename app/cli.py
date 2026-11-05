from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

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


def cmd_status(_: argparse.Namespace) -> int:
    data = state.load()
    print(f"今天：發文 {data['daily'].get('posts', 0)} 篇，回覆 {data['daily'].get('replies', 0)} 則")
    print(f"歷史貼文：{len(data.get('posts', []))} 篇")
    print(f"回覆紀錄：{len(data.get('replied', {}))} 則")
    if data.get("posts"):
        last = data["posts"][-1]
        print(f"最近一篇：{last.get('iso')} / {last.get('topic')}")
        print(last.get("text", "")[:120])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="大肥魚", description="大肥魚 Threads 機器人")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="設定 Threads token 與 Gemini key")
    sub.add_parser("doctor", help="健康檢查")
    sub.add_parser("status", help="看今天的進度")

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
