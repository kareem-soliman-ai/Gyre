#!/usr/bin/env python3
"""Explore verification and control choices without an API key.

Examples:
    python scripts/loop_playground.py --list
    python scripts/loop_playground.py --case verifier-drift
    python scripts/loop_playground.py --case taste-boundary --level builder
    python scripts/loop_playground.py --case high-stakes-ambiguity --json
    python scripts/loop_playground.py --cases my-cases.json --policy control-menu

The included policies are transparent teaching baselines. They are not fitted
Gyre instruments and have not been qualified for production decisions.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gyre.control_playground import (  # noqa: E402
    evaluate_scenario,
    load_scenarios,
    validate_receipt,
)

DEFAULT_CASES = REPO / "docs" / "examples" / "loop-control-cases.json"


def _beginner(case: dict[str, Any], receipt: dict[str, Any]) -> str:
    human = "yes" if receipt["interrupt_human"] else "no"
    lines = [
        f"\n{case['title']} [{receipt['policy']}]",
        f"  Situation: {case['description']}",
        (
            "  Evidence: objective="
            f"{case['objective_outcome']['status']}; "
            f"acceptance={case['human_acceptance']['status']}"
        ),
        f"  Recommendation: {receipt['recommendation']}",
        f"  Interrupt the human now: {human}",
        f"  Lesson: {receipt['capability_lesson']}",
    ]
    return "\n".join(lines)


def _builder(case: dict[str, Any], receipt: dict[str, Any]) -> str:
    lines = [
        _beginner(case, receipt),
        "  Control trace:",
        (
            "    sensor -> "
            f"objective:{case['objective_outcome']['status']}, "
            f"acceptance:{case['human_acceptance']['status']}"
        ),
        (
            "    policy -> "
            f"consequence:{case['consequence']}, ambiguity:{case['ambiguity']}, "
            f"capability_lead:{case['capability_lead']}"
        ),
        (
            "    action -> "
            f"{receipt['action']} "
            f"(stop_action={str(receipt['stop_current_action']).lower()}, "
            f"terminate_task={str(receipt['task_terminated']).lower()})"
        ),
        f"    authority -> {receipt['authority_boundary']}",
        f"    confidence -> {receipt['confidence']['status']}",
        (
            "    human observation -> "
            f"{receipt['human_measurement']['maturity']} "
            f"{receipt['human_measurement']['target']} signal; "
            "not objective outcome evidence"
        ),
        "  Alternatives considered:",
    ]
    lines.extend(
        f"    - {item['action']}: {item['why_not']}"
        for item in receipt["alternatives"]
    )
    lines.append(
        f"  Human controller ({receipt['human_controller']['mode']}):"
    )
    lines.extend(
        f"    - {item['id']}: {item['effect']}"
        for item in receipt["human_controller"]["actions"]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="JSON case file (default: the five repo examples)",
    )
    parser.add_argument("--case", help="run one case id (default: all)")
    parser.add_argument(
        "--policy",
        choices=("control-menu", "binary-stop", "both"),
        default="both",
    )
    parser.add_argument(
        "--level",
        choices=("beginner", "builder", "expert"),
        default="beginner",
    )
    parser.add_argument(
        "--policy-plugin",
        help=(
            "module:function taking one scenario and returning a complete receipt; "
            "runs alongside the selected public baseline(s)"
        ),
    )
    parser.add_argument("--list", action="store_true", help="list case ids")
    parser.add_argument("--json", action="store_true", help="emit receipts as JSON")
    args = parser.parse_args()

    cases = load_scenarios(args.cases)
    if args.list:
        for case in cases:
            print(f"{case['id']}: {case['title']}")
        return 0

    selected = [case for case in cases if not args.case or case["id"] == args.case]
    if not selected:
        parser.error(f"unknown case id: {args.case}")

    policies = (
        ("control-menu", "binary-stop")
        if args.policy == "both"
        else (args.policy,)
    )
    results = [
        {
            "case": case,
            "receipt": evaluate_scenario(case, policy=policy),
        }
        for case in selected
        for policy in policies
    ]
    if args.policy_plugin:
        module_name, separator, function_name = args.policy_plugin.partition(":")
        if not separator or not module_name or not function_name:
            parser.error("--policy-plugin must be module:function")
        policy_function = getattr(importlib.import_module(module_name), function_name)
        for case in selected:
            receipt = policy_function(case)
            validate_receipt(receipt)
            results.append({"case": case, "receipt": receipt})

    if args.json or args.level == "expert":
        print(json.dumps(results, indent=2))
        return 0

    render = _builder if args.level == "builder" else _beginner
    print("Gyre Loop Control Lab")
    print(
        "Teaching baselines only: a route is a hypothesis until its sensor, "
        "policy, and outcome chain are tested."
    )
    for result in results:
        print(render(result["case"], result["receipt"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
