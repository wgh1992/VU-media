from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from wechat_mcp.unread import _locate_sidebar_red_dots, focus_unread_by_red_dot


class UnreadTests(unittest.TestCase):
    def test_locate_sidebar_red_dots_ignores_far_left_nav_dot(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            image = Image.new("RGB", (1000, 800), "white")
            for x in range(45, 56):
                for y in range(145, 156):
                    image.putpixel((x, y), (255, 70, 70))
            for x in range(170, 182):
                for y in range(250, 262):
                    image.putpixel((x, y), (255, 70, 70))
            image.save(source)

            dots = _locate_sidebar_red_dots(str(source))

        self.assertEqual(len(dots), 1)
        self.assertAlmostEqual(dots[0]["x_ratio"], 0.175, delta=0.02)
        self.assertAlmostEqual(dots[0]["y_ratio"], 0.319, delta=0.02)

    def test_focus_unread_clicks_row_body_by_red_dot_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            image = Image.new("RGB", (1000, 800), "white")
            for x in range(170, 182):
                for y in range(250, 262):
                    image.putpixel((x, y), (255, 70, 70))
            image.save(source)
            with patch.dict("os.environ", {"WECHAT_MCP_DATA_DIR": tmp}):
                with patch("wechat_mcp.unread.capture_wechat_window", return_value=source):
                    with patch("wechat_mcp.unread.click_wechat_normalized", return_value="clicked") as click_mock:
                        result = focus_unread_by_red_dot(1)

        self.assertEqual(result["red_dot_count"], 1)
        click_mock.assert_called_once()
        x_ratio, y_ratio = click_mock.call_args.args
        self.assertEqual(x_ratio, 0.18)
        self.assertAlmostEqual(y_ratio, 0.319, delta=0.02)


if __name__ == "__main__":
    unittest.main()
