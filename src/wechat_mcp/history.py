from __future__ import annotations

from typing import Any

from .prompts import PromptManager
from .store import ConversationStore
from .vision import analyze_screenshot
from .wechat import capture_wechat_chat_pane, scroll_current_chat_history, scroll_current_chat_to_bottom


DEFAULT_HISTORY_PROMPT = """
Read the visible WeChat main chat pane from this screenshot.
Return JSON only with:
- current_chat: string|null
- visible_messages: array of objects with sender, approximate_time, text
- oldest_visible_hint: string|null
- newest_visible_hint: string|null
- uncertainty: string|null
Only extract messages from the active main chat pane.
Ignore the left conversation list, search box, side navigation, app chrome, input toolbar, and unrelated previews if visible.
Preserve message order from older to newer when possible.
Do not invent text. If text is unclear, say so in uncertainty.
""".strip()


def read_current_chat_history(
    scroll_pages: int = 3,
    scroll_notches: int = 18,
    scroll_delay_seconds: float = 0.05,
    settle_to_bottom: bool = True,
    bottom_scroll_notches: int = 60,
    settle_delay_seconds: float = 0.2,
) -> dict[str, Any]:
    pages = max(1, min(int(scroll_pages), 10))
    notches = max(1, min(int(scroll_notches), 30))
    delay = max(0.0, min(float(scroll_delay_seconds), 1.0))
    bottom_notches = max(1, min(int(bottom_scroll_notches), 120))
    settle_delay = max(0.0, min(float(settle_delay_seconds), 2.0))
    prompt = PromptManager().get("read_chat_history_page", DEFAULT_HISTORY_PROMPT)
    store = ConversationStore()
    captures = []
    results = []

    if settle_to_bottom:
        scroll_current_chat_to_bottom(bottom_notches, settle_delay)

    for index in range(pages):
        image_path = capture_wechat_chat_pane()
        captures.append(image_path)
        if index < pages - 1:
            scroll_current_chat_history(notches, delay)

    for index, image_path in enumerate(captures):
        analysis = analyze_screenshot(image_path, prompt)
        stored_image = store.save_screenshot("__current_chat_history__", image_path)
        results.append(
            {
                "page": index + 1,
                "image_path": stored_image,
                "analysis": analysis,
            }
        )

    event = store.append_event(
        "__current_chat_history__",
        "chat_history_read",
        {
            "scroll_pages": pages,
            "scroll_notches": notches,
            "scroll_delay_seconds": delay,
            "settle_to_bottom": bool(settle_to_bottom),
            "bottom_scroll_notches": bottom_notches,
            "settle_delay_seconds": settle_delay,
            "pages": results,
        },
    )
    return {
        "scroll_pages": pages,
        "scroll_notches": notches,
        "scroll_delay_seconds": delay,
        "settle_to_bottom": bool(settle_to_bottom),
        "bottom_scroll_notches": bottom_notches,
        "settle_delay_seconds": settle_delay,
        "pages": results,
        "event": event,
    }
