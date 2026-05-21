from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from agents import Agent, ModelSettings, Runner

from .config import get_settings
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
Never send a message unless the user explicitly asks for sending.
Prefer write_reply over send_message_confirmed.
In send mode, prefer safe_send_current_chat_with_vision when the target chat is already open.
Use auto_send_message only when the user's requested recipient and exact message intent are clear.
When uncertain, ask for human confirmation.
Return concise Chinese output.
""".strip()


def instructions_for_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized in {"send", "full"}:
        return SEND_INSTRUCTIONS
    return DAILY_INSTRUCTIONS


def create_wechat_agent(mode: str = "daily") -> tuple[Agent, Any]:
    settings = get_settings()
    mcp_server = create_stdio_mcp_server(mode=mode)
    agent = Agent(
        name="WeChat Desktop Agent",
        instructions=instructions_for_mode(mode),
        model=settings.openai_model_fast,
        model_settings=ModelSettings(tool_choice="auto", parallel_tool_calls=False),
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
