# Data Dictionary

## Overview

This document provides comprehensive documentation of all data structures, tables, and fields used in the Defense Logistics Analytics Platform.

## Raw Data Layer

### countries
Reference table containing country information and metadata.

| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| country_code | STRING | ISO 3-letter country code | 'USA', 'GBR', 'DEU' |
| country_name | STRING | Full country name | 'United States', 'Germany' |
| region | STRING | Geographic region | 'Europe', 'Asia', 'Americas' |
| sub_region | STRING | Sub-regional classification | 'Western Europe', 'Southeast Asia' |
| latitude | FLOAT64 | Country centroid latitude | 52.5200 |
| longitude | FLOAT64 | Country centroid longitude | 13.4050 |
| population | BIGINT | Total population | 83240525 |
| gdp_usd | FLOAT64 | GDP in US Dollars | 4259934911821.0 |
| created_at | TIMESTAMP | Record creation timestamp | 2025-01-01 10:30:00 UTC |

**Partitioning**: BY DATE(created_at)
**Clustering**: BY country_code, region

### trade_flows
Transaction records for defense-related trade between countries.

| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| trade_id | STRING | Unique trade transaction identifier | 'TRADE_001', 'TRADE_002' |
| trade_date | DATE | Date of trade transaction | 2025-01-15 |
| exporter_country | STRING | Exporting country code | 'USA' |
| importer_country | STRING | Importing country code | 'DEU' |
| commodity_category | STRING | Type of defense equipment | 'DEFENSE_EQUIPMENT', 'LOGISTICS_VEHICLES' |
| trade_value_usd | FLOAT64 | Transaction value in USD | 5000000.0 |
| quantity | FLOAT64 | Number of units traded | 250.0 |
| unit_type | STRING | Unit of measurement | 'UNITS', 'TONS', 'SYSTEMS' |
| created_at | TIMESTAMP | Record creation timestamp | 2025-01-01 10:30:00 UTC |

**Partitioning**: BY trade_date
**Clustering**: BY exporter_country, importer_country, commodity_category

## Staging Layer

### global_events
Processed political and economic events data from multiple sources.

| Column Name | Data Type | Description | Range/Example |
|-------------|-----------|-------------|---------------|
| event_id | STRING | Unique event identifier | 'BBC_tech_001', 'GEN_USA_001' |
| event_date | DATE | Date when event occurred | 2024-01-01 to 2025-06-30 |
| event_type | STRING | Category of event | 'POLITICAL', 'ECONOMIC', 'MILITARY' |
| country_code | STRING | Country where event occurred | 'USA', 'GBR', 'DEU' |
| actor1_country | STRING | Primary actor country | 'USA', 'CHN', 'RUS' |
| actor2_country | STRING | Secondary actor country | NULL, 'DEU', 'FRA' |
| event_tone | FLOAT64 | Sentiment score of event | -10.0 (very negative) to +10.0 (very positive) |
| goldstein_scale | FLOAT64 | Cooperation/conflict scale | -10.0 (conflict) to +10.0 (cooperation) |
| latitude | FLOAT64 | Event location latitude | 52.5200 |
| longitude | FLOAT64 | Event location longitude | 13.4050 |
| source_url | STRING | Original source reference | URL or source identifier |
| processed_at | TIMESTAMP | Processing timestamp | 2025-01-01 10:30:00 UTC |

**Partitioning**: BY event_date
**Clustering**: BY country_code, event_type

## Data Marts Layer

### country_risk_assessment
Business intelligence view providing country-level risk analysis.

| Column Name | Data Type | Description | Calculation Logic |
|-------------|-----------|-------------|------------------|
| country_code | STRING | ISO country code | From countries table |
| country_name | STRING | Country name | From countries table |
| region | STRING | Geographic region | From countries table |
| total_events_30d | INT64 | Event count (last 30 days) | COUNT(DISTINCT event_id) |
| avg_event_sentiment | FLOAT64 | Average sentiment score | AVG(event_tone) |
| avg_stability_score | FLOAT64 | Average stability measure | AVG(goldstein_scale) |
| risk_level | STRING | Categorized risk level | HIGH/MEDIUM/LOW based on sentiment and event count |
| calculated_at | TIMESTAMP | Analysis timestamp | CURRENT_TIMESTAMP() |

**Risk Level Logic**:
- HIGH: avg_event_sentiment < -3 AND total_events > 5
- MEDIUM: avg_event_sentiment < 0 AND total_events > 2
- LOW: All other cases

### supply_chain_intelligence
Comprehensive supply chain analysis combining trade and risk data.

| Column Name | Data Type | Description | Source |
|-------------|-----------|-------------|--------|
| exporter_country | STRING | Exporting country code | trade_flows |
| exporter_name | STRING | Exporting country name | countries |
| importer_country | STRING | Importing country code | trade_flows |
| importer_name | STRING | Importing country name | countries |
| commodity_category | STRING | Product category | trade_flows |
| total_transactions | INT64 | Number of trades | COUNT(*) |
| total_trade_value | FLOAT64 | Total USD value | SUM(trade_value_usd) |
| avg_transaction_value | FLOAT64 | Average trade value | AVG(trade_value_usd) |
| exporter_risk | STRING | Exporter risk level | country_risk_assessment |
| importer_risk | STRING | Importer risk level | country_risk_assessment |
| supply_chain_risk | STRING | Combined risk assessment | Logic based on both countries |

## ML Models Layer

### supply_chain_training_data
Feature engineering table for machine learning model training.

| Column Name | Data Type | Description | Feature Type |
|-------------|-----------|-------------|--------------|
| trade_value_usd | FLOAT64 | Transaction value | Numerical |
| quantity | FLOAT64 | Trade quantity | Numerical |
| trade_month | INT64 | Month of transaction (1-12) | Numerical |
| trade_day_of_week | INT64 | Day of week (1-7) | Numerical |
| exporter_events | INT64 | Exporter country events | Numerical |
| exporter_sentiment | FLOAT64 | Exporter sentiment score | Numerical |
| importer_events | INT64 | Importer country events | Numerical |
| importer_sentiment | FLOAT64 | Importer sentiment score | Numerical |
| commodity_category | STRING | Product category | Categorical |
| risk_score | INT64 | Target variable (0=Low, 1=Medium, 2=High) | Target |

### supply_chain_risk_predictor
BigQuery ML linear regression model for risk prediction.

**Model Type**: Linear Regression
**Input Features**: All columns except risk_score
**Target Variable**: risk_score
**Model Performance**: R² = 0.5464, MAE = 0.2631 (held-out 20% test split, verified 2026-07-26 — see README.md "ML Model Performance" for full methodology). An earlier R² = 0.62 / MAE = 0.26 figure was hand-copied from a lost historical run and was never reproducible; see AUDIT.md for that history.

## Data Quality Rules

### Validation Constraints
- country_code: Must be valid 3-letter ISO code
- trade_value_usd: Must be positive, < $10B per transaction
- event_tone: Range -10.0 to +10.0
- risk_level: Must be 'HIGH', 'MEDIUM', or 'LOW'
- dates: Must be within reasonable historical range

### Null Handling
- Required fields: country_code, event_id, trade_id
- Optional fields: latitude, longitude, gdp_usd
- Default values: event_tone=0.0, goldstein_scale=0.0

### Data Refresh Patterns
- countries: Weekly updates
- trade_flows: Daily batch loads
- global_events: Hourly incremental updates
- marts: Computed on-demand with materialized view refresh

## Performance Optimization

### Partitioning Strategy
- Time-series data: Partition by date
- Reference data: No partitioning (small tables)

### Clustering Strategy
- High-cardinality filters first: country_code
- Low-cardinality filters second: region, event_type

### Query Optimization
- Use appropriate WHERE clauses for partition pruning
- Leverage clustering keys in JOIN conditions
- Consider materialized views for expensive aggregations
