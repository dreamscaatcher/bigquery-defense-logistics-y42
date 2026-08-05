"""FastAPI app exposing the LangGraph pipeline.

Run locally: uvicorn agent.api:app --reload
(requires .env populated - see .env.example - and the vector index built
via `python -m agent.ingest_docs` at least once).

This is a single-endpoint demo API for now, not a production service: no
auth, no rate limiting, no queueing. Roadmap item 4 (MCP server) is expected
to wrap this rather than duplicate it - see ADR-0001.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, model_validator

from agent.graph import compiled_graph
from agent.state import Briefing
from agent.tools.bigquery_tools import query_all_countries_risk
from agent.tools.neo4j_tools import query_all_depots_capacity

_STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Operations Intelligence Agent",
    description=(
        "Reads BigQuery country-risk marts and a Neo4j supply-network graph, "
        "produces a SITREP-style briefing."
    ),
    version="0.1.0",
)


class BriefingRequest(BaseModel):
    country_code: Optional[str] = None
    depot_id: Optional[str] = None

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "BriefingRequest":
        if not self.country_code and not self.depot_id:
            raise ValueError("Provide at least one of country_code or depot_id.")
        return self


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/briefing", response_model=Briefing)
def get_briefing(request: BriefingRequest) -> Briefing:
    try:
        result = compiled_graph.invoke(
            {
                "country_code": request.country_code,
                "depot_id": request.depot_id,
            }
        )
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500 for the demo API
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result["briefing"]


@app.get("/map-data")
def get_map_data() -> dict:
    """Country risk + depot capacity, with coordinates, for the map view
    (roadmap item 5). No LLM call - two direct reads, combined.
    """
    try:
        countries = query_all_countries_risk()
        depots = query_all_depots_capacity()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"countries": countries, "depots": depots}


@app.get("/map")
def get_map_page() -> FileResponse:
    """Serves the standalone Leaflet map page (agent/static/map.html),
    which fetches its data from GET /map-data client-side. Not a template -
    a plain static file, no server-side rendering needed for this."""
    return FileResponse(_STATIC_DIR / "map.html")
