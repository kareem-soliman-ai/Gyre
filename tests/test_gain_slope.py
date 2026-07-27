"""Slope-of-information-gain sensor: a plateau is a claim about a derivative.

Every other L1 sensor here reads a LEVEL (is this step novel?) or a consecutive
difference. But "the loop has stopped paying" is a statement about the slope of
information gain over recent steps, and a slope estimated from noisy readings
needs a standard error before it can decide anything.

These tests pin that the sensor decides on slope/SE (a t-like statistic) rather
than on a hand-picked slope threshold, weights each reading by its declared
measurement error, and refuses to decide before it has enough points.
"""

import pytest

from gyre.loops._policy import trigger_state
from gyre.loops.rumination import IterationObservation
from gyre.measurement import Meaning, Measurement
from gyre.providers.gain_slope import GainSlopeSensor, weighted_slope


class _Scripted:
    """Inner sensor returning a scripted gain sequence, optionally with sigma."""

    loop_id = "L1"
    name = "scripted"

    def __init__(self, gains, sigmas=None):
        self._gains = list(gains)
        self._sigmas = list(sigmas) if sigmas else None
        self._i = -1

    def measure(self, observation):
        self._i += 1
        i = min(self._i, len(self._gains) - 1)
        return Measurement(
            value=self._gains[i],
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            measurement_error=self._sigmas[i] if self._sigmas else None,
            provider=self.name,
        )

    def reset(self):
        self._i = -1


def _run(sensor, n):
    out = []
    for i in range(n):
        out.append(sensor.measure(IterationObservation(artifact=f"step {i}", index=i)))
    return out


# --- the estimator ---------------------------------------------------------------


def test_weighted_slope_recovers_a_known_line():
    xs = [0, 1, 2, 3, 4]
    ys = [1.0, 0.8, 0.6, 0.4, 0.2]
    slope, se = weighted_slope(xs, ys, [1.0] * 5)
    assert slope == pytest.approx(-0.2)
    assert se == pytest.approx(0.0, abs=1e-9)  # perfect fit, no residual scatter


def test_noisy_points_are_downweighted():
    xs = [0, 1, 2, 3, 4]
    ys = [0.0, 0.0, 0.0, 0.0, 10.0]  # last point is an outlier
    trusted, _ = weighted_slope(xs, ys, [1.0] * 5)
    distrusted, _ = weighted_slope(xs, ys, [1.0, 1.0, 1.0, 1.0, 50.0])
    assert abs(distrusted) < abs(trusted)


def test_scatter_produces_a_standard_error():
    xs = [0, 1, 2, 3, 4, 5]
    ys = [1.0, 0.2, 0.9, 0.1, 0.8, 0.3]  # no trend, lots of scatter
    slope, se = weighted_slope(xs, ys, [1.0] * 6)
    assert se > 0
    assert abs(slope / se) < 2.0  # not a significant trend


def test_too_few_points_is_refused():
    with pytest.raises(ValueError):
        weighted_slope([0, 1], [1.0, 0.5], [1.0, 1.0])


# --- the sensor ------------------------------------------------------------------


def test_burn_in_reports_no_trend_and_does_not_fire():
    s = GainSlopeSensor(_Scripted([1.0] * 10), window=6, min_points=4)
    for m in _run(s, 3):
        assert m.standardized == 0.0
        assert trigger_state(m) is False


def test_a_steady_decline_fires_without_any_threshold():
    gains = [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.15, 0.05]
    s = GainSlopeSensor(_Scripted(gains), window=8, min_points=4)
    fired = [trigger_state(m) for m in _run(s, len(gains))]
    assert any(fired), "a clear decline in information gain should fire"


def test_healthy_variation_does_not_fire():
    gains = [0.8, 0.9, 0.7, 0.95, 0.75, 0.85, 0.9, 0.8]
    s = GainSlopeSensor(_Scripted(gains), window=8, min_points=4)
    assert not any(trigger_state(m) for m in _run(s, len(gains)))


def test_a_flat_high_gain_trace_does_not_fire():
    # constant gain is a zero slope, not a decline: the loop is still paying
    s = GainSlopeSensor(_Scripted([0.9] * 8), window=8, min_points=4)
    assert not any(trigger_state(m) for m in _run(s, 8))


def test_noisy_readings_make_the_sensor_more_conservative():
    gains = [1.0, 0.85, 0.7, 0.55, 0.4, 0.25]
    confident = GainSlopeSensor(_Scripted(gains, [0.01] * 6), window=6, min_points=4)
    unsure = GainSlopeSensor(_Scripted(gains, [0.9] * 6), window=6, min_points=4)
    zs_conf = [m.standardized for m in _run(confident, 6)]
    zs_unsure = [m.standardized for m in _run(unsure, 6)]
    # same trend, but declared uncertainty must not make it MORE confident
    assert abs(zs_unsure[-1]) <= abs(zs_conf[-1]) + 1e-9


def test_window_bounds_what_the_slope_sees():
    # a decline long past should not keep firing once recent steps recover
    gains = [1.0, 0.6, 0.2, 0.1, 0.5, 0.9, 1.2, 1.5]
    s = GainSlopeSensor(_Scripted(gains), window=4, min_points=4)
    zs = [m.standardized for m in _run(s, len(gains))]
    assert zs[-1] > 0  # the recent window is rising


def test_reset_clears_history():
    s = GainSlopeSensor(_Scripted([1.0, 0.5, 0.25, 0.1]), window=6, min_points=4)
    _run(s, 4)
    s.reset()
    m = s.measure(IterationObservation(artifact="fresh", index=0))
    assert m.standardized == 0.0


def test_it_names_its_confounds():
    s = GainSlopeSensor(_Scripted([1.0] * 5))
    m = _run(s, 5)[-1]
    assert m.confounds
    assert any("slope" in c.lower() or "trend" in c.lower() for c in m.confounds)


def test_registered_under_the_taxonomy_name():
    from gyre.providers import get_provider

    p = get_provider("pcr:gain-slope")
    assert p.loop_id == "L1"
