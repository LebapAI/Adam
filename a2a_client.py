"""Conservative A2A discovery and JSON-RPC task adapter.

Remote agent metadata and responses are untrusted. This client never executes
remote code or tools. Network checks are defense-in-depth; production deployments
should additionally enforce outbound policy at the OS/container/network layer.
"""
import asyncio
import ipaddress
import json
import socket
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx

MAX_TASK_CHARS = 12_000
MAX_RESPONSE_BYTES = 1_000_000
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 15.0


def _parse_https_url(url: str):
    """Parse a public HTTPS URL and reject ambiguous or unsafe URL forms."""
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("A valid HTTPS URL is required.")
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
        or parsed.fragment
    ):
        raise ValueError("A valid HTTPS URL without credentials or fragments is required.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost endpoints are not allowed.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Non-public IP addresses are not allowed for A2A endpoints.")
    return parsed, hostname, port


def _https_origin(url: str) -> tuple[str, int]:
    """Return a normalized HTTPS origin, rejecting unsafe or malformed URLs."""
    _, hostname, port = _parse_https_url(url)
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


async def _check_public_dns(url: str) -> None:
    """Reject hostnames that resolve to any non-public address.

    DNS is checked before each request, but ordinary HTTP clients resolve again
    when connecting. This check alone cannot eliminate DNS-rebinding races; use
    egress firewall/container policy or a transport that pins validated DNS.
    """
    _, hostname, port = _parse_https_url(url)
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise ValueError("Non-public IP addresses are not allowed for A2A endpoints.")
        return

    loop = asyncio.get_running_loop()
    try:
        records = await asyncio.wait_for(
            loop.getaddrinfo(
                hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            ),
            timeout=CONNECT_TIMEOUT,
        )
    except (OSError, TimeoutError) as exc:
        raise ValueError("A2A hostname could not be safely resolved.") from exc
    addresses = {record[4][0] for record in records}
    if not addresses:
        raise ValueError("A2A hostname returned no addresses.")
    for raw_address in addresses:
        try:
            address = ipaddress.ip_address(raw_address.split("%", 1)[0])
        except ValueError as exc:
            raise ValueError("A2A hostname returned an invalid address.") from exc
        if not address.is_global:
            raise ValueError("A2A hostname resolves to a non-public address.")


async def _read_json_limited(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> Any:
    """Fetch JSON while bounding decompressed response bytes."""
    await _check_public_dns(url)
    chunks: list[bytes] = []
    total = 0
    async with client.stream(method, url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise ValueError("A2A response exceeded the configured size limit.")
            chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("A2A endpoint returned invalid JSON.") from exc


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
        _parse_https_url(self.agent_card_url)
        timeout = httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)
        limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
        async with httpx.AsyncClient(
            timeout=timeout, limits=limits, follow_redirects=False
        ) as client:
            card = await _read_json_limited(
                client, "GET", self.agent_card_url, self._headers()
            )
        if not isinstance(card, dict):
            raise TypeError("Agent Card response must be a JSON object.")
        endpoint = card.get("url") or card.get("endpoint")
        if not isinstance(endpoint, str):
            raise TypeError("Agent Card must expose an HTTPS url or endpoint.")
        _validate_endpoint(self.agent_card_url, endpoint)
        return card

    async def send_task(self, task_text: str) -> str:
        if not isinstance(task_text, str) or not task_text.strip():
            raise ValueError("Task text must not be empty.")
        if len(task_text) > MAX_TASK_CHARS:
            raise ValueError(f"Task text exceeds {MAX_TASK_CHARS} characters.")

        card = await self.get_agent_card()
        endpoint = card.get("url") or card.get("endpoint")
        if not isinstance(endpoint, str):
            raise TypeError("Agent Card must expose an HTTPS url or endpoint.")
        _validate_endpoint(self.agent_card_url, endpoint)

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tasks/send",
            "params": {
                "id": str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": task_text}],
                },
            },
        }
        timeout = httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)
        limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
        async with httpx.AsyncClient(
            timeout=timeout, limits=limits, follow_redirects=False
        ) as client:
            data = await _read_json_limited(
                client, "POST", endpoint, self._headers(), payload
            )
        if not isinstance(data, dict):
            raise TypeError("A2A response must be a JSON object.")
        if data.get("jsonrpc") != "2.0" or data.get("id") != request_id:
            raise ValueError("A2A response did not match the expected JSON-RPC request.")
        if "error" in data:
            # Do not include untrusted remote error content in exceptions or logs.
            raise RuntimeError("Remote A2A agent returned an error.")
        result = data.get("result")
        if result is None:
            raise ValueError("A2A response did not contain a result.")
        return json.dumps(result, ensure_ascii=False, indent=2)
