from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wechat_mcp.prompts import PromptManager
from wechat_mcp.safety import auto_send_message, send_message_confirmed


class PromptManagerTests(unittest.TestCase):
    def test_prompt_fallback_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PromptManager(tmp)
            self.assertEqual(manager.get("missing", " fallback "), "fallback")

    def test_prompt_file_overrides_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft_reply.txt"
            path.write_text("Use this prompt", encoding="utf-8")
            manager = PromptManager(tmp)
            self.assertEqual(manager.get("draft_reply", "fallback"), "Use this prompt")

    def test_prompt_dir_can_come_from_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft_reply.txt"
            path.write_text("Env prompt", encoding="utf-8")
            with patch.dict("os.environ", {"WECHAT_MCP_PROMPTS_DIR": tmp}):
                manager = PromptManager()
                self.assertEqual(manager.get("draft_reply", "fallback"), "Env prompt")


class SafetyTests(unittest.TestCase):
    def test_send_refuses_without_confirm_by_default(self):
        result = send_message_confirmed(confirm=False)
        self.assertIn("Refused to send", result)

    def test_send_calls_enter_when_confirmed(self):
        with patch("wechat_mcp.safety.press_enter_to_send", return_value="sent") as mocked:
            result = send_message_confirmed(confirm=True)

        self.assertEqual(result, "sent")
        mocked.assert_called_once_with()

    def test_auto_send_respects_confirmation_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp, "WECHAT_SEND_REQUIRES_CONFIRM": "true"}):
                with patch("wechat_mcp.safety.focus_chat", return_value="focused") as focus_mock:
                    with patch("wechat_mcp.safety.write_reply", return_value="written") as write_mock:
                        with patch("wechat_mcp.safety.press_enter_to_send", return_value="sent") as enter_mock:
                            result = auto_send_message("File Transfer", "hello", confirm=False)

        self.assertFalse(result["sent"])
        self.assertIn("Refused to send", result["send_result"])
        focus_mock.assert_called_once_with("File Transfer")
        write_mock.assert_called_once_with("hello")
        enter_mock.assert_not_called()

    def test_auto_send_sends_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp, "WECHAT_SEND_REQUIRES_CONFIRM": "true"}):
                with patch("wechat_mcp.safety.focus_chat", return_value="focused"):
                    with patch("wechat_mcp.safety.write_reply", return_value="written"):
                        with patch("wechat_mcp.safety.press_enter_to_send", return_value="sent") as enter_mock:
                            result = auto_send_message("File Transfer", "hello", confirm=True)

        self.assertTrue(result["sent"])
        self.assertEqual(result["send_result"], "sent")
        enter_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
