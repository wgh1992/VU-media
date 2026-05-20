from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wechat_mcp.visual_agent import safe_send_current_chat_with_vision


class VisualAgentTests(unittest.TestCase):
    def test_visual_send_stops_when_initial_verification_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp, "WECHAT_SEND_REQUIRES_CONFIRM": "true"}):
                with patch("wechat_mcp.visual_agent.capture_wechat_window", return_value=source):
                    with patch(
                        "wechat_mcp.visual_agent.verify_screenshot_step",
                        return_value={"ok": False, "confidence": "low", "blocking_issue": "search overlay"},
                    ):
                        with patch("wechat_mcp.visual_agent.write_reply") as write_mock:
                            with patch("wechat_mcp.visual_agent.press_enter_to_send") as send_mock:
                                result = safe_send_current_chat_with_vision("hello", confirm=True)

        self.assertFalse(result["sent"])
        self.assertEqual(result["stopped_at"], "before")
        write_mock.assert_not_called()
        send_mock.assert_not_called()

    def test_visual_send_sends_after_step_verifications(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            ok = {"ok": True, "confidence": "high"}
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp, "WECHAT_SEND_REQUIRES_CONFIRM": "true"}):
                with patch("wechat_mcp.visual_agent.capture_wechat_window", return_value=source):
                    with patch("wechat_mcp.visual_agent.verify_screenshot_step", return_value=ok) as verify_mock:
                        with patch("wechat_mcp.visual_agent.close_transient_overlays", return_value="closed"):
                            with patch("wechat_mcp.visual_agent.click_current_chat_input", return_value="clicked"):
                                with patch("wechat_mcp.visual_agent.write_reply", return_value="written") as write_mock:
                                    with patch("wechat_mcp.visual_agent.press_enter_to_send", return_value="sent") as send_mock:
                                        result = safe_send_current_chat_with_vision("hello", confirm=True)
                                        trace_exists = Path(result["trace_path"]).exists()

        self.assertTrue(result["sent"])
        self.assertEqual(result["stopped_at"], None)
        self.assertEqual(verify_mock.call_count, 4)
        write_mock.assert_called_once_with("hello")
        send_mock.assert_called_once_with()
        self.assertTrue(trace_exists)


if __name__ == "__main__":
    unittest.main()
