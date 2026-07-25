// Read queries: demand vs. capacity per depot
// These are the Neo4j-side equivalent of the BigQuery country_risk_assessment
// / supply_chain_intelligence marts -- run independently, read-only, against
// the seeded graph. Run each block separately (they're independent queries,
// not a single script).

// -------------------------------------------------------------------------
// 1. Daily demand vs. capacity, last 30 days, per depot
// -------------------------------------------------------------------------
MATCH (d:Depot)
OPTIONAL MATCH (q:Requisition)-[:REQUESTED_AT]->(d)
WHERE q.request_date >= date() - duration({days: 30})
WITH d, q.request_date AS period, count(q) AS requisition_count, sum(q.quantity) AS total_quantity
RETURN
  d.depot_id AS depot,
  d.name AS depot_name,
  d.capacity_per_day AS capacity_per_day,
  period,
  requisition_count,
  total_quantity,
  round(100.0 * total_quantity / d.capacity_per_day) AS utilization_pct
ORDER BY d.depot_id, period;

// -------------------------------------------------------------------------
// 2. Weekly demand vs. capacity, last 12 weeks, per depot
// -------------------------------------------------------------------------
MATCH (d:Depot)
OPTIONAL MATCH (q:Requisition)-[:REQUESTED_AT]->(d)
WHERE q.request_date >= date() - duration({weeks: 12})
WITH d, date.truncate('week', q.request_date) AS week_start, count(q) AS requisition_count, sum(q.quantity) AS total_quantity
RETURN
  d.depot_id AS depot,
  d.name AS depot_name,
  d.capacity_per_day * 7 AS capacity_per_week,
  week_start,
  requisition_count,
  total_quantity,
  round(100.0 * total_quantity / (d.capacity_per_day * 7)) AS utilization_pct
ORDER BY d.depot_id, week_start;

// -------------------------------------------------------------------------
// 3. Overall utilization summary per depot (avg daily utilization, 90-day window)
// -------------------------------------------------------------------------
MATCH (d:Depot)
OPTIONAL MATCH (q:Requisition)-[:REQUESTED_AT]->(d)
WITH d, q.request_date AS period, sum(q.quantity) AS daily_quantity
WITH d, avg(daily_quantity) AS avg_daily_demand, max(daily_quantity) AS peak_daily_demand
RETURN
  d.depot_id AS depot,
  d.name AS depot_name,
  d.depot_type AS depot_type,
  d.capacity_per_day AS capacity_per_day,
  round(avg_daily_demand) AS avg_daily_demand,
  peak_daily_demand,
  round(100.0 * avg_daily_demand / d.capacity_per_day) AS avg_utilization_pct,
  round(100.0 * peak_daily_demand / d.capacity_per_day) AS peak_utilization_pct,
  CASE
    WHEN peak_daily_demand > d.capacity_per_day THEN 'OVER_CAPACITY'
    WHEN avg_daily_demand > 0.8 * d.capacity_per_day THEN 'NEAR_CAPACITY'
    ELSE 'WITHIN_CAPACITY'
  END AS capacity_status
ORDER BY avg_utilization_pct DESC;

// -------------------------------------------------------------------------
// 4. Route utilization: total quantity routed vs. route capacity, 90-day window
// -------------------------------------------------------------------------
MATCH (r:Route)
OPTIONAL MATCH (q:Requisition)-[:FULFILLED_VIA]->(r)
WITH r, count(q) AS requisitions_routed, sum(q.quantity) AS total_quantity_routed
MATCH (r)-[:ORIGINATES_AT]->(origin:Depot)
MATCH (r)-[:TERMINATES_AT]->(dest:Depot)
RETURN
  r.route_id AS route,
  origin.depot_id AS origin_depot,
  dest.depot_id AS destination_depot,
  r.mode AS mode,
  r.transit_days AS transit_days,
  r.capacity_per_day AS capacity_per_day,
  requisitions_routed,
  total_quantity_routed,
  round(100.0 * total_quantity_routed / (r.capacity_per_day * 90)) AS utilization_pct_over_window
ORDER BY utilization_pct_over_window DESC;
