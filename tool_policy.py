"""Default-deny policy for tools discovered from an MCP server.

This module only classifies discovered tools. It does not execute tools.
A future executor must call this policy immediately before every invocation.
"""
import re
from collections.abc import Iterable, Mapping

_RISKY_TOOL_TEXT = re.compile(
    r"\b(delete|remove|destroy|drop|write|overwrite|modify|update|execute|"
    r"shell|terminal|command|purchase|payment|transfer|withdraw|trade|"
    r"deploy|install|credential|secret|password|admin|permission)\b",
    re.IGNORECASE,
)


def parse_tool_allowlist(raw_value: str) -> set[str]:
    """Parse exact, case-sensitive tool names from a comma-separated setting."""
    if not isinstance(raw_value, str):
        return set()
    return {name.strip() for name in raw_value.split(",") if name.strip()}


def tool_policy(
    tool: Mapping[str, object], allowed_names: Iterable[str]
) -> dict[str, str | bool]:
    """Return a conservative display policy; malformed tools are denied."""
    if not isinstance(tool, Mapping):
        return {"name": "(invalid)", "allowed": False, "reason": "invalid tool metadata"}

    raw_name = tool.get("name", "")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return {"name": "(unnamed)", "allowed": False, "reason": "missing or invalid tool name"}

    name = raw_name.strip()
    raw_description = tool.get("description", "")
    description = raw_description if isinstance(raw_description, str) else ""
    try:
        allowed = set(allowed_names)
    except (TypeError, ValueError):
        allowed = set()

    risk_text = re.sub(r"[_-]+", " ", f"{name} {description}")
    if _RISKY_TOOL_TEXT.search(risk_text):
        return {"name": name, "allowed": False, "reason": "potentially sensitive capability"}
    if name not in allowed:
        return {"name": name, "allowed": False, "reason": "not explicitly allowlisted"}
    return {
        "name": name,
        "allowed": True,
        "reason": "allowlisted for review only; execution is not implemented",
    }
