from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wechat_mcp.history import read_current_chat_history


class HistoryTests(unittest.TestCase):
    def test_read_history_captures_and_scrolls_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.history.capture_wechat_chat_pane", return_value=source) as capture_mock:
                    with patch("wechat_mcp.history.analyze_screenshot", return_value='{"visible_messages": []}') as analyze_mock:
                        with patch("wechat_mcp.history.scroll_current_chat_to_bottom", return_value="bottom") as bottom_mock:
                            with patch("wechat_mcp.history.scroll_current_chat_history", return_value="scrolled") as scroll_mock:
                                result = read_current_chat_history(
                                    scroll_pages=3,
                                    scroll_notches=4,
                                    scroll_delay_seconds=0.2,
                                    bottom_scroll_notches=70,
                                    settle_delay_seconds=0.4,
                                )

        self.assertEqual(result["scroll_pages"], 3)
        self.assertEqual(result["scroll_notches"], 4)
        self.assertEqual(result["bottom_scroll_notches"], 70)
        self.assertEqual(result["settle_delay_seconds"], 0.4)
        self.assertEqual(len(result["pages"]), 3)
        self.assertEqual(capture_mock.call_count, 3)
        self.assertEqual(analyze_mock.call_count, 3)
        bottom_mock.assert_called_once_with(70, 0.4)
        self.assertEqual(scroll_mock.call_count, 2)
        self.assertEqual(result["scroll_delay_seconds"], 0.2)
        scroll_mock.assert_called_with(4, 0.2)

    def test_read_history_clamps_page_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.history.capture_wechat_chat_pane", return_value=source):
                    with patch("wechat_mcp.history.analyze_screenshot", return_value='{}'):
                        with patch("wechat_mcp.history.scroll_current_chat_to_bottom"):
                            with patch("wechat_mcp.history.scroll_current_chat_history"):
                                result = read_current_chat_history(
                                    scroll_pages=99,
                                    scroll_notches=99,
                                    scroll_delay_seconds=9,
                                    bottom_scroll_notches=999,
                                    settle_delay_seconds=9,
                                )

        self.assertEqual(result["scroll_pages"], 10)
        self.assertEqual(result["scroll_notches"], 30)
        self.assertEqual(result["scroll_delay_seconds"], 1.0)
        self.assertEqual(result["bottom_scroll_notches"], 120)
        self.assertEqual(result["settle_delay_seconds"], 2.0)

    def test_read_history_can_skip_bottom_settle(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.history.capture_wechat_chat_pane", return_value=source):
                    with patch("wechat_mcp.history.analyze_screenshot", return_value='{}'):
                        with patch("wechat_mcp.history.scroll_current_chat_to_bottom") as bottom_mock:
                            result = read_current_chat_history(scroll_pages=1, settle_to_bottom=False)

        self.assertFalse(result["settle_to_bottom"])
        bottom_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
