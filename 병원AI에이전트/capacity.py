"""Deterministic ER capacity check against the hospital's Notion databases.

The acceptance rule (수술실 >= 1 AND 베드 >= 1 AND 수술가능 의사 >= 1) lives HERE,
in code - the LLM only maps symptoms to a department name and relays the result.

The Notion DBs use ENGLISH property names and values:
  진료과 DB : department_name (title), department_number (number), phone (rich_text)
  의사   DB : doctor_name (title), doctor_number, department_number, in_surgery (checkbox), phone_number
  공간   DB : facility_name (title, e.g. "operating_rooms"/"beds"), available (number)
The host sends Korean department names, so we translate 한글 -> English first.
"""

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{db_id}/query"
NOTION_VERSION = "2022-06-28"

# 한글 진료과 -> DB의 영어 진료과명 (필요시 확장)
DEPARTMENT_KO_EN = {
    "가정의학과": "Family Medicine",
    "내과": "Internal Medicine",
    "마취통증의학과": "Anesthesiology",
    "마취과": "Anesthesiology",
    "산부인과": "Obstetrics & Gynecology",
    "소아청소년과": "Pediatrics",
    "소아과": "Pediatrics",
    "신경과": "Neurology",
    "신경외과": "Neurosurgery",
    "심장내과": "Cardiology",
    "순환기내과": "Cardiology",
    "영상의학과": "Radiology",
    "외과": "General Surgery",
    "일반외과": "General Surgery",
    "응급의학과": "Emergency Medicine",
    "정형외과": "Orthopedics",
    "재활의학과": "Rehabilitation Medicine",
    "진단검사의학과": "Clinical Pathology",
    "흉부외과": "Thoracic Surgery",
    "흉부심장과": "Thoracic Surgery",
    "심장혈관흉부외과": "Thoracic Surgery",
    "피부과": "Dermatology",
    "비뇨기과": "Urology",
    "비뇨의학과": "Urology",
    "치과": "Dentistry",
    "안과": "Ophthalmology",
}


def _translate_department(name: str) -> str:
    """한글 진료과명을 DB의 영어명으로 변환. 매핑 없으면 원문 그대로(이미 영어일 수 있음)."""
    name = (name or "").strip()
    if name in DEPARTMENT_KO_EN:
        return DEPARTMENT_KO_EN[name]
    for ko, en in DEPARTMENT_KO_EN.items():
        if ko in name:  # "신경외과 전문의" 같은 경우
            return en
    return name


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


def _title(props: dict, name: str) -> str:
    p = props.get(name, {})
    return "".join(t.get("plain_text", "") for t in p.get("title", []))


def _number(props: dict, name: str) -> float | None:
    p = props.get(name, {})
    return p.get("number") if p.get("type") == "number" else None


def _rich_text(props: dict, name: str) -> str:
    p = props.get(name, {})
    return "".join(t.get("plain_text", "") for t in p.get("rich_text", []))


async def check_capacity(department_name: str) -> dict:
    """Checks whether this hospital can accept a patient needing the given department.

    Args:
        department_name: 진료과 이름 (한글, 예: "신경외과", "정형외과").

    Returns a dict with "decision": "accept" | "decline" | "unknown" | "error",
    plus the doctor list and facility counts backing that decision.
    """
    hospital = os.getenv("HOSPITAL_NAME", "병원")
    dept_db = os.getenv("NOTION_DEPARTMENT_DB_ID", "")
    doctor_db = os.getenv("NOTION_DOCTOR_DB_ID", "")
    space_db = os.getenv("NOTION_SPACE_DB_ID", "")
    dept_en = _translate_department(department_name)
    result: dict = {
        "hospital": hospital,
        "department_requested": department_name,
        "department_matched": dept_en,
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
            # 1. Department -> department_number
            dept_rows = await _query_db(client, dept_db, {
                "filter": {
                    "property": "department_name",
                    "title": {"contains": dept_en},
                }
            })
            if not dept_rows:
                result.update(
                    decision="decline",
                    reason=f"'{department_name}'({dept_en}) 진료과가 이 병원에 없습니다.",
                )
                return result
            dept_props = dept_rows[0].get("properties", {})
            dept_number = _number(dept_props, "department_number")
            result["department"] = {
                "name": _title(dept_props, "department_name"),
                "number": dept_number,
            }
            if dept_number is None:
                result.update(decision="unknown", reason="department_number를 찾지 못했습니다.")
                return result

            # 2. Doctors in that department who are not in surgery
            doctor_rows = await _query_db(client, doctor_db, {
                "filter": {
                    "and": [
                        {"property": "department_number", "number": {"equals": dept_number}},
                        {"property": "in_surgery", "checkbox": {"equals": False}},
                    ]
                }
            })
            doctors = [
                {
                    "name": _title(row.get("properties", {}), "doctor_name"),
                    "phone": _rich_text(row.get("properties", {}), "phone_number"),
                }
                for row in doctor_rows
            ]
            result["available_doctors"] = doctors

            # 3. Facility counts (facility_name -> available)
            space_rows = await _query_db(client, space_db, {})
            operating_rooms = beds = None
            raw_spaces = []
            for row in space_rows:
                props = row.get("properties", {})
                title = _title(props, "facility_name")
                count = _number(props, "available")
                raw_spaces.append({"facility": title, "available": count})
                key = (title or "").lower()
                if count is not None:
                    if "operating" in key or "수술실" in key:
                        operating_rooms = count
                    elif "bed" in key or "베드" in key or "병상" in key:
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
