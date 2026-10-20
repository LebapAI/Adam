"""Basic A2A discovery and JSON-RPC task adapter.

A2A protocol versions and server implementations may differ. Review the remote
Agent Card and documentation before using this adapter with a real service.
"""
import ipaddress
import json
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx


def _https_origin(url: str) -> tuple[str, int]:
    """Return a normalized HTTPS origin, rejecting unsafe or malformed URLs."""
    try:
        parsed = urlsplit(url)
        port = parsed.port or 443
    except ValueError as exc:
        raise ValueError("Invalid HTTPS URL.") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("A valid HTTPS URL without embedded credentials is required.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost endpoints are not allowed.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Non-public IP addresses are not allowed for A2A endpoints.")
    return hostname, port


def _validate_endpoint(agent_card_url: str, endpoint: str) -> str:
    """Require the task endpoint to share the configured Agent Card origin."""
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("Agent Card must expose a valid HTTPS url or endpoint.")
    if _https_origin(agent_card_url) != _https_origin(endpoint):
        raise ValueError(
            "Agent task endpoint must use the same HTTPS origin as its Agent Card."
        )
    return endpoint


class A2AClient:
    def __init__(self, agent_card_url: str, bearer_token: str = "") -> None:
        self.agent_card_url = agent_card_url.strip()
        self.bearer_token = bearer_token.strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def get_agent_card(self) -> dict[str, Any]:
        if not self.agent_card_url:
            raise RuntimeError("A2A_AGENT_CARD_URL is not configured.")
        _https_origin(self.agent_card_url)
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(self.agent_card_url, headers=self._headers())
            response.raise_for_status()
            card = response.json()
        if not isinstance(card, dict):
            raise ValueError("Agent Card response was not a JSON object.")
        return card

    async def send_task(self, task_text: str) -> str:
        if not task_text.strip():
            raise ValueError("Task text must not be empty.")
        card = await self.get_agent_card()
        endpoint = card.get("url") or card.get("endpoint")
        if not isinstance(endpoint, str):
            raise ValueError("Agent Card must expose an HTTPS url or endpoint.")
        _validate_endpoint(self.agent_card_url, endpoint)

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/send",
            "params": {
                "id": str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": task_text}],
                },
            },
        }
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=False) as client:
            response = await client.post(endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("A2A response was not a JSON object.")
        if "error" in data:
            raise RuntimeError(f"Remote A2A error: {json.dumps(data['error'])}")
        return json.dumps(data.get("result", data), ensure_ascii=False, indent=2)
