import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

load_dotenv()

from _lang import make_instruction
from insurance_tool import send_insurance_request
from prompt import INSURANCE_PROMPT


def create_agent() -> LlmAgent:
    """Constructs the ADK agent for insurance_agent."""
    return LlmAgent(
        model=os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite"),
        name="insurance_agent",
        instruction=make_instruction(INSURANCE_PROMPT),
        tools=[send_insurance_request],
    )
