from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from wechat_mcp.clicking import click_wechat_by_template, click_wechat_by_vision, locate_template_in_wechat


class ClickingTests(unittest.TestCase):
    def test_locate_template_in_wechat_finds_matching_icon(self):
        with TemporaryDirectory() as tmp:
            screenshot = Path(tmp) / "wechat.png"
            template = Path(tmp) / "template.png"
            image = Image.new("L", (80, 60), 255)
            icon = Image.new("L", (8, 8), 30)
            image.paste(icon, (16, 20))
            image.save(screenshot)
            icon.save(template)

            with patch("wechat_mcp.clicking.capture_wechat_window", return_value=screenshot):
                result = locate_template_in_wechat(
                    str(template),
                    threshold=0.90,
                    search_right_ratio=1.0,
                    downscale=1.0,
                    stride=1,
                )

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["score"], 0.90)
        self.assertAlmostEqual(result["x_ratio"], 20 / 80, places=2)
        self.assertAlmostEqual(result["y_ratio"], 24 / 60, places=2)

    def test_click_by_template_clicks_best_match(self):
        with TemporaryDirectory() as tmp:
            screenshot = Path(tmp) / "wechat.png"
            template = Path(tmp) / "template.png"
            image = Image.new("L", (80, 60), 255)
            icon = Image.new("L", (8, 8), 30)
            image.paste(icon, (16, 20))
            image.save(screenshot)
            icon.save(template)

            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}, clear=False):
                with patch("wechat_mcp.clicking.capture_wechat_window", return_value=screenshot):
                    with patch("wechat_mcp.clicking.click_wechat_normalized", return_value="clicked") as click_mock:
                        result = click_wechat_by_template(
                            str(template),
                            threshold=0.90,
                            search_right_ratio=1.0,
                            downscale=1.0,
                            stride=1,
                        )

        self.assertTrue(result["clicked"])
        click_mock.assert_called_once()

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
