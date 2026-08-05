"""Run the labeled eval set end-to-end against the live pipeline.

Run: python -m eval.run_evals

For each case: invokes the real graph (BigQuery + Neo4j + Claude, same as
the API), fetches live ground truth via the same tool functions, checks the
briefing's text against it structurally, and runs an LLM-judge faithfulness
pass. Prints a pass/fail table and writes a JSON report to
eval/results/<timestamp>.json - "documented pass rate," not a vibes check,
per the portfolio non-negotiables.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.graph import compiled_graph
from eval.cases import CASES, EvalCase
from eval.ground_truth import GroundTruth, fetch as fetch_ground_truth
from eval.judge import judge_faithfulness

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _normalize(text: str) -> str:
    return text.lower().replace("_", " ")


def _check_structural(case: EvalCase, ground_truth: GroundTruth, briefing: dict) -> list[str]:
    """Returns a list of failure reasons; empty list = pass."""
    failures: list[str] = []
    full_text = _normalize(
        " ".join(
            [
                briefing.get("situation", ""),
                briefing.get("assessment", ""),
                briefing.get("recommendation", ""),
            ]
        )
    )

    if ground_truth.risk_level:
        if _normalize(ground_truth.risk_level) not in full_text:
            failures.append(
                f"expected risk_level '{ground_truth.risk_level}' not mentioned in briefing text"
            )

    if case.expect_depot_data:
        if not ground_truth.depot_found:
            failures.append(
                "test case setup error: expected depot data but ground truth found none "
                "(check eval/cases.py against the current seed data)"
            )
        elif ground_truth.capacity_status:
            if _normalize(ground_truth.capacity_status) not in full_text:
                failures.append(
                    f"expected capacity_status '{ground_truth.capacity_status}' "
                    "not mentioned in briefing text"
                )
    else:
        no_data_warning = briefing.get("no_data_warning")
        mentions_missing = any(
            phrase in full_text for phrase in ("no depot", "not found", "no data")
        )
        if not no_data_warning and not mentions_missing:
            failures.append(
                "expected no depot data to be found, but briefing neither set "
                "no_data_warning nor mentioned missing depot data - possible fabrication risk"
            )

    return failures


def run() -> int:
    results = []
    for case in CASES:
        print(f"--- {case.name} ---")
        ground_truth = fetch_ground_truth(case)

        try:
            state = compiled_graph.invoke(
                {"country_code": case.country_code, "depot_id": case.depot_id}
            )
            briefing = state["briefing"].model_dump()
            retrieved = state.get("retrieved", {})
        except Exception as exc:  # noqa: BLE001 - a crash is itself a failure to record
            print(f"  ERROR: {exc}")
            results.append(
                {"case": case.name, "passed": False, "failures": [f"exception: {exc}"]}
            )
            continue

        failures = _check_structural(case, ground_truth, briefing)

        full_text = " ".join(
            [briefing.get("situation", ""), briefing.get("assessment", ""), briefing.get("recommendation", "")]
        )
        verdict = judge_faithfulness(retrieved, full_text)
        if not verdict.faithful:
            failures.append(f"faithfulness judge flagged: {verdict.notes}")

        passed = not failures
        status = "PASS" if passed else "FAIL"
        print(f"  {status}")
        for f in failures:
            print(f"    - {f}")

        results.append(
            {
                "case": case.name,
                "passed": passed,
                "failures": failures,
                "judge_notes": verdict.notes,
                "briefing": briefing,
            }
        )

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{passed_count}/{total} passed")

    RESULTS_DIR.mkdir(exist_ok=True)
    report_path = RESULTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(
        json.dumps(
            {"passed": passed_count, "total": total, "results": results}, indent=2, default=str
        ),
        encoding="utf-8",
    )
    print(f"report written to {report_path}")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(run())
