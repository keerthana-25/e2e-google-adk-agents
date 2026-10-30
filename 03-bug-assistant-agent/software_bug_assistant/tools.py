"""Tools for the software bug assistant.

1. Function tool      -> get_current_date
2. Built-in tool      -> google_search (wrapped in an AgentTool)
3. Third-party tool   -> StackExchange via LangChain
4. MCP tool (DB)      -> MCP Toolbox for Databases (tickets in PostgreSQL)
5. MCP tool (remote)  -> GitHub's official MCP server (read-only)
"""

import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

load_dotenv()
log = logging.getLogger(__name__)

MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")


# ---- 1. function tool ----
def get_current_date() -> dict:
    """Returns today's date as YYYY-MM-DD."""
    return {"current_date": datetime.now().strftime("%Y-%m-%d")}


# ---- 2. built-in google search (needs its own agent, it can't share an agent with other tools) ----
search_agent = Agent(
    model=MODEL,
    name="search_agent",
    description="Searches the web (Google Search) for known issues, CVEs, docs.",
    instruction="You are a Google Search specialist. Answer using search results and include source links.",
    tools=[google_search],
)
search_tool = AgentTool(agent=search_agent)


# ---- 3. LangChain StackExchange tool ----
def _stack_exchange_tool():
    try:
        from google.adk.tools.langchain_tool import LangchainTool
        from langchain_community.tools import StackExchangeTool
        from langchain_community.utilities import StackExchangeAPIWrapper

        return LangchainTool(StackExchangeTool(api_wrapper=StackExchangeAPIWrapper()))
    except Exception as e:  # langchain/stackapi not installed
        log.warning("StackExchange tool disabled: %s", e)
        return None


stack_exchange_tool = _stack_exchange_tool()


# ---- 4. MCP Toolbox for Databases (served over MCP streamable HTTP) ----
TOOLBOX_URL = os.getenv("MCP_TOOLBOX_URL", "http://127.0.0.1:5000")
toolbox_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url=f"{TOOLBOX_URL}/mcp/tickets_toolset"),
)


# ---- 5. GitHub remote MCP server (read-only endpoint + only the tools we need) ----
def _github_mcp():
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        log.warning("GITHUB_PERSONAL_ACCESS_TOKEN not set, GitHub MCP tools disabled")
        return None
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://api.githubcopilot.com/mcp/readonly",
            headers={"Authorization": f"Bearer {token}"},
        ),
        tool_filter=[
            "search_repositories",
            "search_issues",
            "list_issues",
            "issue_read",
            "list_pull_requests",
            "pull_request_read",
        ],
    )


github_mcp = _github_mcp()
