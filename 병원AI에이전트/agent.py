"""Parameterized hospital agent - one codebase, N hospitals via env profiles."""

import os

from google.adk.agents import LlmAgent

from capacity import check_capacity
from prompt import build_prompt
from slack_tool import slack_post_message


def create_agent() -> LlmAgent:
    """Constructs the ADK agent for the configured hospital."""
    agent_name = os.getenv("HOSPITAL_AGENT_NAME")
    if not agent_name:
        raise ValueError("HOSPITAL_AGENT_NAME is not set (load a profile from configs/)")
    return LlmAgent(
        model=os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite"),
        name=agent_name,
        instruction=build_prompt(),
        tools=[check_capacity, slack_post_message],
    )
