from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import pyperclip
try:
    from pywinauto import Desktop
    from pywinauto.keyboard import send_keys
    from pywinauto.mouse import click, scroll
except Exception:
    Desktop = None
    send_keys = None
    click = None
    scroll = None

from .config import get_settings
from .screen import Region, capture_region


WECHAT_PROCESS_NAMES = {"weixin.exe", "wechat.exe", "wechatappex.exe"}
WINDOW_CHROME_GUARD_PX = 48
WECHAT_MAIN_TITLES = {"weixin", "wechat", "微信"}
WECHAT_TASKBAR_LABELS = ("wechat", "weixin", "微信")


def _require_desktop_automation() -> None:
    if Desktop is None or send_keys is None or click is None or scroll is None:
        raise RuntimeError(
            "Windows desktop automation is not available in this runtime. "
            "Run this command on the Windows host Python environment, not inside Linux Docker."
        )


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


def _restore_wechat_process_windows() -> None:
    try:
        import psutil
        import win32con
        import win32gui
        import win32process
    except Exception:
        return

    wechat_pids = {
        process.info["pid"]
        for process in psutil.process_iter(["pid", "name"])
        if (process.info.get("name") or "").lower() in WECHAT_PROCESS_NAMES
    }
    if not wechat_pids:
        return

    restored = False

    def enum_callback(hwnd, _extra):
        nonlocal restored
        if restored:
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid not in wechat_pids:
                return True
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            if title.strip().lower() not in WECHAT_MAIN_TITLES:
                return True
            if not class_name.startswith("Qt") or "TrayIcon" in class_name:
                return True
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            if right - left <= 0 or bottom - top <= 0:
                return True
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            restored = True
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        return


def _ensure_window_not_topmost(window) -> None:
    try:
        import win32con
        import win32gui
    except Exception:
        return

    try:
        win32gui.SetWindowPos(
            int(window.handle),
            win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )
    except Exception:
        return


def _is_foreground_window(window) -> bool:
    try:
        import win32gui
    except Exception:
        return False

    try:
        return win32gui.GetForegroundWindow() == int(window.handle)
    except Exception:
        return False


def _activate_window(window) -> bool:
    try:
        import win32api
        import win32con
        import win32gui
        import win32process
    except Exception:
        return False

    try:
        hwnd = int(window.handle)
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        _ensure_window_not_topmost(window)
        win32gui.BringWindowToTop(hwnd)

        foreground = win32gui.GetForegroundWindow()
        current_thread = win32api.GetCurrentThreadId()
        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground)

        attached_target = False
        attached_foreground = False
        try:
            if target_thread:
                win32process.AttachThreadInput(current_thread, target_thread, True)
                attached_target = True
            if foreground_thread and foreground_thread != target_thread:
                win32process.AttachThreadInput(current_thread, foreground_thread, True)
                attached_foreground = True
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetActiveWindow(hwnd)
            win32gui.SetFocus(hwnd)
        finally:
            if attached_foreground:
                win32process.AttachThreadInput(current_thread, foreground_thread, False)
            if attached_target:
                win32process.AttachThreadInput(current_thread, target_thread, False)
    except Exception:
        return False

    time.sleep(0.2)
    return _is_foreground_window(window)


def _activate_wechat_from_taskbar() -> bool:
    _require_desktop_automation()
    desktop = Desktop(backend="uia")
    for class_name in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        try:
            taskbar = desktop.window(class_name=class_name)
            controls = taskbar.descendants()
        except Exception:
            continue
        for control in controls:
            try:
                label = (control.window_text() or "").strip().lower()
                if not label or not any(marker in label for marker in WECHAT_TASKBAR_LABELS):
                    continue
                control.click_input()
                time.sleep(0.6)
                return True
            except Exception:
                continue
    return False


def _find_wechat_window(allow_restore: bool = True):
    _require_desktop_automation()
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
            if not title or not window.is_visible():
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
            if width > 0 and height > 0:
                score += min(width * height // 100_000, 20)
            else:
                score -= 10
            candidates.append((score, window))
        except Exception:
            continue
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates[0][0] > 0:
            return candidates[0][1]
    if allow_restore:
        _restore_wechat_process_windows()
        time.sleep(0.5)
        return _find_wechat_window(allow_restore=False)
    raise RuntimeError("Could not find a visible WeChat window. Open and log in to WeChat first.")


def list_visible_windows() -> list[dict[str, str | int | bool]]:
    _require_desktop_automation()
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
    try:
        rect = window.rectangle()
        if rect.right - rect.left <= 0 or rect.bottom - rect.top <= 0:
            window.restore()
            time.sleep(0.5)
    except Exception:
        pass
    activated = _activate_window(window)
    if not activated:
        try:
            window.set_focus()
            time.sleep(0.2)
            activated = _is_foreground_window(window)
        except Exception:
            activated = False
    if not activated and _activate_wechat_from_taskbar():
        window = _find_wechat_window(allow_restore=False)
        _activate_window(window)
    _ensure_window_not_topmost(window)
    time.sleep(0.3)
    return window


def get_wechat_bounds() -> WindowBounds:
    window = focus_wechat()
    rect = window.rectangle()
    return WindowBounds(rect.left, rect.top, rect.right, rect.bottom)


def capture_wechat_window(output_path: str | Path | None = None) -> Path:
    bounds = get_wechat_bounds()
    return capture_region(bounds.as_region(), output_path)


def capture_wechat_chat_pane(output_path: str | Path | None = None) -> Path:
    bounds = get_wechat_bounds()
    left = bounds.left + int(bounds.width * 0.35)
    region = {
        "left": left,
        "top": bounds.top,
        "width": bounds.right - left,
        "height": bounds.height,
    }
    return capture_region(region, output_path)


def close_transient_overlays() -> str:
    focus_wechat()
    send_keys("{ESC}")
    time.sleep(0.3)
    return "Pressed Escape to close transient WeChat overlays."


def click_current_chat_input() -> str:
    _require_desktop_automation()
    bounds = get_wechat_bounds()
    x = bounds.left + int(bounds.width * 0.70)
    y = bounds.bottom - 80
    click(button="left", coords=(x, y))
    time.sleep(0.2)
    return f"Clicked current chat input area at ({x}, {y})."


def scroll_current_chat_history(notches: int = 36, delay_seconds: float = 0.02) -> str:
    _require_desktop_automation()
    bounds = get_wechat_bounds()
    x = bounds.right - 18
    y = bounds.top + int(bounds.height * 0.55)
    total = abs(int(notches))
    click(button="left", coords=(x, y))
    remaining = total
    while remaining > 0:
        step = min(remaining, 20)
        scroll(wheel_dist=step, coords=(x, y))
        remaining -= step
    time.sleep(max(0.0, float(delay_seconds)))
    return f"Scrolled current chat history up by {total} notches from the scrollbar edge at ({x}, {y}) with {max(0.0, float(delay_seconds)):.2f}s delay."


def scroll_current_chat_to_bottom(notches: int = 120, delay_seconds: float = 0.15) -> str:
    _require_desktop_automation()
    bounds = get_wechat_bounds()
    x = bounds.right - 18
    y = bounds.top + int(bounds.height * 0.55)
    total = abs(int(notches))
    click(button="left", coords=(x, y))
    remaining = total
    while remaining > 0:
        step = min(remaining, 20)
        scroll(wheel_dist=-step, coords=(x, y))
        remaining -= step
    time.sleep(max(0.0, float(delay_seconds)))
    return f"Scrolled current chat to bottom by {total} notches from the scrollbar edge at ({x}, {y}) with {max(0.0, float(delay_seconds)):.2f}s delay."


def click_wechat_normalized(x_ratio: float, y_ratio: float) -> str:
    _require_desktop_automation()
    if not 0 <= x_ratio <= 1 or not 0 <= y_ratio <= 1:
        raise ValueError("x_ratio and y_ratio must be between 0 and 1.")

    bounds = get_wechat_bounds()
    x = bounds.left + int(bounds.width * x_ratio)
    y = bounds.top + int(bounds.height * y_ratio)
    min_safe_y = bounds.top + WINDOW_CHROME_GUARD_PX
    if y < min_safe_y:
        raise ValueError(
            f"Refusing to click WeChat window chrome/titlebar area at y={y}. "
            f"Use a y_ratio that resolves below {min_safe_y}."
        )
    click(button="left", coords=(x, y))
    time.sleep(1.0)
    return f"Clicked WeChat normalized coordinate ({x_ratio:.3f}, {y_ratio:.3f}) at ({x}, {y})."


def click_visible_voice_to_text(index: int = 1) -> str:
    if index < 1:
        raise ValueError("index must be >= 1.")

    window = focus_wechat()
    candidates = []
    for control in window.descendants():
        try:
            text = (control.window_text() or "").strip().lower()
            if not any(label in text for label in ("convert to text", "转文字", "转换为文字", "语音转文字")):
                continue
            rect = control.rectangle()
            if rect.right <= rect.left or rect.bottom <= rect.top:
                continue
            candidates.append((rect.top, rect.left, control, rect))
        except Exception:
            continue

    if not candidates:
        raise RuntimeError("Could not find a visible voice 'Convert to text' / '转文字' button in the current WeChat chat.")

    candidates.sort(key=lambda item: (item[0], item[1]))
    if index > len(candidates):
        raise RuntimeError(f"Only found {len(candidates)} visible voice convert buttons; requested index {index}.")

    _, _, control, rect = candidates[index - 1]
    try:
        control.click_input()
    except Exception:
        click(button="left", coords=(rect.left + rect.width() // 2, rect.top + rect.height() // 2))
    time.sleep(1.0)
    return f"Clicked visible voice Convert to text / 转文字 button #{index}."


def focus_chat(chat_name: str) -> str:
    _require_desktop_automation()
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
    _require_desktop_automation()
    if not text.strip():
        raise ValueError("text is required.")

    focus_wechat()
    pyperclip.copy(text)
    send_keys("^v")
    return "Reply text pasted into the active WeChat input box."


def replace_current_chat_input(text: str) -> str:
    _require_desktop_automation()
    if not text.strip():
        raise ValueError("text is required.")

    click_current_chat_input()
    send_keys("^a")
    time.sleep(0.1)
    send_keys("{BACKSPACE}")
    time.sleep(0.1)
    pyperclip.copy(text)
    send_keys("^v")
    return "Current chat input replaced with reply text."


def press_enter_to_send() -> str:
    _require_desktop_automation()
    focus_wechat()
    send_keys("{ENTER}")
    return "Pressed Enter in WeChat."
