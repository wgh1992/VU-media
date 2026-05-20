from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model_fast: str
    send_requires_confirm: bool
    wechat_window_title_regex: str
    wechat_window_class_regex: str | None
    data_dir: str
    store_message_text: bool
    prompts_dir: str | None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model_fast=os.getenv("OPENAI_MODEL_FAST", "gpt-5.4-nano"),
        send_requires_confirm=_env_bool("WECHAT_SEND_REQUIRES_CONFIRM", True),
        wechat_window_title_regex=os.getenv(
            "WECHAT_WINDOW_TITLE_REGEX",
            r".*微信.*|.*WeChat.*|.*Weixin.*",
        ),
        wechat_window_class_regex=os.getenv("WECHAT_WINDOW_CLASS_REGEX", r"Qt.*|WeChat.*"),
        data_dir=os.getenv("WECHAT_MCP_DATA_DIR", ".data"),
        store_message_text=_env_bool("WECHAT_MCP_STORE_MESSAGE_TEXT", False),
        prompts_dir=os.getenv("WECHAT_MCP_PROMPTS_DIR"),
    )
