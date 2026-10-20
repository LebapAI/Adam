"""Default-deny policy for tools discovered from an MCP server.

This module only classifies discovered tools. It does not execute tools.
A future executor must call this policy immediately before every invocation.
"""
import re
from collections.abc import Iterable

_RISKY_TOOL_TEXT = re.compile(
    r"\b(delete|remove|destroy|drop|write|overwrite|modify|update|execute|"
    r"shell|terminal|command|purchase|payment|transfer|withdraw|trade|"
    r"deploy|install|credential|secret|password|admin|permission)\b",
    re.IGNORECASE,
)


def parse_tool_allowlist(raw_value: str) -> set[str]:
    """Parse exact, case-sensitive tool names from a comma-separated setting."""
    return {name.strip() for name in raw_value.split(",") if name.strip()}


def tool_policy(tool: dict[str, str], allowed_names: Iterable[str]) -> dict[str, str | bool]:
    """Return a conservative display policy; unknown tools are denied by default."""
    name = tool.get("name", "").strip()
    description = tool.get("description", "")
    allowed = set(allowed_names)
    if not name:
        return {"name": "(unnamed)", "allowed": False, "reason": "missing tool name"}
    if _RISKY_TOOL_TEXT.search(f"{name} {description}"):
        return {"name": name, "allowed": False, "reason": "potentially sensitive capability"}
    if name not in allowed:
        return {"name": name, "allowed": False, "reason": "not explicitly allowlisted"}
    return {
        "name": name,
        "allowed": True,
        "reason": "allowlisted for review only; execution is not implemented",
    }
