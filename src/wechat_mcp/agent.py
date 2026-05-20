from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .prompts import PromptManager
from .store import ConversationStore, utc_now_iso
from .vision import analyze_screenshot
from .wechat import capture_wechat_window


def daily_check_once(note: str | None = None) -> dict[str, Any]:
    """Run a low-risk daily WeChat check without opening chats or sending messages."""
    image_path = capture_wechat_window()
    prompt = PromptManager().get(
        "daily_check",
        "Inspect the visible WeChat conversation list and report unread or new messages as JSON.",
    )
    if note:
        prompt = f"{prompt}\n\nOperator note: {note}"

    analysis = analyze_screenshot(image_path, prompt)
    store = ConversationStore()
    stored_image = store.save_screenshot("__daily_check__", image_path)
    event = store.append_event(
        "__daily_check__",
        "daily_check",
        {
            "image_path": stored_image,
            "analysis": analysis,
            "note": note,
        },
    )
    report_path = _write_daily_report(store.data_dir, analysis, stored_image, note)
    return {
        "analysis": analysis,
        "event": event,
        "report_path": str(report_path),
        "image_path": stored_image,
    }


def _write_daily_report(
    data_dir: Path,
    analysis: str,
    image_path: str,
    note: str | None,
) -> Path:
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now_iso().replace(":", "-")
    path = reports_dir / f"daily-check-{timestamp}.json"
    payload = {
        "timestamp": utc_now_iso(),
        "image_path": image_path,
        "note": note,
        "analysis": analysis,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
