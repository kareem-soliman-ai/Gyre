"""Loop-health scoring tests (no API, public sensors only)."""

import json

from gyre.loop_health import LoopHealthResult, estimate_tokens, score_loop_health

_OSCILLATION = [
    "Let me work out why the test fails: it expected 12 rows but got 11.",
    "That is an off-by-one in the aggregation, one group is being dropped.",
    "The last group is never flushed after the loop ends, so its row is not appended.",
    "So the minimal fix is to flush the final group once, after the loop.",
    "Actually, maybe I should flush inside the loop when the group key changes, that is cleaner.",
    "However, flushing inside the loop would double-count the last group, since it also flushes after.",
    "Actually, if I only flush after the loop, the intermediate groups are already fine.",
    "However, flushing inside on key-change is the standard pattern and handles every group uniformly.",
    "Actually, the after-loop flush is simpler and I already know it works for the intermediate groups.",
    "However, mixing inside and after flushing risks the double-count I just mentioned.",
    "Actually, let me just flush after the loop, that is the minimal change.",
    "However, is the after-loop flush definitely handling the final key-change correctly...",
]

_PROGRESS = [
    "Add async so the calls do not block.",
    "Revert async and add a small cache instead.",
    "The cache races, so add an explicit write lock.",
    "The lock deadlocks, so switch to a per-key lock keyed by id.",
    "Per-key locks leak, so add a cleanup pass to evict stale entries.",
]


def test_scores_a_reasoning_loop_as_ruminating():
    r = score_loop_health(_OSCILLATION)
    assert r.ruminating is True
    assert r.onset_step is not None and r.onset_step <= 7   # catches the circle
    assert r.tokens_at_risk > 0 and r.tokens_at_risk < r.tokens_total
    assert 0.0 < r.rumination_fraction <= 1.0
    assert r.exit_reason != "continue"


def test_healthy_progress_is_not_flagged():
    r = score_loop_health(_PROGRESS)
    assert r.ruminating is False
    assert r.onset_step is None
    assert r.tokens_at_risk == 0
    assert r.rumination_fraction == 0.0


def test_result_is_json_safe():
    r = score_loop_health(_OSCILLATION)
    blob = json.dumps(r.to_dict())
    back = json.loads(blob)
    assert back["ruminating"] is True
    assert back["tokens_at_risk"] > 0
    assert len(back["steps"]) == len(_OSCILLATION)


def test_accepts_dicts_and_strings():
    as_dicts = [{"artifact": s} for s in _PROGRESS]
    assert score_loop_health(as_dicts).n_steps == len(_PROGRESS)


def test_token_estimate_is_positive():
    assert estimate_tokens("three word thought") == 4  # 3 words * 1.3 -> 4
    assert estimate_tokens("") == 1
