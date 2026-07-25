-- BigQuery ML Models: Predictive Analytics
-- Demonstrates advanced analytics capabilities that Y42 orchestrates

-- ML Training Data Preparation
CREATE OR REPLACE TABLE `defense-logistics-y42-demo.models.supply_chain_training_data` AS
SELECT
  -- Trade features
  t.trade_value_usd,
  t.quantity,
  EXTRACT(MONTH FROM t.trade_date) as trade_month,
  EXTRACT(DAYOFWEEK FROM t.trade_date) as trade_day_of_week,
  
  -- Country risk features (with null handling)
  COALESCE(exp_risk.total_events_30d, 0) as exporter_events,
  COALESCE(exp_risk.avg_event_sentiment, 0) as exporter_sentiment,
  COALESCE(imp_risk.total_events_30d, 0) as importer_events, 
  COALESCE(imp_risk.avg_event_sentiment, 0) as importer_sentiment,
  
  -- Categorical features
  t.commodity_category,
  
  -- Target variable: enhanced risk score
  CASE 
    WHEN COALESCE(exp_risk.risk_level, 'LOW') = 'HIGH' OR COALESCE(imp_risk.risk_level, 'LOW') = 'HIGH' THEN 2
    WHEN COALESCE(exp_risk.risk_level, 'LOW') = 'MEDIUM' OR COALESCE(imp_risk.risk_level, 'LOW') = 'MEDIUM' THEN 1
    ELSE 0
  END as risk_score

FROM `defense-logistics-y42-demo.raw_data.trade_flows` t
LEFT JOIN `defense-logistics-y42-demo.marts.country_risk_assessment` exp_risk
  ON t.exporter_country = exp_risk.country_code
LEFT JOIN `defense-logistics-y42-demo.marts.country_risk_assessment` imp_risk
  ON t.importer_country = imp_risk.country_code;

-- Supply Chain Risk Predictor Model
CREATE OR REPLACE MODEL `defense-logistics-y42-demo.models.supply_chain_risk_predictor`
OPTIONS(
  model_type='linear_reg',
  input_label_cols=['risk_score']
) AS
SELECT
  trade_value_usd,
  quantity,
  trade_month,
  trade_day_of_week,
  exporter_events,
  exporter_sentiment,
  importer_events,
  importer_sentiment,
  commodity_category,
  risk_score
FROM `defense-logistics-y42-demo.models.supply_chain_training_data`
WHERE risk_score IS NOT NULL;

-- Model Evaluation Query
-- Run this to check model performance after training
/*
SELECT
  mean_absolute_error,
  mean_squared_error,
  r2_score,
  explained_variance
FROM
  ML.EVALUATE(MODEL `defense-logistics-y42-demo.models.supply_chain_risk_predictor`);
*/

-- Sample Prediction Query
-- Run this to generate predictions on new data
/*
SELECT
  *
FROM
  ML.PREDICT(MODEL `defense-logistics-y42-demo.models.supply_chain_risk_predictor`,
    (
    SELECT
      5000000.0 as trade_value_usd,
      500.0 as quantity,
      12 as trade_month,
      2 as trade_day_of_week,
      CAST(16 AS INT64) as exporter_events,
      -6.0 as exporter_sentiment,
      CAST(10 AS INT64) as importer_events,
      0.5 as importer_sentiment,
      'DEFENSE_EQUIPMENT' as commodity_category
    )
  );
*/
