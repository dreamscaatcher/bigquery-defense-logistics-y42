// Seed: Routes
// Every ordered pair of depots gets a route (8 depots -> 56 routes,
// same "all pairs except self" pattern as the BigQuery trade_flows
// generation). mode/transit_days/capacity_per_day are derived from a
// deterministic arithmetic hash of each pair's list position -- no
// RAND(), reproducible on every run.

WITH ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CHN', 'KOR', 'AUS'] AS codes

UNWIND range(0, size(codes) - 1) AS i
UNWIND range(0, size(codes) - 1) AS j
WITH codes, i, j
WHERE i <> j
WITH
  codes[i] AS origin_code,
  codes[j] AS dest_code,
  ((i * 92821) + (j * 15485867)) % 10000 AS seed

WITH
  origin_code,
  dest_code,
  seed,
  CASE seed % 3
    WHEN 0 THEN 'AIR'
    WHEN 1 THEN 'SEA'
    ELSE 'GROUND'
  END AS mode,
  1 + (seed % 14) AS transit_days,
  100 + (seed % 200) AS capacity_per_day

MATCH (origin:Depot {country_code: origin_code})
MATCH (dest:Depot {country_code: dest_code})

MERGE (r:Route {route_id: 'ROUTE_' + origin_code + '_' + dest_code})
SET
  r.mode = mode,
  r.transit_days = transit_days,
  r.capacity_per_day = capacity_per_day,
  r.created_at = datetime()
MERGE (r)-[:ORIGINATES_AT]->(origin)
MERGE (r)-[:TERMINATES_AT]->(dest);
