"""Seam and interface smoke tests.

These check the vocabulary layer: that the seam imports, that a Measurement
carries its honesty fields, that the calibration ladder reads correctly, and that
a loop controller satisfies the LoopMonitor protocol.
"""

from gyre import (
    ExitReason,
    LoopMonitor,
    LoopVerdict,
    Maturity,
    Meaning,
    Measurement,
    MeasurementProvider,
    RuminationMonitor,
    __version__,
)
from gyre.providers import DiffNoveltyProvider


def test_version_bumped_for_measurement_seam():
    assert __version__ == "0.2.0"


def test_measurement_carries_confounds_and_is_uncalibrated_by_default():
    m = Measurement(value=0.03, meaning=Meaning.HIGHER_IS_HEALTHIER, confounds=("lexical only",))
    assert m.confounds == ("lexical only",)
    assert m.is_calibrated() is False  # no decision, no probability


def test_calibration_ladder_reads_as_calibrated_when_decision_present():
    m = Measurement(value=0.0, meaning=Meaning.HIGHER_IS_HEALTHIER, decision=True)
    assert m.is_calibrated() is True


def test_naive_provider_satisfies_provider_protocol():
    p = DiffNoveltyProvider()
    assert isinstance(p, MeasurementProvider)
    assert p.loop_id == "L1"


def test_loop_satisfies_monitor_protocol():
    monitor = RuminationMonitor(DiffNoveltyProvider(), threshold=0.1)
    assert isinstance(monitor, LoopMonitor)
    v = monitor.verdict()
    assert isinstance(v, LoopVerdict)
    assert v.exit_reason is ExitReason.CONTINUE
    assert v.maturity is Maturity.BUILDABLE


def test_provider_loop_id_mismatch_is_caught_early():
    brier_like = DiffNoveltyProvider()  # an L1 provider
    try:
        from gyre import CalibrationGovernor

        CalibrationGovernor(brier_like)  # expects L2
    except ValueError as e:
        assert "L2 provider" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected a ValueError on loop_id mismatch")
