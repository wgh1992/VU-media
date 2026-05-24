from __future__ import annotations

import unittest

from wechat_mcp.agent_sdk import instructions_for_mode, model_settings_from_config
from wechat_mcp.config import Settings


class AgentSdkTests(unittest.TestCase):
    def test_send_mode_sends_clear_requests_without_second_confirmation(self):
        instructions = instructions_for_mode("send")

        self.assertIn("Do not ask for a second confirmation", instructions)
        self.assertIn("Use confirm=false by default", instructions)
        self.assertIn("focus_unread_by_red_dot", instructions)
        self.assertIn("use read_current_chat with scroll_pages greater than 1", instructions)
        self.assertIn("scroll_delay_seconds", instructions)
        self.assertIn("scroll_notches=80", instructions)
        self.assertIn("use convert_visible_voice_to_text", instructions)
        self.assertIn("转换为文字", instructions)
        self.assertIn("call auto_send_message directly", instructions)
        self.assertIn("重新发", instructions)
        self.assertIn("Do not treat an existing matching outgoing bubble as a reason to skip", instructions)
        self.assertIn("first try the relevant send/focus tool", instructions)

    def test_model_settings_use_agent_runtime_config(self):
        settings = Settings(
            openai_api_key="secret",
            openai_model_fast="gpt-5.4-nano",
            agent_reasoning_effort="high",
            agent_verbosity="low",
            agent_service_tier="default",
            send_requires_confirm=False,
            wechat_window_title_regex=".*WeChat.*",
            wechat_window_class_regex="Qt.*",
            data_dir=".data",
            store_message_text=False,
            prompts_dir="prompts",
        )

        model_settings = model_settings_from_config(settings)

        self.assertEqual(model_settings.reasoning.effort, "high")
        self.assertEqual(model_settings.verbosity, "low")
        self.assertEqual(model_settings.extra_body, {"service_tier": "default"})


if __name__ == "__main__":
    unittest.main()
