"""Small safety helpers. Defense-in-depth only; not a complete security system."""
import re

_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_ -]?key|password|secret|private[_ -]?key)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
]


def screen_remote_text(value: str) -> str:
    """Redact obvious secret-shaped strings from remote output."""
    cleaned = value
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned
