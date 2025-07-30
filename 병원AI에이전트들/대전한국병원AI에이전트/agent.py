from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import os
import json
from dotenv import load_dotenv  # Add this import

# Load environment variables from .env file
load_dotenv()  # Add this line

from prompt import NOTION_PROMPT

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
if NOTION_API_KEY is None:
    raise ValueError("NOTION_API_KEY is not set")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if SLACK_BOT_TOKEN is None:
    raise ValueError("SLACK_BOT_TOKEN is not set")

SLACK_TEAM_ID = os.getenv("SLACK_TEAM_ID")
if SLACK_TEAM_ID is None:
    raise ValueError("SLACK_TEAM_ID is not set")

NOTION_MCP_HEADERS = json.dumps(
    {"Authorization": f"Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28"}
)

def create_agent() -> LlmAgent:
    """Constructs the ADK agent for 대전한국병원AI에이전트."""
    return LlmAgent(
        model="gemini-2.5-flash-lite-preview-06-17",
        name="대전한국병원AI에이전트",
        instruction=NOTION_PROMPT,
        tools=[
            MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@notionhq/notion-mcp-server"],
                    env={"OPENAPI_MCP_HEADERS": NOTION_MCP_HEADERS},   
                )
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
