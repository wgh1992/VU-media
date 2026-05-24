from __future__ import annotations

import unittest
from unittest.mock import patch

from wechat_mcp.wechat import WindowBounds, click_wechat_normalized, focus_wechat, scroll_current_chat_history, scroll_current_chat_to_bottom


class FakeWindow:
    handle = 123

    def __init__(self):
        self.focused = False

    def rectangle(self):
        return WindowBounds(0, 0, 1000, 800)

    def set_focus(self):
        self.focused = True


class WeChatScrollTests(unittest.TestCase):
    def test_history_scroll_clicks_scrollbar_edge_not_message_content(self):
        with patch("wechat_mcp.wechat.get_wechat_bounds", return_value=WindowBounds(0, 0, 1000, 800)):
            with patch("wechat_mcp.wechat.click") as click_mock:
                with patch("wechat_mcp.wechat.scroll") as scroll_mock:
                    with patch("wechat_mcp.wechat.time.sleep"):
                        result = scroll_current_chat_history(36, 0)

        click_mock.assert_called_once_with(button="left", coords=(982, 440))
        self.assertGreaterEqual(scroll_mock.call_count, 1)
        self.assertIn("scrollbar edge", result)

    def test_bottom_scroll_clicks_scrollbar_edge_not_message_content(self):
        with patch("wechat_mcp.wechat.get_wechat_bounds", return_value=WindowBounds(0, 0, 1000, 800)):
            with patch("wechat_mcp.wechat.click") as click_mock:
                with patch("wechat_mcp.wechat.scroll") as scroll_mock:
                    with patch("wechat_mcp.wechat.time.sleep"):
                        result = scroll_current_chat_to_bottom(120, 0)

        click_mock.assert_called_once_with(button="left", coords=(982, 440))
        self.assertGreaterEqual(scroll_mock.call_count, 1)
        self.assertIn("scrollbar edge", result)

    def test_normalized_click_refuses_window_chrome_area(self):
        with patch("wechat_mcp.wechat.get_wechat_bounds", return_value=WindowBounds(0, 0, 1000, 800)):
            with patch("wechat_mcp.wechat.click") as click_mock:
                with self.assertRaises(ValueError):
                    click_wechat_normalized(0.85, 0.02)

        click_mock.assert_not_called()

    def test_focus_wechat_uses_taskbar_fallback_when_foreground_activation_fails(self):
        first_window = FakeWindow()
        second_window = FakeWindow()
        with patch("wechat_mcp.wechat._find_wechat_window", side_effect=[first_window, second_window]) as find_mock:
            with patch("wechat_mcp.wechat._activate_window", side_effect=[False, True]) as activate_mock:
                with patch("wechat_mcp.wechat._is_foreground_window", return_value=False):
                    with patch("wechat_mcp.wechat._activate_wechat_from_taskbar", return_value=True) as taskbar_mock:
                        with patch("wechat_mcp.wechat._ensure_window_not_topmost") as not_topmost_mock:
                            with patch("wechat_mcp.wechat.time.sleep"):
                                result = focus_wechat()

        self.assertIs(result, second_window)
        self.assertEqual(find_mock.call_count, 2)
        self.assertEqual(activate_mock.call_count, 2)
        taskbar_mock.assert_called_once_with()
        not_topmost_mock.assert_called_with(second_window)


if __name__ == "__main__":
    unittest.main()
