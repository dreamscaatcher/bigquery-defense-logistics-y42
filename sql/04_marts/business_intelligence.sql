-- Data Marts: Business Intelligence Views
-- Demonstrates complex multi-source analytics that Y42 orchestrates

-- Country Risk Assessment View
CREATE OR REPLACE VIEW `ops-intel-logistics.marts.country_risk_assessment` AS
SELECT
  c.country_code,
  c.country_name,
  c.region,
  -- Event-based risk scoring (30-day rolling window)
  COUNT(DISTINCT e.event_id) as total_events_30d,
  AVG(e.event_tone) as avg_event_sentiment,
  AVG(e.goldstein_scale) as avg_stability_score,

  -- Risk calculation
  CASE
    WHEN AVG(e.event_tone) < -3 AND COUNT(e.event_id) > 5 THEN 'HIGH'
    WHEN AVG(e.event_tone) < 0 AND COUNT(e.event_id) > 2 THEN 'MEDIUM'
    ELSE 'LOW'
  END as risk_level,

  CURRENT_TIMESTAMP() as calculated_at

FROM `ops-intel-logistics.raw_data.countries` c
LEFT JOIN `ops-intel-logistics.staging.global_events` e
  ON c.country_code = e.country_code
  AND e.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY c.country_code, c.country_name, c.region
ORDER BY avg_event_sentiment ASC, total_events_30d DESC;

-- Supply Chain Intelligence View
CREATE OR REPLACE VIEW `ops-intel-logistics.marts.supply_chain_intelligence` AS
SELECT 
  t.exporter_country,
  exp.country_name as exporter_name,
  t.importer_country, 
  imp.country_name as importer_name,
  t.commodity_category,
  
  -- Trade metrics
  COUNT(*) as total_transactions,
  SUM(t.trade_value_usd) as total_trade_value,
  AVG(t.trade_value_usd) as avg_transaction_value,
  
  -- Risk assessment from events data  
  exp_risk.risk_level as exporter_risk,
  imp_risk.risk_level as importer_risk,
  
  -- Supply chain risk score
  CASE 
    WHEN exp_risk.risk_level = 'HIGH' OR imp_risk.risk_level = 'HIGH' THEN 'HIGH_RISK'
    WHEN exp_risk.risk_level = 'MEDIUM' OR imp_risk.risk_level = 'MEDIUM' THEN 'MEDIUM_RISK'
    ELSE 'LOW_RISK'
  END as supply_chain_risk

FROM `ops-intel-logistics.raw_data.trade_flows` t
LEFT JOIN `ops-intel-logistics.raw_data.countries` exp 
  ON t.exporter_country = exp.country_code
LEFT JOIN `ops-intel-logistics.raw_data.countries` imp 
  ON t.importer_country = imp.country_code
LEFT JOIN `ops-intel-logistics.marts.country_risk_assessment` exp_risk
  ON t.exporter_country = exp_risk.country_code
LEFT JOIN `ops-intel-logistics.marts.country_risk_assessment` imp_risk
  ON t.importer_country = imp_risk.country_code

GROUP BY t.exporter_country, exp.country_name, t.importer_country, imp.country_name, 
         t.commodity_category, exp_risk.risk_level, imp_risk.risk_level
ORDER BY total_trade_value DESC;
