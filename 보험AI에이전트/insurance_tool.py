"""Dedicated insurance-request tool.

The LLM only extracts 4 short fields; the Slack message formatting and the
channel are handled HERE in code. This avoids MALFORMED_FUNCTION_CALL, which
gemini-2.5-flash produced when asked to write one long multiline emoji text
argument to a generic slack tool.
"""

import logging
import os
import re
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")


def _format_message(patient_name: str, birth_date: str, details: str, hospital: str) -> str:
    combined = f"{patient_name} {details} {hospital}"
    korean = len(_HANGUL.findall(combined)) > len(_LATIN.findall(combined))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if korean:
        return (
            "🚨 응급환자 보험 확인 요청 🚨\n"
            f"- 환자명: {patient_name or '미상'}\n"
            f"- 생년월일: {birth_date or '미상'}\n"
            f"- 증상·사고경위: {details or '미상'}\n"
            f"- 이송 병원: {hospital or '미상'}\n"
            "- 확인 필요: 보험 가입 여부, 응급치료 보장, 사전승인 요건, 본인부담금\n"
            "- 응급도: 높음(응급환자)\n"
            f"- 요청시각: {now}"
        )
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
        patient_name: 환자 이름 (모르면 빈 문자열).
        birth_date: 생년월일 YYYY-MM-DD (모르면 빈 문자열).
        details: 증상/사고 경위 한 줄 요약.
        hospital: 이송(예정) 병원명.

    Returns {"ok": true, "ts": ...} on success or {"ok": false, "error": ...}.
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("INSURANCE_SLACK_CHANNEL_ID", "C096P6A2Q66")
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
