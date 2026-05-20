from __future__ import annotations

import unittest
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

    def test_chat_runs_agent(self):
        result = SimpleNamespace(final_output="ok from agent")
        with patch("wechat_mcp.web.run_wechat_agent", new=AsyncMock(return_value=result)) as run_mock:
            client = TestClient(app)
            response = client.post(
                "/api/chat",
                json={"message": "read current chat", "mode": "assist", "max_turns": 3},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"output": "ok from agent", "mode": "assist"})
        run_mock.assert_awaited_once_with("read current chat", mode="assist", max_turns=3)

    def test_chat_rejects_invalid_mode(self):
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"message": "hello", "mode": "danger", "max_turns": 3},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
