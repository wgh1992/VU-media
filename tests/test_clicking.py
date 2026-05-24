from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from wechat_mcp.clicking import click_wechat_by_vision


class ClickingTests(unittest.TestCase):
    def test_click_by_vision_captures_locates_and_clicks(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.clicking.capture_wechat_window", return_value=source):
                    with patch(
                        "wechat_mcp.clicking.analyze_screenshot",
                        return_value='{"ok": true, "target": "button", "x_ratio": 0.5, "y_ratio": 0.6, "confidence": "high", "reason": null}',
                    ):
                        with patch("wechat_mcp.clicking.click_wechat_normalized", return_value="clicked") as click_mock:
                            result = click_wechat_by_vision("click the button")

        self.assertTrue(result["clicked"])
        self.assertEqual(result["locator"]["target"], "button")
        self.assertIn("image_path", result)
        click_mock.assert_called_once_with(0.5, 0.6)

    def test_click_by_vision_does_not_click_unclear_target(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.clicking.capture_wechat_window", return_value=source):
                    with patch(
                        "wechat_mcp.clicking.analyze_screenshot",
                        return_value='{"ok": false, "target": null, "x_ratio": null, "y_ratio": null, "confidence": "low", "reason": "not visible"}',
                    ):
                        with patch("wechat_mcp.clicking.click_wechat_normalized") as click_mock:
                            result = click_wechat_by_vision("click missing thing")

        self.assertFalse(result["clicked"])
        click_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
