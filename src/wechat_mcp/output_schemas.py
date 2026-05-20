from __future__ import annotations

from typing import Any


def base_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["Success", "Fail"]},
            "message": {"type": "string"},
            **properties,
        },
        "required": ["status", "message"],
    }


HEALTH_CHECK_OUTPUT_SCHEMA = base_schema(
    {
        "version": {"type": "string"},
        "model": {"type": "string"},
        "openai_api_key_set": {"type": "boolean"},
        "send_requires_confirm": {"type": "boolean"},
    }
)

DAILY_CHECK_OUTPUT_SCHEMA = base_schema(
    {
        "analysis": {"type": "string"},
        "report_path": {"type": "string"},
        "image_path": {"type": "string"},
    }
)

RECENT_EVENTS_OUTPUT_SCHEMA = base_schema(
    {
        "events": {"type": "array", "items": {"type": "object"}},
    }
)


__all__ = [
    "HEALTH_CHECK_OUTPUT_SCHEMA",
    "DAILY_CHECK_OUTPUT_SCHEMA",
    "RECENT_EVENTS_OUTPUT_SCHEMA",
]
