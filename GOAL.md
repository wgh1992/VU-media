# Project Goal

Build a practical Windows WeChat desktop agent that can inspect, triage, and act on visible WeChat conversations through the official desktop client.

The project should behave like a careful computer-use agent: it observes the screen, chooses a bounded action, verifies the visual result, and logs what happened.

## Boundaries

- Use the official Windows WeChat desktop UI only.
- Do not use private WeChat protocols, local database scraping, DLL injection, reverse engineering, or credential extraction.
- Do not send messages unless the user gives a clear recipient/current chat and exact message text.
- Prefer screenshot/vision verification before and after risky UI actions.
- Keep all local logs privacy-conscious by default. Store full message text only when explicitly enabled.

## Primary Outcomes

1. Daily unread triage
   - Detect visible unread red dots in the conversation list.
   - Open unread conversations safely.
   - Read the current visible messages.
   - Summarize what needs attention.

2. Reliable chat reading
   - Read the active chat pane without mixing in the left conversation list.
   - Support fast upward history reading.
   - Avoid opening images, files, or internal WeChat helper windows accidentally.
   - Recover gracefully when WeChat is blank, loading, minimized, or not visible.

3. Safe message sending
   - Send only on explicit user request.
   - Verify the target chat and message draft visually before sending when possible.
   - Avoid duplicate-send confusion by reporting what was observed.

4. Voice-message handling
   - Detect visible voice-message conversion controls.
   - Click "Convert to text" / Chinese equivalents.
   - Read and store the converted text.

5. Agent SDK + MCP integration
   - Keep tools small, explicit, and testable.
   - Expose only low-risk tools in daily mode.
   - Expose send tools only in send mode.
   - Keep Agent traces useful for debugging.

6. Web UI
   - Provide a usable local chat interface.
   - Preserve conversation context with conversation IDs.
   - Make current mode and send risk visible.

## Improvement Backlog

- Add visual verification to `focus_chat` so it confirms the target chat title after search.
- Add `read_unread_once`: focus the next red-dot conversation, read it, summarize, and save an event.
- Improve history scrolling with scrollbar dragging or PageUp fallback when wheel scrolling stalls.
- Add a screenshot diff/check so history reading can detect duplicate pages.
- Add a "current UI state" diagnostic that classifies WeChat as ready, blank, loading, image-preview, search-open, or modal-open.
- Add safer recovery actions for blank panes and transient overlays.
- Add Docker documentation that clearly separates web/API mode from Windows desktop automation mode.
- Add more tests for red-dot detection, blank panes, duplicate history pages, and tool-tier exposure.

## Definition Of Done

For each improvement:

- Keep the change scoped.
- Add or update tests when behavior changes.
- Run `python -m unittest discover -s tests -v`.
- Run `python -m compileall src tests`.
- If Web behavior changes, restart or verify `http://127.0.0.1:8787/api/health`.
- Commit with a clear message and push to GitHub when the user asks, or when the work is clearly ready to preserve.
