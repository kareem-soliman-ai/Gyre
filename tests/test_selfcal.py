"""Self-calibrating decision layer: per-trace baseline z-scores, no fitted constants.

EXP-SC-01's finding made mechanical: the raw signals discriminate on real traces
(AUC ~0.77) while fixed thresholds saturate, and a per-trace head-baseline
z-score keeps almost all of it with ZERO fitted parameters. SelfBaselineProvider
wraps any provider and fills ``Measurement.standardized`` — the calibration
ladder rung that already existed in the architecture with no public provider
filling it.

Also pins the z-branch trigger semantics: at-baseline readings must NOT fire.
"""

import pytest

from gyre.loops._policy import trigger_state
from gyre.loops.rumination import IterationObservation
from gyre.measurement import Meaning, Measurement
from gyre.providers import get_provider
from gyre.providers.naive import DiffNoveltyProvider
from gyre.providers.selfcal import SelfBaselineProvider


# --- trigger_state z-branch semantics -------------------------------------------


def _m(standardized: float, meaning: Meaning) -> Measurement:
    return Measurement(value=0.5, meaning=meaning, standardized=standardized, provider="t")


def test_z_at_baseline_does_not_trigger_for_higher_is_healthier():
    # z = 0 means "exactly at this trace's own baseline" — healthy, never a trigger
    assert trigger_state(_m(0.0, Meaning.HIGHER_IS_HEALTHIER)) is False


def test_z_far_below_baseline_triggers_for_higher_is_healthier():
    # novelty collapsed 3 sigma below the trace's own baseline: fire
    assert trigger_state(_m(-3.0, Meaning.HIGHER_IS_HEALTHIER)) is True


def test_z_far_above_baseline_triggers_for_lower_is_healthier():
    assert trigger_state(_m(3.0, Meaning.LOWER_IS_HEALTHIER)) is True
    assert trigger_state(_m(0.0, Meaning.LOWER_IS_HEALTHIER)) is False


def test_z_deviation_triggers_on_magnitude():
    assert trigger_state(_m(-3.0, Meaning.DEVIATION)) is True
    assert trigger_state(_m(3.0, Meaning.DEVIATION)) is True
    assert trigger_state(_m(0.5, Meaning.DEVIATION)) is False


# --- SelfBaselineProvider --------------------------------------------------------


def _obs(text: str, i: int) -> IterationObservation:
    return IterationObservation(artifact=text, index=i)


DIVERSE_HEAD = [
    "read the config file and note the port",
    "trace the request through the auth middleware",
    "add a failing test for the timeout branch",
    "implement the retry with exponential backoff",
    "run the suite and inspect the two failures",
]


def test_wraps_inner_provider_identity():
    p = SelfBaselineProvider(DiffNoveltyProvider())
    assert p.loop_id == "L1"
    assert p.name == "selfcal:diff-novelty"


def test_burn_in_is_healthy_and_standardized_zero():
    p = SelfBaselineProvider(DiffNoveltyProvider(), baseline_steps=5)
    for i, t in enumerate(DIVERSE_HEAD):
        m = p.measure(_obs(t, i))
        assert m.standardized == 0.0
        assert trigger_state(m) is False


def test_stale_tail_triggers_via_z_with_no_threshold_anywhere():
    p = SelfBaselineProvider(DiffNoveltyProvider(), baseline_steps=5)
    for i, t in enumerate(DIVERSE_HEAD):
        p.measure(_obs(t, i))
    # near-identical repeats: badness rises far above the trace's own baseline
    fired = False
    for j in range(4):
        m = p.measure(_obs("re-run the suite and inspect the two failures", 5 + j))
        fired = fired or trigger_state(m)  # note: NO threshold supplied
    assert fired


def test_healthy_continuation_does_not_trigger():
    p = SelfBaselineProvider(DiffNoveltyProvider(), baseline_steps=5)
    for i, t in enumerate(DIVERSE_HEAD):
        p.measure(_obs(t, i))
    tail = [
        "fix the timeout constant and rerun only that test",
        "green; now profile the slow path with cProfile",
        "cache the parsed schema between calls",
    ]
    for j, t in enumerate(tail):
        m = p.measure(_obs(t, 5 + j))
        assert trigger_state(m) is False


def test_reset_clears_the_baseline():
    p = SelfBaselineProvider(DiffNoveltyProvider(), baseline_steps=3)
    for i, t in enumerate(DIVERSE_HEAD[:4]):
        p.measure(_obs(t, i))
    p.reset()
    m = p.measure(_obs("anything", 0))
    assert m.standardized == 0.0  # back in burn-in


def test_registered_variants_exist():
    for name in ("selfcal:diff-novelty", "selfcal:evidence-novelty"):
        p = get_provider(name)
        assert p.loop_id == "L1"


def test_rejects_baseline_shorter_than_two():
    with pytest.raises(ValueError):
        SelfBaselineProvider(DiffNoveltyProvider(), baseline_steps=1)


def test_a_baseline_relative_score_counts_as_calibrated():
    # REGRESSION GUARD. trigger_state walks decision -> probability ->
    # standardized -> value, but is_calibrated() once stopped at probability.
    # The bench therefore treated z-score sensors as raw and swept thresholds on
    # their raw values, scoring a decision rule the sensor does not implement.
    m = Measurement(value=0.5, meaning=Meaning.HIGHER_IS_HEALTHIER, standardized=-3.0)
    assert m.is_calibrated(), "a baseline-relative score IS a principled boundary"


def test_a_bare_value_is_still_uncalibrated():
    assert not Measurement(value=0.5, meaning=Meaning.HIGHER_IS_HEALTHIER).is_calibrated()
