"""Classical item analysis: the corpus as a calibrated item bank.

This uses classical test theory, not IRT — the honest scope. Given a roster of
judges scored against a
reference, each corpus step becomes an ITEM with:

- ``difficulty``      p = fraction of judges that got it right. An item every
  judge gets right carries no information about judge quality; an item every
  judge misses may be a construct blind spot.
- ``discrimination``  point-biserial correlation between item-correctness and
  each judge's total score: does getting THIS item right go with being a good
  judge overall? Items with |r| < 0.2 cannot separate judges.

Flags (thresholds after the Criterion defaults):
- ``too_easy``     p >= 0.90 — no information; a cull candidate.
- ``non_discrim``  |r| < 0.20 — cannot separate judges; a cull candidate.
- ``hard_review``  p <= 0.20 — flagged for HUMAN eyes, deliberately NOT a cull
  candidate: an item every judge misses is how the in-place-degradation blind
  spot was found. ``cull_candidate`` encodes exactly this asymmetry.

This is also what makes the VoI human-anchor selector difficulty-aware: spend
the anchor budget on mid-difficulty, discriminating steps, not easy anchors.

Dependencies: standard library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ItemStats:
    index: int
    difficulty: float
    discrimination: float
    flags: tuple[str, ...]
    cull_candidate: bool


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    vx = sum((x - mx) ** 2 for x in xs) / n
    vy = sum((y - my) ** 2 for y in ys) / n
    if vx == 0.0 or vy == 0.0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def analyze_items(
    judge_labels: dict[str, Sequence[bool]],
    reference_labels: Sequence[bool],
    *,
    too_easy: float = 0.90,
    non_discrim: float = 0.20,
    hard_review: float = 0.20,
) -> list[ItemStats]:
    """Per-item difficulty and discrimination over a judge roster.

    ``judge_labels`` maps judge name -> its label per item; ``reference_labels``
    is the gold reference the roster is scored against. Returns one ``ItemStats``
    per item, in item order.
    """
    n_items = len(reference_labels)
    if not judge_labels:
        raise ValueError("need at least one judge")
    for name, labels in judge_labels.items():
        if len(labels) != n_items:
            raise ValueError(
                f"judge {name!r} has {len(labels)} labels for {n_items} items"
            )

    judges = sorted(judge_labels)
    # correctness matrix: correct[j][i] = 1 if judge j matched the reference on item i
    correct = {
        j: [1.0 if judge_labels[j][i] == reference_labels[i] else 0.0 for i in range(n_items)]
        for j in judges
    }
    totals = {j: sum(correct[j]) for j in judges}

    out: list[ItemStats] = []
    for i in range(n_items):
        item_correct = [correct[j][i] for j in judges]
        p = sum(item_correct) / len(judges)
        r = _pearson(item_correct, [totals[j] for j in judges])
        flags: list[str] = []
        cull = False
        if p >= too_easy:
            flags.append("too_easy")
            cull = True
        if abs(r) < non_discrim:
            flags.append("non_discrim")
            if p > hard_review:
                cull = True
        if p <= hard_review:
            flags.append("hard_review")
            cull = False  # human eyes, never auto-cull: it may be a blind-spot finding
        out.append(
            ItemStats(
                index=i,
                difficulty=p,
                discrimination=r,
                flags=tuple(flags),
                cull_candidate=cull,
            )
        )
    return out
