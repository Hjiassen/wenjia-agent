"""Golden-case evaluation runner.

Default static checks are intentionally offline: they validate that golden cases
point at known agents/tools and that the target agent has the required tool or
structured-output contract. Passing ``live=True`` executes the real Agent and
asserts event/output expectations.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from wenjia_agent.agents.fortune_agent import fortune_agent
from wenjia_agent.agents.main_agent import main_agent
from wenjia_agent.agents.mystic_tools_agent import mystic_tools_agent
from wenjia_agent.agents.naming_agent import naming_agent
from wenjia_agent.agents.profile_agent import profile_agent
from wenjia_agent.agents.relationship_agent import relationship_agent

DEFAULT_CASES_PATH = Path("evals/golden_cases.json")


class EvalCase(BaseModel):
    """One golden conversation contract."""

    id: str = Field(..., min_length=1)
    category: str = Field(default="general")
    input: str = Field(..., min_length=1)
    expected_route: str = Field(..., min_length=1)
    expected_tools: list[str] = Field(default_factory=list)
    expected_event_types: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    must_include_any: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    min_output_chars: int = 0


@dataclass
class CaseResult:
    id: str
    passed: bool
    mode: str
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def _tool_names(agent: Any) -> set[str]:
    names: set[str] = set()
    for tool in getattr(agent, "tools", []) or []:
        name = getattr(tool, "name", None)
        if isinstance(name, str):
            names.add(name)
    return names


AGENTS = {
    "WenjiaMainAgent": main_agent,
    "ProfileAgent": profile_agent,
    "FortuneAgent": fortune_agent,
    "RelationshipAgent": relationship_agent,
    "NamingAgent": naming_agent,
    "MysticToolsAgent": mystic_tools_agent,
}

AGENT_TOOLS = {name: _tool_names(agent) for name, agent in AGENTS.items()}
ALL_TOOLS = set().union(*AGENT_TOOLS.values())
STRUCTURED_AGENTS = {
    name for name, agent in AGENTS.items() if getattr(agent, "output_type", None) is not None
}


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    """Load and validate golden eval cases."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Eval cases file must contain a JSON array.")
    return [EvalCase.model_validate(item) for item in raw]


def _static_failures(case: EvalCase, seen_ids: set[str]) -> list[str]:
    failures: list[str] = []
    if case.id in seen_ids:
        failures.append(f"duplicate case id: {case.id}")
    seen_ids.add(case.id)

    agent = AGENTS.get(case.expected_route)
    if agent is None:
        failures.append(f"unknown expected_route: {case.expected_route}")
        return failures

    target_tools = AGENT_TOOLS[case.expected_route]
    for tool_name in case.expected_tools:
        if tool_name not in ALL_TOOLS:
            failures.append(f"unknown expected tool: {tool_name}")
        elif tool_name not in target_tools and case.expected_route != "WenjiaMainAgent":
            failures.append(f"{tool_name} is not available on {case.expected_route}")

    if "birth_gate" in case.contracts and "validate_birth_info_tool" not in target_tools:
        failures.append(f"{case.expected_route} does not expose validate_birth_info_tool")
    if "profile_reuse" in case.contracts and "list_profiles_tool" not in target_tools:
        failures.append(f"{case.expected_route} does not expose list_profiles_tool")
    if "structured_output" in case.contracts and case.expected_route not in STRUCTURED_AGENTS:
        failures.append(f"{case.expected_route} is not a structured-output agent")
    if "tool_grounding" in case.contracts and not case.expected_tools:
        failures.append("tool_grounding contract requires expected_tools")

    return failures


def run_static_suite(cases: list[EvalCase]) -> dict[str, Any]:
    """Run offline eval-contract checks."""

    seen_ids: set[str] = set()
    results = [
        CaseResult(
            id=case.id,
            mode="static",
            passed=not (failures := _static_failures(case, seen_ids)),
            failures=failures,
            details={
                "expected_route": case.expected_route,
                "expected_tools": case.expected_tools,
                "contracts": case.contracts,
            },
        )
        for case in cases
    ]
    return _report(results)


async def _run_live_case(case: EvalCase) -> CaseResult:
    from wenjia_agent.runtime.stream_runner import stream_agent_events

    events: list[dict[str, Any]] = []
    output = ""
    session_id = f"eval:{case.id}:{uuid.uuid4().hex}"
    async for event in stream_agent_events(session_id=session_id, message=case.input):
        events.append(event)
        if event.get("type") == "done":
            output = str(event.get("content") or "")

    failures: list[str] = []
    event_types = [str(event.get("type")) for event in events]
    tools = [str(event.get("tool")) for event in events if event.get("tool")]
    agents = [str(event.get("agent")) for event in events if event.get("agent")]

    for event_type in case.expected_event_types:
        if event_type not in event_types:
            failures.append(f"missing event type: {event_type}")
    for tool_name in case.expected_tools:
        if tool_name not in tools:
            failures.append(f"missing tool call: {tool_name}")
    if case.expected_route not in agents and case.expected_route != "WenjiaMainAgent":
        failures.append(f"missing expected agent route: {case.expected_route}")
    if len(output) < case.min_output_chars:
        failures.append(f"output too short: {len(output)} < {case.min_output_chars}")
    for needle in case.must_include:
        if needle not in output:
            failures.append(f"output missing required text: {needle}")
    if case.must_include_any and not any(needle in output for needle in case.must_include_any):
        failures.append("output missing all must_include_any candidates")
    for needle in case.must_not_include:
        if needle in output:
            failures.append(f"output contains forbidden text: {needle}")

    return CaseResult(
        id=case.id,
        mode="live",
        passed=not failures,
        failures=failures,
        details={
            "session_id": session_id,
            "event_types": event_types,
            "tools": tools,
            "agents": agents,
            "output_chars": len(output),
        },
    )


async def run_eval_suite(cases: list[EvalCase], *, live: bool = False) -> dict[str, Any]:
    """Run static checks and optionally real Agent golden-case checks."""

    static_report = run_static_suite(cases)
    if not live:
        return static_report

    live_results = [_dict_to_case_result(item) for item in static_report["cases"]]
    for case in cases:
        live_results.append(await _run_live_case(case))
    return _report(live_results)


def _dict_to_case_result(item: dict[str, Any]) -> CaseResult:
    return CaseResult(
        id=item["id"],
        mode=item["mode"],
        passed=bool(item["passed"]),
        failures=list(item.get("failures") or []),
        details=dict(item.get("details") or {}),
    )


def _report(results: list[CaseResult]) -> dict[str, Any]:
    passed = sum(1 for result in results if result.passed)
    return {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "cases": [
            {
                "id": result.id,
                "mode": result.mode,
                "passed": result.passed,
                "failures": result.failures,
                "details": result.details,
            }
            for result in results
        ],
    }


def format_report(report: dict[str, Any]) -> str:
    """Human-readable summary for CLI output."""

    summary = report["summary"]
    lines = [
        f"evals: {summary['passed']}/{summary['total']} passed",
    ]
    for case in report["cases"]:
        status = "PASS" if case["passed"] else "FAIL"
        lines.append(f"- {status} {case['mode']}::{case['id']}")
        for failure in case["failures"]:
            lines.append(f"  - {failure}")
    return "\n".join(lines)


def validate_cases_file(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    """Load cases with a clearer exception type for CLI/tests."""

    try:
        return load_cases(path)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
