# Project Context — Operations Intelligence Agent

Claude Code reads this file automatically at the start of every session in
this repo, so context carries over without re-explaining it each time.

## What this repo is

`bigquery-defense-logistics-y42` — a BigQuery-native supply-chain/logistics risk
analytics platform. Originally built ~1 year ago as a job-application demo
project (for Y42), now being evolved into a portfolio flagship called the
**Operations Intelligence Agent**.

## Current known state (as of 2026-07-26)

- 2 commits total. `sql/01_setup` through `sql/05_ml_models` (staged BigQuery
  pipeline: raw data → staging → marts → BQML model), plus `docs/`.
- **Decision made (2026-07-26): EXTEND, do not rebuild from scratch.** A full
  Claude Code audit (see AUDIT.md in repo root) found the schema design
  (02_raw_data), mart logic (04_marts), and ML feature engineering
  (05_ml_models training data) are solid and would come out identical if
  rebuilt — no reason to redo them.
- **Known problems to fix (not rebuild):**
  1. `country_risk_assessment` view column `total_events_30d` doesn't actually
     filter to 30 days — it aggregates all-time events. Needs a real
     `WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)` filter.
  2. `raw_data.countries` and `raw_data.trade_flows` are schema-only, no load
     statements — nothing populates them.
  3. `05_ml_models`'s evaluation query and prediction sample query are
     commented out. **The R²=0.62 / MAE=0.26 numbers in README.md are NOT
     reproducible from current code** — no saved model artifact, no way to
     re-derive them. Treat these numbers as unverified until the evaluation
     query is uncommented, run, and the README updated with real numbers.
  4. `03_staging`'s event data is generated via `RAND()` — non-deterministic,
     and has hardcoded country-name → sentiment bias (Syria/Afghanistan
     negative, Norway/Denmark positive) baked in rather than measured. Needs
     deterministic generation.
  5. `docs/architecture.md` and `docs/y42_insights.md` are ~95-100% Y42
     marketing copy with no real technical content — delete, don't fix.
     `docs/data_dictionary.md` is genuinely good, keep it.
- **Progress (2026-07-26, commit 197436f):** issues 1, 2, 4, 5 fixed —
  30-day filter added, real countries + deterministic FARM_FINGERPRINT
  trade/event generation (bias removed), eval query uncommented, marketing
  docs deleted, README metrics marked `[UNVERIFIED]`. Issue 3 (real eval
  numbers) still pending — was blocked on missing gcloud/bq CLI.
- **GCP project provisioned:** `ops-intel-logistics`. Project ID renamed
  across all SQL files (25 occurrences).
- **Pipeline actually run end-to-end (2026-07-26) — first time ever.**
  Running it for real surfaced 3 bugs that had gone undetected because the
  pipeline had never been executed before:
  1. `%` used as a modulo operator in `02_raw_data/create_tables.sql` and
     `03_staging/global_events.sql` — BigQuery Standard SQL requires
     `MOD(a, b)`, doesn't support `%` as an operator at all. Fixed.
  2. `INSERT INTO staging.global_events` column list only had 7 columns
     but the SELECT produced 12 (column-count mismatch). Fixed by listing
     all 12 target columns explicitly, matching SELECT order.
  3. Bare `NULL` literals for `actor2_country`/`source_url` (STRING) and
     `latitude`/`longitude` (FLOAT64) were defaulting to INT64, causing a
     type mismatch on insert. Fixed with explicit `CAST(NULL AS ...)`.
  Also: the evaluation/prediction queries in `05_ml_models` were only
  *cosmetically* uncommented in the earlier session (line comments swapped
  for block comments, still inert) — now genuinely live SQL.
- **Verified model metrics (2026-07-26):** R²=0.5365, MAE=0.2666,
  MSE=0.1064, explained_variance=0.5365. Evaluated via `ML.EVALUATE`
  against the full `models.supply_chain_training_data` table (in-sample,
  not held-out — noted as a limitation in the README). Reproducible: all
  data generation is deterministic, re-running the pipeline gives the same
  numbers. Replaces the old unverified 0.62/0.26 claim.
- **Verified risk distribution:** 15 countries MEDIUM, 16 LOW, 0 HIGH (out
  of 31 real countries) — replaces the old fabricated 249-country table
  that was leftover from the original unverified demo.
- **Committed and pushed (2026-07-26, commit `8465c7d`):** all of the above
  — SQL bug fixes, real verified metrics, corrected risk distribution,
  cleaned-up README — is now live on `origin/main`.
- **Train/test split added (2026-07-26):** `05_ml_models/predictive_analytics.sql`
  now does a deterministic 80/20 split keyed on `trade_id`
  (`MOD(ABS(FARM_FINGERPRINT(trade_id)), 100) < 80`), trains only on the
  80% partition (`data_split_method='NO_SPLIT'`), and evaluates only on
  the held-out 20%. Verified held-out metrics: R²=0.5464, MAE=0.2631,
  MSE=0.1043, explained_variance=0.5465 — close to the earlier in-sample
  number (0.5365), suggesting no meaningful overfitting. README updated.
  **Committed and pushed (commit `5fe86c2`)** — live on `origin/main`.
- **Neo4j supply-network graph added (2026-07-26):** `neo4j/` folder with
  schema constraints, deterministic seed data, and demand-vs-capacity read
  queries. Schema: `Depot`/`Route`/`Requisition` nodes, reusing the same 8
  country codes as the BigQuery trade_flows data. 8 depots, 56 routes (all
  ordered pairs), ~2,160 requisitions (8 × 90 days × 3/day), all generated
  deterministically (arithmetic hash on depot index/day offset/req number,
  no `RAND()`). Verified working: `%` modulo operator, `date.truncate()`,
  and cross-join `UNWIND` patterns all confirmed against the live Neo4j
  instance before writing the seed scripts, to avoid repeating the
  BigQuery `%`-operator mistake. **Deliberately scoped to schema + seed +
  queries only — no application/UI layer yet** (this repo has no frontend
  at all currently, and the LangGraph/MCP layers below may end up being
  how this data gets exposed rather than a hand-built dashboard). See
  `neo4j/README.md`.
- **Neo4j graph seeded and verified (2026-07-26):** ran against a dedicated
  `opsintel-supply-network` database in Neo4j Desktop (separate from
  whatever tracks project state). Confirmed: 3 constraints + 2 indexes
  online, 8 depots, 56 routes, 2,160 requisitions (priority split exactly
  1512/432/216 = 70/20/10 as designed). **Found and fixed a real
  calibration bug**: the initial depot `capacity_per_day` values (200-500)
  were all at or below the actual average demand the generator produces
  (~493-523/day), so every depot came back `OVER_CAPACITY` trivially —
  the capacities had been chosen narratively without checking them against
  the demand math. Recalibrated (260-900, scaled by depot tier) to produce
  a realistic mixed result: USA/CHN `WITHIN_CAPACITY`, DEU borderline
  (fine on average, peak-day-only overage), JPN/GBR/AUS/FRA/KOR
  increasingly over capacity, KOR (forward operating base) most strained —
  a coherent "forward positions are hardest to supply" pattern. Route
  utilization also verified (54-76%, comfortably within capacity).
  **Committed and pushed (commit `419bc8a`)** — neo4j/ folder with full schema, seed, and read queries now live on `origin/main`.
- **Session wrap-up (2026-07-26):** All work completed, committed, pushed, and documented. IMPLEMENTATION.md created as a persistent session tracking log. CLAUDE.md updated with final state.
- No LangGraph, no MCP server, no geospatial view exist in this repo yet —
  those are roadmap items, not built.

## LangGraph orchestration layer (2026-08-05)

- **ADR-0001** (`docs/adr/0001-langgraph-orchestration-layer.md`) designed a
  three-agent pipeline (Retriever → Analyst → Briefing) with hybrid
  retrieval: structured tools against BigQuery/Neo4j + a local Chroma vector
  store over the repo's own methodology docs, Claude via Anthropic API,
  FastAPI `POST /briefing` endpoint. Scaffolded as `agent/` (config, state,
  graph, api, ingest_docs, tools/, agents/), committed `e2684ec` + `610b860`.
- **Verified working end-to-end (2026-08-05).** `POST /briefing
  {"country_code": "KOR"}` correctly produced a SITREP flagging that KOR's
  country-level `risk_level` is LOW while `DEPOT_KOR` (Osan Forward Base) is
  OVER_CAPACITY (189% avg / 268% peak utilization) — exactly the
  cross-system correlation this layer was designed to catch, with routes
  correctly identified as not the bottleneck (depot itself is).
- **Bugs found and fixed getting there:**
  1. BigQuery client needs `gcloud auth application-default login`
     specifically — separate from the `gcloud auth login` used for `bq`/SQL
     work. Different auth mechanism (ADC vs CLI credentials).
  2. `temperature=0` on `ChatAnthropic` was rejected outright by the model
     in use ("temperature is deprecated for this model") — removed from
     both `agent/agents/analyst.py` and `agent/agents/briefing.py`.
  3. Briefing agent's structured output (`with_structured_output`) was
     getting truncated mid-response (missing `assessment`/`recommendation`
     fields, a stray `</invoke>` tag in the output) — no explicit
     `max_tokens` had been set. Fixed: `max_tokens=2048` on both LLM calls,
     plus tightened the Briefing system prompt to ask for concise
     (2-4 sentence) fields.
  4. The Briefing agent's own grounding caught a real doc bug: the vector
     index include `docs/data_dictionary.md`, which still had the old
     unverified `R² = 0.62, MAE = 0.26` figure (never updated when the real
     0.5464 number was verified back on 2026-07-26) — while `README.md` had
     the correct number. Fixed in `docs/data_dictionary.md`; the historical
     mention in `AUDIT.md` was left as-is since that file is explicitly a
     historical record of why the old number wasn't reproducible. Vector
     index rebuilt (`python -m agent.ingest_docs`) after the fix.
  All four fixes committed and pushed.

### Evals + LangSmith tracing (2026-08-05)

- **`eval/` harness added** per ADR-0001's fast-follow action item:
  `cases.py` (10 labeled cases - the 8 countries with a Neo4j depot, one
  depot-id-only request, one country with no depot data),
  `ground_truth.py` (fetches live expected values via the same tool
  functions the agent uses, not hardcoded numbers), `judge.py` (LLM-as-judge
  faithfulness check, a hand-rolled RAGAS-style pass), `run_evals.py`
  (orchestrates, prints pass/fail, writes JSON report to `eval/results/`).
- **LangSmith tracing wired via env vars only** (`LANGCHAIN_TRACING_V2`,
  `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` in `.env`) - no code changes,
  LangChain/LangGraph auto-detect.
- **First real run: 9/10.** `aus_country` failed on the same Briefing
  truncation bug as the original KOR case. Fixed: `max_tokens` raised to
  4096 on both Analyst and Briefing LLM calls, plus a one-time retry with a
  "be more concise" nudge if the Briefing agent's structured output still
  fails validation.
- **Second run: 8/10 - a *new* failure surfaced**, not the same one:
  1. `jpn_country` crashed: the model returned `sources` as one
     comma-separated string instead of a JSON list, failing Pydantic
     validation outright. Fixed with a `field_validator` on
     `Briefing.sources` that coerces a string into a list defensively, plus
     a tightened prompt showing the exact expected format.
  2. `kor_depot_direct` failed the faithfulness judge: the briefing cited
     "R²≈0.55" for a depot-only request where country risk data (and thus
     the model performance figure) was never retrieved. Root cause found:
     the Analyst system prompt's own guardrail example hardcoded
     `R^2 is 0.5464` as illustrative text, and the model was reciting it as
     a known fact regardless of what was actually in that call's retrieved
     bundle. Fixed by rewriting the prompt to only caveat with a
     performance figure if it's present in the current bundle, and adding
     an explicit "don't cite things you already know about this project,
     only what's in front of you now" instruction.
- **Third run: 10/10, clean.** All fixes committed and pushed (`ea21507`,
  `4188b6d`).

**Lesson worth keeping in mind:** the eval harness's most valuable catch
wasn't a crash, it was the faithfulness judge catching the guardrail
prompt itself leaking a hardcoded fact. Worth remembering when writing
prompts for this kind of grounded-briefing agent: illustrative examples
inside a "don't fabricate" instruction can themselves become the
fabrication source if they contain a real, specific number.

## MCP server (2026-08-05, roadmap item 4)

- **`mcp_server/` added**, wrapping `agent/` for any MCP client (Claude
  Desktop, MCP Inspector) - not a rewrite, pure glue over
  `agent.graph.compiled_graph` and `agent.tools.*`. Five tools: the
  flagship `ops_intel_get_briefing` (full LLM pipeline) plus four narrower
  read-only passthroughs (`ops_intel_get_country_risk`,
  `ops_intel_get_depot_capacity`, `ops_intel_get_route_utilization`,
  `ops_intel_search_methodology`) for when the full synthesis isn't needed.
  All read-only (`readOnlyHint: true`). See `mcp_server/README.md` for the
  Claude Desktop config snippet and MCP Inspector testing instructions.
- **SDK gotcha found while scaffolding (not yet run live - needs Gurinder's
  local BigQuery/Neo4j creds, same as always):** the current `mcp` PyPI
  package (verified against 2.0.0) has renamed `FastMCP` to `MCPServer` and
  moved it from `mcp.server.fastmcp` to `mcp.server.mcpserver`. Most
  tutorials/guides (including the mcp-builder skill's cached reference)
  still document the old `mcp.server.fastmcp.FastMCP` path, which does not
  exist in this installed version - importing it fails outright. Fixed by
  using `from mcp.server.mcpserver import MCPServer` instead; the rest of
  the interface (`.tool()` decorator, `.run()`) is unchanged. `requirements.txt`
  pinned to `mcp>=2.0.0` deliberately, since older 1.x releases use the old
  import path and would break this code.
- Scaffolded and import/registration-verified in the Cowork sandbox (all 5
  tools list correctly with `readOnlyHint=True`) but not yet tested against
  live BigQuery/Neo4j/Claude, and not yet installed into Claude Desktop -
  that's the next step, same pattern as `agent/` and `eval/` before it.

### Lesson learned: git lock files and the Cowork sandbox mount

The Cowork sandbox that mounts this repo **cannot unlink or rename files**
inside `.git/` (Operation not permitted on `rm`/`mv`) even though it can
create and overwrite them in place. This caused a real problem on
2026-08-05: an earlier Cowork session hit a stuck `.git/index.lock` after a
normal commit, worked around it with a manual `git commit-tree` +
direct-overwrite of `refs/heads/main`, but **left `.git/refs/heads/main.lock`
behind uncleaned** (couldn't delete it, and didn't flag it clearly enough at
the time). That stray lock file then sat on disk and later blocked a
completely unrelated real commit from VS Code/GitLens on Gurinder's actual
machine, with `cannot lock ref 'HEAD': Unable to create
.../refs/heads/main.lock: File exists` — cost a debugging detour before the
actual cause (a leftover file from an earlier Cowork session, not a live
process) was identified.

**If a Cowork session hits a stuck git lock again:** prefer asking Gurinder
to delete it via Windows (`Remove-Item .git\<path>.lock -Force`) first —
native Windows delete succeeds where the sandbox's `rm`/`mv` do not, per
direct evidence from this incident — rather than doing sandbox-side
`commit-tree`/ref-surgery workarounds. If a workaround is unavoidable,
**explicitly name every lock file left behind and its exact path** in the
same message, so it gets cleaned up immediately instead of surfacing as a
mystery failure in an unrelated later session.

## Roadmap (in priority order)

1. ✅ **Completed:** BigQuery pipeline (design, implementation, testing, verified metrics)
2. ✅ **Completed:** Neo4j supply-network graph (schema, seed data, read queries, tested)
3. ✅ **Completed (verified end-to-end 2026-08-05):** LangGraph multi-agent orchestration layer (reads both BigQuery and Neo4j for holistic supply-chain risk assessment), plus evals (`eval/`, 10/10 passing) and LangSmith tracing — see above. Cost-per-run tracking still open (minor, manual).
4. **Scaffolded, not yet run live (2026-08-05):** MCP server (`mcp_server/`) wrapping the platform — see above. Next: install into Claude Desktop / test with MCP Inspector.
5. **Pending:** Add geospatial map view for logistics risk
6. **Pending (Future):** Real-time event streaming and alerting
7. **Pending (Future):** API-driven data access with role-based access control

## Constraints

- WIP limit: this is the one active flagship project. Don't let scope drift
  into the other two flagship ideas (SITREP Job Intelligence Agent — blocked,
  source repo possibly deleted; German-Market Agent — not started).
- Keep the military-background → data-platform-strategy narrative; it's a
  deliberate positioning choice, not filler.
- Don't reintroduce vendor-specific (Y42) pitch language anywhere.

## Context continuity

Gurinder runs Claude Code in Antigravity/VS Code for hands-on repo work, and
uses Claude in Cowork (a separate session) to track overall project state in
a Neo4j graph (Focus Guardian: Project → FlagshipProject → NextStep/CheckIn).
After a Claude Code session, paste a summary of what changed back into the
Cowork session so it can update that tracker and this file. Update this
CLAUDE.md's "Current known state" section whenever real progress is made, so
it stays the source of truth instead of memory.
