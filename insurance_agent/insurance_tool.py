"""Dedicated insurance-request tool.

The LLM only extracts 4 short fields; the Slack message formatting and the
channel are handled HERE in code. This avoids MALFORMED_FUNCTION_CALL, which
gemini-2.5-flash produced when asked to write one long multiline emoji text
argument to a generic slack tool.
"""

import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


def _format_message(patient_name: str, birth_date: str, details: str, hospital: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "🚨 EMERGENCY INSURANCE VERIFICATION REQUEST 🚨\n"
        f"- Patient: {patient_name or 'unknown'}\n"
        f"- DOB: {birth_date or 'unknown'}\n"
        f"- Symptoms/context: {details or 'unknown'}\n"
        f"- Destination hospital: {hospital or 'unknown'}\n"
        "- Needed: active policy, ER coverage, pre-authorization, copay/deductible\n"
        "- Urgency: HIGH (emergency patient)\n"
        f"- Requested at: {now}"
    )


async def send_insurance_request(
    patient_name: str, birth_date: str, details: str, hospital: str
) -> dict:
    """Send the emergency insurance verification request to the insurer's Slack channel.

    Args:
        patient_name: patient name (empty string if unknown).
        birth_date: date of birth, YYYY-MM-DD (empty string if unknown).
        details: one-line summary of symptoms and mechanism of injury.
        hospital: destination hospital name.

    Returns {"ok": true, "ts": ...} on success or {"ok": false, "error": ...}.
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("INSURANCE_SLACK_CHANNEL_ID", "")
    if not token:
        return {"ok": False, "error": "SLACK_BOT_TOKEN is not set"}
    text = _format_message(patient_name, birth_date, details, hospital)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                SLACK_POST_MESSAGE_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": channel, "text": text},
            )
        data = response.json()
    except Exception as e:
        logger.warning("Insurance Slack post failed: %s", e)
        return {"ok": False, "error": f"Slack request failed: {e}"}
    if not data.get("ok"):
        logger.warning("Slack API error: %s", data.get("error"))
    return {"ok": data.get("ok", False), "error": data.get("error"), "ts": data.get("ts")}
