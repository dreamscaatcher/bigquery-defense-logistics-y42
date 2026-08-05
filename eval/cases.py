"""The labeled eval set.

Deliberately does NOT hardcode expected numbers (risk_level, utilization %,
etc.) - those come from live BigQuery/Neo4j data via
eval/ground_truth.py, reusing the same tool functions the agent itself
calls. Hardcoding numbers here would make this eval brittle against the
same kind of drift that caused the stale-R^2 doc bug this pipeline already
caught once. What IS hardcoded is the *shape* of what we expect: which
countries have depot data and which don't, so a case can assert the agent
handled that correctly instead of fabricating or omitting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvalCase:
    name: str
    country_code: Optional[str] = None
    depot_id: Optional[str] = None
    expect_depot_data: bool = True  # False = deliberately a country with no depot


# The 8 countries with both a BigQuery risk row and a Neo4j depot - these
# exercise the full hybrid-retrieval / cross-system-correlation path that's
# the actual point of this project.
CASES: list[EvalCase] = [
    EvalCase("usa_country", country_code="USA"),
    EvalCase("chn_country", country_code="CHN"),
    EvalCase("deu_country", country_code="DEU"),
    EvalCase("jpn_country", country_code="JPN"),
    EvalCase("gbr_country", country_code="GBR"),
    EvalCase("aus_country", country_code="AUS"),
    EvalCase("fra_country", country_code="FRA"),
    EvalCase("kor_country", country_code="KOR"),  # the flagship case - most capacity-strained
    # Depot-id-only request (no country_code) - exercises the other input path.
    EvalCase("kor_depot_direct", depot_id="DEPOT_KOR"),
    # A country with BigQuery risk data but NO Neo4j depot - the agent
    # should say so plainly (no_data_warning / explicit "no depot" text),
    # not fabricate capacity numbers for a depot that doesn't exist.
    EvalCase("ind_country_no_depot", country_code="IND", expect_depot_data=False),
]
