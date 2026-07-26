# ADR-0001: LangGraph Multi-Agent Orchestration Layer

**Status:** Proposed
**Date:** 2026-07-26
**Deciders:** Gurinder Singh Ghuman

## Context

The Operations Intelligence Agent currently has two working, independent data layers and no application layer on top of either:

- **BigQuery** (`sql/`): a staged pipeline (raw → staging → marts → ML) producing `marts.country_risk_assessment` (risk level, sentiment, 30-day event counts per country) and a trained linear regression risk predictor, verified R²=0.5464 held-out.
- **Neo4j** (`neo4j/`): a `Depot`/`Route`/`Requisition` graph modeling the physical resupply network — demand vs. capacity per depot, per route, over a 90-day window — reusing the same 8 country codes as the BigQuery side.

Both are narratively connected (same countries, complementary views of the same logistics problem) but nothing today reads both together, and nothing produces a synthesized assessment. This is roadmap item 3: a LangGraph multi-agent layer that reads both sources and produces a holistic, natural-language briefing — the first application/UI-adjacent layer this repo will have.

This also needs to demonstrate, for the AI Agent Engineer portfolio narrative, agent orchestration, hybrid retrieval, and — per the military-intelligence framing already established — guardrails against fabricating an assessment the data doesn't support.

## Decision

Build a three-agent LangGraph pipeline — **Retriever → Analyst → Briefing** — exposed via a FastAPI endpoint, using Claude (Anthropic API) as the LLM, with **hybrid retrieval**: structured tool calls against BigQuery and Neo4j for facts, plus a local vector store over the repo's own methodology docs (`README.md`, `docs/data_dictionary.md`, `neo4j/README.md`, `AUDIT.md`) so the agents can ground claims in documented definitions and known limitations rather than inventing them.

### Agent roles

1. **Retriever agent** — given a request (country code and/or depot id), calls structured tools to pull raw facts:
   - `query_country_risk(country_code)` → BigQuery `marts.country_risk_assessment` row
   - `query_depot_capacity(depot_id | country_code)` → Neo4j demand-vs-capacity query 3 (overall utilization summary)
   - `query_route_utilization(depot_id)` → Neo4j query 4 (routes terminating at that depot)
   - `search_methodology(query)` → vector search over the doc corpus, for definitions/caveats relevant to the request (e.g. "how is risk_score computed," "what does OVER_CAPACITY mean")
   Returns a structured bundle of retrieved facts + citations (source table/file), no interpretation.

2. **Analyst agent** — reasons over the retrieved bundle only. Explicitly instructed: state only conclusions the retrieved data supports; flag cross-system correlations (e.g. a MEDIUM/HIGH-risk country whose depot is OVER_CAPACITY is a compounding risk worth calling out); cite the specific numbers behind every claim; if data is missing or the country/depot isn't found, say so rather than filling the gap.

3. **Briefing agent** — formats the Analyst's findings into a SITREP: **Situation** (what the data shows), **Assessment** (what it means, with confidence caveated by the model's known limitations — e.g. R²=0.55, in-sample distribution skew), **Recommendation** (plain-English next action). This is the only agent whose output is user-facing prose.

### State graph

Linear for v1: `retriever → analyst → briefing → END`. No loops/retries yet — if the Retriever finds nothing for a given country/depot, that's surfaced as a normal "no data" result rather than triggering re-planning. Revisit if eval results show the linear flow is insuf­ficient (e.g. add a conditional edge back to Retriever if Analyst flags missing data it needs).

### Interface

FastAPI endpoint: `POST /briefing` accepting `{country_code?: str, depot_id?: str}`, returning the SITREP as structured JSON (`situation`, `assessment`, `recommendation`, `sources`) plus a rendered plain-text version. Chosen over a CLI script since it's the more natural shape for later integration (an MCP server wrapping this API is roadmap item 4) and for demoing live in an interview.

### Stack

- **Orchestration:** LangGraph (`StateGraph`)
- **LLM:** Claude via `langchain-anthropic` (`ChatAnthropic`), reads `ANTHROPIC_API_KEY`
- **Vector store:** Chroma, local/persistent (`./agent/vector_store/`) — no new hosted dependency, fits a repo with no infra yet
- **Embeddings:** local `sentence-transformers` model (e.g. `all-MiniLM-L6-v2`) rather than an OpenAI embeddings call — avoids requiring a second LLM vendor key just for embeddings, given the LLM choice is Claude-only
- **API:** FastAPI + uvicorn
- **Data access:** `google-cloud-bigquery` (reuses existing `gcloud`/ADC auth already set up for project `ops-intel-logistics`), `neo4j` Python driver (reuses the existing `opsintel-supply-network` database)

## Options Considered

### Retrieval scope: structured-only vs. hybrid (chosen)

| Dimension | Structured-only | Hybrid (chosen) |
|---|---|---|
| Complexity | Low | Medium — one more moving part (vector store + embedding step) |
| Fits current data | Yes, cleanly | Requires indexing docs, not query results |
| Portfolio signal | Agent orchestration only | Agent orchestration + hybrid retrieval + a real guardrails mechanism (grounding in documented methodology) |
| Guardrail value | Weaker — model could still invent caveats | Stronger — methodology text is retrieved, not recalled from training data |

Hybrid was chosen specifically because the "don't fabricate an assessment the data doesn't support" positioning (from the portfolio plan) is stronger when the caveats themselves (R² limitations, what OVER_CAPACITY means, the in-sample vs. held-out distinction) are retrieved from the actual docs rather than left to the model's memory.

### Interface: CLI vs. FastAPI (chosen) vs. both

FastAPI chosen: sets up the MCP-server roadmap item (4) more directly (MCP tools commonly wrap an existing API), and is more demoable than a terminal script. A CLI entry point may still be added cheaply later as a thin wrapper over the same graph — not precluded by this decision.

### LLM: Claude (chosen) vs. OpenAI

Claude chosen for consistency with the rest of the AI-agent-engineer positioning and to avoid a second vendor dependency. Embeddings use a local model instead of OpenAI's embeddings API for the same reason (see Stack above).

## Trade-off Analysis

The hybrid retrieval + FastAPI combination is more upfront complexity than the minimal version (structured-only + CLI), but every piece of that complexity is justified by either the portfolio's stated non-negotiables (guardrails) or the immediate next roadmap item (MCP server, item 4, wants an API to wrap). Nothing here is speculative beyond that — no auth layer, no multi-tenant concerns, no queueing, since none of that is needed yet for a single-user demo. Evals and tracing (LangSmith/Langfuse) are real portfolio non-negotiables but are scoped out of this ADR as a fast-follow, not because they're unimportant, but because they're orthogonal to the graph/agent design itself and easier to bolt on once the pipeline runs end-to-end at least once.

## Consequences

- Adds two new local dependencies with no hosted cost: Chroma (embedded, file-based) and a `sentence-transformers` model (downloaded once, runs locally, no per-call cost or API key).
- Introduces a genuinely new artifact type to the repo: Python application code (`agent/`), alongside the existing pure-SQL and pure-Cypher content. `requirements.txt` and a virtualenv become relevant for the first time.
- Testing this end-to-end requires the same credentials the BigQuery/Neo4j work already used (gcloud ADC for `ops-intel-logistics`, the local `opsintel-supply-network` Neo4j database) — this Cowork session can scaffold the code but cannot run/test it live; that happens in Claude Code / locally, consistent with how the rest of this project's execution has worked.
- Will need a small doc-ingestion script (`agent/ingest_docs.py`) to build the Chroma index from the markdown docs before the API can serve hybrid-retrieval requests — this is a one-time/rerun-on-doc-change step, not part of the live request path.
- Evals, LangSmith/Langfuse tracing, and cost-per-run tracking (portfolio non-negotiables) are explicitly deferred to a follow-up pass once the graph runs end-to-end — tracked as action items below, not silently dropped.

## Action Items

1. [ ] Scaffold `agent/` package: `tools/bigquery_tools.py`, `tools/neo4j_tools.py`, `tools/vector_tools.py`, `agents/retriever.py`, `agents/analyst.py`, `agents/briefing.py`, `graph.py`, `api.py`, `ingest_docs.py`
2. [ ] Add `requirements.txt` entries: `langgraph`, `langchain-anthropic`, `langchain-chroma` (or `chromadb` direct), `sentence-transformers`, `google-cloud-bigquery`, `neo4j`, `fastapi`, `uvicorn`
3. [ ] Write `agent/ingest_docs.py` to chunk + embed the four methodology docs into the local Chroma store
4. [ ] Implement the three structured tools against the real schemas (mart columns, Cypher queries already in `neo4j/03_queries/demand_vs_capacity.cypher`)
5. [ ] Wire the linear `StateGraph` (retriever → analyst → briefing)
6. [ ] Implement `POST /briefing` in FastAPI
7. [ ] Run/test locally against `ops-intel-logistics` + `opsintel-supply-network` (requires Gurinder's local credentials — not available in this Cowork sandbox)
8. [ ] Fast-follow: add a small labeled eval set (expected SITREP content per country/depot) and LangSmith or Langfuse tracing, per portfolio non-negotiables
9. [ ] Commit + push
