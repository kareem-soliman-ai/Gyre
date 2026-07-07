"""Synthetic L1 traces with known ground truth.

The escape from hand-scoring. Instead of labelling real traces (which needs you to
hold a long trajectory in working memory and decide, per step, whether it recycled
or advanced — genuinely hard), you *construct* the rumination and therefore know
the labels for free. The sensors do not see the construction rule; they only see
the text, so detecting the injected rumination is a real test, not a circular one.

Three difficulty levels, matching the eval design:

- ``easy``  — lexically identical repeats. Any sensor should catch these.
- ``hard``  — the same fix reworded in genuinely different words (semantic
              staleness under surface novelty). A lexical sensor is fooled; a
              semantic one should catch it. This is where the measurement gap
              lives.
- ``edge``  — genuine progress that *looks* like thrashing: each step changes
              direction, but each is a real response to new information. No sensor
              should fire. This is the false-positive trap.

The `hard` and `edge` cases are deliberately adversarial: `hard` punishes a sensor
that only reads surface form, `edge` punishes one that fires on any change. A
sensor has to understand information gain to pass both, which is the whole point.
"""

from __future__ import annotations

from dataclasses import dataclass

from gyre.bench import LabelledTrace
from gyre.loops.rumination import IterationObservation

# Each concept is one fix, expressed several genuinely different ways (semantic
# equivalents). Reusing a concept across steps = the same idea = rumination.
_CONCEPTS: dict[str, list[str]] = {
    "db_try_except": [
        "Add a try/except around the database call to catch the failure.",
        "Wrap the query in a try-except so a ConnectionError is handled.",
        "Guard the DB access with exception handling for the connection drop.",
        "Put error handling around the database operation to swallow the fault.",
    ],
    "off_by_one": [
        "Fix the loop bound; it's an off-by-one so subtract one from the range.",
        "The range is one too long, adjust the upper index down by one.",
        "Correct the boundary: iterate to n-1 instead of n to stop the overrun.",
    ],
    "null_check": [
        "Add a null check before dereferencing the user object.",
        "Guard against a None value so we don't crash on the empty user.",
        "Verify the object exists before accessing its field to avoid the NPE.",
    ],
    "cache_key": [
        "The cache key is wrong; include the tenant id so results don't collide.",
        "Namespace the cache entry by tenant to stop cross-account bleed.",
        "Add the account identifier to the cache key to separate the tenants.",
    ],
}

# Genuinely distinct fixes, for the edge case where each step is real progress.
_DISTINCT: list[str] = [
    "Rewrite the module to use async so the calls don't block.",
    "Actually sync is fine here; revert the async and add a small cache instead.",
    "The cache introduces a race; replace it with an explicit lock around the write.",
    "The lock is too coarse and deadlocks; switch to a per-key lock keyed by id.",
    "Per-key locks work but leak; add a cleanup pass to evict stale lock entries.",
]


@dataclass
class SyntheticTrace:
    trace: LabelledTrace
    difficulty: str


def _obs(texts: list[str]) -> list[IterationObservation]:
    return [IterationObservation(artifact=t, index=i) for i, t in enumerate(texts)]


def gen_easy(concept: str, n: int = 4) -> SyntheticTrace:
    """Lexically identical repeats: first attempt, then the same line again."""
    phrasing = _CONCEPTS[concept][0]
    texts = [phrasing] * n
    labels = [False] + [True] * (n - 1)  # every repeat after the first is rumination
    return SyntheticTrace(LabelledTrace(_obs(texts), labels, "L1", f"easy:{concept}"), "easy")


def gen_hard(concept: str, tail_new: bool = True) -> SyntheticTrace:
    """The same fix reworded each step (semantic staleness, surface novelty),
    optionally ending with a genuinely new approach that must NOT be flagged."""
    rewordings = _CONCEPTS[concept]
    texts = list(rewordings)  # step 0 new, steps 1..k reworded repeats
    labels = [False] + [True] * (len(rewordings) - 1)
    if tail_new:
        texts.append(_DISTINCT[0])  # a real pivot to a different approach
        labels.append(False)
    return SyntheticTrace(LabelledTrace(_obs(texts), labels, "L1", f"hard:{concept}"), "hard")


def gen_edge(n: int = 5) -> SyntheticTrace:
    """Genuine progress that looks like thrashing: each step is a new, distinct
    response to the previous one. Nothing here is rumination."""
    texts = _DISTINCT[:n]
    labels = [False] * len(texts)
    return SyntheticTrace(LabelledTrace(_obs(texts), labels, "L1", "edge:progress"), "edge")


def gen_l1_corpus() -> list[SyntheticTrace]:
    """A small, balanced synthetic corpus across the three difficulty levels."""
    out: list[SyntheticTrace] = []
    for concept in _CONCEPTS:
        out.append(gen_easy(concept))
        out.append(gen_hard(concept))
    out.append(gen_edge(5))
    out.append(gen_edge(4))
    return out


def by_difficulty(corpus: list[SyntheticTrace]) -> dict[str, list[LabelledTrace]]:
    """Group a corpus's LabelledTraces by difficulty for per-cell scoring."""
    groups: dict[str, list[LabelledTrace]] = {}
    for st in corpus:
        groups.setdefault(st.difficulty, []).append(st.trace)
    return groups
