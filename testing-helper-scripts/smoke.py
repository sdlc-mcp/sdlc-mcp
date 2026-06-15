"""Smoke test for discovery tools.

Usage:
    python tests/smoke.py stdio
    python tests/smoke.py http [url]
"""

import asyncio
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport


async def _call_discovery_tools(client):
    tools = await client.list_tools()
    print("=== tools ===")
    for tool in tools:
        print(f"  {tool.name}: {tool.description}")

    print()
    r = await client.call_tool("list_repos", {})
    print("=== list_repos ===")
    print(r.content[0].text)

    print()
    r = await client.call_tool("list_tools_for_repo", {"repo": "awx"})
    print("=== list_tools_for_repo(awx) ===")
    print(r.content[0].text)


async def smoke_stdio():
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "sdlc_mcp", "serve", "--config", "examples/config.yml"],
    )
    async with Client(transport) as client:
        await _call_discovery_tools(client)


async def smoke_http(url="http://localhost:8000/mcp"):
    transport = StreamableHttpTransport(url)
    async with Client(transport) as client:
        await _call_discovery_tools(client)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("stdio", "http"):
        print("Usage: python tests/smoke.py stdio|http [url]")
        sys.exit(1)

    if sys.argv[1] == "stdio":
        asyncio.run(smoke_stdio())
    else:
        url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/mcp"
        asyncio.run(smoke_http(url))
