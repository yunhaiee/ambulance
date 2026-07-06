"""Deterministic ER capacity check against the hospital's Notion databases.

The acceptance rule (수술실 >= 1 AND 베드 >= 1 AND 수술가능 의사 >= 1) lives HERE,
in code - the LLM only maps symptoms to a department name and relays the result.
"""

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{db_id}/query"
NOTION_VERSION = "2022-06-28"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_API_KEY', '')}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def _query_db(client: httpx.AsyncClient, db_id: str, payload: dict) -> list[dict]:
    response = await client.post(
        NOTION_QUERY_URL.format(db_id=db_id), headers=_headers(), json=payload
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _prop_of_type(props: dict, prop_type: str) -> tuple[str, dict] | None:
    for name, prop in props.items():
        if prop.get("type") == prop_type:
            return name, prop
    return None


def _title_text(props: dict) -> str:
    found = _prop_of_type(props, "title")
    if not found:
        return ""
    return "".join(t.get("plain_text", "") for t in found[1].get("title", []))


def _first_number(props: dict) -> float | None:
    found = _prop_of_type(props, "number")
    return found[1].get("number") if found else None


def _number_named(props: dict, name: str) -> float | None:
    prop = props.get(name)
    if prop and prop.get("type") == "number":
        return prop.get("number")
    return None


def _phone_text(props: dict) -> str | None:
    found = _prop_of_type(props, "phone_number")
    if found and found[1].get("phone_number"):
        return found[1]["phone_number"]
    for name, prop in props.items():
        if prop.get("type") == "rich_text" and any(
            key in name for key in ("전화", "연락처", "폰", "phone")
        ):
            return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    return None


async def check_capacity(department_name: str) -> dict:
    """Checks whether this hospital can accept a patient needing the given department.

    Args:
        department_name: 진료과 이름 (예: "신경외과", "정형외과").

    Returns a dict with "decision": "accept" | "decline" | "unknown" | "error",
    plus the doctor list and facility counts backing that decision.
    """
    hospital = os.getenv("HOSPITAL_NAME", "병원")
    dept_db = os.getenv("NOTION_DEPARTMENT_DB_ID", "")
    doctor_db = os.getenv("NOTION_DOCTOR_DB_ID", "")
    space_db = os.getenv("NOTION_SPACE_DB_ID", "")
    result: dict = {
        "hospital": hospital,
        "department_requested": department_name,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    if not (os.getenv("NOTION_API_KEY") and dept_db and doctor_db and space_db):
        result.update(
            decision="error",
            reason="Notion 설정 누락 (NOTION_API_KEY / NOTION_*_DB_ID 환경변수 확인)",
        )
        return result

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 1. Department -> 과번호
            dept_rows = await _query_db(client, dept_db, {
                "filter": {
                    "property": "과이름",
                    "title": {"contains": department_name},
                }
            })
            if not dept_rows:
                result.update(
                    decision="decline",
                    reason=f"'{department_name}' 진료과가 이 병원에 없습니다.",
                )
                return result
            dept_props = dept_rows[0].get("properties", {})
            dept_number = _number_named(dept_props, "과번호")
            if dept_number is None:
                dept_number = _first_number(dept_props)
            result["department"] = {
                "name": _title_text(dept_props) or department_name,
                "number": dept_number,
            }
            if dept_number is None:
                result.update(decision="unknown", reason="과번호를 찾지 못했습니다.")
                return result

            # 2. Doctors in that department who are not in surgery
            doctor_rows = await _query_db(client, doctor_db, {
                "filter": {
                    "and": [
                        {"property": "과번호", "number": {"equals": dept_number}},
                        {"property": "수술중", "checkbox": {"equals": False}},
                    ]
                }
            })
            doctors = [
                {
                    "name": _title_text(row.get("properties", {})),
                    "phone": _phone_text(row.get("properties", {})),
                }
                for row in doctor_rows
            ]
            result["available_doctors"] = doctors

            # 3. Facility counts (rows titled 수술실/베드 with a number property)
            space_rows = await _query_db(client, space_db, {})
            operating_rooms = beds = None
            raw_spaces = []
            for row in space_rows:
                props = row.get("properties", {})
                title = _title_text(props)
                count = _first_number(props)
                raw_spaces.append({"space": title, "count": count})
                if title and count is not None:
                    if "수술실" in title:
                        operating_rooms = count
                    elif "베드" in title or "병상" in title:
                        beds = count
            result["operating_rooms"] = operating_rooms
            result["beds"] = beds
            result["raw_spaces"] = raw_spaces
    except httpx.HTTPStatusError as e:
        result.update(
            decision="error",
            reason=f"Notion API 오류: HTTP {e.response.status_code} - {e.response.text[:200]}",
        )
        return result
    except Exception as e:
        result.update(decision="error", reason=f"조회 실패: {e}")
        return result

    # The acceptance rule, in code.
    if operating_rooms is None or beds is None:
        result.update(
            decision="unknown",
            reason="공간 DB에서 수술실/베드 수를 해석하지 못했습니다. raw_spaces를 확인하세요.",
        )
    elif len(doctors) >= 1 and operating_rooms >= 1 and beds >= 1:
        result.update(
            decision="accept",
            reason=f"수술가능 의사 {len(doctors)}명, 수술실 {operating_rooms:g}개, 베드 {beds:g}개 확보",
        )
    else:
        shortages = []
        if len(doctors) < 1:
            shortages.append("수술가능 의사 없음")
        if operating_rooms < 1:
            shortages.append("수술실 없음")
        if beds < 1:
            shortages.append("베드 없음")
        result.update(decision="decline", reason=", ".join(shortages))
    return result
