from __future__ import annotations

from pathlib import Path
from time import time
from typing import TypedDict

import mss
from PIL import Image


class Region(TypedDict):
    left: int
    top: int
    width: int
    height: int


def default_capture_path(prefix: str = "wechat") -> Path:
    captures_dir = Path.cwd() / ".captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    return captures_dir / f"{prefix}-{int(time() * 1000)}.png"


def capture_region(region: Region, output_path: str | Path | None = None) -> Path:
    path = Path(output_path) if output_path else default_capture_path("region")
    path.parent.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        raw = sct.grab(region)
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        image.save(path)

    return path.resolve()


def capture_primary_monitor(output_path: str | Path | None = None) -> Path:
    path = Path(output_path) if output_path else default_capture_path("screen")
    path.parent.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        image.save(path)

    return path.resolve()
