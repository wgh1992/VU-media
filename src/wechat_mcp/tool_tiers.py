from __future__ import annotations


DAILY_CHECK_TOOLS = [
    "health_check",
    "list_visible_windows",
    "daily_check_once",
    "recent_conversation_events",
]

SEND_TOOLS = [
    "health_check",
    "list_visible_windows",
    "daily_check_once",
    "focus_chat",
    "read_current_chat",
    "read_current_chat_history",
    "convert_visible_voice_to_text",
    "auto_send_message",
    "safe_send_current_chat_with_vision",
    "recent_conversation_events",
]


def allowed_tools_for_mode(mode: str) -> list[str]:
    normalized = mode.strip().lower()
    if normalized in {"daily", "daily_check", "monitor"}:
        return DAILY_CHECK_TOOLS
    if normalized in {"send", "full"}:
        return SEND_TOOLS
    return DAILY_CHECK_TOOLS
