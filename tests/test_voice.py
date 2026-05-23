from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from wechat_mcp.voice import convert_visible_voice_to_text
from wechat_mcp.voice import _locate_voice_convert_by_red_dot


class VoiceTests(unittest.TestCase):
    def test_convert_visible_voice_to_text_clicks_and_reads_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"fake-png")
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.voice.click_visible_voice_to_text", return_value="clicked") as click_mock:
                    with patch("wechat_mcp.voice.capture_wechat_window", return_value=source) as capture_mock:
                        with patch("wechat_mcp.voice.analyze_screenshot", return_value='{"converted_voice_text": "hello"}') as analyze_mock:
                            result = convert_visible_voice_to_text(index=2)

        self.assertEqual(result["index"], 2)
        self.assertEqual(result["click_result"], "clicked")
        self.assertIn("converted_voice_text", result["analysis"])
        click_mock.assert_called_once_with(2)
        capture_mock.assert_called_once_with()
        analyze_mock.assert_called_once()

    def test_convert_visible_voice_to_text_falls_back_to_visual_locator(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (100, 100), "white").save(source)
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.voice.click_visible_voice_to_text", side_effect=RuntimeError("not exposed")):
                    with patch("wechat_mcp.voice.capture_wechat_window", return_value=source):
                        with patch(
                            "wechat_mcp.voice.analyze_screenshot",
                            side_effect=[
                                '{"found": true, "x_ratio": 0.72, "y_ratio": 0.38}',
                                '{"converted_voice_text": "hello"}',
                            ],
                        ):
                            with patch("wechat_mcp.voice.click_wechat_normalized", return_value="clicked visually") as click_mock:
                                result = convert_visible_voice_to_text(index=1)

        self.assertIn("visual coordinate fallback", result["click_result"])
        click_mock.assert_called_once_with(0.72, 0.38)

    def test_locate_voice_convert_by_red_dot(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            image = Image.new("RGB", (300, 200), "white")
            for x in range(120, 128):
                for y in range(80, 88):
                    image.putpixel((x, y), (255, 70, 70))
            image.save(source)

            result = _locate_voice_convert_by_red_dot(str(source), 1)

        self.assertIsNotNone(result)
        assert result is not None
        x_ratio, y_ratio = result
        self.assertAlmostEqual(x_ratio, 224 / 300, delta=0.02)
        self.assertAlmostEqual(y_ratio, 84 / 200, delta=0.02)


if __name__ == "__main__":
    unittest.main()
