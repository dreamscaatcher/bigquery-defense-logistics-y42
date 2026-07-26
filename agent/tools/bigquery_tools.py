"""Structured retrieval against the BigQuery marts.

Queries `marts.country_risk_assessment`, defined in
sql/04_marts/business_intelligence.sql. Columns: country_code, country_name,
region, total_events_30d, avg_event_sentiment, avg_stability_score,
risk_level (LOW/MEDIUM/HIGH), calculated_at.

Requires `gcloud auth application-default login` (or GOOGLE_APPLICATION_CREDENTIALS)
against a principal with BigQuery read access to the ops-intel-logistics
project - the same auth already set up for the SQL pipeline itself.
"""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery
from langchain_core.tools import tool

from agent.config import load_settings

_settings = load_settings()
_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=_settings.gcp_project)
    return _client


@tool
def query_country_risk(country_code: str) -> dict[str, Any]:
    """Look up the current risk assessment for a country.

    Args:
        country_code: 3-letter ISO country code, e.g. "KOR", "USA".

    Returns a dict with the mart row (risk_level, avg_event_sentiment,
    total_events_30d, etc.), or {"found": False} if the country isn't in
    the dataset.
    """
    country_code = country_code.strip().upper()
    query = f"""
        SELECT
          country_code, country_name, region,
          total_events_30d, avg_event_sentiment, avg_stability_score,
          risk_level, calculated_at
        FROM `{_settings.gcp_project}.{_settings.bq_marts_dataset}.country_risk_assessment`
        WHERE country_code = @country_code
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("country_code", "STRING", country_code)
        ]
    )
    rows = list(_get_client().query(query, job_config=job_config).result())
    if not rows:
        return {"found": False, "country_code": country_code}

    row = dict(rows[0])
    row["found"] = True
    row["source"] = "bigquery:marts.country_risk_assessment"
    # BigQuery returns Decimal/Timestamp objects that aren't JSON-serializable
    # as-is; normalize for downstream agents.
    row["calculated_at"] = str(row.get("calculated_at"))
    for key in ("avg_event_sentiment", "avg_stability_score"):
        if row.get(key) is not None:
            row[key] = float(row[key])
    return row
