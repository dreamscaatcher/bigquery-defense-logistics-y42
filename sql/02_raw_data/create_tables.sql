-- Raw Data Table Definitions
-- Countries reference table with optimization features

CREATE OR REPLACE TABLE `defense-logistics-y42-demo.raw_data.countries` (
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

-- Trade flows table with partitioning and clustering
CREATE OR REPLACE TABLE `defense-logistics-y42-demo.raw_data.trade_flows` (
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
