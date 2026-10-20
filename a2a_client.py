"""Basic A2A discovery and JSON-RPC task adapter.

A2A protocol versions and server implementations may differ. Review the remote
Agent Card and documentation before using this adapter with a real service.
"""
import json
import uuid
from typing import Any

import httpx


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
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(self.agent_card_url, headers=self._headers())
            response.raise_for_status()
            card = response.json()
        if not isinstance(card, dict):
            raise ValueError("Agent Card response was not a JSON object.")
        return card

    async def send_task(self, task_text: str) -> str:
        if not task_text:
            raise ValueError("Task text must not be empty.")
        card = await self.get_agent_card()
        endpoint = card.get("url") or card.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
            raise ValueError("Agent Card must expose an HTTPS url or endpoint; adapt to the server's A2A version.")

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
