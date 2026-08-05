"""Briefing node: formats the Analyst's findings into a SITREP.

Borrows the military intelligence-briefing format (Situation / Assessment /
Recommendation) - a deliberate positioning choice per CLAUDE.md - written in
plain business English. Uses structured output (Briefing pydantic model) so
the API response shape is reliable rather than parsed out of free text.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from agent.config import load_settings
from agent.state import Briefing, GraphState

_SYSTEM_PROMPT = """You are the Briefing agent. You receive an internal \
analysis (already grounded in retrieved data, already fact-checked) and must \
format it into a SITREP - Situation, Assessment, Recommendation - in plain \
business English. Do not add new facts or numbers that weren't in the \
analysis - if a figure or claim isn't in the analysis you were given, leave \
it out, even if it sounds like something you already know to be true. If \
the analysis noted missing data, reflect that in no_data_warning rather \
than glossing over it.

sources must be a list of separate short strings, one per source (e.g. \
["bigquery:marts.country_risk_assessment", "neo4j depot capacity data"]) - \
NOT one combined comma-separated sentence.

Keep every field tight: 2-4 sentences each for situation, assessment, and \
recommendation. This is a briefing, not a report - be concise so the full \
response fits comfortably within the output budget."""

_RETRY_NUDGE = """Your previous attempt did not finish - it likely ran too \
long and got cut off before completing all fields (situation, assessment, \
recommendation, sources are all required). This time, be noticeably more \
concise: 1-2 sentences per field, not 2-4. Every field must still be \
present, even if brief."""


def _get_llm(settings):
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=4096,
    ).with_structured_output(Briefing)


def brief(state: GraphState) -> dict:
    settings = load_settings()
    analysis = state.get("analysis", "")

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Analysis:\n{analysis}"),
    ]

    try:
        result = _get_llm(settings).invoke(messages)
    except ValidationError:
        # Most likely cause: the model's response got cut off mid-way
        # (missing required fields) rather than a real data problem. One
        # retry with an explicit "be shorter" nudge resolves this in
        # practice - seen in eval runs where one case out of several
        # verbose ones needed it. If it fails twice, let the error
        # propagate rather than silently returning a partial briefing.
        retry_messages = messages + [
            HumanMessage(content=_RETRY_NUDGE),
        ]
        result = _get_llm(settings).invoke(retry_messages)

    return {"briefing": result}
