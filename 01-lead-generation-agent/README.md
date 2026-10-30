# (a) Deep Research Agent for Lead Generation

Multi-agent deep research system built with Google ADK. Given a target **country + industry**
(e.g. "fintech in Thailand"), it:

1. finds `k` foreign companies that **already invested** there,
2. researches each one **in parallel** to find its *pre-investment signals*
   (hiring, partnerships, licenses, funding, public statements),
3. synthesizes the **common patterns**, and
4. uses those patterns to find `m` **new leads** (companies that look like they will invest next),
   researches each lead in parallel, and writes a sourced report.

Based on: [Google Cloud blog – deep research agent with ADK](https://cloud.google.com/blog/products/ai-machine-learning/build-a-deep-research-agent-with-google-adk)
and [MagnIeeT/leadGenerationAgentADK](https://github.com/MagnIeeT/leadGenerationAgentADK).

## Architecture

```
lead_generation_root (LlmAgent)
 ├─ AgentTool: intent_extractor_agent      -> country, industry, stage (output_schema)
 ├─ FunctionTool: set_research_size(k, m)
 ├─ AgentTool: pattern_discovery_agent (SequentialAgent)
 │    CompanyFinder (google_search) -> CompanyFormatter (JSON schema)
 │    -> ResearchOrchestrator (custom BaseAgent, builds a ParallelAgent at runtime)
 │         └─ per company: Validator -> SignalSearcher (google_search) -> SignalFormatter
 │    -> FindingsConsolidator (custom BaseAgent) -> PatternSynthesizer
 └─ AgentTool: lead_generation_agent (SequentialAgent)
      LeadFinder (google_search) -> LeadFormatter
      -> LeadResearchOrchestrator (ParallelAgent at runtime)
           └─ per lead: LeadSignalAnalyzer (google_search) -> LeadSignalFormatter
      -> LeadConsolidator -> ReportCompiler
```

Key ADK concepts used:
- **AgentTool** – sub-workflows exposed to the root agent as tools.
- **SequentialAgent / ParallelAgent** – deterministic workflow + fan-out research.
- **Custom BaseAgent** – builds one pipeline per company *at runtime* (number of companies is
  only known after the search) and writes state via `EventActions(state_delta=...)`.
- **Researcher + formatter split** – `google_search` can't be combined with `output_schema`,
  so every search agent writes free text and a cheap formatter agent converts it to a Pydantic schema.
- **Session state** – agents talk to each other through state keys
  (`companies_found`, `validation_i`, `findings_i`, `discovered_patterns`, `leads_found`, ...).
- **Callbacks** – `before_agent_callback` initializes state, `after_tool_callback` moves the
  conversation stage forward.

## Files

| File | What it does |
|---|---|
| `lead_generation_agent/agent.py` | root agent, `set_research_size` tool, callbacks |
| `lead_generation_agent/sub_agents/intent_extractor.py` | structured intent extraction |
| `lead_generation_agent/sub_agents/pattern_discovery.py` | pattern discovery workflow |
| `lead_generation_agent/sub_agents/lead_generation.py` | lead generation workflow |
| `lead_generation_agent/prompts.py` | all prompts |
| `lead_generation_agent/schemas.py` | Pydantic output schemas |

## Run

```bash
cd 01-lead-generation-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp lead_generation_agent/.env.example lead_generation_agent/.env   # add your GOOGLE_API_KEY
adk web            # open http://localhost:8000 and pick lead_generation_agent
```

Example conversation:
1. `Find fintech companies that could expand into Thailand`
2. agent asks how many companies to study → `3`
3. agent shows the discovered patterns and asks to continue → `yes, find leads`
4. agent asks how many leads → `3` → final lead report with source URLs

Use the **Events** tab in `adk web` to show each sub-agent running (parallel branches,
state deltas, google_search calls).

## Notes / differences from the reference repo
- The reference used `get_user_choice` (a long-running tool) to ask for `k` and `m`; here the
  agent asks in chat and saves the answer with a small `set_research_size` function tool.
- Custom agents write state through `state_delta` events instead of mutating
  `ctx.session.state` directly, so the values persist and are forwarded back through `AgentTool`.
- The validator checks each company against the criteria using the data found by the search
  agent (it has no search tool of its own, since it uses `output_schema`).
- Results depend on Google Search grounding; always check the cited URLs.
