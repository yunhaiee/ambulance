import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncIterable, List

import nest_asyncio
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .a2a_client import RemoteAgentRegistry
from .audit import audit_log
from .prompt import get_ambulance_ai_prompt

load_dotenv()
nest_asyncio.apply()

logger = logging.getLogger(__name__)

# Per-hospital time budget for the parallel fan-out (the whole batch takes
# roughly as long as the slowest single hospital).
HOSPITAL_DISPATCH_TIMEOUT_S = float(os.getenv("HOSPITAL_DISPATCH_TIMEOUT_S", "45"))

DEFAULT_REMOTE_AGENT_URLS = [
    "http://localhost:10002",  # 교통
    "http://localhost:10003",  # 병원 (대전한국병원)
    "http://localhost:10004",  # 병원 (대전선병원)
    "http://localhost:10005",  # 보험
]


def _remote_agent_urls() -> List[str]:
    raw = os.getenv("REMOTE_AGENT_URLS")
    if raw:
        return [u.strip() for u in raw.split(",") if u.strip()]
    return DEFAULT_REMOTE_AGENT_URLS


def _normalize(name: str) -> str:
    return re.sub(r"\s+|AI에이전트|응급의료센터|응급센터|응급실", "", name)


_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")


def _detect_lang(context) -> str:
    """Detect the user's language: Korean if Hangul dominates, else English.

    Uses a ratio (not mere presence) so an English message that contains a Korean
    place name (e.g. "Daejeon Station (대전역)") is still detected as English.
    """
    text = ""
    user_content = getattr(context, "user_content", None)
    if user_content is not None:
        for part in getattr(user_content, "parts", None) or []:
            if getattr(part, "text", None):
                text += part.text
    return "ko" if len(_HANGUL.findall(text)) > len(_LATIN.findall(text)) else "en"


# Capture everything between the ```json fences (handles nested braces).
_JSON_BLOCK = re.compile(r"```json\s*(.+?)\s*```", re.DOTALL)


def _find_decision(obj) -> dict | None:
    """Recursively find a dict carrying a string "decision" (the LLM may nest it)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("decision"), str):
            return obj
        for value in obj.values():
            found = _find_decision(value)
            if found:
                return found
    return None


def _parse_hospital_reply(text: str) -> dict:
    """Extract the structured decision from a hospital agent's reply.

    Prefers the JSON block the hospital prompt requires; falls back to the
    accept/decline markers. Returns {"decision": "accept"|"decline"|"unclear", ...}.
    """
    for match in _JSON_BLOCK.finditer(text):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        found = _find_decision(payload)
        if found:
            return found
    if "수용불가" in text or "❌" in text:
        return {"decision": "decline"}
    if "수용가능" in text or "✅" in text:
        return {"decision": "accept"}
    return {"decision": "unclear"}


class HostAgent:
    """The Host agent: orchestrates traffic, hospital, and insurance agents."""

    def __init__(self):
        self.registry = RemoteAgentRegistry()
        self.agents: str = "No agents found"
        self._agent = self.create_agent()
        self._user_id = "구급AI에이전트"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        await self.registry.connect(remote_agent_addresses)
        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.registry.cards.values()
        ]
        self.agents = "\n".join(agent_info) if agent_info else "No agents found"

    @classmethod
    async def create(cls, remote_agent_addresses: List[str]):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        return Agent(
            # Host does KTAS medical triage — default to a stronger model than
            # the worker agents. Override with AGENT_MODEL in host_adk/.env.
            model=os.getenv("AGENT_MODEL", "gemini-2.5-pro"),
            name="구급AI에이전트",
            instruction=self.root_instruction,
            description="This Host agent orchestrates the emergency process at the ambulance.",
            tools=[
                self.send_message,
                self.dispatch_to_hospitals,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return get_ambulance_ai_prompt(self.agents, lang=_detect_lang(context))

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """Streams the agent's response to a given query."""
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                yield {"is_task_complete": True, "content": response}
            else:
                yield {"is_task_complete": False, "updates": "The host agent is thinking..."}

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to one remote agent (교통/보험 or a single hospital).

        Returns {"status": "success", "text": ...} or
        {"status": "error"|"timeout", "reason": ...}. On an error, decide the
        fallback yourself (e.g. retry once or report to the paramedic).
        """
        audit_log.record("dispatch_sent", agent=agent_name, task_chars=len(task))
        result = await self.registry.send(agent_name, task)
        audit_log.record(
            "dispatch_result",
            agent=agent_name,
            status=result["status"],
            duration_ms=result.get("duration_ms"),
            reason=result.get("reason"),
            reply_chars=len(result.get("text", "")),
        )
        return result

    async def dispatch_to_hospitals(
        self, patient_summary: str, hospital_names: list[str], tool_context: ToolContext
    ):
        """Queries several hospitals IN PARALLEL for acceptance (use for step 4).

        Args:
            patient_summary: the full inquiry text (환자정보, 필요 진료과,
                KTAS 등급, 예상 도착시간 포함) - the same text for every hospital.
            hospital_names: hospital names from the traffic agent's ranked list,
                in ETA order (closest first). Names are matched to connected
                hospital agents automatically.

        Returns per-hospital results in the SAME order as hospital_names:
        {"hospital": ..., "agent": ..., "status": "accept"|"decline"|"unclear"|
         "no_agent"|"timeout"|"error", "detail": {...}, "reply": ...,
         "duration_ms": ...}. Pick the first "accept" in list order (that is
        the lowest-ETA accepting hospital); hospitals with "no_agent" must be
        phoned manually by the paramedic.
        """
        known_hospital_agents = [
            name for name in self.registry.agent_names
            if "병원" in name or "hospital" in name.lower()
        ]

        matched: list[tuple[str, str | None]] = []
        for hospital_name in hospital_names:
            normalized = _normalize(hospital_name)
            agent = next(
                (
                    a for a in known_hospital_agents
                    if normalized and (
                        normalized in _normalize(a) or _normalize(a) in normalized
                    )
                ),
                None,
            )
            matched.append((hospital_name, agent))

        audit_log.record(
            "hospital_fanout_started",
            hospitals=[h for h, _ in matched],
            matched_agents=[a for _, a in matched],
            summary_chars=len(patient_summary),
        )

        async def _query(hospital_name: str, agent: str | None) -> dict:
            if agent is None:
                return {
                    "hospital": hospital_name,
                    "agent": None,
                    "status": "no_agent",
                    "detail": {},
                    "reply": "이 병원은 시스템에 연결된 AI에이전트가 없습니다. 구급대원이 직접 전화해야 합니다.",
                }
            result = await self.registry.send(
                agent, patient_summary, timeout_s=HOSPITAL_DISPATCH_TIMEOUT_S
            )
            if result["status"] != "success":
                return {
                    "hospital": hospital_name,
                    "agent": agent,
                    "status": result["status"],
                    "detail": {},
                    "reply": result.get("reason", ""),
                    "duration_ms": result.get("duration_ms"),
                }
            parsed = _parse_hospital_reply(result["text"])
            return {
                "hospital": hospital_name,
                "agent": agent,
                "status": parsed.get("decision", "unclear"),
                "detail": parsed,
                "reply": result["text"],
                "duration_ms": result.get("duration_ms"),
            }

        results = await asyncio.gather(*(_query(h, a) for h, a in matched))
        results = list(results)

        audit_log.record(
            "hospital_fanout_finished",
            outcomes=[
                {
                    "hospital": r["hospital"],
                    "agent": r["agent"],
                    "status": r["status"],
                    "duration_ms": r.get("duration_ms"),
                }
                for r in results
            ],
        )
        return {"results": results}


def _get_initialized_host_agent_sync():
    """Synchronously creates and initializes the HostAgent."""

    async def _async_main():
        logger.info("initializing host agent")
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses=_remote_agent_urls()
        )
        logger.info("HostAgent initialized")
        return hosting_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            logger.warning(
                "Could not initialize HostAgent with asyncio.run(): %s. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application.",
                e,
            )
        else:
            raise


root_agent = _get_initialized_host_agent_sync()
