"""Agentverse-compatible chat protocol for the existing Adam agent.

The Agent runs as a mailbox-enabled uAgent so Railway does not need to expose a
second inbound port. It delegates natural-language responses to AdamAgent's
existing configured LLM client and does not execute tools or remote commands.
"""
import asyncio
import logging
import os
from datetime import datetime
from uuid import uuid4

from main import AdamAgent

try:
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        TextContent,
        chat_protocol_spec,
    )
except ImportError as exc:  # pragma: no cover - exercised by deployment configuration
    raise RuntimeError(
        "Agentverse integration requires the 'uagents' package. "
        "Install project requirements before starting this module."
    ) from exc

LOGGER = logging.getLogger("adam.agentverse")
MAX_MESSAGE_CHARS = 12_000


def create_reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=text),
            EndSessionContent(type="end-session"),
        ],
    )


def build_agent(adam: AdamAgent | None = None) -> Agent:
    seed = os.getenv("AGENT_SEED_PHRASE", "").strip()
    if not seed:
        raise RuntimeError("AGENT_SEED_PHRASE is not configured.")

    adam_agent = adam or AdamAgent()
    agent = Agent(
        name="Adam",
        seed=seed,
        port=int(os.getenv("AGENT_PORT", "8001")),
        mailbox=True,
    )
    chat = Protocol(spec=chat_protocol_spec)

    @chat.on_message(ChatMessage)
    async def handle_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(
            sender,
            ChatAcknowledgement(
                timestamp=datetime.utcnow(),
                acknowledged_msg_id=msg.msg_id,
            ),
        )
        text = (msg.text() or "").strip()
        if not text:
            await ctx.send(sender, create_reply("Please send a text question."))
            return
        if len(text) > MAX_MESSAGE_CHARS:
            await ctx.send(
                sender,
                create_reply(f"Your message is too long. Limit: {MAX_MESSAGE_CHARS} characters."),
            )
            return
        try:
            # ACP messages are external input. The LLM is instructed to treat them as
            # untrusted data; no MCP/A2A tools or consequential actions are invoked.
            answer = await adam_agent.ask_model(text)
        except Exception:
            LOGGER.exception("Adam failed to answer an Agentverse chat message")
            answer = "Adam could not complete that request. Please try again later."
        await ctx.send(sender, create_reply(answer))

    @chat.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        return

    agent.include(chat, publish_manifest=True)
    return agent


def run_agentverse_agent() -> None:
    """Run the mailbox-backed ACP agent; call from a dedicated thread/process."""
    agent = build_agent()
    LOGGER.info("Starting Adam Agentverse chat agent (mailbox enabled).")
    agent.run()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_agentverse_agent()
