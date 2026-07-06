"""Direct Slack posting tool (replaces the archived @modelcontextprotocol/server-slack)."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


async def slack_post_message(channel_id: str, text: str) -> dict:
    """Post a message to a Slack channel.

    Args:
        channel_id: The ID of the channel to post to.
        text: The message text to post.

    Returns {"ok": true, "ts": ...} on success or {"ok": false, "error": ...}.
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return {"ok": False, "error": "SLACK_BOT_TOKEN is not set"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                SLACK_POST_MESSAGE_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": channel_id, "text": text},
            )
        data = response.json()
    except Exception as e:
        logger.warning("Slack post failed: %s", e)
        return {"ok": False, "error": f"Slack request failed: {e}"}
    if not data.get("ok"):
        logger.warning("Slack API error: %s", data.get("error"))
    return {"ok": data.get("ok", False), "error": data.get("error"), "ts": data.get("ts")}
