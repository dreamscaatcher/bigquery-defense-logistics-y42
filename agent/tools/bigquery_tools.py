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


def query_all_countries_risk() -> list[dict[str, Any]]:
    """Fetch risk_level + coordinates for every country, for the map view.

    Not a LangChain @tool (no LLM ever needs "all 31 countries" as a single
    call) - this is a plain data-fetch helper used directly by the
    GET /map-data endpoint in agent/api.py. Joins
    marts.country_risk_assessment with raw_data.countries since the mart
    itself doesn't carry lat/long (see sql/04_marts/business_intelligence.sql).

    Returns a list of dicts: country_code, country_name, latitude,
    longitude, risk_level, total_events_30d, avg_event_sentiment. Countries
    with a null lat/long (shouldn't happen given raw_data.countries always
    sets them, but defensive) are skipped since they can't be plotted.
    """
    query = f"""
        SELECT
          r.country_code, r.country_name, r.risk_level,
          r.total_events_30d, r.avg_event_sentiment,
          c.latitude, c.longitude
        FROM `{_settings.gcp_project}.{_settings.bq_marts_dataset}.country_risk_assessment` r
        JOIN `{_settings.gcp_project}.raw_data.countries` c
          ON r.country_code = c.country_code
        WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
    """
    rows = list(_get_client().query(query).result())
    results = []
    for row in rows:
        entry = dict(row)
        if entry.get("avg_event_sentiment") is not None:
            entry["avg_event_sentiment"] = float(entry["avg_event_sentiment"])
        entry["latitude"] = float(entry["latitude"])
        entry["longitude"] = float(entry["longitude"])
        results.append(entry)
    return results
