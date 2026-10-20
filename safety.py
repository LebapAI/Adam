"""Small safety helpers. Defense-in-depth only; not a complete security system."""
import re

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)\b(api[_ -]?key|password|secret|private[_ -]?key|access[_ -]?token)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]


def screen_remote_text(value: str) -> str:
    """Redact common secret-shaped strings from remote output.

    This is a best-effort display filter, not a security boundary. Never send
    secrets to remote agents in the first place.
    """
    cleaned = value
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned
