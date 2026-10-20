"""Minimal privacy-conscious JSONL audit logging for Adam.

Only fixed event codes and a UTC timestamp are accepted. Never pass prompts,
credentials, tool arguments, or remote response content to this module.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_ALLOWED_ACTIONS = {
    "owner_auth",
    "external_llm_request",
    "external_a2a_request",
    "mcp_tool_discovery",
}
_ALLOWED_OUTCOMES = {"success", "failure", "cancelled", "denied"}
_ALLOWED_REASONS = {
    "authenticated",
    "invalid_password",
    "user_cancelled",
    "owner_approved",
    "request_completed",
    "request_error",
    "server_started",
    "discovery_completed",
    "discovery_error",
    "audit_error",
}


class AuditLogError(OSError):
    """Raised when a safe audit event cannot be persisted."""


def write_audit_event(action: str, outcome: str, reason: str) -> None:
    """Append one allowlisted event; fail closed if the log cannot be written."""
    if (
        action not in _ALLOWED_ACTIONS
        or outcome not in _ALLOWED_OUTCOMES
        or reason not in _ALLOWED_REASONS
        or not all(_TOKEN.fullmatch(value) for value in (action, outcome, reason))
    ):
        raise ValueError("Audit event contains an unsupported code")

    path = Path(os.getenv("ADAM_AUDIT_LOG", "adam_audit.jsonl")).expanduser()
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "outcome": outcome,
        "reason": reason,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path, flags, 0o600)
        try:
            os.chmod(path, 0o600)
        except OSError:
            # File creation mode remains restrictive on POSIX; do not silently
            # ignore a permission correction failure on an existing file.
            raise
        payload = (json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(fd, "ab", closefd=True) as stream:
            fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, TypeError, ValueError) as exc:
        raise AuditLogError("Could not safely write audit log") from exc
    finally:
        if fd is not None:
            os.close(fd)
