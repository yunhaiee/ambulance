from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import os
import json
from dotenv import load_dotenv  # Add this import

PATH_TO_YOUR_MCP_SERVER_SCRIPT = str((Path(__file__).parent / "server.js").resolve())
from prompt import MAP_MCP_PROMPT

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if SLACK_BOT_TOKEN is None:
    raise ValueError("SLACK_BOT_TOKEN is not set")

SLACK_TEAM_ID = os.getenv("SLACK_TEAM_ID")
if SLACK_TEAM_ID is None:
    raise ValueError("SLACK_TEAM_ID is not set")

def create_agent() -> LlmAgent:
    """Constructs the ADK agent for 교통AI에이전트."""
    return LlmAgent(
        model="gemini-2.5-flash-lite-preview-06-17",
        name="교통AI에이전트",
        instruction=MAP_MCP_PROMPT,
        tools=[
            MCPToolset(
                connection_params=StdioServerParameters(
                    command="node",  # ✅ Node.js 사용
                    args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT],
                ),
            ),
            MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-slack"],
                    env={
                        "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
                        "SLACK_TEAM_ID": SLACK_TEAM_ID
                    },   
                )
            )
        ],
    )
