import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StdioServerParameters,
)
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

load_dotenv()

from prompt import MAP_MCP_PROMPT
from slack_tool import slack_post_message

PATH_TO_YOUR_MCP_SERVER_SCRIPT = str((Path(__file__).parent / "server.js").resolve())


def create_agent() -> LlmAgent:
    """Constructs the ADK agent for 교통AI에이전트."""
    return LlmAgent(
        model=os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite"),
        name="교통AI에이전트",
        instruction=MAP_MCP_PROMPT,
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="node",
                        args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT],
                    ),
                    timeout=30,
                ),
            ),
            slack_post_message,
        ],
    )
