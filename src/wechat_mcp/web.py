from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .agent_sdk import run_wechat_agent
from .config import get_settings
from .store import utc_now_iso


Mode = Literal["daily", "send"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: Mode = "send"
    max_turns: int = Field(default=6, ge=1, le=12)
    conversation_id: str | None = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    output: str
    mode: Mode
    conversation_id: str


app = FastAPI(title="WeChat MCP Web Chat")


class WebConversationStore:
    def __init__(self, data_dir: str | Path | None = None):
        settings = get_settings()
        self.root = Path(data_dir or settings.data_dir).resolve() / "web_conversations"
        self.root.mkdir(parents=True, exist_ok=True)

    def normalize_id(self, conversation_id: str | None) -> str:
        value = (conversation_id or "").strip()
        if not value:
            return f"web-{uuid4().hex[:16]}"
        safe = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"})
        return safe[:80] or f"web-{uuid4().hex[:16]}"

    def path_for(self, conversation_id: str) -> Path:
        return self.root / f"{conversation_id}.jsonl"

    def append(self, conversation_id: str, role: str, content: str, mode: Mode | None = None) -> dict[str, Any]:
        event = {
            "timestamp": utc_now_iso(),
            "conversation_id": conversation_id,
            "role": role,
            "mode": mode,
            "content": content,
        }
        with self.path_for(conversation_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def recent(self, conversation_id: str, limit: int = 16) -> list[dict[str, Any]]:
        path = self.path_for(conversation_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events


def _prompt_with_context(message: str, history: list[dict[str, Any]]) -> str:
    if not history:
        return message

    compact_history = [
        {
            "role": event.get("role"),
            "content": str(event.get("content", ""))[:1200],
        }
        for event in history
        if event.get("role") in {"user", "agent"}
    ]
    return (
        "Continue this web chat conversation. Use the prior turns as context, but follow the latest user request.\n"
        "Resolve short replies such as yes, ok, 好的, 可以, 是的, 发, 发送, 可以发, 重新发, 再发, 重发, or 确认 against the immediately preceding agent question or proposed action.\n"
        "If the latest user reply confirms a proposed WeChat send action, send it immediately instead of asking the user to repeat the target or message.\n"
        "If the latest user reply asks to resend/re-send/send again, re-send the prior proposed message even if a similar outgoing bubble is already visible.\n"
        "If a prior turn said WeChat was unavailable, retry the actual requested tool when the latest user asks to try again; do not repeat the old failure from memory.\n"
        "If the confirmed action requires a tool that is unavailable in the current mode, say exactly which mode is needed and what the user should do next.\n\n"
        f"Prior turns JSON:\n{json.dumps(compact_history, ensure_ascii=False)}\n\n"
        f"Latest user request:\n{message}"
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    safe_settings = asdict(settings)
    safe_settings["openai_api_key"] = bool(settings.openai_api_key)
    return {
        "ok": True,
        "settings": safe_settings,
        "modes": ["daily", "send"],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    prompt = request.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message is required")

    store = WebConversationStore()
    conversation_id = store.normalize_id(request.conversation_id)
    history = store.recent(conversation_id)
    agent_prompt = _prompt_with_context(prompt, history)
    store.append(conversation_id, "user", prompt, request.mode)

    try:
        result = await run_wechat_agent(agent_prompt, mode=request.mode, max_turns=request.max_turns)
    except Exception as exc:
        store.append(conversation_id, "agent", f"ERROR: {exc}", request.mode)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output = str(result.final_output)
    store.append(conversation_id, "agent", output, request.mode)
    return ChatResponse(output=output, mode=request.mode, conversation_id=conversation_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local WeChat MCP Web Chat.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("wechat_mcp.web:app", host=args.host, port=args.port, reload=args.reload)


HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WeChat MCP Chat</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #15171a;
      --muted: #6b7280;
      --line: #dfe3e8;
      --green: #11b66d;
      --green-dark: #098a50;
      --blue: #2563eb;
      --danger: #c2410c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 {
      margin: 0;
      font-size: 17px;
      font-weight: 700;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    select, input, textarea, button { font: inherit; }
    select, input {
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: white;
      padding: 0 10px;
      color: var(--ink);
    }
    .status {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .secondary {
      background: #eef2ff;
      color: #1f2937;
      border: 1px solid #c7d2fe;
    }
    .secondary:hover { background: #dbeafe; }
    .conversation {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
      overflow-wrap: anywhere;
    }
    main {
      width: min(1040px, 100%);
      margin: 0 auto;
      padding: 18px;
      overflow: auto;
    }
    .messages {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding-bottom: 12px;
    }
    .msg {
      max-width: 820px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--panel);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .msg.user {
      align-self: flex-end;
      background: #e9f7ef;
      border-color: #b9e7cd;
    }
    .msg.agent { align-self: flex-start; }
    .msg.error {
      border-color: #fed7aa;
      background: #fff7ed;
      color: var(--danger);
    }
    .meta {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 5px;
    }
    footer {
      background: var(--panel);
      border-top: 1px solid var(--line);
      padding: 12px 18px 16px;
    }
    .composer {
      width: min(1040px, 100%);
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: end;
    }
    textarea {
      width: 100%;
      min-height: 72px;
      max-height: 180px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      outline: none;
    }
    textarea:focus {
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, .12);
    }
    button {
      height: 42px;
      border: 0;
      border-radius: 8px;
      padding: 0 16px;
      background: var(--green);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { background: var(--green-dark); }
    button:disabled {
      cursor: not-allowed;
      opacity: .55;
    }
    .hint {
      width: min(1040px, 100%);
      margin: 8px auto 0;
      color: var(--muted);
      font-size: 12px;
    }
    .send-warning {
      color: var(--danger);
      font-weight: 600;
    }
    @media (max-width: 720px) {
      header { align-items: flex-start; flex-direction: column; }
      .toolbar { justify-content: flex-start; }
      .composer { grid-template-columns: 1fr; }
      button { width: 100%; }
      main, footer { padding-left: 12px; padding-right: 12px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div>
        <h1>WeChat MCP Chat</h1>
        <div class="status" id="status">Checking local server...</div>
        <div class="conversation" id="conversation">Conversation: new</div>
      </div>
      <div class="toolbar">
        <label>
          Mode
          <select id="mode">
            <option value="daily">daily</option>
            <option value="send" selected>send</option>
          </select>
        </label>
        <label>
          Turns
          <input id="turns" type="number" min="1" max="12" value="6" />
        </label>
        <button class="secondary" id="new-chat" type="button">New Chat</button>
      </div>
    </header>
    <main>
      <div class="messages" id="messages">
        <div class="msg agent">
          <div class="meta">agent</div>
          可以直接问我读取当前微信、聚焦某个联系人、做 daily check，或者在 send mode 下明确要求发送。Agent SDK trace 会出现在 OpenAI Dashboard。
        </div>
      </div>
    </main>
    <footer>
      <form class="composer" id="form">
        <textarea id="message" placeholder="例如：Focus yuanmiao, read visible messages, summarize in Chinese. Do not send anything."></textarea>
        <button id="send" type="submit">Send</button>
      </form>
      <div class="hint" id="hint">send mode 可以直接发送明确的消息请求。</div>
    </footer>
  </div>
  <script>
    const messages = document.getElementById('messages');
    const form = document.getElementById('form');
    const input = document.getElementById('message');
    const button = document.getElementById('send');
    const mode = document.getElementById('mode');
    const turns = document.getElementById('turns');
    const statusEl = document.getElementById('status');
    const hint = document.getElementById('hint');
    const conversationEl = document.getElementById('conversation');
    const newChat = document.getElementById('new-chat');
    let conversationId = localStorage.getItem('wechat_mcp_conversation_id') || '';

    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      }[ch]));
    }

    function addMessage(role, text, kind = '') {
      const el = document.createElement('div');
      el.className = `msg ${role} ${kind}`;
      el.innerHTML = `<div class="meta">${escapeHtml(role)}</div>${escapeHtml(text)}`;
      messages.appendChild(el);
      el.scrollIntoView({ block: 'end', behavior: 'smooth' });
    }

    function refreshHint() {
      if (mode.value === 'send') {
        hint.innerHTML = '<span class="send-warning">send mode 已开启：</span>明确目标和正文后会直接发送，不再二次确认。';
      } else if (mode.value === 'daily') {
        hint.textContent = 'daily mode 只做低风险检查，不会读取单个聊天详情或发送消息。';
      } else {
        hint.textContent = 'send mode 可以直接发送明确的消息请求。';
      }
    }

    function setConversationId(value) {
      conversationId = value || '';
      if (conversationId) {
        localStorage.setItem('wechat_mcp_conversation_id', conversationId);
        conversationEl.textContent = `Conversation: ${conversationId}`;
      } else {
        localStorage.removeItem('wechat_mcp_conversation_id');
        conversationEl.textContent = 'Conversation: new';
      }
    }

    async function loadHealth() {
      try {
        const res = await fetch('/api/health');
        const data = await res.json();
        const model = data.settings.openai_model_fast;
        const key = data.settings.openai_api_key ? 'API key ready' : 'OPENAI_API_KEY missing';
        statusEl.textContent = `${model} · ${key}`;
      } catch (err) {
        statusEl.textContent = 'Local web server health check failed';
      }
    }

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      addMessage('user', text);
      input.value = '';
      button.disabled = true;
      button.textContent = 'Running...';

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            mode: mode.value,
            max_turns: Number(turns.value || 6),
            conversation_id: conversationId || null
          })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        setConversationId(data.conversation_id);
        addMessage('agent', data.output);
      } catch (err) {
        addMessage('agent', String(err.message || err), 'error');
      } finally {
        button.disabled = false;
        button.textContent = 'Send';
        input.focus();
      }
    });

    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        form.requestSubmit();
      }
    });

    mode.addEventListener('change', refreshHint);
    newChat.addEventListener('click', () => {
      setConversationId('');
      messages.innerHTML = '';
      addMessage('agent', '已开启新对话。下一条消息会创建新的 conversation id。');
      input.focus();
    });
    refreshHint();
    setConversationId(conversationId);
    loadHealth();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
