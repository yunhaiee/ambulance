"""A2A server for 보험AI에이전트 (port 10005)."""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

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

AGENT_NAME = "보험AI에이전트"


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
    path = Path(os.getenv("AMBULANCE_DATA_DIR", "~/.ambulance")).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI") != "TRUE":
        logger.error("GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.")
        raise SystemExit(1)

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "10005"))

    agent_card = AgentCard(
        name=AGENT_NAME,
        description="An agent that verifies the insurance coverage of an emergency patient and contacts the insurance company",
        url=f"http://{host}:{port}/",
        version="2.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="insurance-verification",
                name="Insurance check of an emergency patient",
                description="Sends an urgent insurance verification request for an emergency patient to the insurer's Slack channel",
                tags=["insurance"],
                examples=["응급환자가 발생했는데 보험 여부 확인해줘. 이 환자의 생년월일은 2008년 1월 12일이고 이름은 이윤하야."],
            )
        ],
    )

    data_dir = _data_dir()
    adk_agent = create_agent()
    runner = Runner(
        app_name=AGENT_NAME,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=DatabaseSessionService(
            f"sqlite+aiosqlite:///{data_dir}/{AGENT_NAME}_sessions.db"
        ),
        memory_service=InMemoryMemoryService(),
    )

    task_engine = create_async_engine(
        f"sqlite+aiosqlite:///{data_dir}/{AGENT_NAME}_tasks.db"
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

    logger.info("Starting %s on %s:%s (data dir: %s)", AGENT_NAME, host, port, data_dir)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
