from __future__ import annotations

import os
import sys
from pathlib import Path

from agents.mcp import MCPServerStdio, MCPServerStdioParams

from .tool_tiers import allowed_tools_for_mode


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def create_stdio_mcp_server(
    mode: str = "daily",
    client_session_timeout_seconds: float = 60,
    server_name: str = "WeChat MCP Server",
) -> MCPServerStdio:
    root = project_root()
    env = dict(os.environ)
    src_dir = root / "src"
    pythonpath_parts = [str(src_dir), str(root)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.insert(0, env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["MCP_TRANSPORT"] = "stdio"
    env["MCP_ALLOWED_TOOLS"] = ",".join(allowed_tools_for_mode(mode))

    params = MCPServerStdioParams(
        command=sys.executable,
        args=["-m", "wechat_mcp.server"],
        env=env,
        cwd=str(root),
    )

    return MCPServerStdio(
        params=params,
        name=server_name,
        cache_tools_list=True,
        client_session_timeout_seconds=client_session_timeout_seconds,
        tool_filter={"allowed_tool_names": allowed_tools_for_mode(mode)},
        use_structured_content=True,
    )


async def list_agent_mcp_tools(mode: str = "daily") -> list[str]:
    server = create_stdio_mcp_server(mode=mode)
    async with server:
        tools = await server.list_tools()
        return [tool.name for tool in tools]
