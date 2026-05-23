from __future__ import annotations

import unittest
from unittest.mock import patch

from wechat_mcp.wechat import WindowBounds, scroll_current_chat_history, scroll_current_chat_to_bottom


class WeChatScrollTests(unittest.TestCase):
    def test_history_scroll_does_not_click_message_content(self):
        with patch("wechat_mcp.wechat.get_wechat_bounds", return_value=WindowBounds(0, 0, 1000, 800)):
            with patch("wechat_mcp.wechat.click") as click_mock:
                with patch("wechat_mcp.wechat.scroll") as scroll_mock:
                    with patch("wechat_mcp.wechat.time.sleep"):
                        result = scroll_current_chat_history(36, 0)

        click_mock.assert_not_called()
        self.assertGreaterEqual(scroll_mock.call_count, 1)
        self.assertIn("without clicking message content", result)

    def test_bottom_scroll_does_not_click_message_content(self):
        with patch("wechat_mcp.wechat.get_wechat_bounds", return_value=WindowBounds(0, 0, 1000, 800)):
            with patch("wechat_mcp.wechat.click") as click_mock:
                with patch("wechat_mcp.wechat.scroll") as scroll_mock:
                    with patch("wechat_mcp.wechat.time.sleep"):
                        result = scroll_current_chat_to_bottom(120, 0)

        click_mock.assert_not_called()
        self.assertGreaterEqual(scroll_mock.call_count, 1)
        self.assertIn("without clicking message content", result)


if __name__ == "__main__":
    unittest.main()
