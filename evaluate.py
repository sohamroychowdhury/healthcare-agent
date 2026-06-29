"""Lightweight evaluation harness.

Runs each scenario through the agent and checks the final answer against simple
expectations (keyword presence, sources cited, or that a guard-rail fired).
Prints a per-scenario pass/fail table and an overall score.

Usage:
    python evaluate.py --scenarios tests/scenarios.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from src.agent import run_agent, validate_query


def _check(scenario: Dict, answer: str, sources: List[str]) -> tuple[bool, str]:
    answer_l = answer.lower()
    keywords = [k.lower() for k in scenario.get("expect_keywords", [])]

    if keywords:
        if scenario.get("expect_any"):
            if not any(k in answer_l for k in keywords):
                return False, f"none of {keywords} found"
        else:
            missing = [k for k in keywords if k not in answer_l]
            if missing:
                return False, f"missing {missing}"

    if scenario.get("expect_sources") and not sources:
        return False, "expected sources, got none"

    return True, "ok"


def run_scenario(scenario: Dict) -> tuple[bool, str]:
    # Guard-rail scenarios expect validation to reject the input.
    if scenario.get("expect_error"):
        try:
            validate_query(scenario["query"])
            return False, "expected validation error, none raised"
        except ValueError:
            return True, "guard-rail rejected input as expected"

    result = run_agent(scenario["query"], verbose=False)
    return _check(scenario, result.answer, result.sources)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the healthcare agent")
    parser.add_argument("--scenarios", default="tests/scenarios.json")
    args = parser.parse_args()

    scenarios = json.loads(Path(args.scenarios).read_text())
    passed = 0
    print(f"Running {len(scenarios)} scenarios\n" + "-" * 60)
    for sc in scenarios:
        ok, detail = run_scenario(sc)
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {sc['name']}: {detail}")

    print("-" * 60)
    print(f"Score: {passed}/{len(scenarios)} scenarios passed")


if __name__ == "__main__":
    main()
