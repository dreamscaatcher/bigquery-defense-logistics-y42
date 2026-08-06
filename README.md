# Defense & Logistics Risk Intelligence Platform

**Live demo:** https://ops-intel-agent-960432556484.europe-west3.run.app/map (geospatial risk/capacity map) · [`/briefing`](https://ops-intel-agent-960432556484.europe-west3.run.app/briefing) (POST, e.g. `{"country_code": "KOR"}`) for the full SITREP agent — see `agent/README.md` for the API and `mcp_server/README.md` for the MCP server. Deployed on GCP Cloud Run; see `CLAUDE.md` for architecture and deployment notes.

A BigQuery-native analytics platform for supply chain and logistics risk assessment, combining multi-source data integration, staged transformation pipelines, and BigQuery ML risk modeling.

## Overview

This project ingests country-level trade, event, and sentiment data, transforms it through a staged BigQuery pipeline, and scores geopolitical/supply-chain risk using a trained ML model. It's built to reflect real-world data platform patterns: partitioned and clustered tables, staged transformations with clear dependencies, and business-ready analytics marts on top.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw Data      │    │    Staging      │    │   Data Marts    │
│                 │    │                 │    │                 │
│ • Countries     │───▶│ • Global Events │───▶│ • Risk Assessment│
│ • Trade Flows   │    │ • Processed     │    │ • Supply Chain  │
│ • Public Data   │    │   Trade Data    │    │   Intelligence  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │   ML Models     │
                                              │                 │
                                              │ • Risk Predictor│
                                              │ • Forecasting   │
                                              └─────────────────┘
```

## Key Features

**Data Integration**
- Multi-source integration across public datasets, generated events, and trade flows
- Partitioned tables and clustered indexes for query performance
- Complex joins, null handling, and type conversions across staged layers
- Explicit pipeline dependencies between staging and marts

**Business Intelligence Layer**
- Country-level risk assessment and stability scoring
- Multi-dimensional supply chain risk analysis
- Strategic KPIs for operational decision-making
- Dashboard-ready aggregations for executive reporting

**Advanced Analytics**
- BigQuery ML for predictive risk modeling
- Geospatial groundwork for location-based logistics analysis
- Time series analysis for trend identification and forecasting
- Query and cost optimization (partitioning, clustering, materialized views)

## Results

### Risk Assessment Distribution

Verified 2026-07-26 against the real 31-country dataset (`marts.country_risk_assessment`):

| Risk Level | Countries | Avg Events (30d) | Avg Sentiment |
|---|---|---|---|
| MEDIUM | 15 | 90.0 | -0.35 |
| LOW | 16 | 90.0 | 0.32 |

No country currently crosses the HIGH threshold (avg sentiment < -3 with >5 events) — expected, since event tone is now generated from a neutral, deterministic distribution rather than the old hardcoded country bias. Every country has exactly 90 events in the 30-day window because the full synthetic dataset only spans 30 days.

### ML Model Performance

**Model Type:** BigQuery ML Linear Regression

**Measured Performance** (verified 2026-07-26, held-out test set, project `ops-intel-logistics`):

| Metric | Value |
|---|---|
| R² Score | 0.5464 |
| Mean Absolute Error | 0.2631 |
| Mean Squared Error | 0.1043 |
| Explained Variance | 0.5465 |

**Methodology:** the training data (20,160 rows total) is split deterministically 80/20 into train/test using `MOD(ABS(FARM_FINGERPRINT(trade_id)), 100) < 80` — a hash-based, reproducible split rather than a random one, so re-running the pipeline assigns the exact same rows to train vs. test every time. The model is trained only on the 80% training partition (`data_split_method='NO_SPLIT'` in the model options, since BQML's own auto-split is disabled in favor of this explicit one). `ML.EVALUATE` is run only against the 20% held-out test partition the model never saw during training — a genuine out-of-sample metric, not an in-sample one.

For reference, the earlier in-sample number (evaluating on the same data used for training) was R²=0.5365 — close to the held-out number above, suggesting the model isn't meaningfully overfitting given the current feature set and data size.

Reproduce it yourself:

```bash
gcloud auth login
gcloud config set project ops-intel-logistics
bq query --use_legacy_sql=false < sql/01_setup/create_datasets.sql
bq query --use_legacy_sql=false < sql/02_raw_data/create_tables.sql
bq query --use_legacy_sql=false < sql/03_staging/global_events.sql
bq query --use_legacy_sql=false < sql/04_marts/business_intelligence.sql
bq query --use_legacy_sql=false < sql/05_ml_models/predictive_analytics.sql
```

Since the countries, trade flows, and events are all generated deterministically (`FARM_FINGERPRINT`-keyed, no `RAND()`), this should reproduce the exact same numbers every time.

### Sample Predictions

See `sql/05_ml_models/predictive_analytics.sql` for a sample prediction query. Note: since `risk_score` only ever takes values 0 or 1 in the training data, predictions on inputs far outside the training distribution (e.g. unusually large `trade_value_usd`) can extrapolate outside that range — a known limitation of using linear regression on what's really a bounded/categorical target, not a data bug.

## Technical Implementation

```sql
-- Partitioned and clustered tables for performance
CREATE TABLE `ops-intel-logistics.raw_data.countries`
PARTITION BY DATE(created_at)
CLUSTER BY country_code, region;

-- Complex multi-source analytics
CREATE VIEW `ops-intel-logistics.marts.supply_chain_intelligence` AS
SELECT country_risk + trade_metrics + event_analysis ...
```

**Pipeline layers**
- **Raw data:** direct ingestion from multiple sources
- **Staging:** cleaned, normalized, validated data
- **Data marts:** business-ready analytics tables
- **ML models:** predictive analytics and forecasting

**Cost optimization**
- Date-based partitioning for time-series queries
- Clustering on frequently filtered columns
- Materialized views for expensive aggregations
- Query tuning for reduced slot usage

## Repository Structure

```
├── sql/
│   ├── 01_setup/           # Dataset creation and configuration
│   ├── 02_raw_data/        # Source table definitions + real reference data
│   ├── 03_staging/         # Deterministic event generation
│   ├── 04_marts/           # Business intelligence views
│   └── 05_ml_models/       # BigQuery ML training + evaluation
├── neo4j/                  # Supply network graph (depots, routes, requisitions)
│   ├── 01_schema/          # Constraints and indexes
│   ├── 02_seed_data/       # Deterministic seed data
│   └── 03_queries/         # Demand-vs-capacity read queries
├── docs/
│   └── data_dictionary.md  # Schema documentation
├── CLAUDE.md               # Project context for Claude Code sessions
├── claude-code-prompts.md  # Running log of prompts used to build this out
├── AUDIT.md                # Pipeline audit (2026-07-26)
└── README.md
```

## Background

This project grew out of a broader interest in how operational planning and risk assessment skills from a military background translate into data platform work: coordinating multi-stage pipelines, evaluating risk under incomplete information, and keeping complex systems reliable under pressure.

## Roadmap

This platform is the foundation for a broader **Operations Intelligence Agent**: a LangGraph-based multi-agent layer wrapped in an MCP server, plus a geospatial map view for logistics risk.

**Supply network graph (Neo4j) — schema, seed data, and queries built** (2026-07-26). See `neo4j/README.md`: depots, routes, and requisitions modeling resupply demand vs. capacity, reusing the same 8 countries as the BigQuery trade-flow data. No application layer yet — see that README for why.

Near-term:
- Add a LangGraph multi-agent orchestration layer
- Wrap the platform in an MCP server
- Build a geospatial map view for logistics risk

Longer-term:
- Real-time event streaming and alerting
- Deeper ML models for pattern recognition
- Multi-region deployment considerations
- Role-based access and data governance

---

**Built by:** Gurinder ([dreamscaatcher](https://github.com/dreamscaatcher))
