"""LangGraph wiring: retriever -> analyst -> briefing -> END.

Linear for v1 - no loops or retries. If eval results later show the
Retriever needs to re-run with different parameters based on what the
Analyst finds missing, add a conditional edge back; not needed yet. See
ADR-0001.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.agents.analyst import analyze
from agent.agents.briefing import brief
from agent.agents.retriever import retrieve
from agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("retriever", retrieve)
    graph.add_node("analyst", analyze)
    graph.add_node("briefing", brief)

    graph.set_entry_point("retriever")
    graph.add_edge("retriever", "analyst")
    graph.add_edge("analyst", "briefing")
    graph.add_edge("briefing", END)

    return graph.compile()


# Built once at import time; FastAPI app (agent/api.py) reuses this instance.
compiled_graph = build_graph()
