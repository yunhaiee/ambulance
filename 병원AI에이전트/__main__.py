"""A2A server for one hospital instance.

Run with a hospital profile:
    HOSPITAL_PROFILE=configs/대전선병원.env uv run .
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Profile first (hospital identity), then .env (shared secrets); profile wins.
_profile = os.getenv("HOSPITAL_PROFILE")
if _profile:
    load_dotenv(_profile, override=True)
load_dotenv()
# Optional per-hospital secret overrides (e.g. a distinct GOOGLE_API_KEY so each
# instance gets its own free-tier quota). Gitignored; loaded last so it wins.
_agent_name = os.getenv("HOSPITAL_AGENT_NAME")
if _agent_name:
    _secret_file = Path(__file__).parent / f".env.{_agent_name}"
    if _secret_file.exists():
        load_dotenv(_secret_file, override=True)

import uvicorn
from a2a.server.tasks import DatabaseTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from agent import create_agent


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Rejects A2A requests without the shared bearer token.

    Agent card discovery (GET /.well-known/*) stays public; everything else
    requires "Authorization: Bearer <A2A_AUTH_TOKEN>".
    """

    def __init__(self, app, token: str):
        super().__init__(app)
        self._expected = f"Bearer {token}"

    async def dispatch(self, request, call_next):
        if request.method == "GET" and request.url.path.startswith("/.well-known/"):
            return await call_next(request)
        provided = request.headers.get("authorization") or ""
        try:
            authorized = secrets.compare_digest(provided, self._expected)
        except TypeError:
            authorized = False
        if not authorized:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def _data_dir() -> Path:
    # Outside the repo: SQLite files must not live in an iCloud-synced tree.
    path = Path(os.getenv("AMBULANCE_DATA_DIR", "~/.ambulance")).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    agent_name = os.getenv("HOSPITAL_AGENT_NAME")
    hospital_name = os.getenv("HOSPITAL_NAME", agent_name or "병원")
    if not agent_name:
        logger.error(
            "HOSPITAL_AGENT_NAME is not set. Start with a profile, e.g. "
            "HOSPITAL_PROFILE=configs/대전선병원.env uv run ."
        )
        raise SystemExit(1)
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI") != "TRUE":
        logger.error("GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.")
        raise SystemExit(1)

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "10004"))

    agent_card = AgentCard(
        name=agent_name,
        description=f"{hospital_name}의 응급환자 수용 가능 여부(의료진/수술실/베드)를 확인하는 에이전트",
        url=f"http://{host}:{port}/",
        version="2.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="er-acceptance-check",
                name="응급환자 수용 가능 여부 확인",
                description="필요 진료과 기준으로 수술가능 의사·수술실·베드를 확인해 수용 여부를 판단",
                tags=["hospital", "emergency", "availability"],
                examples=["신경외과 의사가 필요한 응급환자입니다. 수용 가능 여부를 확인해주세요."],
            )
        ],
    )

    data_dir = _data_dir()
    adk_agent = create_agent()
    runner = Runner(
        app_name=agent_name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=DatabaseSessionService(
            f"sqlite+aiosqlite:///{data_dir}/{agent_name}_sessions.db"
        ),
        memory_service=InMemoryMemoryService(),
    )

    task_engine = create_async_engine(
        f"sqlite+aiosqlite:///{data_dir}/{agent_name}_tasks.db"
    )

    @asynccontextmanager
    async def lifespan(app):
        yield
        await task_engine.dispose()

    app = to_a2a(
        adk_agent,
        host=host,
        port=port,
        agent_card=agent_card,
        runner=runner,
        task_store=DatabaseTaskStore(engine=task_engine),
        lifespan=lifespan,
    )

    a2a_auth_token = os.getenv("A2A_AUTH_TOKEN")
    if a2a_auth_token:
        app.add_middleware(BearerAuthMiddleware, token=a2a_auth_token)
    else:
        logger.warning(
            "A2A_AUTH_TOKEN is not set - this A2A endpoint accepts "
            "unauthenticated requests. Set the same A2A_AUTH_TOKEN on every "
            "agent before handling real patient data."
        )

    logger.info("Starting %s on %s:%s (data dir: %s)", agent_name, host, port, data_dir)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
