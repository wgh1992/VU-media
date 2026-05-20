from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

from .prompts import PromptManager
from .store import ConversationStore, text_log_payload, utc_now_iso
from .vision import analyze_screenshot
from .wechat import (
    capture_wechat_window,
    click_current_chat_input,
    press_enter_to_send,
    replace_current_chat_input,
)
from .config import get_settings


@dataclass
class VisualStep:
    name: str
    expectation: str
    image_path: str
    verification: dict[str, Any]


class VisualRunTrace:
    def __init__(self, run_name: str = "safe-send-current"):
        store = ConversationStore()
        self.data_dir = store.data_dir
        timestamp = utc_now_iso().replace(":", "-")
        self.run_id = f"{run_name}-{timestamp}-{int(time() * 1000)}"
        self.run_dir = self.data_dir / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"

    def capture(self, step_name: str) -> Path:
        temp_path = capture_wechat_window()
        target = self.run_dir / f"{len(list(self.run_dir.glob('*.png'))) + 1:02d}-{step_name}.png"
        shutil.copy2(temp_path, target)
        return target

    def append(self, event: dict[str, Any]) -> None:
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": utc_now_iso(), **event}, ensure_ascii=False) + "\n")


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
        "confidence": "low",
        "observed_state": text[:1000],
        "blocking_issue": "Verifier did not return valid JSON.",
        "recommended_next_action": "Stop and inspect the screenshot manually.",
    }


def verify_screenshot_step(
    image_path: str | Path,
    expectation: str,
    expected_text: str | None = None,
) -> dict[str, Any]:
    prompt = PromptManager().get(
        "vision_verify_step",
        "Inspect this WeChat screenshot and verify whether the expected state is true. Return JSON only.",
    )
    request = {
        "expectation": expectation,
        "expected_text": expected_text,
        "output_format": "JSON only",
    }
    raw = analyze_screenshot(
        image_path,
        f"{prompt}\n\nVerification request:\n{json.dumps(request, ensure_ascii=False)}",
    )
    result = _parse_json_object(raw)
    result["raw"] = raw
    return result


def _is_ok(verification: dict[str, Any]) -> bool:
    return bool(verification.get("ok")) and verification.get("confidence") in {"high", "medium"}


def _is_chat_window_usable(verification: dict[str, Any]) -> bool:
    return bool(verification.get("current_chat")) and bool(verification.get("input_box_visible"))


def safe_send_current_chat_with_vision(text: str, confirm: bool = False) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required.")

    trace = VisualRunTrace()
    steps: list[VisualStep] = []

    def verify(step_name: str, expectation: str, expected_text: str | None = None) -> dict[str, Any]:
        image_path = trace.capture(step_name)
        verification = verify_screenshot_step(image_path, expectation, expected_text)
        step = VisualStep(step_name, expectation, str(image_path), verification)
        steps.append(step)
        trace.append(
            {
                "type": "verification",
                "step": step_name,
                "expectation": expectation,
                "image_path": str(image_path),
                "verification": verification,
            }
        )
        return verification

    initial = verify(
        "before",
        "WeChat desktop is visible, File Transfer or another chat is open, and the chat input area is visible. No browser page or WeChat search results should be in front. Existing draft text in the chat input is allowed because the next write step will replace it.",
    )
    if not (_is_ok(initial) or _is_chat_window_usable(initial)):
        return _finish_visual_send(trace, steps, text, sent=False, stopped_at="before", reason="Initial state failed visual verification.")

    ready = verify(
        "ready",
        "The current WeChat chat input area is visible and ready for typing in File Transfer or another chat. Existing draft text is allowed because the write step will replace it.",
    )
    if not (_is_ok(ready) or _is_chat_window_usable(ready)):
        return _finish_visual_send(trace, steps, text, sent=False, stopped_at="ready", reason="Input area was not ready.")

    click_result = click_current_chat_input()
    trace.append({"type": "action", "step": "click_input", "result": click_result})

    write_result = replace_current_chat_input(text)
    trace.append({"type": "action", "step": "write_message", "result": write_result})

    drafted = verify(
        "drafted",
        "The expected text is in the WeChat chat input box, not in a search box. It has not been sent yet.",
        text,
    )
    if not _is_ok(drafted):
        return _finish_visual_send(trace, steps, text, sent=False, stopped_at="drafted", reason="Draft text was not verified in the chat input box.")

    settings = get_settings()
    if settings.send_requires_confirm and not confirm:
        return _finish_visual_send(trace, steps, text, sent=False, stopped_at="confirm", reason="Confirmation required before sending.")

    send_result = press_enter_to_send()
    trace.append({"type": "action", "step": "send", "result": send_result})

    sent_check = verify(
        "sent",
        "The expected text appears as the latest outgoing WeChat message, or the input box is clearly cleared after sending.",
        text,
    )
    sent = _is_ok(sent_check)
    return _finish_visual_send(
        trace,
        steps,
        text,
        sent=sent,
        stopped_at=None if sent else "sent",
        reason=None if sent else "Send action completed, but visual verification did not confirm delivery.",
    )


def _finish_visual_send(
    trace: VisualRunTrace,
    steps: list[VisualStep],
    text: str,
    sent: bool,
    stopped_at: str | None,
    reason: str | None,
) -> dict[str, Any]:
    payload = {
        **text_log_payload(text),
        "sent": sent,
        "stopped_at": stopped_at,
        "reason": reason,
        "run_id": trace.run_id,
        "run_dir": str(trace.run_dir),
        "trace_path": str(trace.trace_path),
        "steps": [
            {
                "name": step.name,
                "expectation": step.expectation,
                "image_path": step.image_path,
                "verification": step.verification,
            }
            for step in steps
        ],
    }
    trace.append({"type": "finish", **payload})
    event = ConversationStore().append_event("__current_chat__", "safe_send_current_chat_with_vision", payload)
    return {**payload, "event": event}
