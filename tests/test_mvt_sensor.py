"""Tests for the MVT (Marginal Value Theorem) rumination sensor.

The MVT sensor is the L1 patch-leaving sensor — it fires when the
agent's marginal gain drops below the long-run environmental average
gain, *after* a minimum dwell. These tests verify the three falsifiers
documented in the machinery mapping:

1. The MVT sensor should NOT fire during a productive prefix.
2. The MVT sensor SHOULD fire on a depleted tail (rumination morphology).
3. The MVT sensor should agree with the literature: marginal below
   habitat ⇒ leave, marginal above habitat ⇒ stay.
"""

import pytest

from gyre.loops.rumination import IterationObservation
from gyre.measurement import Meaning, Measurement
from gyre.providers.mvt_rumination import (
    MarginalValueContext,
    MarginalValueDecision,
    MvtRuminationSensor,
    marginal_value_decision,
)


# --- Pure-function tests for the MVT rule (no Gyre seam) -------------------


def test_mvt_stays_when_marginal_above_habitat():
    ctx = MarginalValueContext(
        marginal_gain_rate=0.6,
        environment_gain_rate=0.4,
        dwell_steps=5,
        min_dwell_steps=2,
    )
    decision = marginal_value_decision(ctx)
    assert decision.action == "stay"
    assert "marginal_gain_sufficient" in decision.reasons


def test_mvt_leaves_when_marginal_below_habitat():
    ctx = MarginalValueContext(
        marginal_gain_rate=0.1,
        environment_gain_rate=0.5,
        dwell_steps=5,
        min_dwell_steps=2,
    )
    decision = marginal_value_decision(ctx)
    assert decision.action == "leave"
    assert "marginal_gain_depleted" in decision.reasons


def test_mvt_respects_min_dwell():
    ctx = MarginalValueContext(
        marginal_gain_rate=0.0,   # way below habitat
        environment_gain_rate=0.5,
        dwell_steps=1,            # below minimum dwell of 2
        min_dwell_steps=2,
    )
    decision = marginal_value_decision(ctx)
    assert decision.action == "stay"
    assert "minimum_dwell" in decision.reasons


def test_mvt_handles_switch_cost():
    """Switch cost raises the threshold; marginal above pure habitat may
    still trigger LEAVE if it cannot clear the threshold.
    """
    # Scenario A: marginal just above habitat but below (habitat+switch)
    #   → LEAVE (because patch-leaving requires clearing the switch-cost)
    ctx_stay_below = MarginalValueContext(
        marginal_gain_rate=0.4,
        environment_gain_rate=0.3,
        switch_cost_rate=0.2,
        dwell_steps=10,
    )
    assert marginal_value_decision(ctx_stay_below).action == "leave"

    # Scenario B: marginal well above (habitat+switch) → STAY
    ctx_stay_clear = MarginalValueContext(
        marginal_gain_rate=0.8,
        environment_gain_rate=0.3,
        switch_cost_rate=0.2,
        dwell_steps=10,
    )
    assert marginal_value_decision(ctx_stay_clear).action == "stay"


# --- Sensor-level tests ------------------------------------------------------


def test_mvt_sensor_does_not_fire_during_productive_prefix():
    """The MVT sensor must stay silent when every observation adds info
    AND the dwell is below the minimum.

    We use a wide-vocabulary productive prefix where the lexical proxy
    sees real novelty each step, combined with a `min_dwell` larger than
    the productive run — the canonical MVT falsifier: 'don't leave the
    patch before travel cost has been served'.
    """
    sensor = MvtRuminationSensor(
        short_window=3, long_window=30, min_dwell=15, burnin=3
    )
    distinct_artifacts = [
        "The quick brown fox jumps over the lazy dog completely fresh novel hypothesis",
        "Zebra states quantum refactor multivariate constraint solver algorithm",
        "Multi-layer cache invalidation pattern using lease-based protocol",
        "Probabilistic data structure with constant-time membership testing",
        "Asynchronous message-passing between distributed worker processes",
        "Optimistic concurrency control via versioned shared state",
        "Differential privacy budget accounting with composition theorems",
        "Out-of-core sort with disk-spilling external merge strategy",
        "Incremental computation via dependency graph re-evaluation",
        "Federated averaging across heterogeneous client populations",
    ]
    decisions = []
    for i, art in enumerate(distinct_artifacts):
        obs = IterationObservation(
            artifact=art,
            error=f"evidence set {i}",
            index=i,
        )
        m = sensor.measure(obs)
        decisions.append(m.decision)
    # None of these should fire: productive prefix AND dwell < min_dwell.
    assert not any(decisions), (
        f"MVT should not fire during productive prefix with min_dwell > "
        f"productive run length: {decisions}"
    )


def test_mvt_sensor_fires_on_depleted_tail():
    """The MVT sensor SHOULD fire once a depleted tail shows up.

    The classic productive-prefix-then-stale-tail morphology (the
    depletion cell of Gyre's synthetic corpus)."""
    sensor = MvtRuminationSensor(
        short_window=3, long_window=30, min_dwell=2, burnin=3
    )
    # 8 productive, distinct steps
    for i in range(8):
        sensor.measure(IterationObservation(
            artifact=f"productive distinct idea {i}",
            error=f"evidence step {i}",
            index=i,
        ))
    # Stale tail: same idea many times
    for i in range(8, 20):
        sensor.measure(IterationObservation(
            artifact="same idea stale",
            error="same error same error",
            index=i,
        ))
    last = sensor.measure(IterationObservation(
        artifact="same idea stale",
        error="same error",
        index=20,
    ))
    assert last.decision is True, (
        f"MVT should fire on depleted tail; "
        f"marginal={last.detail['marginal']:.3f}, "
        f"environment={last.detail['environment']:.3f}, "
        f"reasons={last.detail['reasons']}"
    )


def test_mvt_sensor_carries_meaning_and_provider():
    sensor = MvtRuminationSensor()
    m = sensor.measure(IterationObservation(artifact="anything"))
    assert m.meaning == Meaning.HIGHER_IS_HEALTHIER
    assert m.provider == "mvt:rumination"
    assert m.is_calibrated()  # reports standardized + decision


def test_mvt_sensor_reset_clears_state():
    sensor = MvtRuminationSensor(burnin=3)
    for i in range(10):
        sensor.measure(IterationObservation(artifact=f"x {i}"))
    sensor.reset()
    # After reset, the first observation is treated as a cold start.
    m = sensor.measure(IterationObservation(artifact="anything"))
    assert m.detail.get("burnin") is True


# --- Integration: drive a RuminationMonitor with the MVT sensor --------------


def test_mvt_drives_rumination_monitor_to_reframe():
    from gyre.loops.rumination import RuminationMonitor
    from gyre.interfaces import ExitReason

    sensor = MvtRuminationSensor(
        short_window=2, long_window=20, min_dwell=1, burnin=3
    )
    monitor = RuminationMonitor(sensor, patience=1)
    # Productive prefix
    for i in range(8):
        monitor.observe(IterationObservation(
            artifact=f"productive idea number {i}",
            error=f"novel evidence {i}",
            index=i,
        ))
    # Stale tail
    for i in range(8, 12):
        monitor.observe(IterationObservation(
            artifact="stale repeated idea",
            error="same error same error",
            index=i,
        ))
    verdict = monitor.verdict()
    assert verdict.exit_reason is ExitReason.REFRAME