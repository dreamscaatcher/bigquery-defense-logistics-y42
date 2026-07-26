# Operations Intelligence Agent - orchestration layer

LangGraph pipeline (Retriever -> Analyst -> Briefing) that reads the
BigQuery country-risk marts and the Neo4j supply-network graph and produces
a SITREP-style briefing. Design rationale: `docs/adr/0001-langgraph-orchestration-layer.md`.

## Status

Scaffolded, not yet run. This was built in a Cowork session that has no
access to the live `ops-intel-logistics` BigQuery project or the local
`opsintel-supply-network` Neo4j database - both live only on Gurinder's
machine / GCP account. Run and debug it there (Claude Code / local
terminal), not here.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# fill in ANTHROPIC_API_KEY, NEO4J_URI, NEO4J_PASSWORD
# GCP auth is separate: gcloud auth application-default login

# Build the vector index (rerun any time the source docs change)
python -m agent.ingest_docs

# Run the API
uvicorn agent.api:app --reload
```

## Try it

```bash
curl -X POST http://localhost:8000/briefing \
  -H "Content-Type: application/json" \
  -d '{"country_code": "KOR"}'
```

`KOR` is a good first test: per the verified README numbers, South Korea's
depot (`DEPOT_KOR`, a forward operating base) is the most capacity-strained
in the Neo4j graph, so a `country_code=KOR` briefing should exercise both
the BigQuery risk lookup and a real OVER_CAPACITY/NEAR_CAPACITY signal from
Neo4j - the cross-system correlation the Analyst agent is specifically
instructed to flag.

You can also query by depot directly: `{"depot_id": "DEPOT_KOR"}`.

## What's not built yet

Per ADR-0001's action items, deliberately deferred as fast-follows once the
pipeline runs end-to-end at least once:

- Evals (labeled expected-briefing set per country/depot)
- LangSmith or Langfuse tracing
- Cost-per-run tracking
- Any auth/rate limiting on the API (fine for a single-user local demo, not
  fine for anything public)

## Module map

```
agent/
  config.py           env var loading
  state.py             GraphState + Briefing pydantic model
  graph.py              StateGraph wiring (retriever -> analyst -> briefing)
  api.py                 FastAPI app (POST /briefing)
  ingest_docs.py          builds the Chroma index from methodology docs
  tools/
    bigquery_tools.py      query_country_risk
    neo4j_tools.py          query_depot_capacity, query_route_utilization
    vector_tools.py          search_methodology
  agents/
    retriever.py              deterministic tool-calling node
    analyst.py                 reasons over retrieved bundle, cites numbers
    briefing.py                  formats into Situation/Assessment/Recommendation
```
