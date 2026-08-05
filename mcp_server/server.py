#!/usr/bin/env python3
"""MCP server for the Operations Intelligence Agent.

Exposes the LangGraph briefing pipeline plus the four underlying structured
tools (BigQuery country risk, Neo4j depot capacity, Neo4j route utilization,
vector search over methodology docs) as MCP tools, so any MCP client
(Claude Desktop, etc.) can drive this project directly instead of only via
curl/Swagger against agent/api.py.

Deliberately wraps the *same* functions agent/ already uses
(agent.graph.compiled_graph, agent.tools.*) rather than re-implementing
anything - this file is glue, not logic. See docs/adr/0001 for the
underlying pipeline design and README.md for verified project state.

Run: python -m mcp_server.server
Install into Claude Desktop: see mcp_server/README.md.
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent.graph import compiled_graph
from agent.tools.bigquery_tools import query_country_risk
from agent.tools.neo4j_tools import query_depot_capacity, query_route_utilization
from agent.tools.vector_tools import search_methodology

# NOTE: the `mcp` SDK renamed FastMCP -> MCPServer (moved to
# mcp.server.mcpserver) in the SDK version this was built against
# (2.0.0) - the class formerly known as FastMCP. Same interface
# (.tool() decorator, .run()), just a new name/location. If you're
# following older MCP tutorials referencing `mcp.server.fastmcp.FastMCP`,
# that import path no longer exists in this SDK version.
mcp = MCPServer("ops_intel_mcp")

_CONNECTION_HINT = (
    "This usually means either: (1) BigQuery - run "
    "`gcloud auth application-default login` (this is a different, separate "
    "credential from `gcloud auth login`), or (2) Neo4j - open Neo4j Desktop "
    "and confirm the opsintel-supply-network DBMS is Active, not stopped. "
    "Both have caused exactly this error before in this project."
)


def _handle_tool_error(e: Exception) -> str:
    """Consistent, actionable error formatting across all tools here.

    Deliberately pattern-matches on the actual errors this project has hit
    in practice (see CLAUDE.md) rather than generic exception types, since
    those are the errors an agent using this server will actually see.
    """
    message = str(e)
    if "routing information" in message or "ServiceUnavailable" in type(e).__name__:
        return f"Error: could not reach Neo4j. {_CONNECTION_HINT}"
    if "Application Default Credentials" in message or "credentials were not found" in message:
        return f"Error: could not reach BigQuery. {_CONNECTION_HINT}"
    if "ANTHROPIC_API_KEY" in message or "NEO4J_URI" in message:
        return f"Error: missing configuration - {message}. Check your .env file (see .env.example)."
    return f"Error: {type(e).__name__}: {message}"


# ---------------------------------------------------------------------------
# get_briefing - the flagship workflow tool (full Retriever -> Analyst ->
# Briefing pipeline, an LLM call, slower/costlier than the tools below)
# ---------------------------------------------------------------------------


class BriefingInput(BaseModel):
    """Input for a full SITREP briefing."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country_code: Optional[str] = Field(
        default=None,
        description="3-letter ISO country code, e.g. 'KOR', 'USA'. Provide this and/or depot_id.",
        min_length=3,
        max_length=3,
    )
    depot_id: Optional[str] = Field(
        default=None,
        description="Depot identifier, e.g. 'DEPOT_KOR'. Provide this and/or country_code.",
    )

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "BriefingInput":
        if not self.country_code and not self.depot_id:
            raise ValueError("Provide at least one of country_code or depot_id.")
        return self


@mcp.tool(
    name="ops_intel_get_briefing",
    annotations={
        "title": "Get Operations Intelligence Briefing",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ops_intel_get_briefing(params: BriefingInput) -> str:
    """Generate a SITREP-style operational risk briefing for a country and/or depot.

    Runs the full three-agent pipeline (Retriever -> Analyst -> Briefing):
    pulls country-level geopolitical risk from BigQuery, depot capacity and
    inbound route utilization from a Neo4j supply-network graph, and
    grounding context from the project's own methodology docs, then has
    Claude synthesize a Situation / Assessment / Recommendation briefing.
    This is the tool to use for "what's the risk picture for X" questions -
    for a single raw data point instead, use one of the narrower tools
    (ops_intel_get_country_risk, ops_intel_get_depot_capacity,
    ops_intel_get_route_utilization) instead, which are faster and cheaper
    since they skip the LLM synthesis step.

    Args:
        params (BriefingInput): Validated input containing:
            - country_code (Optional[str]): 3-letter ISO code, e.g. "KOR"
            - depot_id (Optional[str]): e.g. "DEPOT_KOR"
            At least one of the two must be provided.

    Returns:
        str: JSON-formatted briefing with the schema:
        {
            "situation": str,        # what the retrieved data shows
            "assessment": str,       # what it means, with caveats
            "recommendation": str,   # concrete next action
            "sources": [str],        # tables/files the briefing draws on
            "no_data_warning": str | null  # set if some data was missing
        }

    Examples:
        - Use when: "What's the operational risk picture for South Korea?"
          -> params with country_code="KOR"
        - Use when: "Is DEPOT_KOR under strain?" -> params with depot_id="DEPOT_KOR"
        - Don't use when: you just need the raw risk_level or capacity_status
          number - use the narrower tools instead, they're faster.

    Error Handling:
        Returns "Error: ..." with a specific, actionable hint if BigQuery or
        Neo4j can't be reached, or if required config is missing.
    """
    try:
        state = compiled_graph.invoke(
            {"country_code": params.country_code, "depot_id": params.depot_id}
        )
        return state["briefing"].model_dump_json(indent=2)
    except Exception as e:  # noqa: BLE001 - convert to an agent-actionable message
        return _handle_tool_error(e)


# ---------------------------------------------------------------------------
# Narrower read tools - direct passthroughs to the same functions
# agent/agents/retriever.py calls, for when the full LLM pipeline is
# unnecessary overhead.
# ---------------------------------------------------------------------------


class CountryRiskInput(BaseModel):
    """Input for a country risk lookup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country_code: str = Field(
        ..., description="3-letter ISO country code, e.g. 'KOR', 'USA'.", min_length=3, max_length=3
    )


@mcp.tool(
    name="ops_intel_get_country_risk",
    annotations={
        "title": "Get Country Risk Assessment",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ops_intel_get_country_risk(params: CountryRiskInput) -> str:
    """Look up the current BigQuery risk assessment for a single country.

    Direct read from marts.country_risk_assessment - no LLM call, no
    synthesis, just the raw row. Faster/cheaper than
    ops_intel_get_briefing when you only need this one number.

    Args:
        params (CountryRiskInput): Validated input containing:
            - country_code (str): 3-letter ISO code, e.g. "KOR"

    Returns:
        str: JSON with country_code, country_name, region, total_events_30d,
        avg_event_sentiment, avg_stability_score, risk_level
        (LOW/MEDIUM/HIGH), calculated_at, found (bool). If the country
        isn't in the dataset, found is false and other fields are absent.

    Examples:
        - Use when: "What's KOR's current risk_level?" -> country_code="KOR"
        - Don't use when: you want a synthesized assessment combining this
          with depot/capacity data - use ops_intel_get_briefing instead.
    """
    try:
        result = query_country_risk.invoke({"country_code": params.country_code})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:  # noqa: BLE001
        return _handle_tool_error(e)


class DepotCapacityInput(BaseModel):
    """Input for a depot capacity lookup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    depot_id: Optional[str] = Field(default=None, description="e.g. 'DEPOT_KOR'.")
    country_code: Optional[str] = Field(
        default=None, description="3-letter ISO code - matches all depots in that country."
    )

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "DepotCapacityInput":
        if not self.depot_id and not self.country_code:
            raise ValueError("Provide at least one of depot_id or country_code.")
        return self


@mcp.tool(
    name="ops_intel_get_depot_capacity",
    annotations={
        "title": "Get Depot Capacity Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ops_intel_get_depot_capacity(params: DepotCapacityInput) -> str:
    """Look up demand-vs-capacity status for one or more depots from the
    Neo4j supply-network graph.

    Direct read, no LLM call. Provide depot_id for a specific depot, or
    country_code to match all depots in that country.

    Args:
        params (DepotCapacityInput): Validated input containing:
            - depot_id (Optional[str]): e.g. "DEPOT_KOR"
            - country_code (Optional[str]): e.g. "KOR"
            At least one must be provided.

    Returns:
        str: JSON with found (bool) and, if found, a "depots" list where
        each entry has depot_id, depot_name, depot_type, country_code,
        capacity_per_day, avg_daily_demand, peak_daily_demand,
        avg_utilization_pct, peak_utilization_pct, and capacity_status
        (OVER_CAPACITY / NEAR_CAPACITY / WITHIN_CAPACITY).

    Examples:
        - Use when: "Is DEPOT_KOR over capacity?" -> depot_id="DEPOT_KOR"
        - Use when: "What depot(s) does Korea have and how are they doing?"
          -> country_code="KOR"
        - Don't use when: no Neo4j depot exists for this country - not
          every country in the BigQuery risk data has one; check
          found=false in the response rather than assuming.
    """
    try:
        if params.depot_id:
            result = query_depot_capacity.invoke({"depot_id": params.depot_id})
        else:
            result = query_depot_capacity.invoke({"country_code": params.country_code})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:  # noqa: BLE001
        return _handle_tool_error(e)


class RouteUtilizationInput(BaseModel):
    """Input for a route utilization lookup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    depot_id: str = Field(..., description="e.g. 'DEPOT_KOR'. Looks up routes terminating here.")


@mcp.tool(
    name="ops_intel_get_route_utilization",
    annotations={
        "title": "Get Route Utilization",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ops_intel_get_route_utilization(params: RouteUtilizationInput) -> str:
    """Look up utilization of all inbound routes terminating at a depot.

    Direct Neo4j read, no LLM call. Useful for distinguishing whether a
    depot's strain is a transport (route) bottleneck vs. a depot-side
    (handling/processing) bottleneck - a distinction the Briefing agent
    makes explicitly when it has this data.

    Args:
        params (RouteUtilizationInput): Validated input containing:
            - depot_id (str): e.g. "DEPOT_KOR"

    Returns:
        str: JSON with found (bool) and, if found, a "routes" list where
        each entry has route_id, origin_depot, destination_depot, mode
        (AIR/SEA/GROUND), transit_days, capacity_per_day,
        requisitions_routed, total_quantity_routed, and
        utilization_pct_over_window (90-day window).

    Examples:
        - Use when: "Are the routes into DEPOT_KOR the bottleneck, or is it
          the depot itself?" -> depot_id="DEPOT_KOR"
        - Don't use when: you haven't already confirmed the depot exists -
          call ops_intel_get_depot_capacity first if unsure.
    """
    try:
        result = query_route_utilization.invoke({"depot_id": params.depot_id})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:  # noqa: BLE001
        return _handle_tool_error(e)


class MethodologySearchInput(BaseModel):
    """Input for a methodology doc search."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Natural-language question, e.g. 'what does OVER_CAPACITY mean'.",
        min_length=3,
        max_length=300,
    )
    k: Optional[int] = Field(default=3, description="Number of chunks to return.", ge=1, le=10)


@mcp.tool(
    name="ops_intel_search_methodology",
    annotations={
        "title": "Search Project Methodology Docs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ops_intel_search_methodology(params: MethodologySearchInput) -> str:
    """Semantic search over this project's own methodology docs (README.md,
    docs/data_dictionary.md, neo4j/README.md, AUDIT.md).

    Use this for definitional/methodology questions - what a term means,
    what a model's known limitations are - NOT for current data values (use
    the other tools for those). No LLM call, pure vector search.

    Args:
        params (MethodologySearchInput): Validated input containing:
            - query (str): natural-language question
            - k (Optional[int]): number of chunks to return, 1-10 (default 3)

    Returns:
        str: JSON with found (bool) and, if found, a "chunks" list of
        {"text": str, "source_file": str}. found=false if the vector index
        hasn't been built yet (run `python -m agent.ingest_docs` first).

    Examples:
        - Use when: "What does the risk model's R^2 actually measure, and
          is it reliable?" -> query="risk model R2 reliability"
        - Don't use when: you want a specific country's current risk_level
          - use ops_intel_get_country_risk instead, this only searches docs.
    """
    try:
        result = search_methodology.invoke({"query": params.query, "k": params.k})
        return json.dumps(result, indent=2, default=str)
    except Exception as e:  # noqa: BLE001
        return _handle_tool_error(e)


if __name__ == "__main__":
    mcp.run()
