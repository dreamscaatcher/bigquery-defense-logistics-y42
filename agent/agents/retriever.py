"""Retriever node: pulls raw facts, does not interpret them.

Deliberately deterministic rather than LLM-tool-calling for v1: the request
shape (country_code and/or depot_id) fully determines which tools to call,
so there's nothing for an LLM to decide here and adding one would just be
extra latency/cost for no benefit. See ADR-0001 for the fuller reasoning.
If retrieval logic grows more open-ended later (e.g. free-text requests
instead of structured params), revisit as an actual tool-calling agent.
"""

from __future__ import annotations

from agent.state import GraphState
from agent.tools.bigquery_tools import query_country_risk
from agent.tools.neo4j_tools import query_depot_capacity, query_route_utilization
from agent.tools.vector_tools import search_methodology


def retrieve(state: GraphState) -> dict:
    country_code = state.get("country_code")
    depot_id = state.get("depot_id")

    retrieved: dict = {"country_risk": None, "depot_capacity": None, "route_utilization": None}

    if country_code:
        retrieved["country_risk"] = query_country_risk.invoke(
            {"country_code": country_code}
        )

    depot_capacity = None
    if depot_id:
        depot_capacity = query_depot_capacity.invoke({"depot_id": depot_id})
    elif country_code:
        depot_capacity = query_depot_capacity.invoke({"country_code": country_code})
    retrieved["depot_capacity"] = depot_capacity

    # Route utilization needs a concrete depot_id - use the one supplied, or
    # the first depot found via country_code lookup.
    resolved_depot_id = depot_id
    if not resolved_depot_id and depot_capacity and depot_capacity.get("found"):
        depots = depot_capacity.get("depots") or []
        if depots:
            resolved_depot_id = depots[0].get("depot_id")

    if resolved_depot_id:
        retrieved["route_utilization"] = query_route_utilization.invoke(
            {"depot_id": resolved_depot_id}
        )

    # Ground with methodology context relevant to whatever was actually found.
    methodology_terms = []
    risk = retrieved.get("country_risk") or {}
    if risk.get("found"):
        methodology_terms.append(f"what does risk_level {risk.get('risk_level')} mean")
    capacity = retrieved.get("depot_capacity") or {}
    if capacity.get("found"):
        statuses = {d.get("capacity_status") for d in capacity.get("depots", [])}
        for status in statuses:
            if status:
                methodology_terms.append(f"what does {status} mean")
    if not methodology_terms:
        methodology_terms.append("model limitations and known caveats")

    retrieved["methodology"] = search_methodology.invoke(
        {"query": "; ".join(methodology_terms)}
    )

    return {"retrieved": retrieved}
