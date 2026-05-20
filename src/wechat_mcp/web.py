from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .agent_sdk import run_wechat_agent
from .config import get_settings


Mode = Literal["daily", "assist", "send"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: Mode = "assist"
    max_turns: int = Field(default=6, ge=1, le=12)


class ChatResponse(BaseModel):
    output: str
    mode: Mode


app = FastAPI(title="WeChat MCP Web Chat")


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
        "modes": ["daily", "assist", "send"],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    prompt = request.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        result = await run_wechat_agent(prompt, mode=request.mode, max_turns=request.max_turns)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(output=str(result.final_output), mode=request.mode)


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
    .msg.assistant { align-self: flex-start; }
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
      </div>
      <div class="toolbar">
        <label>
          Mode
          <select id="mode">
            <option value="assist" selected>assist</option>
            <option value="daily">daily</option>
            <option value="send">send</option>
          </select>
        </label>
        <label>
          Turns
          <input id="turns" type="number" min="1" max="12" value="6" />
        </label>
      </div>
    </header>
    <main>
      <div class="messages" id="messages">
        <div class="msg assistant">
          <div class="meta">assistant</div>
          可以直接问我读取当前微信、聚焦某个联系人、做 daily check，或者在 send mode 下明确要求发送。Agent SDK trace 会出现在 OpenAI Dashboard。
        </div>
      </div>
    </main>
    <footer>
      <form class="composer" id="form">
        <textarea id="message" placeholder="例如：Focus yuanmiao, read visible messages, summarize in Chinese. Do not send anything."></textarea>
        <button id="send" type="submit">Send</button>
      </form>
      <div class="hint" id="hint">assist mode 不会发送消息；send mode 会暴露发送工具，仍建议在 prompt 中写清 confirm=true。</div>
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
        hint.innerHTML = '<span class="send-warning">send mode 已开启：</span>会暴露发送工具。发送前请在指令里明确目标、正文和 confirm=true。';
      } else if (mode.value === 'daily') {
        hint.textContent = 'daily mode 只做低风险检查，不会读取单个聊天详情或发送消息。';
      } else {
        hint.textContent = 'assist mode 可读取、总结、写草稿，但不会发送消息。';
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
            max_turns: Number(turns.value || 6)
          })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        addMessage('assistant', data.output);
      } catch (err) {
        addMessage('assistant', String(err.message || err), 'error');
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
    refreshHint();
    loadHealth();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
