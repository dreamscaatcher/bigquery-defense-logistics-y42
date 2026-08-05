# Operations Intelligence Agent - orchestration layer

LangGraph pipeline (Retriever -> Analyst -> Briefing) that reads the
BigQuery country-risk marts and the Neo4j supply-network graph and produces
a SITREP-style briefing. Design rationale: `docs/adr/0001-langgraph-orchestration-layer.md`.

## Status

**Verified working end-to-end (2026-08-05).** `POST /briefing
{"country_code": "KOR"}` correctly flagged that KOR's country-level
risk_level is LOW while DEPOT_KOR (Osan Forward Base) is OVER_CAPACITY
(189% avg / 268% peak utilization) - the cross-system correlation this
layer exists to catch. See `CLAUDE.md` for the bugs found/fixed getting
there (BigQuery ADC auth, `temperature` param, output truncation, a stale
doc caught by the agent's own grounding).

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

## Evals

```bash
python -m eval.run_evals
```

Runs the 10-case labeled set in `eval/cases.py` against the live pipeline:
the 8 countries with a Neo4j depot (checks the briefing correctly states
the live risk_level and capacity_status - fetched fresh from BigQuery/Neo4j
at eval time, not hardcoded), one depot-id-only request, and one country
with no depot data (checks the agent says so instead of fabricating a
depot). Each case also gets an LLM-judge faithfulness pass (`eval/judge.py`)
- a hand-rolled, lighter version of RAGAS-style faithfulness scoring.
Prints a pass/fail table and writes a JSON report to `eval/results/`.

## Tracing

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env` (free
tier at [smith.langchain.com](https://smith.langchain.com)) - no code
changes needed, LangChain/LangGraph pick these up automatically. Every
`/briefing` call and every `python -m eval.run_evals` run will show up as
a trace in your LangSmith project (`LANGCHAIN_PROJECT`, defaults to
`ops-intel-agent`), with the full Retriever -> Analyst -> Briefing
breakdown, tool calls, and token usage per step - useful both for
debugging and as something to pull up live in an interview.

## What's not built yet

Per ADR-0001's action items, still open:

- Cost-per-run tracking (LangSmith gives token counts per trace; turning
  that into a $/run number is still manual)
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

eval/
  cases.py              the 10 labeled test cases
  ground_truth.py         fetches live expected values via the same tools
  judge.py                  LLM-as-judge faithfulness check
  run_evals.py                orchestrates + reports (python -m eval.run_evals)
```
