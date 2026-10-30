"""Root agent for the lead generation deep research agent."""

from datetime import datetime
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .config import ADVANCED_MODEL
from .prompts import ROOT_PROMPT
from .sub_agents.intent_extractor import intent_extractor_agent
from .sub_agents.lead_generation import lead_generation_agent
from .sub_agents.pattern_discovery import pattern_discovery_agent


def set_research_size(tool_context: ToolContext, k: Optional[int] = None,
                      m: Optional[int] = None) -> dict:
    """Saves how many companies to study (k) and/or how many leads to find (m).

    Args:
        k: number of already-invested companies to analyze for patterns (1-10).
        m: number of new leads to find (1-10).
    """
    if k is not None:
        tool_context.state["k"] = max(1, min(int(k), 10))
    if m is not None:
        tool_context.state["m"] = max(1, min(int(m), 10))
    return {"k": tool_context.state.get("k"), "m": tool_context.state.get("m")}


def init_state(callback_context: CallbackContext):
    s = callback_context.state
    s["current_year"] = datetime.now().year
    for key, default in [("country", ""), ("industry", ""), ("stage", "initial"),
                         ("k", ""), ("m", ""), ("has_patterns", False)]:
        if key not in s:
            s[key] = default
    return None


def after_tool(tool, args, tool_context: ToolContext, tool_response):
    """Move the conversation stage forward based on which tool just ran."""
    s = tool_context.state
    if tool.name == intent_extractor_agent.name:
        result = tool_response if isinstance(tool_response, dict) else (s.get("intent_result") or {})
        if result.get("country"):
            s["country"] = result["country"]
        if result.get("industry"):
            s["industry"] = result["industry"]
        if result.get("stage"):
            s["stage"] = result["stage"]
    elif tool.name == pattern_discovery_agent.name and s.get("discovered_patterns"):
        s["has_patterns"] = True
        s["stage"] = "patterns_shown"
    elif tool.name == lead_generation_agent.name:
        s["stage"] = "follow_up"
    return None


root_agent = LlmAgent(
    name="lead_generation_root",
    model=ADVANCED_MODEL,
    instruction=ROOT_PROMPT,
    tools=[
        AgentTool(agent=intent_extractor_agent),
        set_research_size,
        AgentTool(agent=pattern_discovery_agent),
        AgentTool(agent=lead_generation_agent),
    ],
    before_agent_callback=init_state,
    after_tool_callback=after_tool,
)
