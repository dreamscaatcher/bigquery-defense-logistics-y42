# Defense & Logistics Risk Intelligence Platform

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

| Risk Level | Countries | Avg Events | Avg Sentiment |
|---|---|---|---|
| HIGH | 1 | 16.0 | -6.06 |
| MEDIUM | 85 | 24.6 | -0.31 |
| LOW | 163 | 11.8 | 0.33 |

### ML Model Performance

- **R² Score:** 0.62 (explains 62% of risk variance)
- **Mean Absolute Error:** 0.26
- **Model Type:** Linear regression, multi-feature input

### Sample Predictions

- High-risk scenario (defense equipment trade, negative sentiment) → Risk Score: 4.18
- Low-risk scenario (logistics vehicles, positive sentiment) → Risk Score: -2.04

## Technical Implementation

```sql
-- Partitioned and clustered tables for performance
CREATE TABLE `defense_logistics_analytics.raw_data.countries`
PARTITION BY DATE(created_at)
CLUSTER BY country_code, region;

-- Complex multi-source analytics
CREATE VIEW `supply_chain_intelligence` AS
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
│   ├── 02_raw_data/        # Source table definitions
│   ├── 03_staging/         # Data transformation queries
│   ├── 04_marts/           # Business intelligence views
│   └── 05_ml_models/       # BigQuery ML implementations
├── docs/
│   ├── architecture.md     # Detailed system design
│   └── data_dictionary.md  # Schema documentation
├── dashboards/             # Visualization configurations
├── terraform/              # Infrastructure as Code
└── README.md
```

## Background

This project grew out of a broader interest in how operational planning and risk assessment skills from a military background translate into data platform work: coordinating multi-stage pipelines, evaluating risk under incomplete information, and keeping complex systems reliable under pressure.

## Roadmap

This platform is the foundation for a broader **Operations Intelligence Agent**: a LangGraph-based multi-agent layer wrapped in an MCP server, incorporating the supply-network graph work currently living in a separate Neo4j-backed prototype, plus a geospatial map view for logistics risk.

Near-term:
- Fold in Neo4j-based supply-network modeling
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
