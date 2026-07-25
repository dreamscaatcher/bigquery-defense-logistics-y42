# Implementation Tracking: Defense & Logistics Risk Intelligence Platform

**Last Updated:** 2026-07-26 | **Status:** BigQuery pipeline + Neo4j graph both built, executed, and verified

---

## Overview

This document tracks all implementations and modifications to the Defense & Logistics Risk Intelligence Platform (now the Operations Intelligence Agent). Each session logs changes, issues encountered, and current status.

**Attribution note:** All code edits, terminal commands (gcloud/bq CLI), and Neo4j Browser/Desktop actions described below were executed manually by Gurinder on his own machine, working from debugging and instructions worked out interactively in a Claude (Cowork) chat session. No autonomous Claude Code agent session ran these commands independently — earlier drafts of this document implied otherwise and have been corrected.

---

## Session 1: Code Audit & Pipeline Reproducibility Fixes (2026-07-25 → 2026-07-26)

### Objective
Audit the BigQuery pipeline for reproducibility, consistency, and documentation quality. Fix identified issues.

### Issues Identified (via AUDIT.md)
1. ❌ Missing 30-day time filter on `country_risk_assessment` view (semantic bug)
2. ❌ Raw data tables (`countries`, `trade_flows`) schema-only, no loads
3. ❌ Non-deterministic RAND()-based event generation
4. ❌ Hardcoded country-name → sentiment mapping (geopolitical bias)
5. ❌ Model evaluation queries commented out; R²=0.62/MAE=0.26 unverified
6. ❌ Documentation fluff: `architecture.md` and `y42_insights.md` are 95-100% Y42 marketing

### Implementations Completed

#### 1. Added 30-day Time Filter ✅
**File:** `sql/04_marts/business_intelligence.sql`
**Change:** Added `AND e.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)` to LEFT JOIN condition
**Impact:** Column `total_events_30d` now semantically accurate; filters events to 30-day rolling window

#### 2. Populated Raw Data with Real Countries ✅
**File:** `sql/02_raw_data/create_tables.sql`
**Change:** Added INSERT statement with 31 real countries (USA, GBR, DEU, FRA, JPN, CHN, IND, RUS, AUS, CAN, KOR, NOR, SWE, DNK, POL, ITA, ESP, BRA, MEX, ZAF, EGY, SAU, ARE, ISR, SGP, IDN, THA, VNM, MYS, PHL, NZL)
**Data Points:** country_code, country_name, region, sub_region, latitude, longitude, population, gdp_usd

#### 3. Generated Deterministic Trade Flows ✅
**File:** `sql/02_raw_data/create_tables.sql`
**Change:** Replaced empty schema with deterministic synthetic data generation using FARM_FINGERPRINT
**Method:** Hash-based pseudo-random generation keyed on (trade_date, exporter, importer, commodity)
**Volume:** ~20,000 trade records across 90 days, 8 countries, 4 commodity categories

#### 4. Replaced RAND() with Deterministic Event Generation ✅
**File:** `sql/03_staging/global_events.sql`
**Change:** Replaced RAND()-based generation with FARM_FINGERPRINT-based approach
**Key Improvements:** removed hardcoded country-name → sentiment bias (Syria/Afghanistan negative, Norway positive); neutral sentiment distribution keyed on fingerprint hash

#### 5. "Uncommented" ML Model Evaluation Queries ⚠️ (cosmetic only — see Session 2)
**File:** `sql/05_ml_models/predictive_analytics.sql`
**Change made this session:** Changed `--` line comments to `/* ... */` block comments
**Correction (discovered in Session 2):** this only changed the comment *style* — the queries were still inert block comments, not live SQL. The evaluation queries were not actually executable until fixed in Session 2.

#### 6. Deleted Marketing Documentation ✅
**Files Deleted:** `docs/architecture.md` (134 lines, 95% Y42 positioning), `docs/y42_insights.md` (242 lines, 100% sales pitch)
**Files Kept:** `docs/data_dictionary.md` — legitimate technical reference

#### 7. Updated README.md ✅
Removed unverified claims (R²=0.62, MAE=0.26), marked old metrics `[UNVERIFIED]`, added evaluation instructions.

### Commit Record
**Hash:** `197436f` — "Fix pipeline reproducibility and data quality issues"

### Blockers Encountered
**BigQuery CLI Access:** `gcloud` and `bq` not available in the environment used for this session.
- **Resolution:** Code prepared; pipeline execution deferred to a session with a real GCP project and CLI access (Session 2).

### Current Status (end of Session 1)
✅ Code changes made and reviewed for syntax
⏳ Pipeline never actually executed yet — everything below is still unverified at this point
⏳ Model metrics still unverified

---

## Session 2: Project ID Migration & Manual Pipeline Execution (2026-07-26)

### Objective
Migrate hardcoded project IDs to a real GCP project (`ops-intel-logistics`), then run the full pipeline end-to-end for the first time ever and capture real model evaluation metrics.

### Implementations Completed

#### 1. Project ID Migration ✅
Replaced all occurrences of the placeholder project ID with `ops-intel-logistics` across `01_setup` through `05_ml_models` — 25 occurrences total.

#### 2. Manual Pipeline Execution ✅
Gurinder set up the `ops-intel-logistics` GCP project, installed and authenticated `gcloud`/`bq` in WSL, and ran each stage manually from his own terminal:
```bash
bq query --use_legacy_sql=false < sql/01_setup/create_datasets.sql
bq query --use_legacy_sql=false < sql/02_raw_data/create_tables.sql
bq query --use_legacy_sql=false < sql/03_staging/global_events.sql
bq query --use_legacy_sql=false < sql/04_marts/business_intelligence.sql
bq query --use_legacy_sql=false < sql/05_ml_models/predictive_analytics.sql
```
This was the pipeline's **first real execution ever** (it had only ever been code-reviewed before, never run). Running it for real surfaced three genuine bugs that pure code review had missed — see below.

**Outputs Created:**
- 4 datasets (raw_data, staging, marts, models)
- 31 countries loaded into raw_data.countries
- 20,160 trade flows generated in raw_data.trade_flows (deterministic)
- 2,790 events generated in staging.global_events (deterministic)
- 2 views (country_risk_assessment, supply_chain_intelligence)
- 1 training table (supply_chain_training_data)
- 1 BQML linear regression model (supply_chain_risk_predictor)

#### 3. Model Evaluation ✅
**Actual metrics captured (held-out 20% test set, ~4,032 rows, via `MOD(ABS(FARM_FINGERPRINT(trade_id)), 100) < 80` split):**

| Metric | Value |
|--------|-------|
| r2_score | 0.5464 |
| mean_absolute_error | 0.2631 |
| mean_squared_error | 0.1043 |
| explained_variance | 0.5465 |

Model trained on the 80% partition (~16,128 rows), evaluated only on the held-out 20% — genuine out-of-sample metrics, not in-sample. (An in-sample check against the full table, done before the split was added, had shown R²=0.5365 — consistent, no meaningful overfitting.)

#### 4. README Updates ✅
Replaced `[UNVERIFIED]` placeholders with real measured metrics, added the risk distribution table, documented the train/test split methodology.

### Bugs Found & Fixed During Execution

These three bugs only surfaced because the pipeline was actually run for the first time — none were caught by code review:

**Bug #1: `%` is not a valid operator in BigQuery Standard SQL** ✅
- **Files:** `sql/02_raw_data/create_tables.sql`, `sql/03_staging/global_events.sql` (multiple occurrences across both)
- **Root cause:** BigQuery Standard SQL has no `%` modulo operator at all — it only supports the `MOD(a, b)` function. This is a hard syntax restriction, not an overflow or range issue.
- **Fix:** Replaced every `x % y` with `MOD(x, y)` in both files (value_multiplier generation, event type CASE branching, event_tone/goldstein_scale mapping).

**Bug #2: INSERT column-count mismatch** ✅
- **File:** `sql/03_staging/global_events.sql`
- **Root cause:** The `INSERT INTO staging.global_events` column list only named 7 columns, but the SELECT produced 12 — BigQuery rejected it ("Has 12, expected 7").
- **Fix:** Listed all 12 target columns explicitly, in the same order as the SELECT: `event_id, event_date, event_type, country_code, actor1_country, actor2_country, event_tone, goldstein_scale, latitude, longitude, source_url, processed_at`.

**Bug #3: Untyped NULL literals defaulting to INT64** ✅
- **File:** `sql/03_staging/global_events.sql`
- **Root cause:** Bare `NULL` literals for `actor2_country`/`source_url` (STRING) and `latitude`/`longitude` (FLOAT64) default to INT64 in BigQuery, causing "type INT64 cannot be inserted into column ... which has type STRING/FLOAT64".
- **Fix:** Explicit casts — `CAST(NULL AS STRING)`, `CAST(NULL AS FLOAT64)`.

**Also fixed: cosmetic-only "uncommenting" from Session 1** ✅
- The evaluation/prediction queries in `05_ml_models/predictive_analytics.sql` were still inert block comments after Session 1 (only the comment delimiter had changed, not the fact that it was still a comment). Removed the `/* */` wrapper entirely so the queries genuinely execute as live SQL.

### Current Status
✅ Project ID migration complete
✅ Pipeline executed end-to-end for the first time, all 5 stages succeeded after the 3 bug fixes above
✅ Model evaluation complete, real metrics captured
✅ README updated with verified data
✅ **Commit:** `8465c7d` — "Run pipeline end-to-end against ops-intel-logistics, fix 3 real SQL bugs found only by execution, record verified model metrics"

### Outcomes
- **Risk Distribution:** 15 countries MEDIUM, 16 LOW, 0 HIGH (out of 31 real countries) — replaces the old fabricated 249-country table left over from the original demo
- **Model R² Score:** 0.5464 — replaces the old unverified 0.62 claim
- **Determinism confirmed:** all data generation is deterministic; re-running the pipeline reproduces identical numbers

### Follow-up: Train/Test Split (same day, 2026-07-26)
`05_ml_models/predictive_analytics.sql` was updated to add a proper held-out split: `trade_id` added to the training_data SELECT, `MOD(ABS(FARM_FINGERPRINT(trade_id)), 100) < 80 AS is_training` added, `data_split_method='NO_SPLIT'` set on the model, training query filtered to the 80% partition, and the evaluation query rewritten to explicitly evaluate only on the held-out 20%. Verified held-out metrics: **R²=0.5464, MAE=0.2631, MSE=0.1043, explained_variance=0.5465** (the numbers already shown above — this table already reflects the held-out run, not the earlier in-sample one). **Commit:** `5fe86c2`.

---

## Session 3: Neo4j Supply-Network Graph — Schema & Seed Files (2026-07-26)

### Objective
Design a Neo4j graph layer modeling defense-logistics resupply demand vs. capacity, separate from (but narratively connected to) the BigQuery trade/risk analytics. Scoped deliberately to schema + seed data + read queries only — no application/UI layer.

### Implementations Completed

#### 1. Graph Schema Definition ✅
**File:** `neo4j/01_schema/constraints.cypher`
Unique constraints on `depot_id`, `route_id`, `requisition_id`; indexes on `requisition.request_date` and `depot.country_code`.

#### 2. Node Types ✅
**Depot** — `depot_id`, `country_code`, `name`, `depot_type` (SUPPLY_DEPOT/PORT/AIRBASE/FORWARD_OPERATING_BASE), `capacity_per_day`. 8 depots, reusing the same 8 country codes as BigQuery's trade_flows (USA, GBR, DEU, FRA, JPN, CHN, KOR, AUS).

**Route** — `route_id`, `mode` (AIR/SEA/GROUND), `transit_days`, `capacity_per_day`. 56 routes (all ordered pairs of depots), parameters deterministically derived from a pair-index hash.

**Requisition** — `requisition_id`, `request_date`, `quantity`, `commodity_category`, `priority` (ROUTINE/PRIORITY/URGENT). ~2,160 requisitions (8 depots × 90 days × ~3/day).

#### 3. Relationship Types ✅
`(:Route)-[:ORIGINATES_AT]->(:Depot)`, `(:Route)-[:TERMINATES_AT]->(:Depot)`, `(:Requisition)-[:REQUESTED_AT]->(:Depot)`, `(:Requisition)-[:FULFILLED_VIA]->(:Route)`

#### 4. Deterministic Seed Data ✅
- `neo4j/02_seed_data/depots.cypher` — capacities calibrated by tier (see Session 4 for the calibration bug found when this was actually run)
- `neo4j/02_seed_data/routes.cypher` — seed `((i * 92821) + (j * 15485867)) % 10000`
- `neo4j/02_seed_data/requisitions.cypher` — seed `((i * 2654435761) + (day_offset * 40503) + (req_num * 7919)) % 100000`, priorities weighted 70/20/10 ROUTINE/PRIORITY/URGENT

#### 5. Read Query Suite ✅
**File:** `neo4j/03_queries/demand_vs_capacity.cypher` — daily demand vs. capacity, weekly demand vs. capacity, overall 90-day utilization summary (with WITHIN/NEAR/OVER capacity status), route utilization.

### Design Philosophy
Same 8 country codes as BigQuery so the two systems model the same logistics network from two angles (BigQuery = macro/country-level trade risk, Neo4j = micro/depot-level physical capacity). No RAND() or database sequences anywhere — every value is arithmetic on indices/dates, so re-running the seed scripts against a fresh database reproduces an identical graph.

### Status at end of Session 3
✅ All schema/seed/query files written
⚠️ **Not yet run against a live database at this point** — see Session 4, where this was actually executed and verified, and a real calibration bug was found.

---

## Session 4: Neo4j Database Setup, Seeding & Verification (2026-07-26)

### Objective
Actually create the Neo4j database, run the schema/seed/query files against it, and verify the results — none of which had happened yet at the end of Session 3.

### What Gurinder did manually (in Neo4j Desktop / Browser)
1. Created a dedicated database, `opsintel-supply-network` (separate from the Focus Guardian project-tracking graph). Note: underscores are not legal in Neo4j database names — had to use dashes.
2. Ran `constraints.cypher`, then `depots.cypher`, `routes.cypher`, `requisitions.cypher`, then the read query suite, pasting output back for verification at each step.

### Verified Results ✅
- 3 constraints + 2 indexes online
- 8 depots, 56 routes, 2,160 requisitions
- Priority split exactly 1,512 / 432 / 216 = 70/20/10 as designed
- Route utilization 54–76%, comfortably within capacity

### Bug Found & Fixed: Depot Capacity Calibration ✅
- **Issue:** The depot `capacity_per_day` values chosen in Session 3 (200–500) were narrative guesses, never checked against what the requisitions generator actually produces (~493–523/day average demand per depot, ~698–794/day peak). As a result, every single depot came back `OVER_CAPACITY` — trivially, not meaningfully.
- **Fix:** Recalibrated capacities to 260–900, scaled by depot tier (rear-area hubs like USA/CHN highest, forward bases like KOR/FRA lowest), re-running the MERGE-based seed script (idempotent, no duplication).
- **Result:** A realistic mixed outcome — USA/CHN `WITHIN_CAPACITY`, DEU borderline (fine on average, peak-day-only overage), JPN/GBR/AUS/FRA/KOR increasingly over capacity, KOR (forward operating base) most strained. A coherent "forward positions are hardest to keep supplied" pattern, not an artifact of bad calibration.

### Current Status
✅ **Commit:** `419bc8a` — "Add Neo4j supply-network graph: schema, deterministic seed data, demand-vs-capacity queries" (includes the recalibrated depot capacities)
✅ **Commit:** `9ccbdad` — "Document Neo4j implementation and final session status"
✅ Neo4j layer fully built, seeded, and verified against the live instance — nothing here is still pending

### Known Limitations (deliberate, not gaps)
- No application/UI layer — schema and read queries only, by design (this repo has no frontend yet; the LangGraph/MCP layers may end up being how this data gets exposed instead of a hand-built dashboard)
- Static seed data — requisitions are pre-generated, not simulated in real time
- FULFILLED_VIA edges are deterministically assigned, not computed from constraint satisfaction

---

## Known Issues & Resolutions

| Issue | Status | Details |
|-------|--------|---------|
| `created_at` vs `trade_date` mismatch | ⏳ Open | `trade_flows.created_at` is set to `CURRENT_TIMESTAMP`; `trade_date` may be historical. Doesn't block execution but could affect partition pruning in future queries. |
| Model metrics unverified | ✅ Resolved | Held-out evaluation run in Session 2: R²=0.5464, MAE=0.2631, MSE=0.1043, explained_variance=0.5465. |
| BBC News public dataset dependency | ✅ Removed | Replaced with deterministic generation; no external dataset dependency remains. |
| Neo4j depot capacity calibration | ✅ Resolved | Fixed in Session 4 — see above. |

---

## Implementation Statistics

- **SQL files modified:** 5 (01_setup through 05_ml_models)
- **Documentation files deleted:** 2 (376 lines of marketing copy)
- **Neo4j files created:** 6 (constraints, 3 seed files, read query suite, README)
- **Real bugs found only by execution (not caught by code review):** 4 total — `%` operator misuse, INSERT column-count mismatch, untyped NULL type mismatch (all BigQuery), plus the Neo4j capacity calibration bug

---

## Roadmap Status (matches CLAUDE.md)

### Completed ✅
1. BigQuery pipeline — design, implementation, bug fixes, verified held-out model metrics
2. Neo4j supply-network graph — schema, seed data, read queries, seeded and verified against a live database

### Ready to Start
3. LangGraph multi-agent orchestration layer (reads both BigQuery and Neo4j for holistic supply-chain risk assessment)

### Pending
4. Wrap the platform in an MCP server
5. Add geospatial map view for logistics risk
6. (Future) Real-time event streaming and alerting
7. (Future) API-driven data access with role-based access control

---

**Document maintained across:** Claude (Cowork) sessions for planning/debugging + manual execution by Gurinder in WSL and Neo4j Desktop. No autonomous Claude Code agent session has executed commands in this repo to date.
**Last Updated:** 2026-07-26
