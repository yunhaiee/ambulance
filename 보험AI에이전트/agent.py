import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

load_dotenv()

from prompt import NOTION_PROMPT
from slack_tool import slack_post_message


def create_agent() -> LlmAgent:
    """Constructs the ADK agent for 보험AI에이전트."""
    return LlmAgent(
        model=os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite"),
        name="보험AI에이전트",
        instruction=NOTION_PROMPT,
        tools=[slack_post_message],
    )
