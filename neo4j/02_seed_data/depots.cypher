// Seed: Depots
// Reuses the same 8 country codes used in the BigQuery side's
// raw_data.trade_flows exporter/importer list, so the two systems
// model the same logistics network from two angles (trade risk vs.
// resupply demand/capacity).
//
// Literal, deterministic data -- no RAND(), reproducible on every run.

// Capacity values below are calibrated against the actual demand the
// requisitions generator produces (avg ~493-523/day, peak ~698-794/day
// per depot -- see requisitions.cypher). Large rear-area hubs (USA, CHN)
// get capacity comfortably above peak; forward/smaller nodes (KOR, FRA)
// are intentionally under-provisioned, matching the real-world pattern
// that forward positions are hardest to keep supplied.
UNWIND [
  {depot_id: 'DEPOT_USA', country_code: 'USA', name: 'CONUS Distribution Center', depot_type: 'SUPPLY_DEPOT', capacity_per_day: 900},
  {depot_id: 'DEPOT_CHN', country_code: 'CHN', name: 'Shanghai Distribution Hub', depot_type: 'SUPPLY_DEPOT', capacity_per_day: 800},
  {depot_id: 'DEPOT_DEU', country_code: 'DEU', name: 'Ramstein Logistics Hub', depot_type: 'SUPPLY_DEPOT', capacity_per_day: 700},
  {depot_id: 'DEPOT_JPN', country_code: 'JPN', name: 'Yokosuka Supply Terminal', depot_type: 'PORT', capacity_per_day: 550},
  {depot_id: 'DEPOT_GBR', country_code: 'GBR', name: 'Portsmouth Naval Support Base', depot_type: 'PORT', capacity_per_day: 450},
  {depot_id: 'DEPOT_AUS', country_code: 'AUS', name: 'Darwin Port Facility', depot_type: 'PORT', capacity_per_day: 400},
  {depot_id: 'DEPOT_FRA', country_code: 'FRA', name: 'Istres Air Base', depot_type: 'AIRBASE', capacity_per_day: 320},
  {depot_id: 'DEPOT_KOR', country_code: 'KOR', name: 'Osan Forward Base', depot_type: 'FORWARD_OPERATING_BASE', capacity_per_day: 260}
] AS depot

MERGE (d:Depot {depot_id: depot.depot_id})
SET
  d.country_code = depot.country_code,
  d.name = depot.name,
  d.depot_type = depot.depot_type,
  d.capacity_per_day = depot.capacity_per_day,
  d.created_at = datetime();
