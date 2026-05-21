from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from .agent_sdk import run_wechat_agent
from .mcp_adapter import list_agent_mcp_tools
from .server import (
    analyze_screenshot,
    auto_send_message,
    capture_wechat_window,
    daily_check_once,
    draft_reply,
    focus_chat,
    health_check,
    list_visible_windows,
    read_current_chat,
    read_current_chat_and_store,
    recent_conversation_events,
    safe_send_current_chat_with_vision,
    send_current_chat_message,
    summarize_chat,
    write_reply,
)


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=True, indent=2))


def _print_text(value: Any) -> None:
    text = str(value)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    except Exception:
        print(text.encode("ascii", errors="backslashreplace").decode("ascii"))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wechat-mcp-dev",
        description="Local developer CLI for testing wechat-mcp without an MCP client.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Show local configuration and prompt readiness.")
    subparsers.add_parser("list-windows", help="List visible top-level Windows windows.")

    agent_tools_parser = subparsers.add_parser("agent-tools", help="List MCP tools visible to the Agent SDK wrapper.")
    agent_tools_parser.add_argument("--mode", default="daily", choices=["daily", "send"])

    agent_run_parser = subparsers.add_parser("agent-run", help="Run an Agent SDK prompt through the local MCP server.")
    agent_run_parser.add_argument("prompt", nargs="?", default="Please run one WeChat daily check.")
    agent_run_parser.add_argument("--mode", default="daily", choices=["daily", "send"])
    agent_run_parser.add_argument("--max-turns", type=int, default=6)

    daily_parser = subparsers.add_parser("daily-check", help="Run one low-risk daily WeChat check.")
    daily_parser.add_argument("--note", default=None, help="Optional note to include in the report prompt.")

    capture_parser = subparsers.add_parser("capture", help="Capture the WeChat window.")
    capture_parser.add_argument("--output", default=None, help="Optional output PNG path.")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze an existing screenshot.")
    analyze_parser.add_argument("image_path")
    analyze_parser.add_argument("--instruction", default=None)

    focus_parser = subparsers.add_parser("focus", help="Focus a WeChat chat by name.")
    focus_parser.add_argument("chat_name")

    subparsers.add_parser("read", help="Capture and analyze the current WeChat chat.")

    read_store_parser = subparsers.add_parser("read-store", help="Read current chat and store the event.")
    read_store_parser.add_argument("--contact", default=None)

    draft_parser = subparsers.add_parser("draft", help="Draft a reply from chat text.")
    draft_parser.add_argument("chat_text")
    draft_parser.add_argument("--instruction", default=None)

    summary_parser = subparsers.add_parser("summary", help="Summarize chat text and store the summary.")
    summary_parser.add_argument("chat_text")
    summary_parser.add_argument("--contact", default=None)
    summary_parser.add_argument("--instruction", default=None)

    events_parser = subparsers.add_parser("events", help="Show recent stored events.")
    events_parser.add_argument("--contact", default=None)
    events_parser.add_argument("--limit", type=int, default=20)

    write_parser = subparsers.add_parser("write", help="Paste reply text into WeChat without sending.")
    write_parser.add_argument("text")
    write_parser.add_argument("--contact", default=None)

    send_parser = subparsers.add_parser("send", help="Focus a chat, paste text, and send if confirmation policy allows.")
    send_parser.add_argument("chat_name")
    send_parser.add_argument("text")
    send_parser.add_argument("--confirm", action="store_true")

    send_current_parser = subparsers.add_parser("send-current", help="Paste text into the current open chat and send.")
    send_current_parser.add_argument("text")
    send_current_parser.add_argument("--confirm", action="store_true")

    safe_send_current_parser = subparsers.add_parser(
        "safe-send-current",
        help="Send to the current open chat with visual verification at each step.",
    )
    safe_send_current_parser.add_argument("text")
    safe_send_current_parser.add_argument("--confirm", action="store_true")

    args = parser.parse_args()

    if args.command == "health":
        _print_json(health_check())
    elif args.command == "list-windows":
        _print_json(list_visible_windows())
    elif args.command == "agent-tools":
        _print_json(asyncio.run(list_agent_mcp_tools(args.mode)))
    elif args.command == "agent-run":
        result = asyncio.run(run_wechat_agent(args.prompt, args.mode, args.max_turns))
        _print_text(result.final_output)
    elif args.command == "daily-check":
        _print_json(daily_check_once(args.note))
    elif args.command == "capture":
        _print_json(capture_wechat_window(args.output))
    elif args.command == "analyze":
        _print_text(analyze_screenshot(args.image_path, args.instruction))
    elif args.command == "focus":
        _print_text(focus_chat(args.chat_name))
    elif args.command == "read":
        _print_text(read_current_chat())
    elif args.command == "read-store":
        _print_json(read_current_chat_and_store(args.contact))
    elif args.command == "draft":
        _print_text(draft_reply(args.chat_text, args.instruction))
    elif args.command == "summary":
        _print_json(summarize_chat(args.chat_text, args.contact, args.instruction))
    elif args.command == "events":
        _print_json(recent_conversation_events(args.contact, args.limit))
    elif args.command == "write":
        _print_text(write_reply(args.text, args.contact))
    elif args.command == "send":
        _print_json(auto_send_message(args.chat_name, args.text, args.confirm))
    elif args.command == "send-current":
        _print_json(send_current_chat_message(args.text, args.confirm))
    elif args.command == "safe-send-current":
        _print_json(safe_send_current_chat_with_vision(args.text, args.confirm))


if __name__ == "__main__":
    main()
