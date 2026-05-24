from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

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


def _load_match_image(path: str | Path, downscale: float) -> np.ndarray:
    image = Image.open(path).convert("L")
    if downscale <= 0:
        raise ValueError("downscale must be > 0.")
    if downscale != 1:
        width = max(1, int(image.width * downscale))
        height = max(1, int(image.height * downscale))
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32)


def locate_template_in_wechat(
    template_image_path: str,
    threshold: float = 0.20,
    search_left_ratio: float = 0.0,
    search_top_ratio: float = 0.0,
    search_right_ratio: float = 0.25,
    search_bottom_ratio: float = 1.0,
    downscale: float = 0.5,
    stride: int = 2,
) -> dict[str, Any]:
    if not Path(template_image_path).is_file():
        raise FileNotFoundError(f"Template image not found: {template_image_path}")
    if stride < 1:
        raise ValueError("stride must be >= 1.")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")
    ratios = [search_left_ratio, search_top_ratio, search_right_ratio, search_bottom_ratio]
    if any(ratio < 0 or ratio > 1 for ratio in ratios):
        raise ValueError("search region ratios must be between 0 and 1.")
    if search_right_ratio <= search_left_ratio or search_bottom_ratio <= search_top_ratio:
        raise ValueError("search region right/bottom ratios must be greater than left/top ratios.")

    screenshot_path = capture_wechat_window()
    screenshot = _load_match_image(screenshot_path, downscale)
    template = _load_match_image(template_image_path, downscale)

    screen_h, screen_w = screenshot.shape
    template_h, template_w = template.shape
    left = int(screen_w * search_left_ratio)
    top = int(screen_h * search_top_ratio)
    right = int(screen_w * search_right_ratio)
    bottom = int(screen_h * search_bottom_ratio)
    search = screenshot[top:bottom, left:right]

    if template_h > search.shape[0] or template_w > search.shape[1]:
        raise ValueError("Template is larger than the requested search region.")

    template_centered = template - float(template.mean())
    template_norm = float(np.linalg.norm(template_centered))
    use_absolute_difference = template_norm == 0

    best_score = -1.0
    best_xy: tuple[int, int] | None = None
    max_y = search.shape[0] - template_h
    max_x = search.shape[1] - template_w
    for y in range(0, max_y + 1, stride):
        for x in range(0, max_x + 1, stride):
            patch = search[y : y + template_h, x : x + template_w]
            if use_absolute_difference:
                score = 1.0 - float(np.mean(np.abs(patch - template)) / 255.0)
            else:
                patch_centered = patch - float(patch.mean())
                patch_norm = float(np.linalg.norm(patch_centered))
                if patch_norm == 0:
                    continue
                score = float(np.sum(patch_centered * template_centered) / (patch_norm * template_norm))
            if score > best_score:
                best_score = score
                best_xy = (x, y)

    if best_xy is None:
        x_ratio = None
        y_ratio = None
    else:
        x_ratio = (left + best_xy[0] + template_w / 2) / screen_w
        y_ratio = (top + best_xy[1] + template_h / 2) / screen_h

    ok = bool(best_xy is not None and best_score >= threshold)
    return {
        "ok": ok,
        "score": best_score,
        "threshold": threshold,
        "x_ratio": x_ratio,
        "y_ratio": y_ratio,
        "image_path": str(screenshot_path),
        "template_image_path": template_image_path,
        "search_region": {
            "left_ratio": search_left_ratio,
            "top_ratio": search_top_ratio,
            "right_ratio": search_right_ratio,
            "bottom_ratio": search_bottom_ratio,
        },
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


def click_wechat_by_template(
    template_image_path: str,
    threshold: float = 0.20,
    search_left_ratio: float = 0.0,
    search_top_ratio: float = 0.0,
    search_right_ratio: float = 0.25,
    search_bottom_ratio: float = 1.0,
    downscale: float = 0.5,
    stride: int = 2,
) -> dict[str, Any]:
    match = locate_template_in_wechat(
        template_image_path,
        threshold,
        search_left_ratio,
        search_top_ratio,
        search_right_ratio,
        search_bottom_ratio,
        downscale,
        stride,
    )
    store = ConversationStore()
    stored_image = store.save_screenshot("__wechat_click__", match["image_path"])
    match["image_path"] = stored_image

    if not match["ok"]:
        event = store.append_event("__wechat_click__", "click_wechat_by_template", {"clicked": False, "match": match})
        return {"clicked": False, "match": match, "event": event}

    click_result = click_wechat_normalized(float(match["x_ratio"]), float(match["y_ratio"]))
    event = store.append_event(
        "__wechat_click__",
        "click_wechat_by_template",
        {
            "clicked": True,
            "match": match,
            "click_result": click_result,
        },
    )
    return {"clicked": True, "match": match, "click_result": click_result, "event": event}


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
