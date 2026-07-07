"""Loop-controller tests, written to be provider-agnostic.

The point of these tests is that the *loop logic* is correct regardless of the
sensor, and that swapping the sensor changes what the loop catches. The
centrepiece is ``test_value_gap_same_loop_two_sensors``: the same RuminationMonitor
misses a rumination episode with a naive lexical sensor and catches it with a
better one. That is the whole architecture in one assertion.
"""

import pytest

from gyre import (
    CalibrationGovernor,
    ChannelObservation,
    EinstellungBreaker,
    ExitReason,
    HabituationFilter,
    IterationObservation,
    Meaning,
    Measurement,
    PredictionOutcome,
    RuminationMonitor,
)
from gyre.loops._policy import ThresholdRequired
from gyre.providers import (
    DiffNoveltyProvider,
    RollingBrierProvider,
    ZScoreDeviationProvider,
)


# --- test doubles: fakes standing in for "better" sensors ---------------------

class _Obs:
    """An observation carrying both a surface artifact (for a lexical sensor) and
    a hidden concept id (for a semantic sensor). Lets two sensors read the same
    stream and disagree."""

    def __init__(self, artifact: str, concept: int) -> None:
        self.artifact = artifact
        self.concept = concept
        self.error = None
        self.index = 0


class FakeSemanticL1:
    """A stand-in for a semantic rumination sensor. It "knows" the concept id and
    fires when the agent lands on the same concept twice running, catching
    rumination that renaming would hide from a lexical proxy."""

    loop_id = "L1"
    name = "fake:semantic"

    def __init__(self) -> None:
        self._prev = None

    def measure(self, obs) -> Measurement:
        ruminating = self._prev is not None and obs.concept == self._prev
        self._prev = obs.concept
        return Measurement(
            value=0.0 if ruminating else 1.0,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            decision=ruminating,
            probability=1.0 if ruminating else 0.0,
            provider=self.name,
        )

    def reset(self) -> None:
        self._prev = None


class FakeCalibratedL2:
    """An L2 sensor that reports the agent is overconfident (standardized > 0),
    which a naive Brier cannot do."""

    loop_id = "L2"
    name = "fake:overconfident"

    def measure(self, obs) -> Measurement:
        return Measurement(
            value=0.3,
            meaning=Meaning.LOWER_IS_HEALTHIER,
            standardized=2.0,  # calibration error well above baseline
            measurement_error=0.02,
            provider=self.name,
        )

    def reset(self) -> None:
        return None


# --- L1 rumination ------------------------------------------------------------

def test_naive_l1_refuses_to_decide_without_a_threshold():
    monitor = RuminationMonitor(DiffNoveltyProvider())  # no threshold given
    with pytest.raises(ThresholdRequired):
        monitor.observe(IterationObservation(artifact="anything"))


def test_calibrated_l1_needs_no_threshold():
    monitor = RuminationMonitor(FakeSemanticL1(), patience=3)  # no threshold, fine
    for i in range(5):
        monitor.observe(_Obs(artifact=f"surface {i}", concept=1))  # same concept repeatedly
    assert monitor.verdict().exit_reason is ExitReason.REFRAME


def test_value_gap_same_loop_two_sensors():
    # An agent that keeps landing on the same fix (concept 1 from step 1 on) while
    # wording it completely differently each time. Rumination hidden under novelty.
    surfaces = [
        "alpha bravo charlie delta",
        "xray yankee zulu whiskey",
        "one two three four five",
        "crimson viridian cerulean",
        "north south east by west",
    ]
    concepts = [0, 1, 1, 1, 1]
    stream = [_Obs(s, c) for s, c in zip(surfaces, concepts)]

    # Naive lexical sensor: surfaces are all different, so novelty stays high and
    # the monitor never suspects a thing. It even gets a threshold to work with.
    naive = RuminationMonitor(DiffNoveltyProvider(), patience=3, threshold=0.3)
    for obs in stream:
        naive.observe(obs)
    assert naive.verdict().exit_reason is ExitReason.CONTINUE  # missed it

    # Better sensor: catches the repeated concept and routes to a reframe.
    smart = RuminationMonitor(FakeSemanticL1(), patience=3)
    for obs in stream:
        smart.observe(obs)
    assert smart.verdict().exit_reason is ExitReason.REFRAME  # caught it


# --- L6 habituation -----------------------------------------------------------

def test_habituation_stays_silent_on_baseline_then_orients_on_spike():
    filt = HabituationFilter(ZScoreDeviationProvider(warmup=8))
    # A steady channel with realistic small jitter around 10.0 (a zero-variance
    # baseline would leave the naive z-score undefined, which is its own confound).
    baseline = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0]
    for v in baseline:
        filt.observe(ChannelObservation(value=v))
    assert filt.verdict().exit_reason is ExitReason.CONTINUE
    assert filt.orienting() is False

    filt.observe(ChannelObservation(value=25.0))  # a clear deviation
    assert filt.orienting() is True
    assert filt.verdict().exit_reason is ExitReason.DEVIATION


# --- L2 calibration -----------------------------------------------------------

def test_calibration_governor_routes_low_confidence_to_seek_info():
    gov = CalibrationGovernor(RollingBrierProvider(), min_confidence=0.5)
    gov.observe(PredictionOutcome(predicted=0.9, outcome=True))
    assert gov.policy(next_confidence=0.8) == "act"
    assert gov.policy(next_confidence=0.3) == "seek_info"


def test_calibrated_l2_tightens_the_bar_when_overconfident():
    # A naive Brier cannot tighten the bar; a sensor that reports overconfidence can.
    gov = CalibrationGovernor(FakeCalibratedL2(), min_confidence=0.5)
    gov.observe(PredictionOutcome(predicted=0.9, outcome=False))
    # bar rises to 0.5 + 0.1 * 2.0 = 0.7, so 0.6 confidence now routes to seek_info
    assert gov.policy(next_confidence=0.6) == "seek_info"
    assert gov.policy(next_confidence=0.75) == "act"


# --- L5 incubation policy -----------------------------------------------------

def test_einstellung_breaker_resets_divergent_escalates_convergent():
    breaker = EinstellungBreaker()
    assert breaker.decide(True, divergent=True) is ExitReason.REFRAME
    assert breaker.decide(True, divergent=False) is ExitReason.ESCALATE
    # No impasse: nothing to break.
    assert breaker.decide(False, divergent=True) is ExitReason.CONTINUE
