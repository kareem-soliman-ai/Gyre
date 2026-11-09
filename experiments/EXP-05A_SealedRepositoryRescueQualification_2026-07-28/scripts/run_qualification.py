"""Run the EXP-05A scorer engineering qualification."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.reconciliation import ReconciliationError, reconcile_reference
from gyre.challenge.scoring import RescueScorer

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SEEDS = (419, 919, 1429)


def alternate_correct(events, checkpoint=None):
    """Independent dictionary-reduction implementation of the public contract."""

    source = checkpoint or {
        "values": {},
        "applied_ids": [],
        "seen": {},
        "last_sequence": -1,
    }
    values = dict(source["values"])
    order = list(source["applied_ids"])
    seen = {key: dict(value) for key, value in source["seen"].items()}
    frontier = source["last_sequence"]

    prepared = {}
    for raw in events:
        if not isinstance(raw, dict):
            raise ReconciliationError("event must be a dictionary")
        event_id = raw.get("id")
        sequence = raw.get("sequence")
        op = raw.get("op")
        key = raw.get("key")
        if not isinstance(event_id, str) or not event_id:
            raise ReconciliationError("bad id")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ReconciliationError("bad sequence")
        if not isinstance(key, str) or not key:
            raise ReconciliationError("bad key")
        if op not in {"set", "increment", "delete"}:
            raise ReconciliationError("bad op")
        event = {"id": event_id, "sequence": sequence, "op": op, "key": key}
        if op != "delete":
            if "value" not in raw:
                raise ReconciliationError("missing value")
            event["value"] = raw["value"]
        if op == "increment" and (
            isinstance(raw["value"], bool)
            or not isinstance(raw["value"], (int, float))
            or raw["value"] != raw["value"]
            or abs(raw["value"]) == float("inf")
        ):
            raise ReconciliationError("bad increment")
        prior = prepared.get(event_id, seen.get(event_id))
        if prior is not None:
            if prior != event:
                raise ReconciliationError("conflict")
            continue
        if sequence <= frontier:
            raise ReconciliationError("stale")
        prepared[event_id] = event

    for event in sorted(prepared.values(), key=lambda item: (item["sequence"], item["id"])):
        key = event["key"]
        if event["op"] == "set":
            values[key] = event["value"]
        elif event["op"] == "increment":
            current = values.get(key, 0)
            if isinstance(current, bool) or not isinstance(current, (int, float)):
                raise ReconciliationError("non-numeric current value")
            values[key] = current + event["value"]
        else:
            values.pop(key, None)
        order.append(event["id"])
        seen[event["id"]] = event
        frontier = event["sequence"]

    return {
        "values": values,
        "applied_ids": order,
        "seen": seen,
        "last_sequence": frontier,
        "summary": {
            "applied_count": len(order),
            "key_count": len(values),
            "last_sequence": frontier,
            "numeric_total": float(
                sum(
                    value
                    for value in values.values()
                    if not isinstance(value, bool) and isinstance(value, (int, float))
                )
            ),
        },
    }


def broken_starter(events, checkpoint=None):
    """Intentionally order-dependent, non-replayable starter implementation."""

    values = {}
    seen = {}
    applied = []
    for event in events:
        if event["op"] == "set":
            values[event["key"]] = event["value"]
        elif event["op"] == "increment":
            values[event["key"]] = values.get(event["key"], 0) + event["value"]
        else:
            values.pop(event["key"], None)
        seen[event["id"]] = dict(event)
        applied.append(event["id"])
    frontier = max((event["sequence"] for event in events), default=-1)
    return {
        "values": values,
        "applied_ids": applied,
        "seen": seen,
        "last_sequence": frontier,
        "summary": {
            "applied_count": len(applied),
            "key_count": len(values),
            "last_sequence": frontier,
            "numeric_total": float(
                sum(value for value in values.values() if isinstance(value, (int, float)))
            ),
        },
    }


def mutant_no_summary(events, checkpoint=None):
    state = reconcile_reference(events, checkpoint)
    state["summary"]["key_count"] = -1
    return state


def mutant_no_checkpoint(events, checkpoint=None):
    return reconcile_reference(events, None)


def mutant_input_order(events, checkpoint=None):
    return broken_starter(events, checkpoint)


IMPLEMENTATIONS = {
    "reference": reconcile_reference,
    "alternate_correct": alternate_correct,
    "broken_starter": broken_starter,
    "mutant_no_summary": mutant_no_summary,
    "mutant_no_checkpoint": mutant_no_checkpoint,
    "mutant_input_order": mutant_input_order,
}


def main() -> Path:
    matrix = {}
    for name, implementation in IMPLEMENTATIONS.items():
        matrix[name] = {}
        for seed in SEEDS:
            receipt = RescueScorer(seed=seed).score(implementation)
            matrix[name][str(seed)] = {
                "score": receipt.score,
                "categories": receipt.category_scores,
                "elapsed_seconds": receipt.elapsed_seconds,
            }

    correct_pass = all(
        matrix[name][str(seed)]["score"] == 100.0
        for name in ("reference", "alternate_correct")
        for seed in SEEDS
    )
    invalid_rejected = all(
        matrix[name][str(seed)]["score"] < 100.0
        for name in (
            "broken_starter",
            "mutant_no_summary",
            "mutant_no_checkpoint",
            "mutant_input_order",
        )
        for seed in SEEDS
    )
    result = {
        "experiment": "EXP-05A",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "development_seeds": list(SEEDS),
        "matrix": matrix,
        "engineering_gate": {
            "alternate_correct_acceptance": correct_pass,
            "declared_invalid_rejection": invalid_rejected,
            "passed": correct_pass and invalid_rejected,
        },
        "public_benchmark_gate": {
            "passed": False,
            "open_requirements": [
                "three independent fairness reviewers",
                "clean-container parity",
                "genuinely sealed post-freeze seeds",
                "anti-tamper review",
            ],
        },
        "claim_boundary": (
            "Engineering qualification only; not independent benchmark, "
            "controller-promotion, or joint-capability evidence."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "qualification_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()

