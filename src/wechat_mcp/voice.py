from __future__ import annotations

import json
import time
from typing import Any

from .prompts import PromptManager
from .store import ConversationStore
from .vision import analyze_screenshot
from .wechat import capture_wechat_window, click_visible_voice_to_text, click_wechat_normalized


DEFAULT_VOICE_TEXT_PROMPT = """
Inspect this WeChat screenshot after clicking a voice message "Convert to text" button.
Return JSON only with:
- current_chat: string|null
- converted_voice_text: string|null
- voice_duration: string|null
- uncertainty: string|null
If the converted text is not visible or unclear, set converted_voice_text to null and explain uncertainty.
Do not invent text.
""".strip()


LOCATE_VOICE_CONVERT_PROMPT = """
Inspect this WeChat screenshot and locate the visible voice message "Convert to text" button.
Return JSON only with:
- found: boolean
- x_ratio: number|null, center x of the button divided by screenshot width
- y_ratio: number|null, center y of the button divided by screenshot height
- reason: string|null
If there are multiple visible Convert to text buttons, choose the one requested by index in reading order from top to bottom.
Do not choose browser UI, taskbar UI, or non-WeChat controls.
""".strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {"found": False, "reason": "Model did not return valid JSON."}


def _click_visible_voice_to_text_with_vision(index: int) -> str:
    image_path = capture_wechat_window()
    raw = analyze_screenshot(
        image_path,
        f"{LOCATE_VOICE_CONVERT_PROMPT}\n\nRequested index: {index}",
    )
    result = _parse_json_object(raw)
    if not result.get("found"):
        raise RuntimeError(f"Could not visually locate a voice Convert to text button. {result.get('reason') or raw[:300]}")

    x_ratio = result.get("x_ratio")
    y_ratio = result.get("y_ratio")
    if not isinstance(x_ratio, (int, float)) or not isinstance(y_ratio, (int, float)):
        raise RuntimeError(f"Visual locator returned invalid coordinates: {raw[:300]}")

    click_result = click_wechat_normalized(float(x_ratio), float(y_ratio))
    return f"{click_result} Visual locator raw result: {raw}"


def convert_visible_voice_to_text(index: int = 1) -> dict[str, Any]:
    try:
        click_result = click_visible_voice_to_text(index)
    except RuntimeError as exc:
        click_result = f"UIA lookup failed: {exc}; used visual coordinate fallback. {_click_visible_voice_to_text_with_vision(index)}"
    time.sleep(3.0)
    image_path = capture_wechat_window()
    prompt = PromptManager().get("voice_to_text_result", DEFAULT_VOICE_TEXT_PROMPT)
    analysis = analyze_screenshot(image_path, prompt)
    store = ConversationStore()
    stored_image = store.save_screenshot("__voice_to_text__", image_path)
    event = store.append_event(
        "__voice_to_text__",
        "voice_to_text",
        {
            "index": index,
            "click_result": click_result,
            "image_path": stored_image,
            "analysis": analysis,
        },
    )
    return {
        "index": index,
        "click_result": click_result,
        "image_path": stored_image,
        "analysis": analysis,
        "event": event,
    }
