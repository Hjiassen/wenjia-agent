from pathlib import Path

from wenjia_agent.evals.runner import load_cases, run_static_suite


def test_golden_cases_static_suite_passes():
    cases = load_cases(Path("evals/golden_cases.json"))

    report = run_static_suite(cases)

    assert report["summary"]["total"] == len(cases)
    assert report["summary"]["failed"] == 0
