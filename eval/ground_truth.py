"""Fetches live ground truth for a case using the same tool functions the
agent itself calls - so eval expectations track the real data instead of a
frozen snapshot that can silently drift out of sync (the same failure mode
that let the stale R^2 doc bug happen)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agent.tools.bigquery_tools import query_country_risk
from agent.tools.neo4j_tools import query_depot_capacity
from eval.cases import EvalCase


@dataclass
class GroundTruth:
    risk_level: Optional[str]  # None if country not found
    capacity_status: Optional[str]  # None if no depot found
    depot_found: bool


def fetch(case: EvalCase) -> GroundTruth:
    risk_level = None
    if case.country_code:
        risk = query_country_risk.invoke({"country_code": case.country_code})
        if risk.get("found"):
            risk_level = risk.get("risk_level")

    capacity_status = None
    depot_found = False
    if case.depot_id:
        capacity = query_depot_capacity.invoke({"depot_id": case.depot_id})
    elif case.country_code:
        capacity = query_depot_capacity.invoke({"country_code": case.country_code})
    else:
        capacity = {"found": False}

    if capacity.get("found"):
        depots = capacity.get("depots") or []
        if depots:
            depot_found = True
            capacity_status = depots[0].get("capacity_status")

    return GroundTruth(
        risk_level=risk_level, capacity_status=capacity_status, depot_found=depot_found
    )
