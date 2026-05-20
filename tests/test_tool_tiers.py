from __future__ import annotations

import unittest

from wechat_mcp.tool_tiers import allowed_tools_for_mode


class ToolTierTests(unittest.TestCase):
    def test_daily_mode_excludes_write_and_send_tools(self):
        tools = set(allowed_tools_for_mode("daily"))
        self.assertIn("daily_check_once", tools)
        self.assertNotIn("write_reply", tools)
        self.assertNotIn("send_message_confirmed", tools)

    def test_assist_mode_can_write_but_not_send(self):
        tools = set(allowed_tools_for_mode("assist"))
        self.assertIn("write_reply", tools)
        self.assertNotIn("send_message_confirmed", tools)

    def test_send_mode_must_be_explicit(self):
        tools = set(allowed_tools_for_mode("send"))
        self.assertIn("send_message_confirmed", tools)
        self.assertIn("auto_send_message", tools)


if __name__ == "__main__":
    unittest.main()
