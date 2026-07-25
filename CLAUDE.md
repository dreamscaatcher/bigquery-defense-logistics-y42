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
  **Not yet committed/pushed** — see pending NextStep.
- No Neo4j, no LangGraph, no MCP server, no geospatial view exist in this repo
  yet — those are roadmap items, not built.

## Roadmap (in priority order)

1. **Next:** commit + push the train/test split change. Then move on to
   the bigger roadmap items below.
2. Fold in a Neo4j-based supply-network graph layer. Schema TBD — a
   demand-vs-capacity "supply planning" component was prototyped in a
   separate repo (`E-Commerce`) against generic Order/Product nodes; it needs
   a real defense-logistics schema (e.g. shipment/requisition demand vs.
   route/depot capacity) before it's reusable here.
3. Add a LangGraph multi-agent orchestration layer.
4. Wrap the platform in an MCP server.
5. Add a geospatial map view for logistics risk.

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
