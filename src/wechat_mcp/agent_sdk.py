from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from agents import Agent, ModelSettings, Runner
from openai.types.shared.reasoning import Reasoning

from .config import Settings, get_settings
from .mcp_adapter import create_stdio_mcp_server, list_agent_mcp_tools


DAILY_INSTRUCTIONS = """
You are a local WeChat daily-check agent.
Your job is to inspect WeChat once, summarize visible unread/new-message state, and stop.
Use the MCP tool daily_check_once when the user asks for a check.
Do not open individual conversations unless explicitly asked.
Do not write replies.
Do not send messages.
If WeChat is not visible or logged in, explain the required human action.
Return a concise Chinese report with the saved report path when available.
""".strip()


SEND_INSTRUCTIONS = """
You are a local WeChat desktop agent.
You may inspect visible WeChat state, focus chats, read current chat screenshots, summarize, and draft or write replies.
When the user asks to handle unread messages, red dots, unread badges, or next unread conversation, use focus_unread_by_red_dot, then read_current_chat.
When the user asks for history, older messages, 往上翻, 历史消息, or more previous messages, use read_current_chat with scroll_pages greater than 1.
read_current_chat defaults to fast history scrolling with scroll_notches=80 and scroll_delay_seconds=0.02. You may reduce scroll_notches when WeChat looks unstable, or keep 80 when the user wants faster or bigger scrolling.
read_current_chat scrolls to the bottom/newest message first by default. Keep settle_to_bottom=true unless the user explicitly wants to continue reading from the current scrolled position.
You may set bottom_scroll_notches and settle_delay_seconds yourself. Use a larger settle_delay_seconds when WeChat needs more time to render after jumping to the bottom.
When the user asks to convert a WeChat voice message to text, Convert to text, 转文字, 转换为文字, or 语音转文字, use convert_visible_voice_to_text.
When the user asks to click a visible WeChat UI element, button, icon, link, video, tab, menu, or says 点一下/点击/click/tap, prefer click_wechat_by_vision with a precise description of the target. If the user provides or references a small template screenshot file, use click_wechat_by_template. Use click_wechat only when exact normalized coordinates are already known.
Never click WeChat titlebar/window controls such as pin, minimize, maximize, or close.
Send immediately when the user explicitly asks to send and both the recipient/current chat and exact message text are clear.
Do not ask for a second confirmation before sending a clear send request.
For "send to <recipient> <text>" requests, call auto_send_message directly instead of first checking visible windows.
Prefer safe_send_current_chat_with_vision when the target chat is already open.
Use auto_send_message when the user gives a recipient and exact message text.
Use confirm=false by default; the local safety setting will decide whether confirmation is required.
If the user says resend, re-send, send again, 重新发, 再发, 重发, 可以发, or 发, treat it as a send request tied to the prior proposed message.
Do not treat an existing matching outgoing bubble as a reason to skip a user's explicit resend request.
Do not report that WeChat is unavailable based only on list_visible_windows or screenshots; first try the relevant send/focus tool and report its actual result or exception.
Only ask a follow-up question when the recipient or exact message text is missing.
Return concise Chinese output.
""".strip()


def instructions_for_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized in {"send", "full"}:
        return SEND_INSTRUCTIONS
    return DAILY_INSTRUCTIONS


def model_settings_from_config(settings: Settings) -> ModelSettings:
    return ModelSettings(
        tool_choice="auto",
        parallel_tool_calls=False,
        reasoning=Reasoning(effort=settings.agent_reasoning_effort),
        verbosity=settings.agent_verbosity,
        extra_body={"service_tier": settings.agent_service_tier},
    )


def create_wechat_agent(mode: str = "daily") -> tuple[Agent, Any]:
    settings = get_settings()
    mcp_server = create_stdio_mcp_server(mode=mode)
    agent = Agent(
        name="WeChat Desktop Agent",
        instructions=instructions_for_mode(mode),
        model=settings.openai_model_fast,
        model_settings=model_settings_from_config(settings),
        mcp_servers=[mcp_server],
    )
    return agent, mcp_server


def _print_text(value: Any) -> None:
    text = str(value)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    except Exception:
        print(text.encode("ascii", errors="backslashreplace").decode("ascii"))


async def run_wechat_agent(prompt: str, mode: str = "daily", max_turns: int = 6) -> Any:
    agent, mcp_server = create_wechat_agent(mode=mode)
    async with mcp_server:
        return await Runner.run(agent, prompt, max_turns=max_turns)


async def _amain() -> None:
    parser = argparse.ArgumentParser(
        prog="wechat-agent",
        description="Run the WeChat Agent SDK wrapper using the local WeChat MCP server.",
    )
    parser.add_argument("prompt", nargs="?", default="Please run one WeChat daily check.")
    parser.add_argument("--mode", default="daily", choices=["daily", "send"])
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--max-turns", type=int, default=6)
    args = parser.parse_args()

    if args.list_tools:
        print(json.dumps(await list_agent_mcp_tools(args.mode), ensure_ascii=True, indent=2))
        return

    result = await run_wechat_agent(args.prompt, mode=args.mode, max_turns=args.max_turns)
    _print_text(result.final_output)


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
