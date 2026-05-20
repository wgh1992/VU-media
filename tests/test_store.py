from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wechat_mcp.store import ConversationStore, safe_contact_id, text_log_payload


class ConversationStoreTests(unittest.TestCase):
    def test_safe_contact_id_is_stable_and_hides_name(self):
        first = safe_contact_id("小王")
        second = safe_contact_id("小王")
        self.assertEqual(first, second)
        self.assertNotIn("小王", first)
        self.assertEqual(len(first), 16)

    def test_append_and_recent_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConversationStore(tmp)
            event = store.append_event("Alice", "check", {"ok": True})

            events = store.recent_events("Alice")
            self.assertEqual(events, [event])
            self.assertEqual(events[0]["payload"]["ok"], True)

            path = Path(tmp) / "sessions" / safe_contact_id("Alice") / "events.jsonl"
            raw = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(raw["event_type"], "check")

    def test_recent_events_limit_is_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConversationStore(tmp)
            for i in range(105):
                store.append_event("Alice", "n", {"i": i})

            self.assertEqual(len(store.recent_events("Alice", 1000)), 100)
            self.assertEqual(len(store.recent_events("Alice", 0)), 1)

    def test_save_screenshot_copies_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")

            store = ConversationStore(Path(tmp) / "data")
            saved = Path(store.save_screenshot("Alice", source))

            self.assertTrue(saved.exists())
            self.assertEqual(saved.read_bytes(), b"fake-png")

    def test_text_log_payload_redacts_full_text_by_default(self):
        with patch.dict(os.environ, {"WECHAT_MCP_STORE_MESSAGE_TEXT": "false"}):
            payload = text_log_payload("hello secret world")

        self.assertEqual(payload["text_length"], 18)
        self.assertIn("text_preview", payload)
        self.assertNotIn("text", payload)

    def test_text_log_payload_can_store_full_text(self):
        with patch.dict(os.environ, {"WECHAT_MCP_STORE_MESSAGE_TEXT": "true"}):
            payload = text_log_payload("hello")

        self.assertEqual(payload["text"], "hello")


if __name__ == "__main__":
    unittest.main()
