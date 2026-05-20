from __future__ import annotations


DAILY_CHECK_TOOLS = [
    "health_check",
    "list_visible_windows",
    "daily_check_once",
    "recent_conversation_events",
]

ASSISTIVE_TOOLS = [
    *DAILY_CHECK_TOOLS,
    "capture_wechat_window",
    "analyze_screenshot",
    "analyze_and_store_screenshot",
    "focus_chat",
    "read_current_chat",
    "read_current_chat_and_store",
    "draft_reply",
    "summarize_chat",
    "write_reply",
]

SEND_TOOLS = [
    *ASSISTIVE_TOOLS,
    "send_message_confirmed",
    "auto_send_message",
]


def allowed_tools_for_mode(mode: str) -> list[str]:
    normalized = mode.strip().lower()
    if normalized in {"daily", "daily_check", "monitor"}:
        return DAILY_CHECK_TOOLS
    if normalized in {"assist", "assistant", "assistive", "chat"}:
        return ASSISTIVE_TOOLS
    if normalized in {"send", "full"}:
        return SEND_TOOLS
    return DAILY_CHECK_TOOLS
