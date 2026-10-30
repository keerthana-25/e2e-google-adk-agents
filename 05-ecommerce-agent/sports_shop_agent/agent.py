"""Finn - GenAI Sports e-commerce agent (ADK + MCP Toolbox for Databases + PostgreSQL)."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.toolbox_toolset import ToolboxToolset

from .prompt import INSTRUCTION

load_dotenv()

MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
TOOLBOX_URL = os.getenv("MCP_TOOLBOX_URL", "http://127.0.0.1:5000")
TOOLSET = "shop_toolset"


def build_agent(user_email: str) -> Agent:
    """Creates the agent for one signed-in user.

    `user_email` is bound into every tool that has that parameter, so the model never
    sees it and can't read or change another customer's cart/orders.
    """
    headers = None
    if os.getenv("TOOLBOX_USE_ID_TOKEN", "").lower() == "true":
        # toolbox deployed as a private Cloud Run service -> send a Google ID token
        from toolbox_core.auth_methods import aget_google_id_token
        headers = {"Authorization": aget_google_id_token(TOOLBOX_URL)}

    toolbox = ToolboxToolset(
        server_url=TOOLBOX_URL,
        toolset_name=TOOLSET,
        bound_params={"user_email": user_email},
        additional_headers=headers,
    )
    return Agent(
        name="finn",
        model=MODEL,
        description="GenAI Sports shopping assistant.",
        instruction=INSTRUCTION,
        tools=[toolbox],
    )


# Used by `adk web` for local testing: acts as a fixed demo user from the sample data.
root_agent = build_agent(os.getenv("DEMO_USER_EMAIL", "alex@example.com"))
