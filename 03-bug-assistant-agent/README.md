# (c) MCP Tools Based Agent – Software Bug Assistant

A bug triage assistant for a fictional coffee machine company (QuantumRoast). It can search
for duplicate tickets, create/update tickets, look up GitHub issues and PRs, search
StackOverflow and Google.

Based on: [Tools make an agent: from zero to assistant with ADK](https://cloud.google.com/blog/topics/developers-practitioners/tools-make-an-agent-from-zero-to-assistant-with-adk)
and the [software-bug-assistant ADK sample](https://github.com/google/adk-samples/tree/main/python/agents/software-bug-assistant).

## Tools

| Type | Tool | How |
|---|---|---|
| Function tool | `get_current_date` | plain Python function |
| Built-in tool | Google Search | `google_search` inside a `search_agent`, exposed with `AgentTool` |
| Third-party tool | StackExchange | LangChain `StackExchangeTool` wrapped with `LangchainTool` |
| **MCP tool (database)** | tickets DB (9 tools) | **MCP Toolbox for Databases** → PostgreSQL, connected with `MCPToolset` over streamable HTTP (`/mcp/tickets_toolset`) |
| **MCP tool (remote)** | GitHub | GitHub's official remote MCP server (`/mcp/readonly`), `MCPToolset` + `tool_filter` |

```
software_bug_assistant (LlmAgent)
 ├─ get_current_date
 ├─ search_agent (AgentTool -> google_search)
 ├─ stack_exchange (LangchainTool)
 ├─ MCPToolset ──HTTP──> MCP Toolbox :5000 ──SQL──> PostgreSQL (tickets)
 └─ MCPToolset ──HTTP──> api.githubcopilot.com/mcp/readonly
```

Ticket tools (defined in `mcp-toolbox/tools.yaml`): `search-tickets`, `get-ticket-by-id`,
`get-tickets-by-assignee`, `get-tickets-by-status`, `get-tickets-by-priority`,
`get-tickets-by-date-range`, `update-ticket-priority`, `update-ticket-status`, `create-new-ticket`.

## Run

```bash
cd 03-bug-assistant-agent

# 1. database (Docker) – creates the tickets table + 8 sample tickets
docker compose up -d

# 2. MCP Toolbox for Databases on :5000 (separate terminal, needs Node for npx)
./run_toolbox.sh

# 3. agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp software_bug_assistant/.env.example software_bug_assistant/.env  # GOOGLE_API_KEY, GITHUB_PERSONAL_ACCESS_TOKEN
adk web
```

Example prompts:
- `Any issues around the login page freezing?`
- `What tickets were opened in the last week?`
- `Show me all P0 tickets` / `What is samuel.green working on?`
- `Customers say the grinder jams with oily beans. Create a ticket.` (agent checks duplicates first)
- `Set ticket 5 to In Progress`
- `Are there open issues in the google/adk-python repo about MCPToolset?` (GitHub MCP)
- `Search StackOverflow for "SMTP timeout python smtplib"`

## Notes / differences from the reference
- The reference used Cloud SQL + pgvector with `embedding('text-embedding-005', ...)` for
  `search-tickets`. That function only exists in Cloud SQL/AlloyDB, so this version uses
  PostgreSQL **full-text search** (match any word, ranked with `ts_rank`) and runs on plain local Postgres.
- `tools.yaml` uses the current **flat config format** of MCP Toolbox v1.x
  (`kind: source / tool / group`); the reference used the old `sources:/tools:/toolsets:` format.
- GitHub MCP tool names follow the current server (`issue_read`, `pull_request_read`).
- If `GITHUB_PERSONAL_ACCESS_TOKEN` is not set or StackExchange is unreachable, those tools are
  skipped and the agent still starts.
