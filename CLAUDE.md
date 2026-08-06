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
- **Verified working end-to-end via MCP Inspector (2026-08-05).**
  `ops_intel_get_country_risk({"country_code": "KOR"})` returned the correct
  BigQuery row. `ops_intel_get_briefing({"country_code": "KOR"})` ran the
  full pipeline through the MCP layer and produced the same quality SITREP
  as the direct FastAPI endpoint - correctly flagging the KOR
  LOW-risk/OVER_CAPACITY compounding pattern. Confirms the MCP wrapper adds
  no regressions versus calling `agent/` directly.
- **MCP Inspector UI quirk found:** its JSON param editor for object-typed
  tool inputs (`params: CountryRiskInput` etc.) auto-escapes quote
  characters as you type, making manual editing produce stray `\`
  characters. Workaround: select all existing content with a mouse drag
  (not Ctrl+A - didn't reliably select in this field) and paste
  (Ctrl+V) the full JSON to overwrite in one shot, rather than typing
  character by character.
- **Installed into Claude Desktop and verified live (2026-08-05).** Hit one
  real gotcha: the `cwd` key in the server config isn't honored by Claude
  Desktop, so `python -m mcp_server.server` couldn't find the `mcp_server`
  package (`ModuleNotFoundError: No module named 'mcp_server'` in the MCP
  log). Fixed by adding `PYTHONPATH` (pointing at the repo root) to the
  `env` block instead of relying on `cwd`. After that: "Server started and
  connected successfully." Confirmed working from a completely separate
  Claude session (Cowork) calling `ops_intel_get_country_risk` live -
  full-circle proof the server works for any MCP client, not just the one
  it was configured in. **Roadmap item 4 is now fully done: built, fixed,
  verified via Inspector, installed, and verified live in Claude Desktop.**

### MCP server bug found and fixed: relative CHROMA_PERSIST_DIR breaks under Claude Desktop (2026-08-06)

- **Found via a Cowork status check** (calling the live `ops-intel-agent`
  MCP tools directly, not just reading code): `ops_intel_get_country_risk`
  and `ops_intel_get_depot_capacity` worked (BigQuery/Neo4j both live and
  fresh), but `ops_intel_get_briefing` failed with `AttributeError:
  'RustBindingsAPI' object has no attribute 'bindings'`, and
  `ops_intel_search_methodology` failed with `Access is denied (os error
  5)`.
- **Root cause:** `agent/config.py`'s `CHROMA_PERSIST_DIR` default was the
  relative string `"agent/vector_store"`, which resolves against the
  process's cwd. `agent/ingest_docs.py` had always been run manually from
  the repo root, so the index built correctly on disk - masking the bug.
  But the MCP server, launched by Claude Desktop, only has `PYTHONPATH` set
  (per the 2026-08-05 `cwd`-not-honored note above), not an actual working
  directory at the repo root. So the relative path resolved elsewhere,
  chromadb's Rust `Bindings()` constructor failed opening/creating the
  sqlite file there (Windows error 5, access denied), and left the client
  half-constructed - which is why the *next* call surfaced as the unrelated
  -looking `AttributeError` instead of the real cause. `agent/agents/
  retriever.py` always calls `search_methodology` as part of retrieval, so
  this took the whole briefing pipeline down with it, not just the
  standalone search tool.
- **Why earlier verification missed it:** the 2026-08-05 "verified via MCP
  Inspector" test of `ops_intel_get_briefing` ran from the repo root
  (masking the cwd bug); the separate "verified live in Claude Desktop"
  test that same day only exercised `ops_intel_get_country_risk`, which
  never touches the vector store. The two verifications together looked
  like full coverage but had a gap.
- **Fix:** `agent/config.py` now anchors the default to `Path(__file__)`'s
  own location instead of cwd, so it resolves correctly regardless of
  launch directory. `.env.example` and `mcp_server/README.md` updated with
  notes so this doesn't get silently reintroduced.
- **Re-verified live (2026-08-06), after Gurinder restarted Claude
  Desktop:** `ops_intel_get_briefing({"country_code": "KOR"})` ran the
  full pipeline clean - correctly flagged the MEDIUM-risk/OVER_CAPACITY
  compounding pattern, identified the depot (not routes) as the
  bottleneck, and properly caveated that the R²=0.5464 model wasn't
  applied to this classification. `ops_intel_search_methodology` also
  confirmed working (real chunks from neo4j/README.md,
  data_dictionary.md, AUDIT.md). Committed natively by Gurinder as
  `ad55d07` (sandbox git couldn't commit - see the git lock lesson
  below, which this incident finally explained).

### Lesson learned: git lock files and the Cowork sandbox mount

**ROOT CAUSE FOUND (2026-08-06) - read this before running ANY git command
from a Cowork sandbox in this repo:**

The repo is mounted into the Cowork sandbox as a FUSE filesystem
(`fuseblk`) that can *create* files inside `.git/` but **cannot unlink or
rename them**. Git's locking protocol is create `index.lock` → write new
index into it → rename over `index`. The rename/unlink step fails with
`Operation not permitted` on this mount, so **every index-writing git
command run from the sandbox leaves a stray `index.lock` behind** - which
then blocks the next git command (sandbox or native) with `File exists`.
Crucially, even plain `git status` does this: it opportunistically
refreshes the index (takes the lock, rewrites, renames). This is why the
lock kept "mysteriously reappearing" after Gurinder deleted it on
2026-08-06 - each sandbox `git status`/`git commit` retry was recreating
it. It also explains the original 2026-08-05 incident below.

**Standing rules for Cowork sessions in this repo:**

1. **Never run `git add`, `git commit`, or any index-writing git command
   from the sandbox.** Edit files only; Gurinder commits natively
   (PowerShell/VS Code), where unlink works fine.
2. **Read-only git (status/log/diff) must set `GIT_OPTIONAL_LOCKS=0`**
   (or use `git --no-optional-locks`) so `git status` skips the
   opportunistic index refresh and takes no lock at all. Verified working
   2026-08-06: status ran clean, no lock created.
3. If a stray lock or `tmp_obj_*` litter does appear, ask Gurinder to
   remove it natively (`Remove-Item .git\<path> -Force`) - do not attempt
   sandbox-side workarounds.

Original incident (2026-08-05), kept for the record:

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

## Geospatial map view (2026-08-05, roadmap item 5)

- **Standalone Leaflet page added**, per Gurinder's choice of "standalone
  page" over embedding in an existing UI (this repo still has no other
  frontend). `agent/static/map.html` — dark CARTO basemap via CDN, no build
  tooling. Two layers on one map: country risk (circle markers, colored by
  `risk_level`) from BigQuery, and depot capacity (diamond markers, colored
  by `capacity_status`) from Neo4j. Served at `GET /map`; data comes from a
  new `GET /map-data` endpoint (no LLM call, two direct reads combined).
- **Real depot coordinates added** to `neo4j/02_seed_data/depots.cypher`
  (public lat/long for all 8 depot locations — CONUS/Norfolk, Shanghai,
  Ramstein, Yokosuka, Portsmouth, Darwin, Istres, Osan), via `MERGE`+`SET`
  so re-running against the already-seeded database updates in place rather
  than duplicating. `neo4j/README.md` updated with a note that pre-2026-08-05
  seeds need this script re-run to pick up coordinates.
- New helper functions (not LangChain `@tool`s — plain data-fetch helpers,
  since no LLM needs "all countries"/"all depots" as a single call):
  `query_all_countries_risk()` in `agent/tools/bigquery_tools.py` (joins
  `marts.country_risk_assessment` to `raw_data.countries` for lat/long),
  `query_all_depots_capacity()` in `agent/tools/neo4j_tools.py`.
- Sanity-checked in the Cowork sandbox: `py_compile` clean on all three
  edited Python files (`agent/api.py`, `agent/tools/bigquery_tools.py`,
  `agent/tools/neo4j_tools.py`); `map.html` checked for balanced structure,
  required CDN/script references, and the `/map-data` fetch call.
- **Docs fixed while here:** `mcp_server/README.md`'s Claude Desktop config
  snippet still had the `"cwd"` key that was already known (per the MCP
  server section below) not to work — corrected to the `PYTHONPATH`-in-`env`
  form that Gurinder actually confirmed working, with an explanatory note so
  this doesn't get silently reverted later. `agent/README.md` got a new
  "Map view" section and an updated module map.
- **Live-verified by Gurinder (2026-08-06)** at `http://localhost:8000/map`
  — both marker layers render correctly. Committed and pushed as `b5099af`
  ("Add geospatial map view (roadmap item 5)"). One real hiccup along the
  way: a Cowork-sandbox commit attempt hit the same stuck-`.git/index.lock`
  issue documented below, and Gurinder had to manually delete the lock file
  via PowerShell before his own `git commit`/`git push` would run — consistent
  with the standing rule to prefer native-OS deletion over sandbox workarounds.
  **Roadmap item 5 is now fully done: built, documented, live-tested, committed.**

### Case study + reference docs (2026-08-06)

- **`Operations_Intelligence_Agent_Case_Study.pdf`** (repo root, not committed
  to git — a generated deliverable, not source) — a 15-page, non-technical
  case study built for job-search use: the project's origin/military-to-data
  narrative, a plain-language walkthrough of the KOR compounding-risk
  example, all six build phases with the real bugs hit and how each was
  fixed (BigQuery `%`-operator/column-mismatch/NULL-type bugs, the Neo4j
  depot over-capacity calibration bug, the LangGraph truncation/temperature/
  sources-format bugs, the R²-hallucination-leak eval catch, the MCP SDK
  rename, the git-lock incident), verified results tables, the roadmap, and
  a 10-question interview-prep appendix with answers drawn directly from
  these real incidents. Built as HTML + CSS rendered to PDF via `weasyprint`
  (installed ad hoc in the Cowork sandbox), verified page-by-page (15 pages,
  no overflow/cutoff) before handoff.
- **Full cross-database parameter/column reference produced** (chat-delivered,
  not a saved file) — every column in `raw_data.countries`, `raw_data.trade_flows`,
  `staging.global_events`, both `marts.*` views, `models.supply_chain_training_data`,
  and the `supply_chain_risk_predictor` model's input/output features; plus
  every property on Neo4j's `Depot`/`Route`/`Requisition` nodes. Sourced
  directly from the current SQL/Cypher files, not from `AUDIT.md` (which
  predates the Phase-1 bug fixes and would be stale for this purpose).

## Plan deviation: BI dashboard twin formally descoped (2026-08-06)

The original portfolio plan (`docs/Gurinder_AI_Agent_Portfolio_Plan.md`,
Project 2 deliverable) called for "expose the same briefing as a Power BI
or Tableau dashboard alongside the chat interface, so one project visibly
serves both the AI agent engineer and BI/data analyst audiences." This is
now **explicitly descoped, not an oversight** — decided 2026-08-06 during a
Cowork status-check session.

Reasoning: `neo4j/README.md` had already flagged this direction informally
("no application/UI layer yet... the LangGraph/MCP layers below may end up
being how this data gets exposed rather than a hand-built dashboard"), and
by 2026-08-06 that's exactly what happened — the MCP server (5 tools, any
MCP client), the FastAPI `/briefing` + `/map` endpoints, and the geospatial
map view together already serve both audiences without a second
hand-built BI tool duplicating the same country-risk/depot-capacity data.
Building a separate Power BI/Tableau twin now would be maintaining two
presentation layers over one dataset for no functional gain — the
`{query_country_risk, query_depot_capacity}` tool functions are already
BI-analyst-legible outputs (structured JSON with clear field names,
documented in `docs/data_dictionary.md`), and a screen-recording of the
`/map` view plus a walked-through MCP Inspector session covers the "prove
you can bridge AI-agent and BI-analyst roles" interview need just as well.

If this decision needs revisiting later (e.g. a specific BI-analyst-track
application explicitly wants to see a Power BI file), it's a small,
well-scoped addition at that point — not blocking anything else in the
meantime.

## Roadmap (in priority order)

1. ✅ **Completed:** BigQuery pipeline (design, implementation, testing, verified metrics)
2. ✅ **Completed:** Neo4j supply-network graph (schema, seed data, read queries, tested)
3. ✅ **Completed (verified end-to-end 2026-08-05):** LangGraph multi-agent orchestration layer (reads both BigQuery and Neo4j for holistic supply-chain risk assessment), plus evals (`eval/`, 10/10 passing) and LangSmith tracing — see above. Cost-per-run tracking still open (minor, manual).
4. ✅ **Completed (installed + live-verified in Claude Desktop, 2026-08-05):** MCP server (`mcp_server/`) wrapping the platform — see above.
5. ✅ **Completed (live-verified by Gurinder, 2026-08-06):** Geospatial map view for logistics risk (`agent/static/map.html`, `GET /map`) — see above. Committed as `b5099af`.
6. **Pending (Future):** Real-time event streaming and alerting
7. **Pending (Future):** API-driven data access with role-based access control

**All five near-term roadmap items are now complete and verified live.**
A non-technical case study (PDF) and a full cross-database parameter
reference were produced 2026-08-06 for job-search use — see the "Case study
+ reference docs" section above. Remaining items (6-7) are explicitly
longer-term/future, not actively being worked.

**In progress (2026-08-06): public deployment.** The plan's own
non-negotiables (§5, "Deployed, not just cloned locally... every project
needs a live URL") aren't met yet — everything currently runs on
`localhost:8000`. Decided to deploy to **GCP Cloud Run** (reuses the
already-provisioned `ops-intel-logistics` project/auth rather than a new
platform account). This surfaced a real blocker: Neo4j is currently a
**local** Neo4j Desktop instance (`neo4j://localhost:7687`), which Cloud
Run cannot reach. Decided to **migrate to Neo4j AuraDB Free** rather than
ship a BigQuery-only/depot-data-missing demo. AuraDB Free is single-database
(no `CREATE DATABASE opsintel-supply-network` like the local Enterprise
instance) — the migrated instance uses the default `neo4j` database name,
so `NEO4J_DATABASE` changes from `opsintel-supply-network` to `neo4j` for
the cloud deployment. `Dockerfile` and `.dockerignore` added in this
session, targeting Cloud Run specifically (reads `$PORT`, relies on the
attached service account for BigQuery ADC instead of a baked-in key).
While building the image spec, found and fixed a second real bug:
`agent/ingest_docs.py` was calling `agent.config.load_settings()`, which
requires `ANTHROPIC_API_KEY` and all three `NEO4J_*` vars even though
building the doc index needs neither — that would have broken the
Docker build step (which runs `ingest_docs.py` at build time so the
vector index doesn't need to be built on every cold start). Decoupled:
`ingest_docs.py` now reads only `CHROMA_PERSIST_DIR`/`EMBEDDING_MODEL`
directly instead of going through the full Settings dataclass. **Not yet
deployed** — next steps are the AuraDB migration (Gurinder needs to
create the instance and re-run the seed scripts against it; the sandbox's
`mcp__neo4j__*` connector was checked and found to be bound to the
separate Focus Guardian project-tracking graph, not this project's data,
so it can't be used for this).

**AuraDB Free instance created and seeded (2026-08-06).** Instance
`028e4334` (name `opsintel-supply-network`), region as chosen in Aura
console. One real correction to the plan above: Aura's generated
credentials file sets `NEO4J_USERNAME` and `NEO4J_DATABASE` to the
instance ID (`028e4334`), not the literal string `neo4j` as assumed
earlier — fixed in `.env.example` and `neo4j/README.md`. Migrated via
Neo4j Desktop's "Deploy to Aura" (export local `opsintel-supply-network`
→ deploy to the new Aura instance) rather than manually re-running the
seed scripts — confirmed both steps succeeded in the Desktop UI.
**Verified directly from Cowork** (installed the `neo4j` Python driver in
the sandbox and queried the live Aura instance, independent of Gurinder's
machine): node counts exact match (8 Depot, 56 Route, 2160 Requisition),
all 3 uniqueness constraints present, `DEPOT_KOR` data byte-identical to
local including the 2026-08-05 lat/long addition. `.env` updated to point
at Aura; the downloaded `Neo4j-028e4334-Created-*.txt` credentials file
is gitignored (`Neo4j-*-Created-*.txt` pattern added) and should be
deleted from disk now that its values are in `.env`.

**Deployed live to Cloud Run (2026-08-06).** Service `ops-intel-agent`,
region `europe-west3`, project `ops-intel-logistics`. Public URL:
**https://ops-intel-agent-960432556484.europe-west3.run.app**

Real issues hit and fixed during the deploy (all from Gurinder's machine,
`gcloud` not available in the Cowork sandbox):
1. `gcloud projects add-iam-policy-binding` for the default compute SA
   failed with "Service account does not exist" — this project had never
   enabled the Compute Engine API, so that SA was never auto-created.
   Fixed by not depending on it at all: created a dedicated
   `ops-intel-agent-sa` service account scoped to just this service
   (least-privilege, and sidesteps the missing-default-SA issue) with
   `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`, passed via
   `gcloud run deploy --service-account`.
2. First `gcloud run deploy --source .` attempt failed at the build stage:
   `PERMISSION_DENIED... default service account is missing required IAM
   permissions` for `960432556484-compute@developer.gserviceaccount.com`
   reading the uploaded source from GCS. This is a *different* service
   account concern than #1 - Cloud Build's own build-step identity
   (Google migrated this to the project's compute default SA, which has
   zero permissions by default, away from the old broadly-privileged
   Cloud Build SA). Fixed by granting that account
   `roles/cloudbuild.builds.builder` at the project level.
3. Second attempt built and deployed clean.

**Verified live from Cowork** (independent network from Gurinder's
machine - real proof of public reachability, not just "works on my
laptop"): `/health` → `{"status":"ok"}`; `/map-data` → real BigQuery rows
with coordinates for CHN/USA/PHL/IDN/ESP/IND/VNM/MYS/ZAF and more;
`/briefing` (KOR) → full three-agent SITREP, same quality as every prior
local verification - correctly flags the MEDIUM-risk/OVER_CAPACITY
compounding pattern, identifies the depot (not routes) as the bottleneck,
properly caveats that no risk_score was retrieved for this bundle and
that R²=0.5464 only explains about half of variance; `/map` → 200,
`text/html`.

**Public deployment (plan §5 non-negotiable) is now satisfied.** Only
remaining loose end: `Neo4j-028e4334-Created-*.txt` should be deleted
from the repo root now that its values are in both `.env` (local) and
the Cloud Run service's env vars (deployed) - it's gitignored so it was
never at risk of being committed, but it's still a live plaintext copy
of working credentials sitting on disk unnecessarily.

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
