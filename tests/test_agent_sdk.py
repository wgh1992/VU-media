from __future__ import annotations

import unittest

from wechat_mcp.agent_sdk import instructions_for_mode


class AgentSdkTests(unittest.TestCase):
    def test_send_mode_sends_clear_requests_without_second_confirmation(self):
        instructions = instructions_for_mode("send")

        self.assertIn("Do not ask for a second confirmation", instructions)
        self.assertIn("Use confirm=false by default", instructions)
        self.assertIn("重新发", instructions)
        self.assertIn("Do not treat an existing matching outgoing bubble as a reason to skip", instructions)


if __name__ == "__main__":
    unittest.main()
