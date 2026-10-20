"""Restricted MCP stdio discovery using the official Python SDK.

This client only discovers tool metadata. It never invokes remote tools. The
MCP child receives a minimal environment so Adam's credentials are not inherited.
"""
import asyncio
import os
import re

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MAX_COMMAND_PARTS = 64
MAX_COMMAND_PART_CHARS = 2048
MAX_TOOLS = 256
MAX_TOOL_NAME_CHARS = 128
MAX_DESCRIPTION_CHARS = 4000
DISCOVERY_TIMEOUT_SECONDS = 20
_FORBIDDEN_ENV = {
    "ADAM_OWNER_PASSWORD",
    "LLM_API_KEY",
    "A2A_BEARER_TOKEN",
    "MCP_SERVER_COMMAND",
}
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _child_environment() -> dict[str, str]:
    """Build a minimal child environment plus explicitly approved variables."""
    safe_names = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    configured = os.getenv("MCP_SERVER_ENV_ALLOWLIST", "")
    for name in configured.split(","):
        name = name.strip()
        if (
            name
            and _ENV_NAME.fullmatch(name)
            and name not in _FORBIDDEN_ENV
        ):
            safe_names.add(name)
    return {
        name: os.environ[name]
        for name in safe_names
        if name in os.environ and name not in _FORBIDDEN_ENV
    }


def _validate_command(command: list[str]) -> list[str]:
    if not isinstance(command, list) or not command:
        raise ValueError("MCP command must be a non-empty argument list.")
    if len(command) > MAX_COMMAND_PARTS:
        raise ValueError("MCP command contains too many arguments.")
    if any(
        not isinstance(part, str)
        or not part
        or len(part) > MAX_COMMAND_PART_CHARS
        or "\x00" in part
        for part in command
    ):
        raise ValueError("MCP command contains an invalid argument.")
    return command


class MCPToolClient:
    async def list_tools(self, command: list[str]) -> list[dict[str, str]]:
        command = _validate_command(command)
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:],
            env=_child_environment(),
        )
        async with asyncio.timeout(DISCOVERY_TIMEOUT_SECONDS):
            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools
                    if len(tools) > MAX_TOOLS:
                        raise ValueError("MCP server returned too many tools.")
                    names: set[str] = set()
                    safe_tools: list[dict[str, str]] = []
                    for tool in tools:
                        name = tool.name
                        description = tool.description or ""
                        if (
                            not isinstance(name, str)
                            or not name.strip()
                            or len(name) > MAX_TOOL_NAME_CHARS
                            or not isinstance(description, str)
                            or len(description) > MAX_DESCRIPTION_CHARS
                            or name in names
                        ):
                            raise ValueError("MCP server returned invalid tool metadata.")
                        names.add(name)
                        safe_tools.append(
                            {"name": name, "description": description}
                        )
                    return safe_tools
