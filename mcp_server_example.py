"""Example MCP server exposing a harmless text metadata tool."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Adam Example Tools")


@mcp.tool()
def summarize_text(text: str) -> str:
    """Return simple metadata about supplied text."""
    safe_text = text[:5000]
    return f"Characters: {len(safe_text)}; words: {len(safe_text.split())}"


if __name__ == "__main__":
    mcp.run()
