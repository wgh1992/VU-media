from __future__ import annotations

from .config import get_settings
from .store import ConversationStore, text_log_payload
from .wechat import close_transient_overlays
from .wechat import focus_chat, write_reply
from .wechat import press_enter_to_send


def send_message_confirmed(confirm: bool = False) -> str:
    settings = get_settings()
    if settings.send_requires_confirm and not confirm:
        return (
            "Refused to send. Call send_message_confirmed(confirm=true) only after "
            "a human has checked the WeChat input box."
        )
    return press_enter_to_send()


def auto_send_message(chat_name: str, text: str, confirm: bool = False) -> dict:
    if not chat_name.strip():
        raise ValueError("chat_name is required.")
    if not text.strip():
        raise ValueError("text is required.")

    focus_result = focus_chat(chat_name)
    write_result = write_reply(text)
    send_result = send_message_confirmed(confirm=confirm)
    sent = not send_result.startswith("Refused to send")

    event = ConversationStore().append_event(
        chat_name,
        "auto_send_message",
        {
            **text_log_payload(text),
            "focus_result": focus_result,
            "write_result": write_result,
            "send_result": send_result,
            "sent": sent,
        },
    )
    return {
        "chat_name": chat_name,
        "sent": sent,
        "focus_result": focus_result,
        "write_result": write_result,
        "send_result": send_result,
        "event": event,
    }


def send_current_chat_message(text: str, confirm: bool = False) -> dict:
    if not text.strip():
        raise ValueError("text is required.")

    close_result = close_transient_overlays()
    write_result = write_reply(text)
    send_result = send_message_confirmed(confirm=confirm)
    sent = not send_result.startswith("Refused to send")

    event = ConversationStore().append_event(
        "__current_chat__",
        "send_current_chat_message",
        {
            **text_log_payload(text),
            "close_result": close_result,
            "write_result": write_result,
            "send_result": send_result,
            "sent": sent,
        },
    )
    return {
        "sent": sent,
        "close_result": close_result,
        "write_result": write_result,
        "send_result": send_result,
        "event": event,
    }
