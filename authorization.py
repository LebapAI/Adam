"""Explicit confirmation policy for operations that cross a trust boundary."""

_CONFIRMATION_PHRASES = {
    "send_to_llm": "SEND",
    "send_to_a2a": "SEND",
    "start_mcp_server": "START",
}


def confirmation_phrase(action: str) -> str:
    """Return the required confirmation word for a known action."""
    try:
        return _CONFIRMATION_PHRASES[action]
    except KeyError as exc:
        raise ValueError("Unknown action; refusing by default.") from exc


def confirmation_granted(action: str, response: str) -> bool:
    """Fail closed unless the exact required confirmation word is supplied."""
    try:
        expected = confirmation_phrase(action)
    except ValueError:
        return False
    return response.strip() == expected
