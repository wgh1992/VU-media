from __future__ import annotations

from .config import get_settings
from .wechat import press_enter_to_send


def send_message_confirmed(confirm: bool = False) -> str:
    settings = get_settings()
    if settings.send_requires_confirm and not confirm:
        return (
            "Refused to send. Call send_message_confirmed(confirm=true) only after "
            "a human has checked the WeChat input box."
        )
    return press_enter_to_send()
