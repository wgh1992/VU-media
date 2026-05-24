from __future__ import annotations

import json
from typing import Any

from .store import ConversationStore
from .vision import analyze_screenshot
from .wechat import capture_wechat_window, click_wechat_normalized


CLICK_LOCATOR_PROMPT = """
You locate a clickable target in a WeChat desktop screenshot.
Return JSON only with:
- ok: boolean
- target: string
- x_ratio: number|null
- y_ratio: number|null
- confidence: "low"|"medium"|"high"
- reason: string|null

Coordinates must be normalized relative to the whole WeChat window screenshot:
top-left is 0,0 and bottom-right is 1,1.
Never choose window titlebar controls such as pin, minimize, maximize, or close.
If the requested target is not clearly visible, return ok=false.
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
    return {
        "ok": False,
        "target": None,
        "x_ratio": None,
        "y_ratio": None,
        "confidence": "low",
        "reason": "Locator did not return valid JSON.",
        "raw": text[:1000],
    }


def click_wechat(x_ratio: float, y_ratio: float, reason: str | None = None) -> dict[str, Any]:
    click_result = click_wechat_normalized(x_ratio, y_ratio)
    payload = {
        "x_ratio": x_ratio,
        "y_ratio": y_ratio,
        "reason": reason,
        "click_result": click_result,
    }
    event = ConversationStore().append_event("__wechat_click__", "click_wechat", payload)
    return {**payload, "event": event}


def click_wechat_by_vision(instruction: str) -> dict[str, Any]:
    if not instruction.strip():
        raise ValueError("instruction is required.")

    image_path = capture_wechat_window()
    prompt = f"{CLICK_LOCATOR_PROMPT}\n\nRequested click target:\n{instruction.strip()}"
    raw = analyze_screenshot(image_path, prompt)
    locator = _parse_json_object(raw)
    locator["raw"] = raw

    store = ConversationStore()
    stored_image = store.save_screenshot("__wechat_click__", image_path)

    if not locator.get("ok"):
        event = store.append_event(
            "__wechat_click__",
            "click_wechat_by_vision",
            {
                "image_path": stored_image,
                "instruction": instruction,
                "locator": locator,
                "clicked": False,
            },
        )
        return {
            "clicked": False,
            "image_path": stored_image,
            "instruction": instruction,
            "locator": locator,
            "event": event,
        }

    try:
        x_ratio = float(locator["x_ratio"])
        y_ratio = float(locator["y_ratio"])
    except (TypeError, ValueError, KeyError) as exc:
        raise RuntimeError(f"Vision locator returned invalid coordinates: {locator}") from exc

    click_result = click_wechat_normalized(x_ratio, y_ratio)
    event = store.append_event(
        "__wechat_click__",
        "click_wechat_by_vision",
        {
            "image_path": stored_image,
            "instruction": instruction,
            "locator": locator,
            "clicked": True,
            "click_result": click_result,
        },
    )
    return {
        "clicked": True,
        "image_path": stored_image,
        "instruction": instruction,
        "locator": locator,
        "click_result": click_result,
        "event": event,
    }
