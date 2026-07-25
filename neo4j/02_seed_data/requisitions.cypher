// Seed: Requisitions (demand events)
// For each depot, 3 requisitions/day over 90 days (same volume pattern as
// the BigQuery side's staging.global_events: 8 depots x 90 days x 3 = 2,160
// requisitions). Quantity/commodity/priority/fulfilling-route are all
// derived from a deterministic arithmetic hash of (depot index, day offset,
// requisition number) -- no RAND(), reproducible on every run, and no
// hardcoded country-name bias (learned from the BigQuery side's original
// mistake of baking in Syria/Norway-style assumptions).
//
// Requires depots.cypher and routes.cypher to have been run first.

WITH ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CHN', 'KOR', 'AUS'] AS codes

UNWIND range(0, size(codes) - 1) AS i
UNWIND range(0, 89) AS day_offset
UNWIND range(1, 3) AS req_num

WITH codes, i, day_offset, req_num,
  ((i * 2654435761) + (day_offset * 40503) + (req_num * 7919)) % 100000 AS seed

WITH codes, i, day_offset, req_num, seed,
  codes[i] AS depot_code,
  date() - duration({days: day_offset}) AS request_date,
  20 + (seed % 300) AS quantity,
  CASE seed % 4
    WHEN 0 THEN 'DEFENSE_EQUIPMENT'
    WHEN 1 THEN 'LOGISTICS_VEHICLES'
    WHEN 2 THEN 'ELECTRONICS'
    ELSE 'AIRCRAFT_PARTS'
  END AS commodity_category,
  CASE
    WHEN seed % 10 = 9 THEN 'URGENT'
    WHEN seed % 10 >= 7 THEN 'PRIORITY'
    ELSE 'ROUTINE'
  END AS priority,
  CASE WHEN (seed % 7) < i THEN (seed % 7) ELSE (seed % 7) + 1 END AS origin_index

WITH codes, depot_code, day_offset, req_num, request_date, quantity,
     commodity_category, priority, codes[origin_index] AS origin_code

MATCH (d:Depot {country_code: depot_code})
MATCH (r:Route {route_id: 'ROUTE_' + origin_code + '_' + depot_code})

MERGE (q:Requisition {requisition_id: 'REQ_' + depot_code + '_' + toString(request_date) + '_' + toString(req_num)})
SET
  q.request_date = request_date,
  q.quantity = quantity,
  q.commodity_category = commodity_category,
  q.priority = priority,
  q.created_at = datetime()
MERGE (q)-[:REQUESTED_AT]->(d)
MERGE (q)-[:FULFILLED_VIA]->(r);
