"""Minimal MCP stdio client using the official MCP Python SDK."""
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPToolClient:
    async def list_tools(self, command: list[str]) -> list[dict[str, str]]:
        if not command:
            return []
        server_params = StdioServerParameters(command=command[0], args=command[1:])
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {"name": tool.name, "description": tool.description or ""}
                    for tool in result.tools
                ]
