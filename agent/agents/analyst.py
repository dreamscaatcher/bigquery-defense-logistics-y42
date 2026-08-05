"""Analyst node: reasons over retrieved facts only. No new tool calls.

Guardrail is enforced in the system prompt, not just aspirationally: state
only conclusions the retrieved bundle supports, cite the actual numbers,
flag cross-system correlations (BigQuery risk x Neo4j capacity), and say so
plainly when something wasn't found rather than filling the gap.
"""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agent.config import load_settings
from agent.state import GraphState

_SYSTEM_PROMPT = """You are the Analyst agent in a supply-chain risk intelligence \
pipeline. You are given a JSON bundle of retrieved facts - country risk data \
from BigQuery, depot capacity and route utilization from a Neo4j supply-network \
graph, and grounding excerpts from the project's own methodology docs.

Rules:
1. State only conclusions the retrieved data actually supports. Do not infer \
   facts that aren't in the bundle.
2. Cite the specific numbers behind every claim (e.g. "avg_event_sentiment of \
   -0.42", not "negative sentiment").
3. Explicitly flag cross-system correlations - e.g. a country with \
   risk_level MEDIUM or HIGH whose depot is OVER_CAPACITY or NEAR_CAPACITY is \
   a compounding risk worth calling out.
4. If a source has found=False or is missing, say so plainly instead of \
   guessing. A partial answer with a clear gap is better than a filled-in one.
5. Use the methodology excerpts to caveat your assessment appropriately - \
   e.g. the risk model's held-out R^2 is 0.5464, not near-perfect; capacity \
   thresholds are heuristic classifications, not hard operational limits.

Write your analysis as plain text - a few short paragraphs. This is an \
internal reasoning step; a separate agent will format it into the final \
user-facing briefing."""


def analyze(state: GraphState) -> dict:
    settings = load_settings()
    llm = ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
    )

    retrieved = state.get("retrieved", {})
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Retrieved bundle:\n"
                f"{json.dumps(retrieved, indent=2, default=str)}\n\n"
                "Produce your analysis."
            )
        ),
    ]

    response = llm.invoke(messages)
    return {"analysis": response.content}
