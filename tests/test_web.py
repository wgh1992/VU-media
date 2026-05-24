from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from wechat_mcp.web import _prompt_with_context, app


class WebTests(unittest.TestCase):
    def test_health_redacts_api_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "secret"}, clear=False):
            client = TestClient(app)
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["settings"]["openai_api_key"])
        self.assertNotEqual(body["settings"]["openai_api_key"], "secret")
        self.assertEqual(body["modes"], ["daily", "send"])

    def test_chat_runs_agent(self):
        result = SimpleNamespace(final_output="ok from agent")
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=result)) as run_mock:
                    client = TestClient(app)
                    response = client.post(
                        "/api/chat",
                        json={"message": "read current chat", "mode": "send", "max_turns": 3},
                    )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["output"], "ok from agent")
        self.assertEqual(body["mode"], "send")
        self.assertTrue(body["conversation_id"].startswith("web-"))
        self.assertEqual(body["screenshots"], [])
        run_mock.assert_awaited_once_with("read current chat", mode="send", max_turns=3)

    def test_chat_returns_new_screenshots(self):
        result = SimpleNamespace(final_output="ok with screenshot")

        async def create_screenshot(*args, **kwargs):
            screenshot_dir = Path(tmp) / "sessions" / "__current_chat__" / "screenshots"
            screenshot_dir.mkdir(parents=True)
            (screenshot_dir / "chat.png").write_bytes(b"png")
            return result

        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(side_effect=create_screenshot)):
                    client = TestClient(app)
                    response = client.post(
                        "/api/chat",
                        json={"message": "read current chat", "mode": "send", "max_turns": 3},
                    )

        self.assertEqual(response.status_code, 200)
        screenshots = response.json()["screenshots"]
        self.assertEqual(len(screenshots), 1)
        self.assertEqual(screenshots[0]["name"], "chat.png")
        self.assertIn("/api/screenshots/", screenshots[0]["url"])

    def test_chat_uses_conversation_history(self):
        result = SimpleNamespace(final_output="second answer")
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=result)) as run_mock:
                    client = TestClient(app)
                    response = client.post(
                        "/api/chat",
                        json={
                            "conversation_id": "web-test",
                            "message": "second question",
                            "mode": "send",
                            "max_turns": 3,
                        },
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_id"], "web-test")
        prompt = run_mock.await_args.args[0]
        self.assertEqual(prompt, "second question")

        result = SimpleNamespace(final_output="third answer")
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                client = TestClient(app)
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=SimpleNamespace(final_output="first answer"))):
                    client.post(
                        "/api/chat",
                        json={
                            "conversation_id": "same-chat",
                            "message": "first question",
                            "mode": "send",
                            "max_turns": 3,
                        },
                    )
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=result)) as run_mock:
                    client.post(
                        "/api/chat",
                        json={
                            "conversation_id": "same-chat",
                            "message": "follow up",
                            "mode": "send",
                            "max_turns": 3,
                        },
                    )

        prompt = run_mock.await_args.args[0]
        self.assertIn("Prior turns JSON", prompt)
        self.assertIn("first question", prompt)
        self.assertIn("first answer", prompt)
        self.assertIn("Latest user request:\nfollow up", prompt)

    def test_context_prompt_treats_resend_as_send_action(self):
        prompt = _prompt_with_context(
            "没有重新发一下",
            [
                {
                    "role": "agent",
                    "content": "已经准备给 Yuan.M 发送 hello，需要我发送吗？",
                }
            ],
        )

        self.assertIn("重新发", prompt)
        self.assertIn("re-send", prompt)
        self.assertIn("even if a similar outgoing bubble is already visible", prompt)
        self.assertIn("retry the actual requested tool", prompt)
        self.assertIn("Latest user request:\n没有重新发一下", prompt)

    def test_chat_rejects_invalid_mode(self):
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"message": "hello", "mode": "chat", "max_turns": 3},
        )

        self.assertEqual(response.status_code, 422)

    def test_chat_accepts_forty_turns(self):
        result = SimpleNamespace(final_output="ok")
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=result)) as run_mock:
                    client = TestClient(app)
                    response = client.post(
                        "/api/chat",
                        json={"message": "read current chat", "mode": "send", "max_turns": 40},
                    )

        self.assertEqual(response.status_code, 200)
        run_mock.assert_awaited_once_with("read current chat", mode="send", max_turns=40)

    def test_chat_rejects_more_than_forty_turns(self):
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"message": "hello", "mode": "send", "max_turns": 41},
        )

        self.assertEqual(response.status_code, 422)

    def test_chat_times_out_long_agent_runs(self):
        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(1)

        with TemporaryDirectory() as tmp:
            with patch.dict(
                "os.environ",
                {"WECHAT_MCP_DATA_DIR": tmp, "WECHAT_WEB_AGENT_TIMEOUT_SECONDS": "0.01"},
                clear=False,
            ):
                with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(side_effect=slow_agent)):
                    client = TestClient(app)
                    response = client.post(
                        "/api/chat",
                        json={"message": "read current chat", "mode": "send", "max_turns": 3},
                    )

        self.assertEqual(response.status_code, 504)
        self.assertIn("timed out", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
