from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model_fast: str
    agent_reasoning_effort: str
    agent_verbosity: str
    agent_service_tier: str
    send_requires_confirm: bool
    wechat_window_title_regex: str
    wechat_window_class_regex: str | None
    data_dir: str
    store_message_text: bool
    prompts_dir: str | None
    web_agent_timeout_seconds: float


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized if normalized in allowed else default


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model_fast=os.getenv("OPENAI_MODEL_FAST", "gpt-5.4-nano"),
        agent_reasoning_effort=_env_choice(
            "AGENT_REASONING_EFFORT",
            "high",
            {"none", "minimal", "low", "medium", "high", "xhigh"},
        ),
        agent_verbosity=_env_choice("AGENT_VERBOSITY", "low", {"low", "medium", "high"}),
        agent_service_tier=os.getenv("AGENT_SERVICE_TIER", "default").strip() or "default",
        send_requires_confirm=_env_bool("WECHAT_SEND_REQUIRES_CONFIRM", True),
        wechat_window_title_regex=os.getenv(
            "WECHAT_WINDOW_TITLE_REGEX",
            r".*微信.*|.*WeChat.*|.*Weixin.*",
        ),
        wechat_window_class_regex=os.getenv("WECHAT_WINDOW_CLASS_REGEX", r"Qt.*|WeChat.*"),
        data_dir=os.getenv("WECHAT_MCP_DATA_DIR", ".data"),
        store_message_text=_env_bool("WECHAT_MCP_STORE_MESSAGE_TEXT", False),
        prompts_dir=os.getenv("WECHAT_MCP_PROMPTS_DIR"),
        web_agent_timeout_seconds=float(os.getenv("WECHAT_WEB_AGENT_TIMEOUT_SECONDS", "240")),
    )
