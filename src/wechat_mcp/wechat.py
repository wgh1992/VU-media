from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import pyperclip
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

from .config import get_settings
from .screen import Region, capture_region


@dataclass(frozen=True)
class WindowBounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_region(self) -> Region:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


def _find_wechat_window():
    settings = get_settings()
    title_pattern = re.compile(settings.wechat_window_title_regex, re.IGNORECASE)
    class_pattern = (
        re.compile(settings.wechat_window_class_regex, re.IGNORECASE)
        if settings.wechat_window_class_regex
        else None
    )
    desktop = Desktop(backend="uia")
    windows = desktop.windows()
    candidates = []
    for window in windows:
        try:
            title = window.window_text()
            class_name = window.class_name()
            rect = window.rectangle()
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if not title or not window.is_visible() or width <= 0 or height <= 0:
                continue
            if not title_pattern.search(title):
                continue

            score = 0
            if class_pattern and class_pattern.search(class_name):
                score += 100
            if title.lower() in {"weixin", "wechat", "微信"}:
                score += 50
            if class_name in {"Chrome_WidgetWin_1", "CabinetWClass"}:
                score -= 100
            score += min(width * height // 100_000, 20)
            candidates.append((score, window))
        except Exception:
            continue
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates[0][0] > 0:
            return candidates[0][1]
    raise RuntimeError("Could not find a visible WeChat window. Open and log in to WeChat first.")


def list_visible_windows() -> list[dict[str, str | int | bool]]:
    desktop = Desktop(backend="uia")
    results = []
    for window in desktop.windows():
        try:
            rect = window.rectangle()
            title = window.window_text()
            class_name = window.class_name()
            process_id = window.process_id()
            if not window.is_visible():
                continue
            results.append(
                {
                    "title": title,
                    "class_name": class_name,
                    "process_id": process_id,
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top,
                }
            )
        except Exception:
            continue
    return results


def focus_wechat():
    window = _find_wechat_window()
    window.set_focus()
    time.sleep(0.3)
    return window


def get_wechat_bounds() -> WindowBounds:
    window = focus_wechat()
    rect = window.rectangle()
    return WindowBounds(rect.left, rect.top, rect.right, rect.bottom)


def capture_wechat_window(output_path: str | Path | None = None) -> Path:
    bounds = get_wechat_bounds()
    return capture_region(bounds.as_region(), output_path)


def close_transient_overlays() -> str:
    focus_wechat()
    send_keys("{ESC}")
    time.sleep(0.3)
    return "Pressed Escape to close transient WeChat overlays."


def focus_chat(chat_name: str) -> str:
    if not chat_name.strip():
        raise ValueError("chat_name is required.")

    focus_wechat()
    pyperclip.copy(chat_name)
    send_keys("^f")
    time.sleep(0.2)
    send_keys("^v")
    time.sleep(0.5)
    send_keys("{ENTER}")
    time.sleep(0.8)
    return f"Focused chat search result for: {chat_name}"


def write_reply(text: str) -> str:
    if not text.strip():
        raise ValueError("text is required.")

    focus_wechat()
    pyperclip.copy(text)
    send_keys("^v")
    return "Reply text pasted into the active WeChat input box."


def press_enter_to_send() -> str:
    focus_wechat()
    send_keys("{ENTER}")
    return "Pressed Enter in WeChat."
