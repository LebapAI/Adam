"""Guarded executor for explicitly registered local tools.

This does not execute arbitrary MCP tools, shell commands, or code from agents.
Only handlers registered by the application owner can run, and every invocation
requires an exact allowlist match plus explicit confirmation.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from tool_policy import tool_policy

MAX_ARGUMENT_BYTES = 8_192
MAX_STRING_CHARS = 4_096
SUPPORTED_TYPES = {"string", "integer", "number", "boolean"}


class ToolExecutionDenied(PermissionError):
    """Raised when a tool invocation fails a security gate."""


def _validate_arguments(
    arguments: Mapping[str, Any], schema: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(arguments, Mapping):
        raise ToolExecutionDenied("Arguments must be a JSON object")
    try:
        encoded = json.dumps(arguments, ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ToolExecutionDenied("Arguments must contain JSON-compatible values") from exc
    if len(encoded) > MAX_ARGUMENT_BYTES:
        raise ToolExecutionDenied("Arguments exceed the configured size limit")

    properties = schema.get("properties")
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ToolExecutionDenied("Tool schema is invalid")
    if set(arguments) - set(properties):
        raise ToolExecutionDenied("Unknown argument supplied")
    if set(required) - set(arguments):
        raise ToolExecutionDenied("Required argument is missing")

    validated: dict[str, Any] = {}
    for key, value in arguments.items():
        spec = properties.get(key)
        if not isinstance(spec, dict) or spec.get("type") not in SUPPORTED_TYPES:
            raise ToolExecutionDenied("Unsupported argument schema")
        kind = spec["type"]
        valid = (
            isinstance(value, str) if kind == "string"
            else isinstance(value, int) and not isinstance(value, bool) if kind == "integer"
            else isinstance(value, (int, float)) and not isinstance(value, bool) if kind == "number"
            else isinstance(value, bool) if kind == "boolean"
            else False
        )
        if not valid:
            raise ToolExecutionDenied("Argument type mismatch")
        if isinstance(value, str) and len(value) > MAX_STRING_CHARS:
            raise ToolExecutionDenied("String argument exceeds the size limit")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in spec and value < spec["minimum"]:
                raise ToolExecutionDenied("Numeric argument is below its minimum")
            if "maximum" in spec and value > spec["maximum"]:
                raise ToolExecutionDenied("Numeric argument exceeds its maximum")
        if kind == "string" and "enum" in spec and value not in spec["enum"]:
            raise ToolExecutionDenied("String argument is not an allowed value")
        validated[key] = value
    return validated


def execute_registered_tool(
    name: str,
    arguments: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    allowed_names: set[str],
    confirm: Callable[[str], bool],
) -> Any:
    """Execute only a locally registered handler after policy and confirmation."""
    if not isinstance(name, str) or name not in registry:
        raise ToolExecutionDenied("Tool is not registered locally")
    if name not in allowed_names:
        raise ToolExecutionDenied("Tool is not explicitly allowlisted")

    entry = registry[name]
    if not isinstance(entry, Mapping):
        raise ToolExecutionDenied("Tool registration is invalid")
    description = entry.get("description", "")
    policy = tool_policy({"name": name, "description": str(description)}, allowed_names)
    if not policy["allowed"]:
        raise ToolExecutionDenied(str(policy["reason"]))

    handler = entry.get("handler")
    schema = entry.get("schema")
    if not callable(handler) or not isinstance(schema, Mapping):
        raise ToolExecutionDenied("Tool registration is incomplete")
    validated = _validate_arguments(arguments, schema)
    if not confirm("EXECUTE"):
        raise ToolExecutionDenied("Owner confirmation was not granted")
    return handler(**validated)
