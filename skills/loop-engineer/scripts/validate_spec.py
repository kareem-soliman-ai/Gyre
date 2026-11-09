#!/usr/bin/env python3
"""Validate a loop-engineer JSON design contract.

Usage:
    python validate_spec.py path/to/loop-graph-spec.json

Exit code 0 means the structural contract passes. It does not validate the
sensor, controller, or claimed outcome.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(message: str) -> None:
    FAILURES.append(message)


def warn(message: str) -> None:
    WARNINGS.append(message)


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def require_fields(item: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if field not in item or not nonempty(item[field]):
            fail(f"{label} requires non-empty field '{field}'.")


def validate(spec: dict[str, Any]) -> None:
    required_top = (
        "name",
        "objective",
        "task_constraints",
        "topology_decision",
        "mode",
        "state",
        "nodes",
        "edges",
        "loops",
        "dynamic_topology",
        "evaluation",
        "prompt_contracts",
    )
    require_fields(spec, required_top, "spec")

    constraints = spec.get("task_constraints", [])
    if isinstance(constraints, list):
        for index, constraint in enumerate(constraints):
            label = f"task_constraints[{index}]"
            if not isinstance(constraint, dict):
                fail(f"{label} must be an object.")
                continue
            require_fields(
                constraint,
                ("id", "requirement", "enforced_by", "on_violation"),
                label,
            )

    mode = spec.get("mode")
    if mode not in {"fixed", "shadow", "active"}:
        fail("spec.mode must be fixed, shadow, or active.")

    topology = spec.get("topology_decision", {})
    if isinstance(topology, dict):
        require_fields(
            topology,
            ("selected", "simpler_baseline", "why_more_structure_is_needed"),
            "topology_decision",
        )

    state = spec.get("state", {})
    if isinstance(state, dict):
        require_fields(state, ("fields", "persistence", "reset_boundary"), "state")

    nodes = spec.get("nodes", [])
    node_ids: set[str] = set()
    if isinstance(nodes, list):
        for index, node in enumerate(nodes):
            label = f"nodes[{index}]"
            if not isinstance(node, dict):
                fail(f"{label} must be an object.")
                continue
            require_fields(
                node,
                (
                    "id",
                    "kind",
                    "purpose",
                    "capability_evidence",
                    "consequence",
                    "authority",
                    "inputs",
                    "outputs",
                    "failure_policy",
                ),
                label,
            )
            node_id = node.get("id")
            if isinstance(node_id, str):
                if node_id in node_ids:
                    fail(f"{label} duplicates node id '{node_id}'.")
                node_ids.add(node_id)
            if node.get("kind") not in {"deterministic", "model", "agent", "human"}:
                fail(f"{label}.kind must be deterministic, model, agent, or human.")
            if node.get("consequence") not in {"low", "medium", "high"}:
                fail(f"{label}.consequence must be low, medium, or high.")
            if node.get("consequence") == "high" and node.get("human_approval") is not True:
                fail(f"{label} is high consequence and requires human approval.")

    edges = spec.get("edges", [])
    if isinstance(edges, list):
        for index, edge in enumerate(edges):
            label = f"edges[{index}]"
            if not isinstance(edge, dict):
                fail(f"{label} must be an object.")
                continue
            require_fields(
                edge,
                ("from", "to", "mechanism", "guard", "handoff_contract", "on_failure"),
                label,
            )
            for endpoint in ("from", "to"):
                node_id = edge.get(endpoint)
                if node_id not in node_ids:
                    fail(f"{label}.{endpoint} references unknown node '{node_id}'.")

    loops = spec.get("loops", [])
    if isinstance(loops, list):
        for index, loop in enumerate(loops):
            label = f"loops[{index}]"
            if not isinstance(loop, dict):
                fail(f"{label} must be an object.")
                continue
            require_fields(
                loop,
                (
                    "id",
                    "controlled_variable",
                    "observation",
                    "sensor",
                    "decision_rule",
                    "actions",
                    "terminal_states",
                    "budget",
                    "escalation",
                    "persistence",
                ),
                label,
            )
            sensor = loop.get("sensor", {})
            if isinstance(sensor, dict):
                require_fields(
                    sensor,
                    ("name", "maturity", "independence", "confounds"),
                    f"{label}.sensor",
                )
                if sensor.get("maturity") not in {
                    "raw",
                    "standardized",
                    "calibrated",
                    "self-deciding",
                }:
                    fail(
                        f"{label}.sensor.maturity must be raw, standardized, "
                        "calibrated, or self-deciding."
                    )
                if (
                    sensor.get("maturity") == "calibrated"
                    and not nonempty(sensor.get("calibration_evidence"))
                ):
                    fail(
                        f"{label}.sensor labelled calibrated requires non-empty "
                        "calibration_evidence."
                    )
                if sensor.get("independence") == "same_context":
                    warn(
                        f"{label}.sensor uses the generator's same context; treat "
                        "this as a correlated self-report, not independent evidence."
                    )
            budget = loop.get("budget", {})
            if isinstance(budget, dict):
                require_fields(
                    budget,
                    ("max_cycles", "max_cost_usd", "max_minutes"),
                    f"{label}.budget",
                )

    dynamic = spec.get("dynamic_topology", {})
    if isinstance(dynamic, dict):
        require_fields(dynamic, ("mode", "hysteresis", "promotion_gate"), "dynamic_topology")
        if dynamic.get("mode") not in {"fixed", "shadow", "active"}:
            fail("dynamic_topology.mode must be fixed, shadow, or active.")
        if dynamic.get("enabled") or mode == "active" or dynamic.get("mode") == "active":
            if not dynamic.get("switching_costs"):
                fail("Active or enabled dynamic topology requires switching costs.")
            if not nonempty(dynamic.get("hysteresis")):
                fail("Active or enabled dynamic topology requires hysteresis.")
            if not nonempty(dynamic.get("promotion_gate")):
                fail("Active or enabled dynamic topology requires a promotion gate.")

    evaluation = spec.get("evaluation", {})
    if isinstance(evaluation, dict):
        require_fields(
            evaluation,
            (
                "link_a_sensor",
                "link_b_policy",
                "link_c_outcome",
                "matched_baseline",
                "trap_cases",
            ),
            "evaluation",
        )

    prompts = spec.get("prompt_contracts", {})
    if isinstance(prompts, dict):
        require_fields(prompts, ("generator", "sensor", "controller"), "prompt_contracts")
        texts = [str(prompts.get(key, "")).strip() for key in ("generator", "sensor", "controller")]
        if len(set(texts)) != 3:
            fail("Generator, sensor, and controller prompt contracts must be distinct.")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: could not read a JSON spec: {exc}")
        return 1
    if not isinstance(data, dict):
        print("FAIL: the root JSON value must be an object.")
        return 1

    validate(data)
    for message in WARNINGS:
        print(f"WARN: {message}")
    for message in FAILURES:
        print(f"FAIL: {message}")
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} failure(s), {len(WARNINGS)} warning(s))")
        return 1
    print(f"RESULT: PASS ({len(WARNINGS)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
