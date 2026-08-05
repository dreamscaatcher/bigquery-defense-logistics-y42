"""Structured retrieval against the Neo4j supply-network graph.

Parameterized versions of queries 3 and 4 in
neo4j/03_queries/demand_vs_capacity.cypher, scoped to a single depot (or all
depots in a country) instead of returning the whole graph. Schema is
Depot/Route/Requisition - see neo4j/README.md.

Requires the `opsintel-supply-network` database to exist and be seeded
(neo4j/01_schema + neo4j/02_seed_data) - the same local/Aura instance
already used for that work.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from neo4j import GraphDatabase

from agent.config import load_settings

_settings = load_settings()
_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            _settings.neo4j_uri,
            auth=(_settings.neo4j_username, _settings.neo4j_password),
        )
    return _driver


_CAPACITY_QUERY = """
MATCH (d:Depot)
WHERE ($depot_id IS NOT NULL AND d.depot_id = $depot_id)
   OR ($country_code IS NOT NULL AND d.country_code = $country_code)
OPTIONAL MATCH (q:Requisition)-[:REQUESTED_AT]->(d)
WITH d, q.request_date AS period, sum(q.quantity) AS daily_quantity
WITH d, avg(daily_quantity) AS avg_daily_demand, max(daily_quantity) AS peak_daily_demand
RETURN
  d.depot_id AS depot_id,
  d.name AS depot_name,
  d.depot_type AS depot_type,
  d.country_code AS country_code,
  d.capacity_per_day AS capacity_per_day,
  round(avg_daily_demand) AS avg_daily_demand,
  peak_daily_demand,
  round(100.0 * avg_daily_demand / d.capacity_per_day) AS avg_utilization_pct,
  round(100.0 * peak_daily_demand / d.capacity_per_day) AS peak_utilization_pct,
  CASE
    WHEN peak_daily_demand > d.capacity_per_day THEN 'OVER_CAPACITY'
    WHEN avg_daily_demand > 0.8 * d.capacity_per_day THEN 'NEAR_CAPACITY'
    ELSE 'WITHIN_CAPACITY'
  END AS capacity_status
ORDER BY avg_utilization_pct DESC
"""

_ROUTE_QUERY = """
MATCH (r:Route)-[:TERMINATES_AT]->(dest:Depot {depot_id: $depot_id})
OPTIONAL MATCH (q:Requisition)-[:FULFILLED_VIA]->(r)
WITH r, dest, count(q) AS requisitions_routed, sum(q.quantity) AS total_quantity_routed
MATCH (r)-[:ORIGINATES_AT]->(origin:Depot)
RETURN
  r.route_id AS route_id,
  origin.depot_id AS origin_depot,
  dest.depot_id AS destination_depot,
  r.mode AS mode,
  r.transit_days AS transit_days,
  r.capacity_per_day AS capacity_per_day,
  requisitions_routed,
  total_quantity_routed,
  round(100.0 * total_quantity_routed / (r.capacity_per_day * 90)) AS utilization_pct_over_window
ORDER BY utilization_pct_over_window DESC
"""


@tool
def query_depot_capacity(
    depot_id: str | None = None, country_code: str | None = None
) -> dict[str, Any]:
    """Look up demand-vs-capacity status for one or more depots.

    Provide either depot_id (e.g. "DEPOT_KOR") or country_code (e.g. "KOR") -
    country_code matches all depots in that country (usually one).

    Returns avg/peak daily demand, capacity, utilization %, and a
    capacity_status of OVER_CAPACITY / NEAR_CAPACITY / WITHIN_CAPACITY per
    depot found. {"found": False} if neither param matches a depot.
    """
    if not depot_id and not country_code:
        return {"found": False, "error": "must provide depot_id or country_code"}

    with _get_driver().session(database=_settings.neo4j_database) as session:
        records = session.run(
            _CAPACITY_QUERY,
            depot_id=depot_id,
            country_code=country_code.strip().upper() if country_code else None,
        ).data()

    if not records:
        return {"found": False, "depot_id": depot_id, "country_code": country_code}

    return {
        "found": True,
        "source": "neo4j:opsintel-supply-network (depot capacity, 90-day window)",
        "depots": records,
    }


@tool
def query_route_utilization(depot_id: str) -> dict[str, Any]:
    """Look up utilization of all routes terminating at a depot (i.e. the
    routes that resupply it).

    Args:
        depot_id: e.g. "DEPOT_KOR".

    Returns route_id, origin/destination, mode, transit_days, and
    utilization_pct_over_window (90-day window) per route.
    """
    with _get_driver().session(database=_settings.neo4j_database) as session:
        records = session.run(_ROUTE_QUERY, depot_id=depot_id).data()

    if not records:
        return {"found": False, "depot_id": depot_id}

    return {
        "found": True,
        "source": "neo4j:opsintel-supply-network (route utilization, 90-day window)",
        "routes": records,
    }


_ALL_DEPOTS_QUERY = """
MATCH (d:Depot)
OPTIONAL MATCH (q:Requisition)-[:REQUESTED_AT]->(d)
WITH d, q.request_date AS period, sum(q.quantity) AS daily_quantity
WITH d, avg(daily_quantity) AS avg_daily_demand, max(daily_quantity) AS peak_daily_demand
RETURN
  d.depot_id AS depot_id,
  d.name AS depot_name,
  d.depot_type AS depot_type,
  d.country_code AS country_code,
  d.latitude AS latitude,
  d.longitude AS longitude,
  d.capacity_per_day AS capacity_per_day,
  round(100.0 * avg_daily_demand / d.capacity_per_day) AS avg_utilization_pct,
  round(100.0 * peak_daily_demand / d.capacity_per_day) AS peak_utilization_pct,
  CASE
    WHEN peak_daily_demand > d.capacity_per_day THEN 'OVER_CAPACITY'
    WHEN avg_daily_demand > 0.8 * d.capacity_per_day THEN 'NEAR_CAPACITY'
    ELSE 'WITHIN_CAPACITY'
  END AS capacity_status
"""


def query_all_depots_capacity() -> list[dict[str, Any]]:
    """Fetch every depot's location + capacity_status, for the map view.

    Not a LangChain @tool, same reasoning as query_all_countries_risk in
    bigquery_tools.py - a plain data-fetch helper for GET /map-data.
    Depots seeded before 2026-08-05 won't have latitude/longitude set (see
    neo4j/README.md) - those are skipped here since they can't be plotted.
    """
    with _get_driver().session(database=_settings.neo4j_database) as session:
        records = session.run(_ALL_DEPOTS_QUERY).data()

    return [r for r in records if r.get("latitude") is not None and r.get("longitude") is not None]
