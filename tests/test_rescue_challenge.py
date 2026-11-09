import copy

import pytest

from gyre.challenge.reconciliation import ReconciliationError, reconcile_reference
from gyre.challenge.scoring import RescueScorer


def _event(event_id, sequence, op, key, value=None):
    event = {"id": event_id, "sequence": sequence, "op": op, "key": key}
    if value is not None:
        event["value"] = value
    return event


def test_reference_orders_deduplicates_and_summarises():
    events = [
        _event("b", 2, "increment", "count", 2),
        _event("a", 1, "set", "count", 3),
        _event("b", 2, "increment", "count", 2),
    ]
    result = reconcile_reference(events)
    assert result["values"] == {"count": 5}
    assert result["applied_ids"] == ["a", "b"]
    assert result["summary"] == {
        "applied_count": 2,
        "key_count": 1,
        "last_sequence": 2,
        "numeric_total": 5.0,
    }


def test_reference_rejects_conflicting_duplicate_atomically():
    events = [
        _event("a", 1, "set", "count", 3),
        _event("a", 1, "set", "count", 4),
    ]
    original = copy.deepcopy(events)
    with pytest.raises(ReconciliationError):
        reconcile_reference(events)
    assert events == original


def test_reference_checkpoint_replay_is_idempotent():
    first = reconcile_reference([_event("a", 1, "set", "count", 3)])
    second = reconcile_reference(
        [
            _event("a", 1, "set", "count", 3),
            _event("b", 2, "increment", "count", 2),
        ],
        checkpoint=first,
    )
    replayed = reconcile_reference([], checkpoint=second)
    assert second == replayed
    assert second["values"] == {"count": 5}


def test_reference_rejects_unseen_stale_event_after_checkpoint():
    checkpoint = reconcile_reference([_event("b", 2, "set", "count", 3)])
    with pytest.raises(ReconciliationError):
        reconcile_reference(
            [_event("a", 1, "increment", "count", 2)],
            checkpoint=checkpoint,
        )


def test_reference_solution_scores_100_on_multiple_seeds():
    for seed in (419, 919, 1429):
        receipt = RescueScorer(seed=seed).score(reconcile_reference)
        assert receipt.integrity_passed
        assert receipt.score == pytest.approx(100.0)
        assert set(receipt.category_scores) == {
            "behavioral_conformance",
            "regression_preservation",
            "robustness_metamorphic",
            "recovery_replay_idempotency",
            "performance_boundary",
        }


def test_obviously_order_dependent_candidate_loses_robustness_points():
    def broken(events, checkpoint=None):
        values = {}
        applied = []
        seen = {}
        for event in events:
            if event["op"] == "set":
                values[event["key"]] = event["value"]
            elif event["op"] == "increment":
                values[event["key"]] = values.get(event["key"], 0) + event["value"]
            elif event["op"] == "delete":
                values.pop(event["key"], None)
            applied.append(event["id"])
            seen[event["id"]] = dict(event)
        return {
            "values": values,
            "applied_ids": applied,
            "seen": seen,
            "last_sequence": max((e["sequence"] for e in events), default=-1),
            "summary": {
                "applied_count": len(applied),
                "key_count": len(values),
                "last_sequence": max((e["sequence"] for e in events), default=-1),
                "numeric_total": float(
                    sum(v for v in values.values() if isinstance(v, (int, float)))
                ),
            },
        }

    receipt = RescueScorer(seed=419).score(broken)
    assert receipt.score < 80
    assert receipt.category_scores["robustness_metamorphic"] < 15

