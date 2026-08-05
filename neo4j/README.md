# Supply Network Graph (Neo4j)

A graph layer modeling defense-logistics resupply demand vs. capacity, separate from (but narratively connected to) the BigQuery side's trade/risk analytics.

## Why this exists

The BigQuery pipeline (`sql/`) models country-level trade flows and geopolitical risk. This graph models the physical resupply network underneath that: depots, the routes connecting them, and the day-to-day requisitions (resupply requests) that create demand against each depot's capacity. It's the "supply planning" capability originally prototyped against a generic e-commerce Order/Product schema in a separate repo (`E-Commerce`), rebuilt here against a real defense-logistics schema.

## Schema

**Nodes**
- `Depot {depot_id, name, country_code, depot_type, capacity_per_day, latitude, longitude}` — a resupply point. `depot_type` is one of `SUPPLY_DEPOT`, `PORT`, `AIRBASE`, `FORWARD_OPERATING_BASE`. `latitude`/`longitude` (added 2026-08-05 for the geospatial map view) are real, public coordinates for the named locations.
- `Route {route_id, mode, transit_days, capacity_per_day}` — a logistics link between two depots. `mode` is `AIR`, `SEA`, or `GROUND`.
- `Requisition {requisition_id, request_date, quantity, commodity_category, priority}` — a demand event: a request for resupply at a depot. `priority` is `ROUTINE`, `PRIORITY`, or `URGENT`. `commodity_category` reuses the same categories as the BigQuery side (`DEFENSE_EQUIPMENT`, `LOGISTICS_VEHICLES`, `ELECTRONICS`, `AIRCRAFT_PARTS`).

**Relationships**
- `(:Route)-[:ORIGINATES_AT]->(:Depot)`
- `(:Route)-[:TERMINATES_AT]->(:Depot)`
- `(:Requisition)-[:REQUESTED_AT]->(:Depot)` — which depot needs the resupply
- `(:Requisition)-[:FULFILLED_VIA]->(:Route)` — which route serves it (always a route terminating at the requesting depot)

## Data

8 depots, reusing the same 8 country codes as the BigQuery side's `trade_flows` (USA, GBR, DEU, FRA, JPN, CHN, KOR, AUS) so the two systems describe the same logistics network from two angles. 56 routes (every ordered pair). ~2,160 requisitions (8 depots × 90 days × 3/day).

All seed data is deterministic — generated from arithmetic on depot index / day offset / requisition number, not `RAND()` or similar. Re-running the seed scripts against a fresh database produces identical data every time.

## Setup

This should live in its **own Neo4j database**, separate from any other graph (e.g. don't mix this into a database you're using to track unrelated project state). Your Neo4j instance is Enterprise edition, which supports multiple databases in one DBMS:

```cypher
CREATE DATABASE `opsintel-supply-network`;
```

Then, against that database (in Neo4j Browser, switch to it with the database dropdown or `:use opsintel-supply-network`), run in order:

1. `01_schema/constraints.cypher`
2. `02_seed_data/depots.cypher`
3. `02_seed_data/routes.cypher`
4. `02_seed_data/requisitions.cypher` (depends on 2 and 3 — depots and routes must exist first)

Then the read queries in `03_queries/demand_vs_capacity.cypher` — these are 4 independent queries, run each one separately (they're not a single script).

## Status

Schema, seed data, and read queries, plus the LangGraph (`agent/`) and MCP
(`mcp_server/`) layers on top — see `CLAUDE.md` for full status. The
original `E-Commerce` prototype's Next.js/React UI (`SupplyPlanning.tsx`,
what-if capacity sliders) is still not ported; the geospatial map view
(roadmap item 5, `agent/static/map.html`) is this repo's first actual UI
instead, and a natural place to eventually fold that what-if-style
interaction back in.

**If you seeded this database before 2026-08-05**, depot nodes won't have
`latitude`/`longitude` yet — re-run `02_seed_data/depots.cypher` (safe,
it's a `MERGE` + `SET` keyed on `depot_id`, so it updates the existing 8
nodes in place rather than duplicating them).
