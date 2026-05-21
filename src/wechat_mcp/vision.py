from __future__ import annotations

import base64
import json
from pathlib import Path

from openai import OpenAI

from .config import get_settings
from .prompts import PromptManager


DEFAULT_SCREENSHOT_INSTRUCTION = """
Analyze this WeChat desktop screenshot.
Return compact JSON only with these keys:
- app_visible: boolean
- current_chat: string|null
- visible_messages: array of strings
- input_box_visible: boolean
- suggested_next_action: string
- uncertainty: string|null
Do not invent message text. If text is unclear, say so in uncertainty.
""".strip()


def _image_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def analyze_screenshot(image_path: str | Path, instruction: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = instruction or PromptManager().get("analyze_screenshot", DEFAULT_SCREENSHOT_INSTRUCTION)

    response = client.responses.create(
        model=settings.openai_model_fast,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": _image_data_url(image_path),
                        "detail": "low",
                    },
                ],
            }
        ],
    )
    return response.output_text


def draft_reply(chat_text: str, instruction: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=settings.openai_api_key)
    user_instruction = instruction or PromptManager().get(
        "draft_reply",
        "Draft a concise, natural Chinese reply. Do not overpromise.",
    )
    response = client.responses.create(
        model=settings.openai_model_fast,
        input=[
            {
                "role": "system",
                "content": "You draft WeChat replies. Output JSON only.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": user_instruction,
                        "chat_text": chat_text,
                        "schema": {
                            "reply": "string",
                            "needs_human_review": "boolean",
                            "risk_reason": "string|null",
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.output_text


def summarize_chat(chat_text: str, instruction: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = instruction or PromptManager().get(
        "summarize_chat",
        "Summarize the WeChat conversation for future context.",
    )
    response = client.responses.create(
        model=settings.openai_model_fast,
        input=[
            {
                "role": "system",
                "content": "You summarize chat context for a local WeChat agent.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": prompt,
                        "chat_text": chat_text,
                        "schema": {
                            "summary": "string",
                            "open_tasks": "array of strings",
                            "needs_human_review": "boolean",
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.output_text
