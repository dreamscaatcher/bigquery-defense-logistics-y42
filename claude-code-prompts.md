# Claude Code Prompts — Operations Intelligence Agent

Running log. Paste each prompt into Claude Code inside this repo, one at a
time. After each one finishes, bring the output (or a summary) back to the
Cowork session so it can be logged and the next prompt tailored to what's
actually there.

---

## Prompt 1 — Audit before deciding rebuild vs. extend (done)

```
Read every file in this repository: README.md, docs/architecture.md,
docs/data_dictionary.md (if present), and everything under sql/01_setup
through sql/05_ml_models. Do not modify anything yet.

Produce a new file, AUDIT.md, containing:

1. What BigQuery datasets, tables, and views actually get created — walk
   through 01_setup through 05_ml_models file by file and summarize what
   each one does.
2. Whether the SQL is internally consistent and would actually run as a
   pipeline (flag any broken references, missing dependencies, or dead code).
3. What the ML model in 05_ml_models actually is: model type, features,
   training query, and whether the R²=0.62 / MAE=0.26 figures the README
   cites are reproducible from what's in the SQL, or if those numbers look
   like they were computed once and hand-copied into the README without a
   saved model artifact.
4. A plain list: what's solid and reusable as-is, what's thin/stubbed and
   needs real work, and what's pure documentation fluff with no
   corresponding implementation (docs/architecture.md is suspected to be
   mostly the latter — confirm or refute).

Keep it factual and specific to what's in the files — no speculation about
what "should" be there.
```

Result: AUDIT.md produced. Verdict: extend, don't rebuild — schema design
and mart logic are solid; staging data and ML evaluation are stubbed;
architecture.md and y42_insights.md are near-100% marketing fluff.

---

## Prompt 2 — Fix the 4 critical issues + clean up docs (decision: extend, not rebuild)

```
Read CLAUDE.md and AUDIT.md in this repo first for full context. We're
extending this pipeline, not rebuilding it — the schema design (02_raw_data)
and mart logic (04_marts) are solid per the audit and should not change
structurally. Make the following fixes:

1. sql/04_marts/business_intelligence.sql: add a real 30-day time filter
   (WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) to the
   event aggregation in country_risk_assessment, so the total_events_30d
   column name is actually accurate. Propagate the same filter logic to
   supply_chain_intelligence and the ML training data query in
   05_ml_models if they rely on the same aggregation.

2. sql/02_raw_data/create_tables.sql: add real INSERT/LOAD logic for
   raw_data.countries (a static, real reference list of countries with
   country_code, region, etc. — pull from a public source or hardcode a
   reasonable set covering the regions used elsewhere in the pipeline).
   For raw_data.trade_flows, generate deterministic synthetic data (see
   point 4) rather than leaving it schema-only.

3. sql/03_staging/global_events.sql: replace the RAND()-based event
   generation with a deterministic approach — either a fixed seed
   (e.g. FARM_FINGERPRINT-based pseudo-randomness keyed on a stable id, so
   re-running produces identical output) or a static generated dataset
   checked into the repo. Remove the hardcoded country-name → sentiment
   mapping (Syria/Afghanistan negative, Norway/Denmark positive) — if you
   keep any synthetic sentiment signal, derive it from something
   measurable (e.g. a distribution keyed on a neutral hash) rather than
   baking in real-world geopolitical assumptions as ground truth.

4. sql/05_ml_models/predictive_analytics.sql: uncomment the model
   evaluation query and the prediction sample query. Run the full pipeline
   end to end (01 through 05) against a real or test BigQuery project, and
   report back the ACTUAL R² and MAE the evaluation query produces. Do not
   assume the README's existing 0.62/0.26 numbers are correct.

5. Delete docs/architecture.md and docs/y42_insights.md entirely (per
   audit: near-100% Y42 marketing copy, no technical content). Keep
   docs/data_dictionary.md as-is.

6. Once you have real evaluation numbers from step 4, update README.md's
   "ML Model Performance" section to reflect the actual measured R² and
   MAE instead of the old unverified numbers.

Report back: what you changed, the actual model evaluation numbers you
got, and anything that couldn't be completed (e.g. if you don't have
BigQuery credentials configured locally, say so explicitly rather than
guessing at numbers).
```

**Note:** this requires a live BigQuery project and local `gcloud`/`bq`
authentication to actually run the pipeline and get real evaluation numbers.
If that's not set up in the Claude Code/Antigravity environment yet, the
model-evaluation part (points 4 and 6) will block — everything else (1, 2,
3 as code changes, 5) can proceed without cloud access.

---

## Prompt 3 — Rename project ID, run the pipeline, get real evaluation numbers

```
The BigQuery project is now provisioned: project ID is "ops-intel-logistics"
(gcloud/bq are authenticated and pointed at it — verified with `bq ls`).
Every SQL file in this repo still hardcodes the old placeholder project ID
"defense-logistics-y42-demo". Do the following:

1. Find every occurrence of "defense-logistics-y42-demo" across sql/**/*.sql
   (and README.md's example snippet, and anywhere else it appears) and
   replace it with "ops-intel-logistics". Do a full grep first to make sure
   you catch every reference before editing.

2. Run the full pipeline end to end against the real project, in order:
   bq query --use_legacy_sql=false < sql/01_setup/create_datasets.sql
   bq query --use_legacy_sql=false < sql/02_raw_data/create_tables.sql
   bq query --use_legacy_sql=false < sql/03_staging/global_events.sql
   bq query --use_legacy_sql=false < sql/04_marts/business_intelligence.sql
   bq query --use_legacy_sql=false < sql/05_ml_models/predictive_analytics.sql

   Report any errors verbatim rather than working around them silently —
   if something fails, stop and tell me what failed and why before
   proceeding to the next file.

3. Once the model is trained, run the ML.EVALUATE query (already
   uncommented from Prompt 2) and report the actual r2_score,
   mean_absolute_error, mean_squared_error, and explained_variance.

4. Update README.md's "ML Model Performance" section with these real
   numbers, replacing the "[UNVERIFIED]" placeholder from the last commit.

5. Commit the changes with a clear message (e.g. "Point pipeline at real
   GCP project, run end to end, record verified model metrics").

Report back: the full evaluation output, confirmation the pipeline ran
clean end to end (or exactly where it didn't), and the commit hash.
```

---

## Log

- 2026-07-26 — README.md rewritten (Y42 framing removed) in Cowork, copied
  into repo by Gurinder.
- 2026-07-26 — Confirmed via GitHub: repo has 2 commits, sql/ + docs/ only
  (no dashboards/ or terraform/ despite README mentioning them — those were
  aspirational, not built).
- 2026-07-26 — Prompt 1 (audit) run in Claude Code, AUDIT.md produced.
  Decision: extend, not rebuild.
- 2026-07-26 — Prompt 2 drafted: critical fixes + docs cleanup + README
  correction.
- 2026-07-26 — Prompt 2 executed (commit 197436f): 30-day filter added, real
  countries + deterministic FARM_FINGERPRINT trade/event generation (bias
  removed), eval query uncommented, 2 marketing docs deleted, README
  metrics marked [UNVERIFIED]. Blocked on missing gcloud/bq CLI.
- 2026-07-26 — gcloud/bq CLI installed via WSL, authenticated as
  dreamscaatcher@gmail.com, new GCP project provisioned:
  `ops-intel-logistics`.
- 2026-07-26 — Prompt 3 drafted: rename hardcoded project ID from
  defense-logistics-y42-demo to ops-intel-logistics, run pipeline end to
  end, get real ML.EVALUATE numbers, update README.
- 2026-07-26 — Project ID rename executed by Claude Code (25 occurrences).
  Pipeline run manually by Gurinder in a WSL terminal (Claude Code's own
  shell couldn't reach the bq CLI despite it working interactively) —
  this was the first time the pipeline had ever actually been executed.
  Surfaced 3 real bugs invisible from code review alone:
  - `%` used as modulo operator (BigQuery requires `MOD(a,b)`) in
    02_raw_data/create_tables.sql and 03_staging/global_events.sql
  - INSERT column list (7 cols) didn't match SELECT output (12 cols) in
    03_staging/global_events.sql
  - Bare `NULL` literals defaulted to INT64, type mismatch against
    STRING/FLOAT64 target columns
  All fixed directly in this session (Cowork), not via another Claude Code
  prompt, since it was faster to fix inline while debugging interactively.
  Also fixed: 05_ml_models's eval/prediction queries were only cosmetically
  uncommented in Prompt 2 (block comments still inert) — now genuinely live.
- 2026-07-26 — Pipeline ran clean end to end. Real verified metrics:
  R²=0.5365, MAE=0.2666, MSE=0.1064, explained_variance=0.5365 (in-sample,
  via ML.EVALUATE against full training table — plain `ML.EVALUATE(MODEL
  ...)` with no explicit input table gave a degenerate 0.0/0.0/NaN/NaN
  result for unclear reasons, not worth chasing further once the explicit
  version gave a clean answer). Real risk distribution: 15 MEDIUM, 16 LOW,
  0 HIGH out of 31 countries. README updated with both, replacing the old
  unverified 0.62/0.26 claim and the fabricated 249-country distribution
  table. Also cleaned up two other stale README items: a nonexistent
  dashboards/terraform folder listing, and a made-up project ID in the
  technical-implementation SQL example.
- 2026-07-26 — Committed (`8465c7d`) and pushed to `origin/main`. All bug
  fixes, verified metrics, and corrected risk distribution now live.
- 2026-07-26 — Added a real train/test split (fixed in this session,
  applied directly to 05_ml_models/predictive_analytics.sql): deterministic
  80/20 split keyed on `trade_id` via `MOD(ABS(FARM_FINGERPRINT(trade_id)),
  100) < 80`, model trained only on the 80% partition
  (`data_split_method='NO_SPLIT'`), evaluated only on the held-out 20%.
  Verified held-out metrics: R²=0.5464, MAE=0.2631, MSE=0.1043,
  explained_variance=0.5465 — close to the earlier in-sample number
  (0.5365), so no meaningful overfitting. README updated to reflect this
  as the primary metric, with the in-sample number kept as a reference
  point. **Still pending: commit + push this change.**
