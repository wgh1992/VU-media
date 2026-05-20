from __future__ import annotations

from pathlib import Path

from .config import get_settings


class PromptManager:
    def __init__(self, prompts_dir: str | Path | None = None):
        settings = get_settings()
        source_root = Path(__file__).resolve().parents[2]
        candidates = [
            Path(prompts_dir) if prompts_dir else None,
            Path(settings.prompts_dir) if settings.prompts_dir else None,
            Path.cwd() / "prompts",
            source_root / "prompts",
        ]
        self.prompts_dir = next(
            (path for path in candidates if path and path.exists()),
            candidates[-1],
        )

    def get(self, name: str, fallback: str) -> str:
        path = self.prompts_dir / f"{name}.txt"
        if not path.exists():
            return fallback.strip()
        return path.read_text(encoding="utf-8").strip()
