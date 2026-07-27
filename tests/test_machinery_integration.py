"""Integration smoke tests for the new machinery wiring.

These check that the new sensors/controllers actually work through the
public seams:
- The L6 HabituationFilter accepts the AR(1) provider as a drop-in.
- The L1 RuminationMonitor accepts the CUSUM/SPRT providers as drop-ins.
- The SensorFusionGate can wrap two sensors and is itself usable as a
  MeasurementProvider.
- The MetaBanditController can be constructed from the public registry.

This is the seam-level smoke test; unit-level correctness is in the
test_*.py files per module.
"""

import pytest

from gyre.control import available as ctrl_available, get_controller
from gyre.interfaces import ExitReason
from gyre.loops.habituation import HabituationFilter, ChannelObservation
from gyre.loops.rumination import IterationObservation, RuminationMonitor
from gyre.providers import available as prov_available, get_provider


# --- L6 wiring ---------------------------------------------------------------

def test_l6_accepts_ar1_sensor():
    """The AR(1) sensor can drive the L6 HabituationFilter."""
    sensor = get_provider("ar1:residual")
    assert sensor.loop_id == "L6"
    hab = HabituationFilter(sensor, patience=1)
    # Stable baseline
    for v in [10.0, 10.3, 9.7, 10.2, 9.8, 10.0]:
        hab.observe(ChannelObservation(value=v))
    # The filter should not be oriented yet (model still absorbing baseline)
    # ... but with burnin=5 the model is ready
    hab.observe(ChannelObservation(value=25.0))
    assert hab.orienting() is True


# --- L1 wiring ---------------------------------------------------------------

def test_l1_accepts_cusum_sensor():
    sensor = get_provider("cusum:gain-shift")
    assert sensor.loop_id == "L1"
    monitor = RuminationMonitor(sensor, patience=1)
    # A value-only test signal: stable baseline + clear step change
    class _ValueObs(IterationObservation):
        def __init__(self, value):
            super().__init__(artifact=str(value))
            self.value = value

    # Stable baseline for many observations so CUSUM accumulates
    for v in [10.0] * 10 + [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]:
        monitor.observe(_ValueObs(v))
    # CUSUM should fire on this sharp drop
    assert monitor.verdict().exit_reason is ExitReason.REFRAME


def test_l1_accepts_sprt_sensor():
    sensor = get_provider("sprt:gain-shift")
    assert sensor.loop_id == "L1"
    monitor = RuminationMonitor(sensor, patience=1)
    class _ValueObs(IterationObservation):
        def __init__(self, value):
            super().__init__(artifact=str(value))
            self.value = value

    # Stable baseline (10 iterations) + sharp drop
    for v in [10.0] * 10 + [0.01] * 5:
        monitor.observe(_ValueObs(v))
    assert monitor.verdict().exit_reason is ExitReason.REFRAME


# --- Controller wiring -------------------------------------------------------

def test_meta_bandit_default_is_registered():
    assert "meta-bandit:default" in ctrl_available()
    bandit = get_controller("meta-bandit:default")
    assert bandit is not None


def test_meta_bandit_drives_a_route():
    from gyre.interfaces import LoopVerdict
    from gyre.control import ControlContext

    bandit = get_controller("meta-bandit:default")
    ctx = ControlContext(stakes=1.0, divergent=True, steps_remaining=10)
    verdicts = [
        LoopVerdict(exit_reason=ExitReason.PLATEAU, loop_id="L1"),
    ]
    route = bandit.route(verdicts, ctx)
    assert route in (
        ExitReason.REFRAME,
        ExitReason.ESCALATE,
        ExitReason.ABANDON,
        ExitReason.CONTINUE,
    )


def test_meta_bandit_preempts_rupture():
    from gyre.interfaces import LoopVerdict
    from gyre.control import ControlContext

    bandit = get_controller("meta-bandit:default")
    ctx = ControlContext(stakes=1.0, divergent=True, steps_remaining=10)
    verdicts = [
        LoopVerdict(exit_reason=ExitReason.RUPTURE, loop_id="L3"),
    ]
    assert bandit.route(verdicts, ctx) is ExitReason.RUPTURE


# --- Fusion gate wiring ------------------------------------------------------

def test_fusion_gate_drops_into_l1():
    from gyre.providers.fusion import SensorFusionGate
    sensor_a = get_provider("cusum:gain-shift")
    sensor_b = get_provider("sprt:gain-shift")
    gate = SensorFusionGate(
        sensor_a=sensor_a,
        sensor_b=sensor_b,
        strategy="or",
        fusion_name="fusion:cusum-or-sprt",
    )
    provider = gate.as_provider()
    assert provider.loop_id == "L1"
    monitor = RuminationMonitor(provider, patience=1)
    class _ValueObs(IterationObservation):
        def __init__(self, value):
            super().__init__(artifact=str(value))
            self.value = value
    for v in [1.0, 1.0, 1.0, 1.0, 0.01, 0.01, 0.01]:
        monitor.observe(_ValueObs(v))
    # OR gate fires when any underlying sensor fires, so on the plateau
    # either CUSUM or SPRT should fire
    assert monitor.verdict().exit_reason in (ExitReason.REFRAME, ExitReason.PLATEAU)