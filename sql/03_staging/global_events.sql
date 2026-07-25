-- Staging Layer: Global Events Processing
-- Deterministic synthetic event generation for reproducibility

-- Global events staging table
CREATE OR REPLACE TABLE `ops-intel-logistics.staging.global_events` (
  event_id STRING,
  event_date DATE,
  event_type STRING,
  country_code STRING,
  actor1_country STRING,
  actor2_country STRING,
  event_tone FLOAT64,
  goldstein_scale FLOAT64,
  latitude FLOAT64,
  longitude FLOAT64,
  source_url STRING,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY event_date
CLUSTER BY country_code, event_type;

-- Generate deterministic synthetic events (keyed on country_code and day for reproducibility)
INSERT INTO `ops-intel-logistics.staging.global_events`
(event_id, event_date, event_type, country_code, actor1_country, event_tone, goldstein_scale)
WITH event_base AS (
  SELECT
    DATE_SUB(CURRENT_DATE(), INTERVAL day_offset DAY) as event_date,
    c.country_code,
    c.country_name,
    event_num,
    -- Use FARM_FINGERPRINT to derive stable pseudo-random values from country_code and date
    ABS(CAST(FARM_FINGERPRINT(CONCAT(c.country_code, CAST(DATE_SUB(CURRENT_DATE(), INTERVAL day_offset DAY) AS STRING), CAST(event_num AS STRING))) AS INT64)) as seed
  FROM
    `ops-intel-logistics.raw_data.countries` c,
    UNNEST(GENERATE_ARRAY(0, 29)) as day_offset,
    UNNEST(GENERATE_ARRAY(1, 3)) as event_num
)
SELECT
  CONCAT('EVT_', country_code, '_', FORMAT_TIMESTAMP('%Y%m%d', TIMESTAMP(event_date)), '_', CAST(event_num AS STRING)) as event_id,
  event_date,
  CASE (seed % 6)
    WHEN 0 THEN 'POLITICAL'
    WHEN 1 THEN 'ECONOMIC'
    WHEN 2 THEN 'MILITARY'
    WHEN 3 THEN 'DIPLOMATIC'
    WHEN 4 THEN 'TRADE'
    ELSE 'SECURITY'
  END as event_type,
  country_code,
  country_code as actor1_country,
  NULL as actor2_country,
  -- Neutral distribution: map fingerprint seed to [-6, +6] range for event_tone
  CAST((((seed % 1200) - 600) / 100.0) AS FLOAT64) as event_tone,
  -- Goldstein scale: map to [-8, +8] range
  CAST((((seed % 1600) - 800) / 100.0) AS FLOAT64) as goldstein_scale,
  NULL as latitude,
  NULL as longitude,
  NULL as source_url,
  CURRENT_TIMESTAMP() as processed_at
FROM event_base
WHERE country_name IS NOT NULL;
