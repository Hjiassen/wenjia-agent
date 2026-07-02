"""Run wenjia-agent golden evaluations.

Default mode is offline/static and costs no tokens:

    python scripts/run_evals.py

Use --live to execute the real Agent against the golden cases:

    python scripts/run_evals.py --live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from wenjia_agent.evals.runner import (
    DEFAULT_CASES_PATH,
    format_report,
    run_eval_suite,
    validate_cases_file,
)


def _default_report_path(live: bool) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    mode = "live" if live else "static"
    return Path("evals/reports") / f"{stamp}-{mode}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run wenjia-agent evals.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Path to golden case JSON file.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute real Agent calls in addition to offline contract checks.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON report to this path. Defaults under evals/reports/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = validate_cases_file(args.cases)
    report = asyncio.run(run_eval_suite(cases, live=args.live))

    report_path = args.report or _default_report_path(args.live)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(format_report(report))
    print(f"report: {report_path}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
