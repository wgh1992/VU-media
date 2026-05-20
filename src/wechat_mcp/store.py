from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_contact_id(contact_name: str | None) -> str:
    raw = (contact_name or "unknown").strip() or "unknown"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return digest


def text_log_payload(text: str) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {
        "text_length": len(text),
        "text_preview": text[:24],
    }
    if settings.store_message_text:
        payload["text"] = text
    return payload


class ConversationStore:
    def __init__(self, data_dir: str | Path | None = None):
        settings = get_settings()
        self.data_dir = Path(data_dir or settings.data_dir).resolve()
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def session_dir(self, contact_name: str | None) -> Path:
        path = self.sessions_dir / safe_contact_id(contact_name)
        (path / "screenshots").mkdir(parents=True, exist_ok=True)
        return path

    def append_event(self, contact_name: str | None, event_type: str, payload: dict[str, Any]) -> dict:
        if not event_type.strip():
            raise ValueError("event_type is required.")

        event = {
            "timestamp": utc_now_iso(),
            "contact_id": safe_contact_id(contact_name),
            "contact_name": contact_name,
            "event_type": event_type,
            "payload": payload,
        }
        path = self.session_dir(contact_name) / "events.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def save_screenshot(self, contact_name: str | None, image_path: str | Path) -> str:
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"Screenshot does not exist: {source}")

        target = self.session_dir(contact_name) / "screenshots" / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return str(target)

    def append_summary(self, contact_name: str | None, summary: str, source: dict[str, Any] | None = None) -> dict:
        return self.append_event(
            contact_name,
            "summary",
            {
                "summary": summary,
                "source": source or {},
            },
        )

    def recent_events(self, contact_name: str | None, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        path = self.session_dir(contact_name) / "events.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        events = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events
