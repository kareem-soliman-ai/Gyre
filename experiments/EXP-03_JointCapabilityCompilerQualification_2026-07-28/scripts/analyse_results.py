#!/usr/bin/env python3
"""Produce post-run diagnostics without changing EXP-03 primary scores."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = EXPERIMENT_DIR / "results"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    records = read_json(RESULTS_DIR / "records.json")
    arms = sorted({record["arm"] for record in records})
    final_passes = {
        arm: sum(
            bool(record["score"]["final"]["passed"])
            for record in records
            if record["arm"] == arm
        )
        for arm in arms
    }

    index = {
        (record["task_id"], record["model"], record["seed"], record["arm"]):
        int(record["score"]["final"]["passed"])
        for record in records
    }
    blocks = sorted(
        {
            (record["task_id"], record["model"], record["seed"])
            for record in records
        }
    )
    final_pairs = [
        (
            index[(*block, "compiler_skill")],
            index[(*block, "compiler_template")],
        )
        for block in blocks
    ]
    compiler_only = sum(a == 1 and b == 0 for a, b in final_pairs)
    template_only = sum(a == 0 and b == 1 for a, b in final_pairs)

    candidate = [
        record for record in records if record["arm"] == "compiler_skill"
    ]
    check_failures = Counter()
    task_routes: dict[str, list[float]] = defaultdict(list)
    task_final_passes = Counter()
    for record in candidate:
        for check, passed in record["score"]["final"]["checks"].items():
            if not passed:
                check_failures[check] += 1
        task_routes[record["task_id"]].append(
            record["score"]["final"]["runtime_route_accuracy"]
        )
        task_final_passes[record["task_id"]] += int(
            record["score"]["final"]["passed"]
        )

    truncations: dict[str, Counter[str]] = {
        "stage1": Counter(),
        "stage2": Counter(),
    }
    for stage in truncations:
        for path in (RESULTS_DIR / "raw" / stage).glob("*.json"):
            receipt = read_json(path)
            choices = (
                receipt.get("provider_response", {}).get("choices", [])
            )
            if choices and choices[0].get("finish_reason") == "length":
                truncations[stage][receipt["arm"]] += 1

    diagnostics = {
        "status": "posthoc diagnostics; primary scores unchanged",
        "final_contract_passes": final_passes,
        "paired_final_compiler_vs_template": {
            "n": len(final_pairs),
            "compiler_only": compiler_only,
            "template_only": template_only,
            "risk_difference": sum(a - b for a, b in final_pairs)
            / len(final_pairs),
        },
        "compiler_check_failures": dict(check_failures),
        "compiler_by_task": {
            task: {
                "n": len(accuracies),
                "final_passes": task_final_passes[task],
                "runtime_route_accuracy": sum(accuracies) / len(accuracies),
            }
            for task, accuracies in sorted(task_routes.items())
        },
        "length_finish_counts": {
            stage: dict(counts) for stage, counts in truncations.items()
        },
        "integrity_flags": [
            "All 64 cells produced parseable stage receipts and no recorded API error.",
            "The joint-pass outcome has a floor effect: every arm scored 0/16.",
            "The hidden critical-question set omitted obvious route-changing unknowns present in the initial briefs.",
            "Frozen regex patterns also missed clear paraphrases; no primary score was changed post hoc.",
            "Conditional final-contract comparisons remain descriptive because oracle revelation depended on the flawed intake criterion.",
        ],
    }
    write_json(RESULTS_DIR / "diagnostics.json", diagnostics)
    print(json.dumps(diagnostics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
