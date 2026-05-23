from __future__ import annotations

import unittest

from wechat_mcp.agent_sdk import instructions_for_mode


class AgentSdkTests(unittest.TestCase):
    def test_send_mode_sends_clear_requests_without_second_confirmation(self):
        instructions = instructions_for_mode("send")

        self.assertIn("Do not ask for a second confirmation", instructions)
        self.assertIn("Use confirm=false by default", instructions)
        self.assertIn("use read_current_chat with scroll_pages greater than 1", instructions)
        self.assertIn("scroll_delay_seconds", instructions)
        self.assertIn("18-30", instructions)
        self.assertIn("use convert_visible_voice_to_text", instructions)
        self.assertIn("转换为文字", instructions)
        self.assertIn("call auto_send_message directly", instructions)
        self.assertIn("重新发", instructions)
        self.assertIn("Do not treat an existing matching outgoing bubble as a reason to skip", instructions)
        self.assertIn("first try the relevant send/focus tool", instructions)


if __name__ == "__main__":
    unittest.main()
