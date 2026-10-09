import os
import sys
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import Client
from .tools import TOOLS


async def main():
    base_url = os.getenv("OUTLINE_API_URL", "")
    api_key = os.getenv("OUTLINE_API_KEY", "")

    client = Client(base_url, api_key)

    # Create MCP server
    server = Server("outline")

    # Register tools
    for tool_def in TOOLS:
        tool_name = tool_def["name"]
        tool_desc = tool_def["description"]
        handler = tool_def["handler"]

        @server.call_tool()
        async def call_tool(name: str = tool_name, args=None, handler=handler, client=client):
            """Handle tool call"""
            if args is None:
                args = {}

            # Execute handler
            output = await handler(args, client)

            # Determine if error
            is_error = output.startswith("Error:")

            return {
                "content": [{"type": "text", "text": output}],
                "isError": is_error,
            }

    # Run server with stdio transport
    async with stdio_server(server) as server_handle:
        await server_handle.wait_closed()


def run():
    """Entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
