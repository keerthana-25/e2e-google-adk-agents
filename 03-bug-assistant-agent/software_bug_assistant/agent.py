from google.adk.agents import Agent

from .prompt import INSTRUCTION
from .tools import (
    MODEL,
    get_current_date,
    github_mcp,
    search_tool,
    stack_exchange_tool,
    toolbox_mcp,
)

tools = [get_current_date, search_tool, toolbox_mcp]
if stack_exchange_tool is not None:
    tools.append(stack_exchange_tool)
if github_mcp is not None:
    tools.append(github_mcp)

root_agent = Agent(
    model=MODEL,
    name="software_bug_assistant",
    description="Bug triage assistant with MCP tools for tickets DB and GitHub.",
    instruction=INSTRUCTION,
    tools=tools,
)
