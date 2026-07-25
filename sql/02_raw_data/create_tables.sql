-- Raw Data Table Definitions
-- Countries reference table with optimization features

CREATE OR REPLACE TABLE `ops-intel-logistics.raw_data.countries` (
  country_code STRING,
  country_name STRING,
  region STRING,
  sub_region STRING,
  latitude FLOAT64,
  longitude FLOAT64,
  population BIGINT,
  gdp_usd FLOAT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY country_code, region;

-- Load countries reference data
INSERT INTO `ops-intel-logistics.raw_data.countries`
(country_code, country_name, region, sub_region, latitude, longitude, population, gdp_usd, created_at)
VALUES
  ('USA', 'United States', 'Americas', 'North America', 37.0902, -95.7129, 331900000, 23315080000000, CURRENT_TIMESTAMP()),
  ('GBR', 'United Kingdom', 'Europe', 'Western Europe', 55.3781, -3.4360, 67736800, 3019310000000, CURRENT_TIMESTAMP()),
  ('DEU', 'Germany', 'Europe', 'Western Europe', 51.1657, 10.4515, 83370000, 4031240000000, CURRENT_TIMESTAMP()),
  ('FRA', 'France', 'Europe', 'Western Europe', 46.2276, 2.2137, 67970000, 2782950000000, CURRENT_TIMESTAMP()),
  ('JPN', 'Japan', 'Asia', 'East Asia', 36.2048, 138.2529, 123200000, 4080650000000, CURRENT_TIMESTAMP()),
  ('CHN', 'China', 'Asia', 'East Asia', 35.8617, 104.1954, 1425887337, 17839450000000, CURRENT_TIMESTAMP()),
  ('IND', 'India', 'Asia', 'South Asia', 20.5937, 78.9629, 1428627663, 3385090000000, CURRENT_TIMESTAMP()),
  ('RUS', 'Russia', 'Europe', 'Eastern Europe', 61.5240, 105.3188, 144236000, 1608220000000, CURRENT_TIMESTAMP()),
  ('AUS', 'Australia', 'Oceania', 'Oceania', -25.2744, 133.7751, 26068792, 1344000000000, CURRENT_TIMESTAMP()),
  ('CAN', 'Canada', 'Americas', 'North America', 56.1304, -106.3468, 39742154, 2139840000000, CURRENT_TIMESTAMP()),
  ('KOR', 'South Korea', 'Asia', 'East Asia', 35.9078, 127.7669, 51784385, 1662100000000, CURRENT_TIMESTAMP()),
  ('NOR', 'Norway', 'Europe', 'Northern Europe', 60.4720, 8.4689, 5559631, 598750000000, CURRENT_TIMESTAMP()),
  ('SWE', 'Sweden', 'Europe', 'Northern Europe', 60.1282, 18.6435, 10490873, 592560000000, CURRENT_TIMESTAMP()),
  ('DNK', 'Denmark', 'Europe', 'Northern Europe', 56.2639, 9.5018, 5944457, 405280000000, CURRENT_TIMESTAMP()),
  ('POL', 'Poland', 'Europe', 'Eastern Europe', 51.9194, 19.1451, 37621000, 688270000000, CURRENT_TIMESTAMP()),
  ('ITA', 'Italy', 'Europe', 'Southern Europe', 41.8719, 12.5674, 58940000, 2010660000000, CURRENT_TIMESTAMP()),
  ('ESP', 'Spain', 'Europe', 'Southern Europe', 40.4637, -3.7492, 47620000, 1390120000000, CURRENT_TIMESTAMP()),
  ('BRA', 'Brazil', 'Americas', 'South America', -14.2350, -51.9253, 215313498, 2117860000000, CURRENT_TIMESTAMP()),
  ('MEX', 'Mexico', 'Americas', 'North America', 23.6345, -102.5528, 130262216, 1158230000000, CURRENT_TIMESTAMP()),
  ('ZAF', 'South Africa', 'Africa', 'Southern Africa', -30.5595, 22.9375, 60142978, 406840000000, CURRENT_TIMESTAMP()),
  ('EGY', 'Egypt', 'Africa', 'Northern Africa', 26.8206, 30.8025, 110672382, 476750000000, CURRENT_TIMESTAMP()),
  ('SAU', 'Saudi Arabia', 'Asia', 'Western Asia', 23.8859, 45.0792, 36408820, 1095680000000, CURRENT_TIMESTAMP()),
  ('ARE', 'United Arab Emirates', 'Asia', 'Western Asia', 23.4241, 53.8478, 9890402, 616080000000, CURRENT_TIMESTAMP()),
  ('ISR', 'Israel', 'Asia', 'Western Asia', 31.0461, 34.8516, 9485000, 525660000000, CURRENT_TIMESTAMP()),
  ('SGP', 'Singapore', 'Asia', 'Southeast Asia', 1.3521, 103.8198, 5975688, 626300000000, CURRENT_TIMESTAMP()),
  ('IDN', 'Indonesia', 'Asia', 'Southeast Asia', -0.7893, 113.9213, 277534122, 1317760000000, CURRENT_TIMESTAMP()),
  ('THA', 'Thailand', 'Asia', 'Southeast Asia', 15.8700, 100.9925, 71801915, 514200000000, CURRENT_TIMESTAMP()),
  ('VNM', 'Vietnam', 'Asia', 'Southeast Asia', 14.0583, 108.2772, 98186856, 430630000000, CURRENT_TIMESTAMP()),
  ('MYS', 'Malaysia', 'Asia', 'Southeast Asia', 4.2105, 101.6964, 33928409, 514760000000, CURRENT_TIMESTAMP()),
  ('PHL', 'Philippines', 'Asia', 'Southeast Asia', 12.8797, 121.7740, 120437620, 561760000000, CURRENT_TIMESTAMP()),
  ('NZL', 'New Zealand', 'Oceania', 'Oceania', -40.9006, 174.8860, 5228100, 239290000000, CURRENT_TIMESTAMP());

-- Trade flows table with partitioning and clustering
CREATE OR REPLACE TABLE `ops-intel-logistics.raw_data.trade_flows` (
  trade_id STRING,
  trade_date DATE,
  exporter_country STRING,
  importer_country STRING,
  commodity_category STRING,
  trade_value_usd FLOAT64,
  quantity FLOAT64,
  unit_type STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY trade_date
CLUSTER BY exporter_country, importer_country, commodity_category;

-- Load deterministic synthetic trade flows (keyed on trade_date for reproducibility)
INSERT INTO `ops-intel-logistics.raw_data.trade_flows`
(trade_id, trade_date, exporter_country, importer_country, commodity_category, trade_value_usd, quantity, unit_type, created_at)
WITH trade_base AS (
  SELECT
    DATE_SUB(CURRENT_DATE(), INTERVAL day_offset DAY) as trade_date,
    exporter_country,
    importer_country,
    commodity_category,
    ABS(CAST(FARM_FINGERPRINT(
      CONCAT(CAST(DATE_SUB(CURRENT_DATE(), INTERVAL day_offset DAY) AS STRING),
             exporter_country, importer_country, commodity_category,
             CAST(ROW_NUMBER() OVER (PARTITION BY day_offset, exporter_country, importer_country ORDER BY commodity_category) AS STRING))
    ) AS INT64)) % 100 as value_multiplier
  FROM
    UNNEST(GENERATE_ARRAY(0, 89)) as day_offset,
    UNNEST(['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CHN', 'KOR', 'AUS']) as exporter_country,
    UNNEST(['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CHN', 'KOR', 'AUS']) as importer_country,
    UNNEST(['DEFENSE_EQUIPMENT', 'LOGISTICS_VEHICLES', 'ELECTRONICS', 'AIRCRAFT_PARTS']) as commodity_category
  WHERE exporter_country != importer_country
)
SELECT
  CONCAT('TRADE_', FORMAT_TIMESTAMP('%Y%m%d', TIMESTAMP(trade_date)), '_',
         exporter_country, '_', importer_country, '_',
         ROW_NUMBER() OVER (PARTITION BY trade_date, exporter_country, importer_country ORDER BY commodity_category)) as trade_id,
  trade_date,
  exporter_country,
  importer_country,
  commodity_category,
  CAST((1000000 + value_multiplier * 50000) AS FLOAT64) as trade_value_usd,
  CAST((50 + value_multiplier * 10) AS FLOAT64) as quantity,
  CASE
    WHEN commodity_category IN ('DEFENSE_EQUIPMENT', 'AIRCRAFT_PARTS') THEN 'UNITS'
    ELSE 'UNITS'
  END as unit_type,
  CURRENT_TIMESTAMP() as created_at
FROM trade_base;
