"""Weighted, seedable scorer for the event-reconciliation rescue task."""

from __future__ import annotations

import copy
import random
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gyre.challenge.reconciliation import reconcile_reference

Candidate = Callable[
    [Sequence[Mapping[str, Any]], Mapping[str, Any] | None],
    Mapping[str, Any],
]

CATEGORY_WEIGHTS = {
    "behavioral_conformance": 55.0,
    "regression_preservation": 15.0,
    "robustness_metamorphic": 15.0,
    "recovery_replay_idempotency": 10.0,
    "performance_boundary": 5.0,
}


@dataclass(frozen=True)
class CategoryResult:
    passed: int
    total: int
    points: float


@dataclass(frozen=True)
class RescueScoreReceipt:
    seed: int
    score: float
    integrity_passed: bool
    category_scores: dict[str, float]
    category_results: dict[str, CategoryResult]
    elapsed_seconds: float


def _event(event_id: str, sequence: int, op: str, key: str, value: Any = None):
    event = {"id": event_id, "sequence": sequence, "op": op, "key": key}
    if op != "delete":
        event["value"] = value
    return event


def _equal(candidate: Candidate, events, checkpoint=None) -> bool:
    candidate_events = copy.deepcopy(events)
    candidate_checkpoint = copy.deepcopy(checkpoint)
    expected = reconcile_reference(copy.deepcopy(events), copy.deepcopy(checkpoint))
    try:
        actual = candidate(candidate_events, candidate_checkpoint)
    except Exception:
        return False
    return (
        actual == expected
        and candidate_events == events
        and candidate_checkpoint == checkpoint
    )


def _rejects(candidate: Candidate, events, checkpoint=None) -> bool:
    try:
        candidate(copy.deepcopy(events), copy.deepcopy(checkpoint))
    except ValueError:
        return True
    except Exception:
        return False
    return False


class RescueScorer:
    """Evaluate one candidate against generated, category-weighted cases."""

    def __init__(self, *, seed: int, performance_seconds: float = 1.0) -> None:
        self.seed = seed
        self.performance_seconds = performance_seconds

    def _behavioral(self, candidate: Candidate) -> list[bool]:
        rng = random.Random(self.seed)
        checks = [
            _equal(candidate, [_event("a", 0, "set", "x", 2)]),
            _equal(candidate, [_event("a", 0, "increment", "x", 2)]),
            _equal(
                candidate,
                [
                    _event("b", 2, "increment", "x", 2),
                    _event("a", 1, "set", "x", 3),
                ],
            ),
            _equal(
                candidate,
                [
                    _event("a", 0, "set", "x", 3),
                    _event("b", 1, "delete", "x"),
                ],
            ),
            _equal(
                candidate,
                [
                    _event("a", 0, "set", "x", "label"),
                    _event("b", 1, "set", "y", True),
                ],
            ),
            _rejects(
                candidate,
                [
                    _event("a", 0, "set", "x", 1),
                    _event("a", 0, "set", "x", 2),
                ],
            ),
            _rejects(candidate, [{"id": "a", "sequence": 0, "op": "set", "key": "x"}]),
            _rejects(candidate, [_event("a", -1, "set", "x", 1)]),
            _rejects(candidate, [_event("a", 0, "unknown", "x", 1)]),
        ]
        for case_index in range(12):
            values: dict[str, float] = {}
            events = []
            for event_index in range(8):
                key = rng.choice(["alpha", "beta", "gamma"])
                if key not in values or rng.random() < 0.35:
                    value = rng.randint(-5, 9)
                    values[key] = value
                    op = "set"
                else:
                    value = rng.randint(-3, 4)
                    values[key] += value
                    op = "increment"
                events.append(
                    _event(
                        f"{case_index}-{event_index}",
                        event_index,
                        op,
                        key,
                        value,
                    )
                )
            rng.shuffle(events)
            checks.append(_equal(candidate, events))
        return checks

    def _regression(self, candidate: Candidate) -> list[bool]:
        return [
            _equal(candidate, [_event("a", 0, "set", "legacy", 1)]),
            _equal(
                candidate,
                [
                    _event("a", 0, "set", "legacy", 1),
                    _event("b", 1, "increment", "legacy", 2),
                ],
            ),
            _equal(
                candidate,
                [
                    _event("a", 0, "set", "legacy", 1),
                    _event("b", 1, "delete", "legacy"),
                ],
            ),
        ]

    def _robustness(self, candidate: Candidate) -> list[bool]:
        base = [
            _event("a", 0, "set", "x", 2),
            _event("b", 1, "increment", "x", 3),
            _event("c", 2, "set", "y", 7),
        ]
        permutations = [base[::-1], [base[1], base[2], base[0]]]
        duplicate = [base[0], base[1], base[0], base[2], base[1]]
        return [
            *[_equal(candidate, variant) for variant in permutations],
            _equal(candidate, duplicate),
            _rejects(candidate, [_event("a", 0, "increment", "x", float("inf"))]),
            _rejects(candidate, [{"id": "", "sequence": 0, "op": "delete", "key": "x"}]),
        ]

    def _recovery(self, candidate: Candidate) -> list[bool]:
        first_events = [
            _event("a", 0, "set", "x", 2),
            _event("b", 1, "increment", "x", 3),
        ]
        try:
            first = candidate(copy.deepcopy(first_events), None)
        except Exception:
            return [False, False, False, False]
        later = [
            _event("c", 2, "set", "y", 7),
            _event("d", 3, "delete", "x"),
        ]
        checks = [
            _equal(candidate, later, first),
            _equal(candidate, first_events, first),
            _rejects(candidate, [_event("stale", 0, "set", "z", 1)], first),
            _rejects(candidate, [_event("a", 0, "set", "x", 999)], first),
        ]
        return checks

    def _performance(self, candidate: Candidate) -> tuple[list[bool], float]:
        events = [_event(f"e-{i}", i, "increment", f"k-{i % 17}", 1) for i in range(5000)]
        started = time.perf_counter()
        correct = _equal(candidate, events)
        elapsed = time.perf_counter() - started
        return [correct and elapsed <= self.performance_seconds], elapsed

    def score(self, candidate: Candidate) -> RescueScoreReceipt:
        started = time.perf_counter()
        category_checks = {
            "behavioral_conformance": self._behavioral(candidate),
            "regression_preservation": self._regression(candidate),
            "robustness_metamorphic": self._robustness(candidate),
            "recovery_replay_idempotency": self._recovery(candidate),
        }
        performance_checks, performance_elapsed = self._performance(candidate)
        category_checks["performance_boundary"] = performance_checks
        category_results: dict[str, CategoryResult] = {}
        category_scores: dict[str, float] = {}
        for category, checks in category_checks.items():
            passed = sum(checks)
            total = len(checks)
            points = CATEGORY_WEIGHTS[category] * passed / total
            category_results[category] = CategoryResult(passed, total, points)
            category_scores[category] = points
        return RescueScoreReceipt(
            seed=self.seed,
            score=sum(category_scores.values()),
            integrity_passed=True,
            category_scores=category_scores,
            category_results=category_results,
            elapsed_seconds=time.perf_counter() - started,
        )


__all__ = [
    "CATEGORY_WEIGHTS",
    "CategoryResult",
    "RescueScoreReceipt",
    "RescueScorer",
]

