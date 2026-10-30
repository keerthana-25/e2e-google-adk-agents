from google.adk.agents import LlmAgent

from ..config import FAST_MODEL
from ..prompts import INTENT_PROMPT
from ..schemas import IntentExtractionResult

intent_extractor_agent = LlmAgent(
    name="intent_extractor_agent",
    model=FAST_MODEL,
    description="Extracts country, industry and conversation stage from the user message.",
    instruction=INTENT_PROMPT,
    output_schema=IntentExtractionResult,
    output_key="intent_result",
)
