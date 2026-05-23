from __future__ import annotations

from typing import Any

from .prompts import PromptManager
from .store import ConversationStore
from .vision import analyze_screenshot
from .wechat import capture_wechat_window, scroll_current_chat_history


DEFAULT_HISTORY_PROMPT = """
Read the visible WeChat chat history from this screenshot.
Return JSON only with:
- current_chat: string|null
- visible_messages: array of objects with sender, approximate_time, text
- oldest_visible_hint: string|null
- newest_visible_hint: string|null
- uncertainty: string|null
Preserve message order from older to newer when possible.
Do not invent text. If text is unclear, say so in uncertainty.
""".strip()


def read_current_chat_history(scroll_pages: int = 3, scroll_notches: int = 9) -> dict[str, Any]:
    pages = max(1, min(int(scroll_pages), 10))
    notches = max(1, min(int(scroll_notches), 12))
    prompt = PromptManager().get("read_chat_history_page", DEFAULT_HISTORY_PROMPT)
    store = ConversationStore()
    captures = []
    results = []

    for index in range(pages):
        image_path = capture_wechat_window()
        captures.append(image_path)
        if index < pages - 1:
            scroll_current_chat_history(notches)

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
            "pages": results,
        },
    )
    return {
        "scroll_pages": pages,
        "scroll_notches": notches,
        "pages": results,
        "event": event,
    }
