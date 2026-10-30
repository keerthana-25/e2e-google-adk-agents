"""Lead generation workflow.

LeadFinder -> LeadFormatter -> LeadResearchOrchestrator (parallel per lead:
SignalAnalyzer -> SignalFormatter) -> Consolidator -> ReportCompiler
"""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import google_search

from ..config import ADVANCED_MODEL, FAST_MODEL
from ..prompts import (
    LEAD_FINDER_PROMPT,
    LEAD_FORMATTER_PROMPT,
    REPORT_COMPILER_PROMPT,
    findings_formatter_prompt,
    lead_signal_prompt,
)
from ..schemas import LeadList, ResearchFindings
from .common import state_event, to_json

lead_finder_agent = LlmAgent(
    name="LeadFinderAgent",
    model=ADVANCED_MODEL,
    instruction=LEAD_FINDER_PROMPT,
    tools=[google_search],
    output_key="lead_finder_output",
)

lead_formatter_agent = LlmAgent(
    name="LeadFormatterAgent",
    model=FAST_MODEL,
    instruction=LEAD_FORMATTER_PROMPT,
    output_schema=LeadList,
    output_key="leads_found",
)


class LeadResearchOrchestratorAgent(BaseAgent):
    """Runs one signal-analysis pipeline per lead, in parallel."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        leads = (state.get("leads_found") or {}).get("leads", [])
        if not leads:
            yield state_event(self.name, "No leads to analyze.", {"num_leads": 0})
            return

        patterns = state.get("discovered_patterns", "")
        pipelines = []
        for i, lead in enumerate(leads):
            lj = to_json(lead)
            pipelines.append(
                SequentialAgent(
                    name=f"LeadResearch_{i}",
                    sub_agents=[
                        LlmAgent(
                            name=f"LeadSignalAnalyzer_{i}",
                            model=ADVANCED_MODEL,
                            instruction=lambda _ctx, lj=lj: lead_signal_prompt(lj, patterns),
                            tools=[google_search],
                            output_key=f"lead_signal_text_{i}",
                        ),
                        LlmAgent(
                            name=f"LeadSignalFormatter_{i}",
                            model=FAST_MODEL,
                            instruction=findings_formatter_prompt(f"lead_signal_text_{i}"),
                            output_schema=ResearchFindings,
                            output_key=f"lead_findings_{i}",
                        ),
                    ],
                )
            )

        yield state_event(self.name, f"Analyzing {len(leads)} leads.", {"num_leads": len(leads)})
        async for event in ParallelAgent(name="ParallelLeadResearch",
                                         sub_agents=pipelines).run_async(ctx):
            yield event


class LeadConsolidatorAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        leads = (state.get("leads_found") or {}).get("leads", [])
        blocks = []
        for i, lead in enumerate(leads):
            f = state.get(f"lead_findings_{i}") or {}
            blocks.append(
                f"--- {lead.get('company_name')} ({lead.get('country_of_origin')}) ---\n"
                f"Signals: {f.get('summary', 'n/a')}\n"
                f"Sources: {', '.join(f.get('sources', []))}"
            )
        text = "\n\n".join(blocks) or "No leads were found."
        yield state_event(self.name, "Lead findings consolidated.", {"all_lead_findings": text})


report_compiler_agent = LlmAgent(
    name="ReportCompilerAgent",
    model=ADVANCED_MODEL,
    instruction=REPORT_COMPILER_PROMPT,
    output_key="lead_report",
)

lead_generation_agent = SequentialAgent(
    name="lead_generation_agent",
    description="Uses the discovered patterns to find new companies likely to invest, "
                "researches each one in parallel and compiles a lead report.",
    sub_agents=[
        lead_finder_agent,
        lead_formatter_agent,
        LeadResearchOrchestratorAgent(name="LeadResearchOrchestrator"),
        LeadConsolidatorAgent(name="LeadConsolidator"),
        report_compiler_agent,
    ],
)
