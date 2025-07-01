-- Staging Layer: Global Events Processing
-- Demonstrates complex data transformation and event generation

-- Global events staging table
CREATE OR REPLACE TABLE `defense-logistics-y42-demo.staging.global_events` (
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

-- Load sample data from BBC News (demonstrates multi-source integration)
INSERT INTO `defense-logistics-y42-demo.staging.global_events`
(event_id, event_date, event_type, country_code, actor1_country, event_tone, goldstein_scale)
SELECT 
  CONCAT('BBC_', filename, '_', CAST(ROW_NUMBER() OVER() AS STRING)) as event_id,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(RAND() * 365 AS INT64) DAY) as event_date,
  UPPER(category) as event_type,
  'GBR' as country_code,
  'GBR' as actor1_country,
  CASE 
    WHEN REGEXP_CONTAINS(LOWER(title), r'crisis|war|conflict|attack') THEN -5.0
    WHEN REGEXP_CONTAINS(LOWER(title), r'growth|success|agreement|peace') THEN 3.0
    ELSE 0.0
  END as event_tone,
  CASE 
    WHEN REGEXP_CONTAINS(LOWER(title), r'crisis|war|conflict') THEN -8.0
    WHEN REGEXP_CONTAINS(LOWER(title), r'cooperation|trade|agreement') THEN 4.0
    ELSE 0.0
  END as goldstein_scale
FROM `bigquery-public-data.bbc_news.fulltext`
WHERE title IS NOT NULL
LIMIT 100;

-- Generate comprehensive events data for multiple countries
INSERT INTO `defense-logistics-y42-demo.staging.global_events`
(event_id, event_date, event_type, country_code, actor1_country, event_tone, goldstein_scale)
SELECT 
  CONCAT('GEN_', c.country_code, '_', CAST(ROW_NUMBER() OVER() AS STRING)) as event_id,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(RAND() * 90 AS INT64) DAY) as event_date,
  CASE CAST(RAND() * 6 AS INT64)
    WHEN 0 THEN 'POLITICAL'
    WHEN 1 THEN 'ECONOMIC' 
    WHEN 2 THEN 'MILITARY'
    WHEN 3 THEN 'DIPLOMATIC'
    WHEN 4 THEN 'TRADE'
    ELSE 'SECURITY'
  END as event_type,
  c.country_code,
  c.country_code as actor1_country,
  CASE 
    WHEN c.country_name IN ('Syria', 'Afghanistan', 'Yemen', 'Somalia', 'South Sudan') THEN RAND() * -8 - 2
    WHEN c.country_name IN ('Norway', 'Denmark', 'Switzerland', 'Canada', 'New Zealand') THEN RAND() * 4 + 1
    ELSE (RAND() - 0.5) * 6
  END as event_tone,
  CASE 
    WHEN c.country_name IN ('Syria', 'Afghanistan', 'Yemen') THEN RAND() * -6 - 4
    WHEN c.country_name IN ('Germany', 'Japan', 'South Korea', 'Australia') THEN RAND() * 6 + 2
    ELSE (RAND() - 0.5) * 8
  END as goldstein_scale
FROM `defense-logistics-y42-demo.raw_data.countries` c
CROSS JOIN UNNEST(GENERATE_ARRAY(1, CAST(RAND() * 15 + 5 AS INT64))) as event_num
WHERE c.country_name IS NOT NULL
LIMIT 2000;
