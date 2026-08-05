"""LLM-as-judge faithfulness check - a hand-rolled, lighter-weight version
of RAGAS-style faithfulness scoring (see the original portfolio plan).
Given the retrieved bundle and the final briefing, asks Claude whether the
briefing's claims are actually supported by the bundle. Separate from and
in addition to the structural (keyword) checks in run_evals.py - this
catches things like subtly overstated confidence that a keyword match
can't."""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent.config import load_settings

_SYSTEM_PROMPT = """You are grading a briefing for faithfulness: does every \
factual claim in the briefing trace back to something actually present in \
the retrieved data bundle it was generated from? This is not about whether \
the briefing is well-written - only whether it invents or overstates \
anything the bundle doesn't support.

Common acceptable inference (not a violation): stating a capacity_status or \
risk_level that IS in the bundle, describing what it implies in plain \
language, or noting when a source wasn't found. A violation is inventing a \
number, a country, a depot, or a causal claim that isn't in the bundle."""


class JudgeVerdict(BaseModel):
    faithful: bool = Field(description="True if no unsupported claims were found.")
    notes: str = Field(description="1-2 sentences: what was checked, and why.")


def judge_faithfulness(retrieved_bundle: dict, briefing_text: str) -> JudgeVerdict:
    settings = load_settings()
    llm = ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=512,
    ).with_structured_output(JudgeVerdict)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Retrieved bundle:\n{json.dumps(retrieved_bundle, indent=2, default=str)}\n\n"
                f"Briefing under review:\n{briefing_text}"
            )
        ),
    ]
    return llm.invoke(messages)
