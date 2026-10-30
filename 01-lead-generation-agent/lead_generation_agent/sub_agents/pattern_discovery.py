"""Pattern discovery workflow.

CompanyFinder -> CompanyFormatter -> ResearchOrchestrator (parallel per company:
Validator -> SignalSearcher -> SignalFormatter) -> Consolidator -> PatternSynthesizer
"""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import google_search

from ..config import ADVANCED_MODEL, FAST_MODEL
from ..prompts import (
    COMPANY_FINDER_PROMPT,
    COMPANY_FORMATTER_PROMPT,
    PATTERN_SYNTHESIZER_PROMPT,
    findings_formatter_prompt,
    signal_searcher_prompt,
    validator_prompt,
)
from ..schemas import CompanyList, ResearchFindings, ValidationResult
from .common import current_year, state_event, to_json

# google_search can't be combined with output_schema, so every search agent writes
# free text and a separate formatter agent turns it into JSON.
company_finder_agent = LlmAgent(
    name="CompanyFinderAgent",
    model=ADVANCED_MODEL,
    instruction=COMPANY_FINDER_PROMPT,
    tools=[google_search],
    output_key="company_finder_output",
)

company_formatter_agent = LlmAgent(
    name="CompanyFormatterAgent",
    model=FAST_MODEL,
    instruction=COMPANY_FORMATTER_PROMPT,
    output_schema=CompanyList,
    output_key="companies_found",
)


class ResearchOrchestratorAgent(BaseAgent):
    """Builds one research pipeline per company and runs them in parallel."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        companies = (state.get("companies_found") or {}).get("companies", [])
        if not companies:
            yield state_event(self.name, "No companies to research.", {"num_companies": 0})
            return

        country, industry = state.get("country", ""), state.get("industry", "")
        pipelines = []
        for i, company in enumerate(companies):
            cj = to_json(company)
            pipelines.append(
                SequentialAgent(
                    name=f"CompanyResearch_{i}",
                    sub_agents=[
                        LlmAgent(
                            name=f"Validator_{i}",
                            model=FAST_MODEL,
                            # callable instruction = no {state} injection, so the JSON
                            # braces in the company data are safe
                            instruction=lambda _ctx, cj=cj: validator_prompt(
                                cj, country, industry, current_year()
                            ),
                            output_schema=ValidationResult,
                            output_key=f"validation_{i}",
                        ),
                        LlmAgent(
                            name=f"SignalSearcher_{i}",
                            model=ADVANCED_MODEL,
                            instruction=lambda _ctx, cj=cj: signal_searcher_prompt(cj, country),
                            tools=[google_search],
                            output_key=f"signal_text_{i}",
                        ),
                        LlmAgent(
                            name=f"SignalFormatter_{i}",
                            model=FAST_MODEL,
                            instruction=findings_formatter_prompt(f"signal_text_{i}"),
                            output_schema=ResearchFindings,
                            output_key=f"findings_{i}",
                        ),
                    ],
                )
            )

        yield state_event(self.name, f"Researching {len(companies)} companies.",
                          {"num_companies": len(companies)})
        async for event in ParallelAgent(name="ParallelCompanyResearch",
                                         sub_agents=pipelines).run_async(ctx):
            yield event


class FindingsConsolidatorAgent(BaseAgent):
    """Joins the per-company results into one text block for the synthesizer."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        companies = (state.get("companies_found") or {}).get("companies", [])
        blocks = []
        for i, company in enumerate(companies):
            v = state.get(f"validation_{i}") or {}
            f = state.get(f"findings_{i}") or {}
            blocks.append(
                f"--- {company.get('company_name')} ---\n"
                f"Validation: {'VALID' if v.get('is_valid') else 'INVALID'} ({v.get('reasoning', '')})\n"
                f"Signals: {f.get('summary', 'n/a')}\n"
                f"Sources: {', '.join(f.get('sources', []))}"
            )
        text = "\n\n".join(blocks) or "No companies were found."
        yield state_event(self.name, "Findings consolidated.", {"all_research_findings": text})


pattern_synthesizer_agent = LlmAgent(
    name="PatternSynthesizerAgent",
    model=ADVANCED_MODEL,
    instruction=PATTERN_SYNTHESIZER_PROMPT,
    output_key="discovered_patterns",
)

pattern_discovery_agent = SequentialAgent(
    name="pattern_discovery_agent",
    description="Finds companies that already invested in the target market, researches "
                "their pre-investment signals in parallel and synthesizes common patterns.",
    sub_agents=[
        company_finder_agent,
        company_formatter_agent,
        ResearchOrchestratorAgent(name="ResearchOrchestrator"),
        FindingsConsolidatorAgent(name="FindingsConsolidator"),
        pattern_synthesizer_agent,
    ],
)
