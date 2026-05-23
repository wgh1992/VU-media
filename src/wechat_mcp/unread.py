from __future__ import annotations

from typing import Any

from PIL import Image

from .store import ConversationStore
from .wechat import capture_wechat_window, click_wechat_normalized


def _locate_sidebar_red_dots(image_path: str) -> list[dict[str, Any]]:
    with Image.open(image_path).convert("RGB") as image:
        width, height = image.size
        pixels = image.load()
        points: list[tuple[int, int]] = []
        for y in range(int(height * 0.10), int(height * 0.95)):
            for x in range(int(width * 0.08), int(width * 0.36)):
                r, g, b = pixels[x, y]
                if r > 220 and 35 < g < 130 and 35 < b < 130:
                    points.append((x, y))

    clusters: list[list[tuple[int, int]]] = []
    for point in points:
        px, py = point
        for cluster in clusters:
            cx = sum(p[0] for p in cluster) / len(cluster)
            cy = sum(p[1] for p in cluster) / len(cluster)
            if abs(px - cx) <= 14 and abs(py - cy) <= 14:
                cluster.append(point)
                break
        else:
            clusters.append([point])

    results = []
    for cluster in clusters:
        if len(cluster) < 10:
            continue
        xs = [p[0] for p in cluster]
        ys = [p[1] for p in cluster]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        radius = max(max(xs) - min(xs), max(ys) - min(ys)) / 2
        if radius < 2 or radius > 18:
            continue
        results.append(
            {
                "x_ratio": cx / width,
                "y_ratio": cy / height,
                "x_px": cx,
                "y_px": cy,
                "pixel_count": len(cluster),
            }
        )

    results.sort(key=lambda item: (item["y_ratio"], item["x_ratio"]))
    return results


def focus_unread_by_red_dot(index: int = 1) -> dict[str, Any]:
    if index < 1:
        raise ValueError("index must be >= 1.")

    image_path = capture_wechat_window()
    dots = _locate_sidebar_red_dots(str(image_path))
    if index > len(dots):
        raise RuntimeError(f"Only found {len(dots)} visible unread red dots; requested index {index}.")

    dot = dots[index - 1]
    # Click the conversation row body, not the red dot itself.
    click_x_ratio = 0.18
    click_y_ratio = float(dot["y_ratio"])
    click_result = click_wechat_normalized(click_x_ratio, click_y_ratio)

    store = ConversationStore()
    stored_image = store.save_screenshot("__unread_red_dot__", image_path)
    event = store.append_event(
        "__unread_red_dot__",
        "focus_unread_by_red_dot",
        {
            "index": index,
            "red_dot_count": len(dots),
            "selected_dot": dot,
            "click_x_ratio": click_x_ratio,
            "click_y_ratio": click_y_ratio,
            "image_path": stored_image,
            "click_result": click_result,
        },
    )
    return {
        "index": index,
        "red_dot_count": len(dots),
        "selected_dot": dot,
        "click_result": click_result,
        "image_path": stored_image,
        "event": event,
    }
