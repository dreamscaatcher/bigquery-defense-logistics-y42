"""Briefing node: formats the Analyst's findings into a SITREP.

Borrows the military intelligence-briefing format (Situation / Assessment /
Recommendation) - a deliberate positioning choice per CLAUDE.md - written in
plain business English. Uses structured output (Briefing pydantic model) so
the API response shape is reliable rather than parsed out of free text.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agent.config import load_settings
from agent.state import Briefing, GraphState

_SYSTEM_PROMPT = """You are the Briefing agent. You receive an internal \
analysis (already grounded in retrieved data, already fact-checked) and must \
format it into a SITREP - Situation, Assessment, Recommendation - in plain \
business English. Do not add new facts or numbers that weren't in the \
analysis. If the analysis noted missing data, reflect that in \
no_data_warning rather than glossing over it. List every source mentioned in \
the analysis in the sources field."""


def brief(state: GraphState) -> dict:
    settings = load_settings()
    llm = ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
    ).with_structured_output(Briefing)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Analysis:\n{state.get('analysis', '')}"),
    ]

    result = llm.invoke(messages)
    return {"briefing": result}
