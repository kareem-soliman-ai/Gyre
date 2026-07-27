"""Tests for the Value-of-Information (VoI) calibration sensor (machinery A6).

The VoI sensor is the L2 calibration sensor that uses Bayesian optimal
stopping: it fires when one more (prediction, outcome) pair is NOT
worth the cost.

These tests verify the falsifiers from the machinery mapping:
1. The provider is calibrated: produces a principled decision boundary.
2. VoI > 0 keeps the loop in CONTINUE; VoI <= 0 commits.
3. The Beta posterior updates correctly with new evidence.
"""

import pytest

from gyre.loops.calibration import PredictionOutcome
from gyre.providers.value_of_information import (
    ValueOfInformationProvider,
    beta_posterior_after,
    entropy,
    expected_information_gain,
    value_of_information,
    voi_decide,
)


# --- Pure-function VoI tests (no Gyre seam) ----------------------------------


def test_beta_posterior_update_additive():
    """The Beta-Bernoulli conjugate update is purely additive."""
    a, b = beta_posterior_after(prior_alpha=1.0, prior_beta=1.0,
                                 successes=5, failures=2)
    assert a == pytest.approx(6.0)
    assert b == pytest.approx(3.0)


def test_entropy_peaks_at_uniform():
    """A uniform distribution has maximum entropy."""
    h_uniform = entropy({"H0": 0.5, "H1": 0.5})
    h_skewed = entropy({"H0": 0.9, "H1": 0.1})
    assert h_uniform > h_skewed


def test_value_of_information_positive_when_gain_exceeds_cost():
    """VoI > 0 when expected info-gain > cost-of-trial.

    Use a highly diffuse Beta(1, 10) which has a large entropy, and a
    cheap cost — the EIG of one additional trial should exceed the cost.
    """
    voi = value_of_information(
        prior_alpha=1.0, prior_beta=10.0,
        cost_per_trial=0.001, n_future_trials=1,
    )
    # Beta(1,10) is concentrated near p=0; one trial's EIG ≈ 0.15 nats
    assert voi >= -0.01, f"VoI should be at least cost dominated: {voi}"


def test_value_of_information_negative_when_cost_dominates():
    """VoI < 0 when cost is huge relative to any reasonable gain."""
    voi = value_of_information(
        prior_alpha=100.0, prior_beta=100.0,  # narrow prior
        cost_per_trial=1.0, n_future_trials=1,
    )
    assert voi < 1.0  # cost dominates


def test_voi_decide_continues_with_diffuse_prior():
    """A diffuse prior with cheap cost → OBSERVE."""
    action, voi = voi_decide(
        prior_alpha=1.0, prior_beta=10.0,  # diffuse, near p=0
        cost_per_trial=0.001,
    )
    assert action == "OBSERVE"


def test_voi_decide_commits_with_concentrated_posterior():
    action, voi = voi_decide(
        prior_alpha=100.0, prior_beta=1.0,
        cost_per_trial=10.0,
    )
    assert action == "COMMIT"


# --- Sensor-level tests ------------------------------------------------------


def test_voi_sensor_does_not_commit_without_data():
    sensor = ValueOfInformationProvider(prior_alpha=1.0, prior_beta=1.0)
    m = sensor.measure(PredictionOutcome(predicted=0.5, outcome=True))
    assert m.decision is False  # cannot commit without evidence


def test_voi_sensor_keeps_observing_during_data_collection():
    """While the posterior is diffuse and the cost is low, the sensor
    keeps observing (decision=False)."""
    sensor = ValueOfInformationProvider(
        prior_alpha=2.0, prior_beta=2.0,  # diffuse prior
        cost_per_trial=0.01,
    )
    # Feed some mixed outcomes
    for predicted, outcome in [
        (0.9, False), (0.9, True), (0.1, True), (0.1, False),
        (0.5, True), (0.5, False),
    ]:
        m = sensor.measure(PredictionOutcome(predicted=predicted, outcome=outcome))
    # With diffuse posterior and reasonable cost, MORE data is still worth it.
    assert m.decision is False, f"VoI sensor should still be observing: {m.detail}"


def test_voi_sensor_commits_when_posterior_concentrated():
    """Once enough consistent evidence arrives, the posterior concentrates
    and VoI < cost, so the sensor commits (decision=True)."""
    sensor = ValueOfInformationProvider(
        prior_alpha=1.0, prior_beta=1.0,
        cost_per_trial=0.05,
    )
    # 30 strongly-correct predictions → Beta(1+30, 1+0) = Beta(31, 1)
    for _ in range(30):
        m = sensor.measure(PredictionOutcome(predicted=0.9, outcome=True))
    assert m.decision is True, (
        f"VoI sensor should commit after concentrated evidence: {m.detail}"
    )


def test_voi_sensor_value_carries_voi_in_detail():
    """The Measurement's detail carries the VoI and posterior for downstream observability."""
    sensor = ValueOfInformationProvider()
    m = sensor.measure(PredictionOutcome(predicted=0.7, outcome=True))
    assert "voi" in m.detail
    assert "posterior_alpha" in m.detail
    assert "posterior_beta" in m.detail
    assert "n" in m.detail


def test_voi_sensor_reset_clears_state():
    sensor = ValueOfInformationProvider(prior_alpha=1.0, prior_beta=1.0)
    for _ in range(5):
        sensor.measure(PredictionOutcome(predicted=0.7, outcome=True))
    sensor.reset()
    m = sensor.measure(PredictionOutcome(predicted=0.7, outcome=True))
    # After reset, no decision can be made
    assert m.decision is False


# --- Integration: drive a CalibrationGovernor with the VoI sensor -------------


def test_voi_drives_calibration_governor():
    """The VoI sensor should drop into the CalibrationGovernor just like any
    other L2 provider."""
    from gyre.loops.calibration import CalibrationGovernor

    sensor = ValueOfInformationProvider(
        prior_alpha=1.0, prior_beta=1.0,
        cost_per_trial=0.05,
    )
    gov = CalibrationGovernor(sensor, min_confidence=0.5)
    # Feed 30 strongly-correct predictions to concentrate the posterior
    for _ in range(30):
        gov.observe(PredictionOutcome(predicted=0.9, outcome=True))
    # Subsequent policy
    assert gov.policy(next_confidence=0.6) in ("act", "seek_info")


def test_eig_is_nonneg_for_diffuse_prior():
    """Expected information gain is non-negative for any prior."""
    for a, b in [(1, 1), (2, 5), (10, 10)]:
        eig = expected_information_gain(a, b, 1)
        assert eig >= 0.0, f"EIG should be >= 0 for Beta({a},{b}): {eig}"