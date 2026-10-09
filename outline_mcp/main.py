import asyncio
import os
import sys

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import Client
from .tools import TOOLS


async def main():
    client = Client(os.getenv("OUTLINE_API_URL", ""), os.getenv("OUTLINE_API_KEY", ""))
    tools = {t["name"]: t for t in TOOLS}
    server = Server("outline-mcp-py")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(name=t["name"], description=t["description"], inputSchema=t["schema"])
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        tool = tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        output = await tool["handler"](arguments or {}, client)
        return [types.TextContent(type="text", text=output)]

    print("[outline] MCP server started (stdio transport)", file=sys.stderr, flush=True)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await client.http.aclose()


def run():
    """Entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
