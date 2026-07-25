-- BigQuery ML Models: Predictive Analytics
-- Demonstrates advanced analytics capabilities that Y42 orchestrates

-- ML Training Data Preparation
CREATE OR REPLACE TABLE `ops-intel-logistics.models.supply_chain_training_data` AS
SELECT
  -- Row identifier, used only to derive a deterministic, reproducible
  -- train/test split (not a model feature)
  t.trade_id,

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
  END as risk_score,

  -- Deterministic 80/20 train/test split, keyed on trade_id so it's
  -- reproducible across runs (not random per-query like BQML's
  -- built-in AUTO_SPLIT, and not dependent on row order)
  MOD(ABS(FARM_FINGERPRINT(t.trade_id)), 100) < 80 as is_training

FROM `ops-intel-logistics.raw_data.trade_flows` t
LEFT JOIN `ops-intel-logistics.marts.country_risk_assessment` exp_risk
  ON t.exporter_country = exp_risk.country_code
LEFT JOIN `ops-intel-logistics.marts.country_risk_assessment` imp_risk
  ON t.importer_country = imp_risk.country_code;

-- Supply Chain Risk Predictor Model
-- Trained ONLY on the is_training partition (~80% of rows). data_split_method
-- is explicitly set to NO_SPLIT because we've already done our own manual,
-- deterministic split above -- letting BQML additionally auto-split on top
-- of that would make the held-out set ambiguous.
CREATE OR REPLACE MODEL `ops-intel-logistics.models.supply_chain_risk_predictor`
OPTIONS(
  model_type='linear_reg',
  input_label_cols=['risk_score'],
  data_split_method='NO_SPLIT'
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
FROM `ops-intel-logistics.models.supply_chain_training_data`
WHERE risk_score IS NOT NULL AND is_training;

-- Model Evaluation Query (held-out test set)
-- Runs as part of the pipeline; evaluates ONLY on the ~20% of rows the
-- model never saw during training (is_training = FALSE), for a genuine
-- out-of-sample performance measure rather than an in-sample one.
SELECT
  mean_absolute_error,
  mean_squared_error,
  r2_score,
  explained_variance
FROM
  ML.EVALUATE(
    MODEL `ops-intel-logistics.models.supply_chain_risk_predictor`,
    (
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
      FROM `ops-intel-logistics.models.supply_chain_training_data`
      WHERE risk_score IS NOT NULL AND NOT is_training
    )
  );

-- Sample Prediction Query
-- Runs as part of the pipeline; demonstrates inference on a single example
SELECT
  *
FROM
  ML.PREDICT(MODEL `ops-intel-logistics.models.supply_chain_risk_predictor`,
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
