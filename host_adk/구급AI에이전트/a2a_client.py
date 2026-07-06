"""A2A client helpers for the host agent.

Built on the a2a-sdk 0.3.x ClientFactory generation. Every call returns a
structured dict (never raises, never returns None) so the LLM can always
decide the fallback itself:

    {"status": "success", "agent": ..., "text": ..., "duration_ms": ...}
    {"status": "timeout" | "error", "agent": ..., "reason": ..., "duration_ms": ...}
"""

import asyncio
import logging
import os
import time

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import (
    AgentCard,
    Message,
    Role,
    Task,
    TaskQueryParams,
    TaskState,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = float(os.getenv("A2A_CALL_TIMEOUT_S", "45"))
_TERMINAL_STATES = {
    TaskState.completed,
    TaskState.failed,
    TaskState.canceled,
    TaskState.rejected,
}


def a2a_auth_headers() -> dict[str, str]:
    """Shared bearer token for calls to the remote A2A agents (set A2A_AUTH_TOKEN on every agent)."""
    token = os.getenv("A2A_AUTH_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _message_text(message: Message) -> str:
    return "\n".join(
        part.root.text
        for part in message.parts or []
        if getattr(part.root, "text", None)
    )


def _task_text(task: Task) -> str:
    chunks: list[str] = []
    for artifact in task.artifacts or []:
        for part in artifact.parts or []:
            text = getattr(part.root, "text", None)
            if text:
                chunks.append(text)
    if not chunks and task.status and task.status.message:
        chunks.append(_message_text(task.status.message))
    return "\n".join(chunks)


class RemoteAgentRegistry:
    """Resolves agent cards, holds one A2A client per remote agent."""

    def __init__(self):
        self._httpx_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10, read=DEFAULT_TIMEOUT_S),
            headers=a2a_auth_headers(),
        )
        self._factory = ClientFactory(
            ClientConfig(httpx_client=self._httpx_client, streaming=False, polling=True)
        )
        self.cards: dict[str, AgentCard] = {}
        self._clients: dict[str, object] = {}
        self._addresses: dict[str, str] = {}

    @property
    def agent_names(self) -> list[str]:
        return list(self._clients)

    async def connect(self, addresses: list[str]) -> None:
        for address in addresses:
            try:
                await self._connect_one(address)
            except Exception as e:
                logger.error("Failed to connect to remote agent at %s: %s", address, e)
        logger.info("Connected remote agents: %s", self.agent_names)

    async def _connect_one(self, address: str) -> None:
        resolver = A2ACardResolver(self._httpx_client, address)
        card = await resolver.get_agent_card()
        self.cards[card.name] = card
        self._addresses[card.name] = address
        self._clients[card.name] = self._factory.create(card)
        logger.info("Resolved agent card %r at %s", card.name, address)

    async def send(
        self, agent_name: str, text: str, timeout_s: float | None = None
    ) -> dict:
        """Send one message and collect the remote agent's final reply text."""
        started = time.monotonic()

        def _done(result: dict) -> dict:
            result["duration_ms"] = int((time.monotonic() - started) * 1000)
            return result

        if agent_name not in self._clients:
            return _done({
                "status": "error",
                "agent": agent_name,
                "reason": (
                    f"Agent '{agent_name}' is not connected. "
                    f"Available agents: {self.agent_names}"
                ),
            })

        try:
            reply = await asyncio.wait_for(
                self._send_once(agent_name, text),
                timeout=timeout_s or DEFAULT_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, TimeoutError):
            return _done({
                "status": "timeout",
                "agent": agent_name,
                "reason": f"No reply within {timeout_s or DEFAULT_TIMEOUT_S:.0f}s",
            })
        except httpx.ConnectError:
            # The remote may have restarted: re-resolve its card once and retry.
            try:
                await self._connect_one(self._addresses[agent_name])
                reply = await asyncio.wait_for(
                    self._send_once(agent_name, text),
                    timeout=timeout_s or DEFAULT_TIMEOUT_S,
                )
            except Exception as e:
                return _done({
                    "status": "error",
                    "agent": agent_name,
                    "reason": f"Connection failed (after one reconnect attempt): {e}",
                })
        except Exception as e:
            return _done({
                "status": "error",
                "agent": agent_name,
                "reason": f"Request to remote agent failed: {e}",
            })

        if not reply.strip():
            return _done({
                "status": "error",
                "agent": agent_name,
                "reason": "Remote agent returned an empty response.",
            })
        return _done({"status": "success", "agent": agent_name, "text": reply})

    async def _send_once(self, agent_name: str, text: str) -> str:
        """Send a message and wait for the remote task to actually finish.

        The ADK to_a2a server processes the request asynchronously: the initial
        response carries a `submitted`/`working` task (no result yet), so we poll
        get_task until a terminal state before reading the artifacts. The outer
        asyncio.wait_for in send() bounds the total wait.
        """
        client = self._clients[agent_name]
        message = create_text_message_object(Role.user, text)
        task: Task | None = None
        last_message_text = ""
        async for event in client.send_message(message):
            if isinstance(event, Message):
                last_message_text = _message_text(event)
            else:
                task, _update = event

        if task is None:
            return last_message_text

        # Poll until the task reaches a terminal state, then read its artifacts.
        while task.status is None or task.status.state not in _TERMINAL_STATES:
            await asyncio.sleep(0.6)
            task = await client.get_task(TaskQueryParams(id=task.id))

        return _task_text(task) or last_message_text
