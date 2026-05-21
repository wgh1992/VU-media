# WeChat MCP

Minimal Windows MCP server for WeChat desktop automation.

This project intentionally controls the official Windows desktop client through window focus, screenshots, clipboard paste, and optional UI automation. It does not use private WeChat protocols, local database reads, DLL injection, or client reverse engineering.

## What It Can Do

- Capture the WeChat window or a screen region.
- Send a screenshot to `gpt-5.4-nano` for lightweight UI analysis.
- Find and focus a chat by using WeChat search.
- Read the current chat visually from a screenshot.
- Store local conversation events and summaries as JSONL.
- Draft a reply with OpenAI.
- Write a reply into the input box.
- Send only when explicitly confirmed.

## Setup

```powershell
cd E:\vu\media\wechat-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`.

## Run

For normal MCP clients, run the stdio server:

```powershell
wechat-mcp
```

Or:

```powershell
python -m wechat_mcp.server
```

If your MCP client supports JSON config, adapt `mcp-config.example.json`.

Do not type into this process manually. It expects JSON-RPC messages from an MCP client, so pressing Enter in a terminal can produce an "Invalid JSON" error.

For local PowerShell testing without an MCP client, use:

```powershell
python -m wechat_mcp.dev_cli health
python -m wechat_mcp.dev_cli list-windows
python -m wechat_mcp.dev_cli daily-check
python -m wechat_mcp.dev_cli agent-tools --mode daily
python -m wechat_mcp.dev_cli agent-run "Please run one WeChat daily check." --mode daily
python -m wechat_mcp.dev_cli capture
python -m wechat_mcp.dev_cli safe-send-current "test message" --confirm
python -m wechat_mcp.dev_cli focus "联系人名字"
python -m wechat_mcp.dev_cli read-store --contact "联系人名字"
python -m wechat_mcp.dev_cli draft "对方说：下午三点见。请自然回复。"
python -m wechat_mcp.dev_cli write "好的，我下午三点到。" --contact "联系人名字"
```

After reinstalling with `pip install -e .`, you can also use `wechat-mcp-dev health`.

## Local Web Chat

Run a browser-based chat UI for the Agent SDK workflow:

```powershell
cd E:\vu\media\wechat-mcp
python -m wechat_mcp.web --host 127.0.0.1 --port 8787
```

Then open:

```text
http://127.0.0.1:8787
```

The web UI has two modes:

- `daily`: low-risk daily checks only.
- `send`: exposes send tools, including `safe_send_current_chat_with_vision`.

Example prompt for reading a contact:

```text
Focus the WeChat chat named yuanmiao, read the currently visible messages, and summarize them in Chinese. Do not send anything.
```

Example prompt for visual verified sending when the target chat is already open:

```text
Use safe_send_current_chat_with_vision to send exactly this text to the currently open WeChat chat: hello from web. Pass confirm=true.
```

Requests from the web UI go through `Agent SDK + MCP`, so workflow traces appear in the OpenAI Dashboard Agent Traces page. Visual step screenshots are still saved locally under `.data/runs/<run_id>/`.

The web UI keeps a `conversation_id` in browser local storage and stores recent web turns under `.data/web_conversations/`. Click `New Chat` to start a fresh conversation id.

## MCP Tools

- `capture_wechat_window(output_path: str | None = None)`
- `health_check()`
- `daily_check_once(note: str | None = None)`
- `analyze_screenshot(image_path: str, instruction: str | None = None)`
- `focus_chat(chat_name: str)`
- `read_current_chat()`
- `read_current_chat_and_store(contact_name: str | None = None)`
- `draft_reply(chat_text: str, instruction: str | None = None)`
- `summarize_chat(chat_text: str, contact_name: str | None = None, instruction: str | None = None)`
- `recent_conversation_events(contact_name: str | None = None, limit: int = 20)`
- `write_reply(text: str, contact_name: str | None = None)`
- `send_message_confirmed(confirm: bool = false)`
- `auto_send_message(chat_name: str, text: str, confirm: bool = false)`
- `send_current_chat_message(text: str, confirm: bool = false)`
- `safe_send_current_chat_with_vision(text: str, confirm: bool = false)`

## Safety Defaults

`send_message_confirmed` refuses to press Enter unless `confirm=true`. Keep `WECHAT_SEND_REQUIRES_CONFIRM=true` for normal use.

The recommended flow is:

1. `focus_chat`
2. `read_current_chat`
3. `draft_reply`
4. `write_reply`
5. Human checks the WeChat input box
6. `send_message_confirmed(confirm=true)`

By default, locally stored reply events keep only message length and a short preview. Set `WECHAT_MCP_STORE_MESSAGE_TEXT=true` only if you explicitly want full local text logs.

## Daily Check Agent

Run one check manually:

```powershell
cd E:\vu\media\wechat-mcp
python -m wechat_mcp.dev_cli daily-check
```

This captures the visible WeChat window, asks the configured nano model to inspect visible unread/new-message indicators, and writes a report under `.data/reports/`.

To schedule it once per day with Windows Task Scheduler, run PowerShell as your normal desktop user and create a task like:

```powershell
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File E:\vu\media\wechat-mcp\scripts\run_daily_check.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

Register-ScheduledTask `
  -TaskName "WeChat MCP Daily Check" `
  -Action $action `
  -Trigger $trigger `
  -Description "Runs one local WeChat MCP unread-message check."
```

Keep WeChat logged in before the scheduled time. The first version only inspects the visible conversation list; it does not scroll every chat or open conversations, because opening a chat can mark messages as read.

## Agent SDK + MCP

This project also includes an Agent SDK wrapper inspired by the NestWeb MCP layout:

- `mcp_adapter.py`: starts this MCP server as a stdio subprocess for the Agent SDK.
- `tool_tiers.py`: controls which MCP tools are visible in `daily` and `send` modes.
- `agent_sdk.py`: builds and runs the Agent SDK agent.
- `output_schemas.py`: shared schema definitions for future structured tool outputs.

List the tools visible to the daily-check agent:

```powershell
python -m wechat_mcp.dev_cli agent-tools --mode daily
```

Run the daily-check agent:

```powershell
python -m wechat_mcp.dev_cli agent-run "Please run one WeChat daily check." --mode daily
```

For safety, daily mode only exposes low-risk tools and cannot write or send WeChat messages.

## Sending Messages

Manual send with confirmation:

```powershell
python -m wechat_mcp.dev_cli send "File Transfer" "test message" --confirm
```

If the target chat is already open, prefer the current-chat path because it does not touch WeChat search:

```powershell
python -m wechat_mcp.dev_cli send-current "test message" --confirm
```

For the most reliable desktop-agent path, use visual verification:

```powershell
python -m wechat_mcp.dev_cli safe-send-current "test message" --confirm
```

This captures screenshots before writing, after writing, and after sending. The trace is saved under `.data/runs/<run_id>/`.

Unattended sending requires this in `.env`:

```env
WECHAT_SEND_REQUIRES_CONFIRM=false
```

Then send mode can use `auto_send_message`:

```powershell
python -m wechat_mcp.dev_cli agent-run "Send File Transfer this message: test message" --mode send
```

Only send mode exposes automatic send tools.

## Notes

Vision on screenshots is useful, but Chinese UI text and dense chat bubbles can be inconsistent. For production use, add a local OCR layer and pass OCR text plus cropped screenshots to the model.

Prompt files live in `prompts/`. Tune those before changing Python code when you only want different model behavior.

If your MCP client starts the server from another directory, set `WECHAT_MCP_PROMPTS_DIR` to the absolute `prompts` path.
