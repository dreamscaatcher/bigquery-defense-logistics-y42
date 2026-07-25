-- BigQuery Dataset Creation for Defense Logistics Analytics
-- Demonstrates Y42-style data orchestration complexity

-- Raw data layer
CREATE SCHEMA `ops-intel-logistics.raw_data`
OPTIONS(
  description="Raw data from external sources",
  location="US"
);

-- Staging layer  
CREATE SCHEMA `ops-intel-logistics.staging`
OPTIONS(
  description="Cleaned and normalized data",
  location="US"
);

-- Data marts layer
CREATE SCHEMA `ops-intel-logistics.marts`
OPTIONS(
  description="Business-ready analytics tables",
  location="US"
);

-- ML models
CREATE SCHEMA `ops-intel-logistics.models`
OPTIONS(
  description="Machine learning models and predictions",
  location="US"
);
