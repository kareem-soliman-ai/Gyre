"""Tests for AR(1) residual sensor (machinery B1 from the taxonomy).

Core falsifier:
- AR(1) should NOT fire on slow drift (it absorbs autocorrelation)
- AR(1) SHOULD fire on a sudden break (genuine regime change)
- AR(1) should have a lower false-positive rate than z-score on slow drift

This is the correct sensor for L6: habituation/orienting is all about
detecting genuine novelty on an autocorrelated channel.
"""

import pytest

from gyre.measurement import Meaning, Measurement


class _NumObs:
    """Minimal observation with a numeric value."""
    def __init__(self, value: float):
        self.value = value
        self.artifact = str(value)
        self.index = 0


def _sequence(values):
    return [_NumObs(v) for v in values]


# ---------------------------------------------------------------------------
# AR(1) basic tests
# ---------------------------------------------------------------------------

def test_ar1_does_not_fire_on_burnin():
    from gyre.providers.residual import Ar1ResidualSensor
    s = Ar1ResidualSensor(burnin=5)
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        m = s.measure(_NumObs(v))
        assert m.decision is False
        assert m.standardized == 0.0


def test_ar1_absorbs_slow_drift():
    """AR(1) should NOT fire on a slow drift that the model absorbs.
    This is the falsifier for naive z-score, which fires on every
    slow drift because it underestimates the expected variation."""
    from gyre.providers.residual import Ar1ResidualSensor
    s = Ar1ResidualSensor(burnin=5, threshold=2.0)
    # Burnin: stable baseline
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        s.measure(_NumObs(v))
    # Slow drift: each step is slightly below baseline
    # A z-score would fire on these; AR(1) should not.
    fired_on_drift = False
    for v in [9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9]:
        m = s.measure(_NumObs(v))
        if m.decision:
            fired_on_drift = True
    assert not fired_on_drift, "AR(1) should not fire on slow drift; it absorbs autocorrelation"


def test_ar1_fires_on_sudden_break():
    """AR(1) SHOULD fire on a sudden regime change (genuine break).
    The residual is large because the current observation is not
    explained by the autoregressive model."""
    from gyre.providers.residual import Ar1ResidualSensor
    # Use a low threshold to detect the dramatic break
    s = Ar1ResidualSensor(burnin=5, threshold=1.5)
    # Burnin: noisy but stable baseline
    for v in [10.0, 10.3, 9.7, 10.2, 9.8]:
        s.measure(_NumObs(v))
    # Sudden break: the channel jumps dramatically
    for v in [25.0]:
        m = s.measure(_NumObs(v))
    assert m.decision is True, f"AR(1) should fire on sudden break; last z={m.detail['z']}"


def test_ar1_zscore_is_significant_on_break():
    """On a genuine break, the AR(1) residual should be > threshold * residual_std."""
    from gyre.providers.residual import Ar1ResidualSensor
    s = Ar1ResidualSensor(burnin=5, threshold=2.0)
    # Burnin: stable baseline
    for v in [10.0, 10.2, 9.8, 10.1, 9.9]:
        s.measure(_NumObs(v))
    # Sudden break
    m = s.measure(_NumObs(20.0))
    z = m.detail["z"]
    assert abs(z) > 2.0, f"AR(1) z-score on break should be > threshold: {z}"


# ---------------------------------------------------------------------------
# AR(1) vs z-score (the falsifier) — using HabituationFilter integration
# ---------------------------------------------------------------------------

def test_ar1_vs_zscore_on_slow_drift():
    """The mapping's falsifier cell: AR(1) has fewer false positives on
    slow drift than z-score. This is the L6 On-drift cell.

    We use HabituationFilter from loops/habituation.py to simulate
    real L6 monitoring, with each sensor as a provider."""
    from gyre.providers.residual import Ar1ResidualSensor
    from gyre.providers.naive import ZScoreDeviationProvider
    from gyre.loops.habituation import HabituationFilter, ChannelObservation

    ar1 = Ar1ResidualSensor(burnin=5, threshold=2.0)
    zscore = ZScoreDeviationProvider(window=30, warmup=8)

    ar1_filter = HabituationFilter(ar1, patience=1)
    zscore_filter = HabituationFilter(zscore, patience=1)

    # Baseline with small jitter
    baseline = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0]
    slow_drift = [9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7]

    # Feed baseline first (both warm up)
    for v in baseline:
        ar1_filter.observe(ChannelObservation(value=v))
        zscore_filter.observe(ChannelObservation(value=v))

    ar1_fp = 0
    zscore_fp = 0
    for v in slow_drift:
        ar1_filter.observe(ChannelObservation(value=v))
        zscore_filter.observe(ChannelObservation(value=v))
        if ar1_filter.orienting():
            ar1_fp += 1
        if zscore_filter.orienting():
            zscore_fp += 1

    # AR(1) should have fewer false positives on slow drift than z-score
    assert ar1_fp < zscore_fp, (
        f"AR(1) should have fewer false positives on slow drift than z-score: "
        f"AR(1)={ar1_fp}, z-score={zscore_fp}"
    )