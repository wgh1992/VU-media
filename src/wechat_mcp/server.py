from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import __version__
from .agent import daily_check_once as run_daily_check_once
from .clicking import click_wechat as run_click_wechat
from .clicking import click_wechat_by_template as run_click_wechat_by_template
from .clicking import click_wechat_by_vision as run_click_wechat_by_vision
from .history import read_current_chat_history as run_read_current_chat_history
from .prompts import PromptManager
from .safety import auto_send_message as safe_auto_send_message
from .safety import send_current_chat_message as safe_send_current_chat_message
from .safety import send_message_confirmed as safe_send_message
from .config import get_settings
from .store import ConversationStore, text_log_payload
from .unread import focus_unread_by_red_dot as run_focus_unread_by_red_dot
from .vision import analyze_screenshot as analyze_image
from .vision import draft_reply as draft_reply_text
from .vision import summarize_chat as summarize_chat_text
from .voice import convert_visible_voice_to_text as run_convert_visible_voice_to_text
from .visual_agent import safe_send_current_chat_with_vision as visual_safe_send_current
from .wechat import capture_wechat_window as capture_window
from .wechat import focus_chat as focus_wechat_chat
from .wechat import list_visible_windows as list_windows
from .wechat import write_reply as write_wechat_reply


mcp = FastMCP("wechat-mcp")


@mcp.tool()
def capture_wechat_window(output_path: str | None = None) -> dict:
    """Capture the visible WeChat desktop window to a PNG file."""
    path = capture_window(output_path)
    return {"image_path": str(path)}


@mcp.tool()
def health_check() -> dict:
    """Return local server configuration and dependency readiness without contacting OpenAI or WeChat."""
    settings = get_settings()
    prompt_names = ["analyze_screenshot", "read_current_chat", "draft_reply", "summarize_chat", "daily_check"]
    prompt_manager = PromptManager()
    return {
        "version": __version__,
        "model": settings.openai_model_fast,
        "agent_reasoning_effort": settings.agent_reasoning_effort,
        "agent_verbosity": settings.agent_verbosity,
        "agent_service_tier": settings.agent_service_tier,
        "openai_api_key_set": bool(settings.openai_api_key),
        "send_requires_confirm": settings.send_requires_confirm,
        "store_message_text": settings.store_message_text,
        "data_dir": settings.data_dir,
        "wechat_window_title_regex": settings.wechat_window_title_regex,
        "wechat_window_class_regex": settings.wechat_window_class_regex,
        "prompts": {
            name: bool(prompt_manager.get(name, ""))
            for name in prompt_names
        },
    }


@mcp.tool()
def list_visible_windows() -> list[dict]:
    """List visible Windows UI Automation top-level windows for debugging window matching."""
    return list_windows()


@mcp.tool()
def daily_check_once(note: str | None = None) -> dict:
    """Run one low-risk WeChat daily check and save a local report."""
    return run_daily_check_once(note)


@mcp.tool()
def analyze_screenshot(image_path: str, instruction: str | None = None) -> str:
    """Analyze a screenshot with the configured OpenAI nano model."""
    return analyze_image(image_path, instruction)


@mcp.tool()
def analyze_and_store_screenshot(
    image_path: str,
    contact_name: str | None = None,
    instruction: str | None = None,
) -> dict:
    """Analyze a screenshot and store the result in the local conversation log."""
    analysis = analyze_image(image_path, instruction)
    store = ConversationStore()
    stored_image = store.save_screenshot(contact_name, image_path)
    event = store.append_event(
        contact_name,
        "screenshot_analysis",
        {
            "image_path": stored_image,
            "analysis": analysis,
        },
    )
    return {"analysis": analysis, "event": event}


@mcp.tool()
def focus_chat(chat_name: str) -> str:
    """Use WeChat search to focus a chat by name."""
    return focus_wechat_chat(chat_name)


@mcp.tool()
def focus_unread_by_red_dot(index: int = 1) -> dict:
    """Visually locate unread red dots in the left WeChat conversation list and focus the requested unread conversation."""
    return run_focus_unread_by_red_dot(index)


@mcp.tool()
def read_current_chat(
    scroll_pages: int = 1,
    scroll_notches: int = 80,
    scroll_delay_seconds: float = 0.02,
    settle_to_bottom: bool = True,
    bottom_scroll_notches: int = 120,
    settle_delay_seconds: float = 0.15,
) -> dict:
    """Read the current WeChat chat. By default, first scroll to the newest message at the bottom, wait, then read. Use scroll_pages > 1 to scroll upward for history."""
    return run_read_current_chat_history(
        scroll_pages,
        scroll_notches,
        scroll_delay_seconds,
        settle_to_bottom,
        bottom_scroll_notches,
        settle_delay_seconds,
    )


def read_current_chat_history(
    scroll_pages: int = 3,
    scroll_notches: int = 80,
    scroll_delay_seconds: float = 0.02,
    settle_to_bottom: bool = True,
    bottom_scroll_notches: int = 120,
    settle_delay_seconds: float = 0.15,
) -> dict:
    """Deprecated internal alias. Use read_current_chat(scroll_pages, scroll_notches)."""
    return run_read_current_chat_history(
        scroll_pages,
        scroll_notches,
        scroll_delay_seconds,
        settle_to_bottom,
        bottom_scroll_notches,
        settle_delay_seconds,
    )


@mcp.tool()
def convert_visible_voice_to_text(index: int = 1) -> dict:
    """Click a visible WeChat voice message Convert to text / 转文字 button and visually read the converted text."""
    return run_convert_visible_voice_to_text(index)


@mcp.tool()
def click_wechat(x_ratio: float, y_ratio: float, reason: str | None = None) -> dict:
    """Click a normalized coordinate inside the WeChat window. Refuses titlebar/window chrome clicks."""
    return run_click_wechat(x_ratio, y_ratio, reason)


@mcp.tool()
def click_wechat_by_vision(instruction: str) -> dict:
    """Capture WeChat, visually locate the requested UI target, then click it if clearly visible."""
    return run_click_wechat_by_vision(instruction)


@mcp.tool()
def click_wechat_by_template(
    template_image_path: str,
    threshold: float = 0.20,
    search_left_ratio: float = 0.0,
    search_top_ratio: float = 0.0,
    search_right_ratio: float = 0.25,
    search_bottom_ratio: float = 1.0,
    downscale: float = 0.5,
    stride: int = 2,
) -> dict:
    """Find a small template screenshot inside the WeChat window and click the best match."""
    return run_click_wechat_by_template(
        template_image_path,
        threshold,
        search_left_ratio,
        search_top_ratio,
        search_right_ratio,
        search_bottom_ratio,
        downscale,
        stride,
    )


@mcp.tool()
def read_current_chat_and_store(contact_name: str | None = None) -> dict:
    """Capture the current WeChat chat, analyze it, and store the result locally."""
    path = capture_window()
    analysis = analyze_image(
        path,
        PromptManager().get(
            "read_current_chat",
            "Read the visible WeChat chat. Return JSON only with current_chat, visible_messages, unread_indicators, input_box_visible, uncertainty.",
        ),
    )
    store = ConversationStore()
    stored_image = store.save_screenshot(contact_name, path)
    event = store.append_event(
        contact_name,
        "chat_read",
        {
            "image_path": stored_image,
            "analysis": analysis,
        },
    )
    return {"analysis": analysis, "event": event}


@mcp.tool()
def draft_reply(chat_text: str, instruction: str | None = None) -> str:
    """Draft a WeChat reply from chat text."""
    return draft_reply_text(chat_text, instruction)


@mcp.tool()
def summarize_chat(
    chat_text: str,
    contact_name: str | None = None,
    instruction: str | None = None,
) -> dict:
    """Summarize chat text and append the summary to the local conversation log."""
    summary = summarize_chat_text(chat_text, instruction)
    event = ConversationStore().append_summary(
        contact_name,
        summary,
        {"chat_text_length": len(chat_text)},
    )
    return {"summary": summary, "event": event}


@mcp.tool()
def recent_conversation_events(contact_name: str | None = None, limit: int = 20) -> list[dict]:
    """Return recent locally stored events for a contact."""
    return ConversationStore().recent_events(contact_name, limit)


@mcp.tool()
def write_reply(text: str, contact_name: str | None = None) -> str:
    """Paste reply text into the active WeChat input box without sending."""
    result = write_wechat_reply(text)
    ConversationStore().append_event(
        contact_name,
        "reply_written",
        {
            **text_log_payload(text),
            "result": result,
        },
    )
    return result


@mcp.tool()
def send_message_confirmed(confirm: bool = False) -> str:
    """Send the current WeChat input only after explicit confirmation."""
    return safe_send_message(confirm)


@mcp.tool()
def auto_send_message(chat_name: str, text: str, confirm: bool = False) -> dict:
    """Focus a chat, paste text, and send it if confirmation policy allows it."""
    return safe_auto_send_message(chat_name, text, confirm)


@mcp.tool()
def send_current_chat_message(text: str, confirm: bool = False) -> dict:
    """Paste text into the currently open WeChat chat and send if confirmation policy allows it."""
    return safe_send_current_chat_message(text, confirm)


@mcp.tool()
def safe_send_current_chat_with_vision(text: str, confirm: bool = False) -> dict:
    """Send to the currently open WeChat chat with screenshot verification before and after each key step."""
    return visual_safe_send_current(text, confirm)


@mcp.resource("wechat-mcp://status")
def status() -> str:
    return f"wechat-mcp {__version__} ready"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
