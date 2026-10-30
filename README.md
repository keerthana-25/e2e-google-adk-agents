# ADK Agents Assignment

Five agents built end-to-end with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/).

| # | Agent | Folder | Main ADK concepts |
|---|---|---|---|
| a | Deep research agent for lead generation | [`01-lead-generation-agent`](01-lead-generation-agent) | AgentTool, Sequential + Parallel agents, custom BaseAgent, google_search, output schemas, callbacks |
| b | Advanced tool agent using Gemini CLI as a tool | [`02-gemini-cli-agent`](02-gemini-cli-agent) | Function tool wrapping a CLI (headless Gemini CLI), Cloud Run |
| c | MCP tools based bug assistant | [`03-bug-assistant-agent`](03-bug-assistant-agent) | MCPToolset (MCP Toolbox for Databases + GitHub MCP), LangChain tool, built-in search |
| d | Production quality code review assistant | [`04-code-review-assistant`](04-code-review-assistant) | Sequential + Loop agents, code executor, deterministic tools, artifacts, escalation |
| e | Production quality e-commerce agent | [`05-ecommerce-agent`](05-ecommerce-agent) | ToolboxToolset with bound params, PostgreSQL, FastAPI backend, ID-token auth |

Each folder has its own README with architecture, setup, example prompts and notes on what
differs from the reference implementation.

**Video walkthrough:** _add YouTube link here_ (script in [`VIDEO_WALKTHROUGH.md`](VIDEO_WALKTHROUGH.md))

## Prerequisites

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) (or a GCP project with Vertex AI)
- Node.js 20+ (Gemini CLI for **b**, MCP Toolbox via `npx` for **c** and **e**)
- Docker (PostgreSQL for **c** and **e**)
- GitHub personal access token (GitHub MCP tools in **c**)

Tested with `google-adk==2.13.0`, MCP Toolbox for Databases `1.15.0`, Gemini CLI `0.66.0`.

## Quick start (any agent)

```bash
cd <agent-folder>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp <agent_package>/.env.example <agent_package>/.env    # fill in keys
adk web                                                  # http://localhost:8000
```

Agents **c** and **e** each start their own PostgreSQL on port 5432 and toolbox on port 5000,
so run one of them at a time (`docker compose down` before switching).

## Repo layout

```
01-lead-generation-agent/   lead_generation_agent/ (agent.py, sub_agents/, prompts.py, schemas.py)
02-gemini-cli-agent/        gemini_cli_agent/agent.py, Dockerfile, deploy.sh
03-bug-assistant-agent/     software_bug_assistant/, mcp-toolbox/tools.yaml, db/init.sql, docker-compose.yml
04-code-review-assistant/   code_review_assistant/ (agent.py, tools.py, sub_agents/), tests/, Dockerfile
05-ecommerce-agent/         sports_shop_agent/, server.py, mcp-toolbox/tools.yaml, db/init.sql, Dockerfile, deploy.sh
```

## References
- a: https://cloud.google.com/blog/products/ai-machine-learning/build-a-deep-research-agent-with-google-adk · https://github.com/MagnIeeT/leadGenerationAgentADK
- b: https://medium.com/@derrickchwong/combine-adk-gemini-cli-and-cloud-run-c5dea5118853 · https://github.com/derrickchwong/gemini-cli-on-adk
- c: https://cloud.google.com/blog/topics/developers-practitioners/tools-make-an-agent-from-zero-to-assistant-with-adk · https://github.com/google/adk-samples (software-bug-assistant)
- d: https://codelabs.developers.google.com/adk-code-reviewer-assistant · https://github.com/ayoisio/adk-code-review-assistant
- e: https://codelabs.developers.google.com/codelabs/sports-agent-adk-mcp-alloydb · https://github.com/mtoscano84/sports-agent-adk-mcp-alloydb
