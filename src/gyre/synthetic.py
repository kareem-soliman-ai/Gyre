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

# --- the evidence channel -----------------------------------------------------
# Per concept: [primary error, changed error]. The changed error models external
# evidence arrival (the environment says something new). Errors share traceback
# boilerplate on purpose, so an error-channel sensor has to detect the changed
# *part*, not just compare trivially different strings.
_ERRORS: dict[str, list[str]] = {
    "db_try_except": [
        'Traceback (most recent call last):\n  File "app/db.py", line 42, in query\n'
        "    conn = pool.acquire(timeout=5)\n"
        "ConnectionError: connection refused by 10.0.0.12:5432",
        'Traceback (most recent call last):\n  File "app/db.py", line 47, in query\n'
        "    rows = conn.execute(sql)\n"
        "OperationalError: SSL connection has been closed unexpectedly",
    ],
    "off_by_one": [
        'Traceback (most recent call last):\n  File "app/report.py", line 88, in build\n'
        "    row = table[i]\n"
        "IndexError: list index out of range",
        "FAILED tests/test_report.py::test_totals - AssertionError: expected 12 rows, got 11",
    ],
    "null_check": [
        'Traceback (most recent call last):\n  File "app/views.py", line 130, in render\n'
        "    name = user.profile.display_name\n"
        "AttributeError: 'NoneType' object has no attribute 'profile'",
        'Traceback (most recent call last):\n  File "app/views.py", line 133, in render\n'
        "    avatar = profile.avatar_url\n"
        "KeyError: 'avatar_url'",
    ],
    "cache_key": [
        "FAILED tests/test_cache.py::test_tenant_isolation - AssertionError: "
        "tenant B read tenant A's dashboard from cache",
        "FAILED tests/test_cache.py::test_eviction - AssertionError: "
        "stale entry survived TTL expiry",
    ],
}

# For the progress control cell: the error moves downstream one stage per step,
# the signature of real debugging progress.
_PROGRESS_ERRORS: list[str] = [
    'Traceback (most recent call last):\n  File "app/main.py", line 12, in <module>\n'
    "    import handlers\n"
    "ModuleNotFoundError: No module named 'handlers'",
    'Traceback (most recent call last):\n  File "app/handlers.py", line 3, in <module>\n'
    "    from app.config import settings\n"
    "ImportError: cannot import name 'settings' from 'app.config'",
    'Traceback (most recent call last):\n  File "app/handlers.py", line 41, in handle\n'
    "    payload = json.loads(body)\n"
    "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
    "FAILED tests/test_handlers.py::test_roundtrip - AssertionError: "
    "status 500 != 200",
    "2 passed, 1 skipped -- tests/test_handlers.py::test_slow_path skipped (needs redis)",
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


def gen_depletion(
    concept: str = "null_check", n_productive: int = 3, n_stale: int = 3
) -> SyntheticTrace:
    """Productive prefix, then a stale tail: the rumination MORPHOLOGY the
    easy/hard/edge cells lack.

    Steps 0..n_productive-1 are genuinely distinct progress; then one fix is
    stated once (a clean first attempt) and repeated identically n_stale times
    (rumination). This is the pattern a marginal-rate sensor is built for: the
    loop WAS paying and then stops, so the tail's gain falls below the trace's own
    productive rate. An absolute-staleness sensor also catches identical repeats,
    but can false-fire on the genuinely novel prefix — so this cell is where the
    two sensor families are told apart (see internal EXP-VN-01)."""
    prefix = _DISTINCT[:n_productive]
    fix = _CONCEPTS[concept][0]
    texts = prefix + [fix] * (n_stale + 1)
    labels = [False] * n_productive + [False] + [True] * n_stale
    return SyntheticTrace(
        LabelledTrace(_obs(texts), labels, "L1", f"depletion:{concept}"), "depletion"
    )


# --- evidence-channel cells ---------------------------------------------------
# The information-arrival hypothesis, made falsifiable: rumination is not low
# *output* novelty, it is low *information* arrival, and the environment's
# response is the channel the agent cannot game. Each cell traps one sensor
# family. Labels follow the rubric: a step gains when it states a genuinely new
# hypothesis OR the environment's response changes; it ruminates when it recycles
# a hypothesis into an environment that is saying the same thing it already said.


def _obs_err(pairs: list[tuple[str, str | None]]) -> list[IterationObservation]:
    return [
        IterationObservation(artifact=a, error=e, index=i)
        for i, (a, e) in enumerate(pairs)
    ]


def gen_evid_easy(concept: str, n: int = 4) -> SyntheticTrace:
    """Identical artifact, identical error, n times. Everyone should catch it."""
    a, e = _CONCEPTS[concept][0], _ERRORS[concept][0]
    pairs = [(a, e)] * n
    labels = [False] + [True] * (n - 1)
    return SyntheticTrace(
        LabelledTrace(_obs_err(pairs), labels, "L1", f"evid-easy:{concept}"), "evid-easy"
    )


def gen_evid_hard(concept: str) -> SyntheticTrace:
    """Reworded artifact each step, identical error throughout. Lexical artifact
    sensors are fooled by the rewording; the unchanged error gives it away."""
    e = _ERRORS[concept][0]
    pairs = [(a, e) for a in _CONCEPTS[concept]]
    labels = [False] + [True] * (len(pairs) - 1)
    return SyntheticTrace(
        LabelledTrace(_obs_err(pairs), labels, "L1", f"evid-hard:{concept}"), "evid-hard"
    )


def gen_evid_retry(concept: str, k_before: int = 3, k_after: int = 2) -> SyntheticTrace:
    """Identical artifact retried, but the error CHANGES partway (external
    evidence arrived: a dependency installed, the world moved). The step that
    surfaces the new error is information arrival, NOT rumination; retries into
    the new error ruminate again. Artifact-only sensors (lexical or semantic)
    cannot get this cell right, whatever their threshold."""
    a = _CONCEPTS[concept][0]
    e1, e2 = _ERRORS[concept][0], _ERRORS[concept][1]
    pairs = [(a, e1)] * k_before + [(a, e2)] * k_after
    labels = (
        [False] + [True] * (k_before - 1)   # same-error retries ruminate
        + [False] + [True] * (k_after - 1)  # new error = gain; retries into it ruminate
    )
    return SyntheticTrace(
        LabelledTrace(_obs_err(pairs), labels, "L1", f"evid-retry:{concept}"), "evid-retry"
    )


def gen_evid_pivot(n: int = 4) -> SyntheticTrace:
    """Genuinely new approaches that all fail with the SAME error. Ruling out a
    hypothesis is information gain, so nothing here is rumination; an error-only
    sensor false-fires on every step after the first."""
    e = _ERRORS["db_try_except"][0]
    pairs = [(a, e) for a in _DISTINCT[:n]]
    labels = [False] * n
    return SyntheticTrace(
        LabelledTrace(_obs_err(pairs), labels, "L1", "evid-pivot"), "evid-pivot"
    )


def gen_evid_progress(n: int = 4) -> SyntheticTrace:
    """Distinct fixes, error moving downstream each step: real debugging
    progress with the evidence channel visible. Control cell; nothing fires."""
    pairs = list(zip(_DISTINCT[:n], _PROGRESS_ERRORS[:n]))
    labels = [False] * n
    return SyntheticTrace(
        LabelledTrace(_obs_err(pairs), labels, "L1", "evid-progress"), "evid-progress"
    )


def gen_l1_evidence_corpus() -> list[SyntheticTrace]:
    """The evidence-channel corpus: every cell carries the error channel."""
    out: list[SyntheticTrace] = []
    for concept in _CONCEPTS:
        out.append(gen_evid_easy(concept))
        out.append(gen_evid_hard(concept))
        out.append(gen_evid_retry(concept))
    out.append(gen_evid_pivot(4))
    out.append(gen_evid_progress(4))
    return out


def gen_l1_corpus() -> list[SyntheticTrace]:
    """A small, balanced synthetic corpus across the difficulty levels, including
    the depletion morphology (productive-then-stale) added after EXP-VN-01."""
    out: list[SyntheticTrace] = []
    for concept in _CONCEPTS:
        out.append(gen_easy(concept))
        out.append(gen_hard(concept))
    out.append(gen_edge(5))
    out.append(gen_edge(4))
    out.append(gen_depletion("null_check"))
    out.append(gen_depletion("cache_key"))
    return out


def by_difficulty(corpus: list[SyntheticTrace]) -> dict[str, list[LabelledTrace]]:
    """Group a corpus's LabelledTraces by difficulty for per-cell scoring."""
    groups: dict[str, list[LabelledTrace]] = {}
    for st in corpus:
        groups.setdefault(st.difficulty, []).append(st.trace)
    return groups
