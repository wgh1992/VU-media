from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from wechat_mcp.web import app


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
        run_mock.assert_awaited_once_with("read current chat", mode="send", max_turns=3)

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

    def test_chat_rejects_invalid_mode(self):
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"message": "hello", "mode": "assist", "max_turns": 3},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
