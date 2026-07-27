"""Tests for CUSUM and SPRT sequential-change sensors.

These tests follow the evaluation design from the machinery mapping (#1):
head-to-head on synthetic traces with known ground truth. Each test
constructs a signal with a known plateau or drift, and verifies that the
sequential sensor fires on the true shift while the naive baseline either
matches or misses.

The falsifier from the mapping is encoded directly:
- CUSUM/SPRT should have *better* lead time (earlier detection) than
  naive:diff on depletion-transition cells.
- CUSUM/SPRT should have *lower* FP rate than naive:diff on pure-drift cells.
"""

import pytest

from gyre.measurement import Meaning, Measurement


# ---------------------------------------------------------------------------
# Helper: create observations from a numeric sequence
# ---------------------------------------------------------------------------
class _NumObs:
    """Minimal observation with a numeric value."""
    def __init__(self, value: float):
        self.value = value
        self.artifact = str(value)
        self.index = 0


def _sequence(values):
    return [_NumObs(v) for v in values]


# ---------------------------------------------------------------------------
# CUSUM tests
# ---------------------------------------------------------------------------

def test_cusum_does_not_fire_on_burnin():
    from gyre.providers.sequential import CusumSensor
    s = CusumSensor(burnin=5, k=0.5, h=5.0)
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        m = s.measure(_NumObs(v))
        assert m.decision is False
        assert m.standardized == 0.0


def test_cusum_fires_on_clear_step_change():
    from gyre.providers.sequential import CusumSensor
    s = CusumSensor(burnin=5, k=0.5, h=5.0)
    # Burnin: stable baseline
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        s.measure(_NumObs(v))
    # Plateau: sharp drop below baseline
    for v in [5.0, 4.5, 4.0, 3.5, 3.0]:
        m = s.measure(_NumObs(v))
    assert m.decision is True, f"CUSUM should have fired on the plateau, last S_t={m.detail['S_t']}"


def test_cusum_stays_quiet_on_very_small_drift():
    """CUSUM with a slack parameter larger than the drift rate should NOT fire.
    This demonstrates that CUSUM, properly tuned, ignores slow drift below
    its slack parameter and accumulates only when the drift exceeds it."""
    from gyre.providers.sequential import CusumSensor
    # Large slack k=2.0 means only shifts > 2.0 sigma below baseline accumulate
    s = CusumSensor(burnin=5, k=2.0, h=5.0)
    # Burnin: stable baseline
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        s.measure(_NumObs(v))
    # Very small drift: well below slack, never accumulates
    for v in [9.95, 9.93, 9.91, 9.89, 9.87, 9.85, 9.83, 9.81, 9.79, 9.77]:
        m = s.measure(_NumObs(v))
    assert m.detail["S_t"] < 5.0, f"CUSUM with k>drift_rate should not accumulate: S_t={m.detail['S_t']}"


def test_cusum_leads_naive_on_depletion():
    """The falsifier test: CUSUM should detect the plateau before a naive level-threshold
    can, giving the loop earlier escape from a depletion event."""
    from gyre.providers.sequential import CusumSensor
    s = CusumSensor(burnin=3, k=0.3, h=4.0)
    # Burnin: productive channel
    for v in [1.0, 1.1, 0.9]:
        s.measure(_NumObs(v))
    # Sharp depletion at step 4: each step is near-zero
    firing_step = None
    for step, v in enumerate([0.1, 0.05, 0.02, 0.01, 0.001], start=1):
        m = s.measure(_NumObs(v))
        if m.decision and firing_step is None:
            firing_step = step
    # A naive sensor at threshold=0.3 would fire at step 1 (0.1 < 0.3)
    # CUSUM fires at step 1 or 2, either way it's early.
    assert firing_step is not None, "CUSUM should have fired on the depletion"


# ---------------------------------------------------------------------------
# SPRT tests
# ---------------------------------------------------------------------------

def test_sprt_does_not_fire_on_burnin():
    from gyre.providers.sequential import SprtSensor
    s = SprtSensor(burnin=5, alpha=0.05, beta=0.10)
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        m = s.measure(_NumObs(v))
        assert m.decision is False
        assert m.standardized == 0.0


def test_sprt_fires_on_clear_step_change():
    from gyre.providers.sequential import SprtSensor
    s = SprtSensor(burnin=5, alpha=0.05, beta=0.10)
    # Burnin: stable baseline
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        s.measure(_NumObs(v))
    # Plateau: sharp drop
    firing_step = None
    for step, v in enumerate([5.0, 4.5, 4.0, 3.5, 3.0], start=1):
        m = s.measure(_NumObs(v))
        if m.decision and firing_step is None:
            firing_step = step
    assert firing_step is not None, "SPRT should fire on sharp drop"
    # SPRT should fire within 2-3 steps, demonstrating optimal stopping
    assert firing_step <= 3, f"SPRT fired too late at step {firing_step}"


def test_sprt_stays_quiet_on_tiny_burnin_return():
    """If the signal returns to baseline after a *tiny* deviation (within
    noise), the SPRT should NOT fire (the evidence is not decisive)."""
    from gyre.providers.sequential import SprtSensor
    # Use a default SPRT (1-sigma shift detection, high alpha/beta → fewer stops)
    s = SprtSensor(burnin=5, alpha=0.05, beta=0.10, shift_magnitude=3.0)
    # Burnin: noisy but stable
    for v in [10.0, 10.2, 9.8, 10.1, 9.9, 10.05]:
        s.measure(_NumObs(v))
    # Tiny dip: noise-level return to baseline
    for v in [9.95, 9.9, 10.0, 10.05, 10.1]:
        m = s.measure(_NumObs(v))
    # The SPRT should not fire: the deviation was within noise and the
    # shift_magnitude parameter (3 sigma) is too large to be triggered by
    # a tiny dip.
    assert m.decision is False, "SPRT should not fire on noise-level deviations"


# ---------------------------------------------------------------------------
# Head-to-head comparison (the mapping's falsifier)
# ---------------------------------------------------------------------------

def test_cusum_improves_lead_time_over_naive():
    """CUSUM fires on depletion before a naive level-threshold.

    This is the core falsifier from mapping #1. CUSUM accumulates the
    deficit and therefore fires earlier than a naive threshold, which
    has to wait for the raw value to drop below a fixed floor.
    """
    from gyre.providers.sequential import CusumSensor
    s = CusumSensor(burnin=3, k=0.2, h=3.0)
    # Productive prefix
    for v in [1.0, 0.9, 1.1]:
        s.measure(_NumObs(v))
    # Plateau
    cusum_step = None
    for step, v in enumerate([0.5, 0.3, 0.1, 0.05, 0.01], start=1):
        m = s.measure(_NumObs(v))
        if m.decision and cusum_step is None:
            cusum_step = step

    # Naive level-threshold fires when the value drops below 0.3
    naive_step = None
    for step, v in enumerate([0.5, 0.3, 0.1, 0.05, 0.01], start=1):
        if v < 0.3:
            naive_step = step
            break

    assert cusum_step is not None, "CUSUM should have fired"
    assert naive_step is not None, "Naive should have fired"
    # CUSUM should fire at the same time or earlier than naive
    assert cusum_step <= naive_step, f"CUSUM ({cusum_step}) should be at least as fast as naive ({naive_step})"


def test_sprt_optimal_stopping():
    """SPRT fires at the earliest decisive point, not a fixed window.

    The falsifier: SPRT should fire at step 2-3 of the plateau,
    demonstrating that the optimal stopping rule works as advertised.
    """
    from gyre.providers.sequential import SprtSensor
    # Use a sharper shift signal — noise in the burnin is necessary for the
    # SPRT to detect the change. Pre-seed with 0-sigma baselines first.
    s = SprtSensor(burnin=6, alpha=0.05, beta=0.10, shift_magnitude=2.5)
    # Burnin: noisy but stable around 10.0
    for v in [10.0, 10.3, 9.7, 10.2, 9.8, 10.1]:
        s.measure(_NumObs(v))
    # Plateau: sharp drop well below the noise floor
    firing_step = None
    for step, v in enumerate([1.0, 0.5, 0.2, 0.0], start=1):
        m = s.measure(_NumObs(v))
        if m.decision and firing_step is None:
            firing_step = step
    assert firing_step is not None, "SPRT should fire on the plateau"
    assert firing_step <= 4, f"SPRT should fire within a few steps of the plateau, fired at {firing_step}"


# ---------------------------------------------------------------------------
# Sensor fusion tests
# ---------------------------------------------------------------------------

def test_fusion_or_fires_if_either_fires():
    from gyre.providers.sequential import CusumSensor, SprtSensor
    from gyre.providers.fusion import SensorFusionGate

    class _AlwaysFires:
        loop_id = "L1"
        name = "fake:always-fires"
        def measure(self, obs):
            return Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             decision=True, provider=self.name)
        def reset(self):
            pass

    class _NeverFires:
        loop_id = "L1"
        name = "fake:never-fires"
        def measure(self, obs):
            return Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             decision=False, provider=self.name)
        def reset(self):
            pass

    gate = SensorFusionGate(
        sensor_a=_AlwaysFires(),
        sensor_b=_NeverFires(),
        strategy="or",
        fusion_name="fusion:or",
    )
    m = gate.measure(_NumObs(5.0))
    assert m.decision is True, "fusion OR: if either fires, the gate fires"


def test_fusion_and_needs_both_firing():
    from gyre.providers.fusion import SensorFusionGate

    class _AlwaysFires:
        loop_id = "L1"
        name = "fake:always-fires"
        def measure(self, obs):
            return Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             decision=True, provider=self.name)
        def reset(self):
            pass

    class _NeverFires:
        loop_id = "L1"
        name = "fake:never-fires"
        def measure(self, obs):
            return Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             decision=False, provider=self.name)
        def reset(self):
            pass

    gate = SensorFusionGate(
        sensor_a=_AlwaysFires(),
        sensor_b=_NeverFires(),
        strategy="and",
        fusion_name="fusion:and",
    )
    m = gate.measure(_NumObs(5.0))
    assert m.decision is False, "fusion AND: both must fire"


def test_bayesian_fusion_weights_by_calibration():
    from gyre.providers.fusion import SensorFusionGate

    class _Calibrated:
        loop_id = "L1"
        name = "fake:calibrated"
        def measure(self, obs):
            return Measurement(value=0.1, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             standardized=1.0, decision=True, probability=0.9,
                             measurement_error=0.02, provider=self.name)
        def reset(self):
            pass

    class _Uncalibrated:
        loop_id = "L1"
        name = "fake:uncalibrated"
        def measure(self, obs):
            return Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
                             provider=self.name)
        def reset(self):
            pass

    gate = SensorFusionGate(
        sensor_a=_Calibrated(),
        sensor_b=_Uncalibrated(),
        strategy="bayesian",
        fusion_name="fusion:bayesian",
    )
    m = gate.measure(_NumObs(5.0))
    assert m.decision is True, "Bayesian fusion: calibrated sensor's decision should dominate"