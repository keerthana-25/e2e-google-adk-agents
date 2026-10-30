"""Root agent: routes to the review pipeline or the fix pipeline."""

from google.adk.agents import Agent

from .config import WORKER_MODEL
from .sub_agents.fix_pipeline import code_fix_pipeline
from .sub_agents.review_pipeline import code_review_pipeline

root_agent = Agent(
    name="CodeReviewAssistant",
    model=WORKER_MODEL,
    description="Python code review assistant: reviews code and can fix the issues it finds.",
    instruction="""You are a Python code review assistant.

- When the user sends Python code to review, transfer to CodeReviewPipeline. Do not change
  the code. After the review, if the style score is below 100, tests failed or critical
  issues were found, ask: "Would you like me to fix these issues?"
- If the user says yes / asks for fixes after a review, transfer to CodeFixPipeline.
- For general questions ("what can you do?"), answer briefly yourself. Don't run the
  pipelines without code.""",
    sub_agents=[code_review_pipeline, code_fix_pipeline],
)
