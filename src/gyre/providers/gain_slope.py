"""A plateau is a claim about a derivative, so measure the derivative.

Every other L1 sensor in this repository reads a LEVEL - how novel is this step
- or a consecutive difference. But the thing the construct actually asserts is
that information gain has *stopped rising*, and that is a statement about the
slope of gain over recent steps. A single low reading is not a plateau; six
readings trending down is.

Estimating a slope from noisy readings without its standard error is how you get
a sensor that fires on scatter. So this fits a weighted line over a rolling
window and decides on **slope divided by its standard error**, a t-like
statistic, which means the decision needs no hand-picked slope threshold. It
reports that statistic as ``standardized``, so the shared trigger policy fires
it on the same evidence bar every other calibrated sensor uses.

**Relationship to errors-in-variables regression.** The weight form here,
``w = 1/(sigma_y^2 + beta^2 * sigma_x^2)``, is the one that falls out of
heteroscedastic errors-in-variables estimation. The predictor in this sensor is
the step index, which is measured exactly, so ``sigma_x = 0`` and the estimator
collapses to weighted least squares - and saying so plainly matters more than
claiming a heavier method than the problem needs. The full correction earns its
keep when the predictor is itself a noisy measurement, which is the case for the
autoregressive variant (regressing gain on lagged gain) where measurement error
in the lagged term attenuates the coefficient toward zero.

Per-point sigma comes from whatever the inner sensor declares in
``Measurement.measurement_error``. A sensor that reports its own uncertainty
makes this estimator better; one that does not is treated as uniformly
weighted, which is honest rather than optimistic.

Dependencies: standard library only.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any, Sequence

from gyre.measurement import Meaning, Measurement, MeasurementProvider

_MIN_SIGMA = 1e-9


def weighted_slope(
    xs: Sequence[float], ys: Sequence[float], sigmas: Sequence[float]
) -> tuple[float, float]:
    """Weighted least-squares slope and its standard error.

    Weights are inverse variance, so a reading the sensor is unsure about pulls
    the line less. The returned standard error is the residual-based one, which
    is what makes the slope decidable: a steep line through scattered points and
    a shallow line through tight ones can carry the same evidence, and only the
    ratio distinguishes them.
    """
    n = len(xs)
    if n < 3:
        raise ValueError("a slope with a standard error needs at least 3 points")
    w = [1.0 / max(s, _MIN_SIGMA) ** 2 for s in sigmas]
    sw = sum(w)
    mx = sum(wi * x for wi, x in zip(w, xs)) / sw
    my = sum(wi * y for wi, y in zip(w, ys)) / sw
    sxx = sum(wi * (x - mx) ** 2 for wi, x in zip(w, xs))
    if sxx <= 0:
        return 0.0, 0.0
    slope = sum(wi * (x - mx) * (y - my) for wi, x, y in zip(w, xs, ys)) / sxx

    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    dof = n - 2
    # weighted residual variance, scaled back onto the slope
    s2 = sum(wi * r * r for wi, r in zip(w, resid)) / dof if dof > 0 else 0.0
    se = math.sqrt(s2 / sxx) if s2 > 0 else 0.0
    return slope, se


class GainSlopeSensor:
    """Wrap any L1 sensor; report the trend in its readings rather than the level.

    ``standardized`` is ``slope / se``: strongly negative means information gain
    is falling faster than the scatter can explain, which is the plateau the
    construct is about. Positive means the loop is still learning. Zero, and
    during burn-in, means there is not yet enough evidence to say - which is a
    verdict, not a gap.
    """

    def __init__(
        self,
        inner: MeasurementProvider,
        *,
        window: int = 6,
        min_points: int = 4,
    ) -> None:
        if min_points < 3:
            raise ValueError("min_points must be >= 3 to estimate a standard error")
        if window < min_points:
            raise ValueError("window must be at least min_points")
        self._inner = inner
        self._window = window
        self._min_points = min_points
        self.loop_id = inner.loop_id
        self.name = "pcr:gain-slope"
        self._xs: deque[float] = deque(maxlen=window)
        self._ys: deque[float] = deque(maxlen=window)
        self._sig: deque[float] = deque(maxlen=window)
        self._n = 0

    def measure(self, observation: Any) -> Measurement:
        m = self._inner.measure(observation)
        # Work in "higher is better" space so a falling slope always means
        # deteriorating, whatever the inner sensor's direction convention.
        y = -m.value if m.meaning is Meaning.LOWER_IS_HEALTHIER else m.value
        sigma = m.measurement_error if m.measurement_error else 1.0

        self._xs.append(float(self._n))
        self._ys.append(float(y))
        self._sig.append(float(sigma))
        self._n += 1

        if len(self._xs) < self._min_points:
            z, slope, se = 0.0, 0.0, 0.0
        else:
            slope, se = weighted_slope(list(self._xs), list(self._ys), list(self._sig))
            z = slope / se if se > _MIN_SIGMA else (0.0 if slope == 0 else math.copysign(4.0, slope))

        return Measurement(
            value=slope,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            standardized=z,
            measurement_error=se or None,
            provider=self.name,
            confounds=(
                "reads a trend, so it is deliberately blind to a loop that was "
                "unproductive from the very first step: there is no decline to detect",
                "a rolling window forgets: a long plateau that recently recovered "
                "reads as healthy, which is usually right and occasionally not",
                "inherits every confound of the inner sensor whose readings it fits",
            )
            + m.confounds,
        )

    def reset(self) -> None:
        self._inner.reset()
        self._xs.clear()
        self._ys.clear()
        self._sig.clear()
        self._n = 0
