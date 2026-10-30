"""Helpers shared by pattern discovery and lead generation."""

import json
from datetime import datetime

from google.adk.events import Event, EventActions
from google.genai.types import Content, Part


def to_json(obj) -> str:
    return json.dumps(obj, indent=2)


def current_year() -> int:
    return datetime.now().year


def state_event(author: str, text: str, delta: dict) -> Event:
    """Event that writes `delta` into session state.

    Custom BaseAgents must write state through state_delta (not by mutating
    ctx.session.state) so it is persisted and forwarded back through AgentTool.
    """
    return Event(
        author=author,
        content=Content(role="model", parts=[Part(text=text)]),
        actions=EventActions(state_delta=delta),
    )
