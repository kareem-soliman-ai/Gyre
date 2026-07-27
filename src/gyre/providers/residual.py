"""AR(1) residual sensor for L6 habituation/orienting.

Implements machinery B1 from the formal-machinery taxonomy: an autoregressive
model that flags the residual of a channel's movement rather than its raw level.

What it computes (signal-theoretic):
    An AR(1) model predicts the next observation from the previous one:
        x_t = φ * x_{t-1} + ε_t

    The residual ε_t = x_t − φ̂ * x_{t-1} measures how much of the current
    observation is *not* explained by its recent autonomy.  A slow drift is
    *expected* under an AR(1) model (φ close to 1 means the channel predicts
    itself), so residuals are small.  A genuine break — a jump, a regime
    change — produces a large residual even under strong autocorrelation,
    killing the false-positive problem the naive z-score has on drifting channels.

Why this matters for Gyre:
    The L6 habituation filter's job is to ignore "expected" channel behaviour
    and fire only on genuine novelty.  A z-score on a slow-drift channel fires
    on every slow change (because the standard deviation underestimates the
    expected variation in a correlated sequence).  An AR(1) model absorbs the
    drift and leaves only the unexpected part, making it the right sensor for
    L6.

Parameters:
    window: int = 30  — number of observations used to fit φ (default: 30)
    burnin: int = 5   — minimum observations before producing a decision
    johansen: bool = False  — reserve for future Johansen correction (not implemented)

The sensor is calibrated: it produces a `decision` field, so loops can defer
to the provider's call instead of guessing a threshold.  It also reports
`standardized` = residual / residual_stderr.

Dependencies: standard library only.  No numpy or scipy.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

from gyre.measurement import Meaning, Measurement


@dataclass
class Ar1ResidualSensor:
    """Detect an unexpected break in a L6 channel by monitoring the AR(1)
    residual.  Slow drift is absorbed by the model; sudden jumps produce
    large residuals.

    For L1 use in the sequencing-scale sense, the channel should be a
    numeric signal (e.g. information gain per step).  For L6, it is
    the ChannelObservation's value.  The sensor is *not* calibrated to
    a specific loop — it models the channel's direction, not the loop's
    protocol.

    Parameters
    ----------
    loop_id: str
        Which loop this sensors (default ``"L6"``; can be ``"L1"`` when
        monitoring an information-gain channel).
    window: int
        Number of observations to use for the AR(1) estimate.
    burnin: int
        Minimum observations before producing a decision.
    threshold: float
        Number of residual standard errors to trigger on.  Default 2.0
        (the conventional significance cutoff).
    """

    loop_id: str = "L6"
    name: str = "ar1:residual"
    window: int = 30
    burnin: int = 5
    threshold: float = 2.0

    def __post_init__(self) -> None:
        self._values: list[float] = []
        self._residuals: list[float] = []

    def _fit_ar1(self) -> tuple[float, float, float]:
        """Fit AR(1): x_t = φ * x_{t-1} + ε.
        Returns (φ, residual_std, last_residual).
        Uses OLS on the window to estimate φ, then computes the residuals.
        """
        n = len(self._values)
        if n < 3:
            return 0.0, 0.0, 0.0

        # Use the last 'window' observations
        data = self._values[-self.window:]
        m = len(data)
        if m < 3:
            return 0.0, 0.0, 0.0

        # OLS: φ = Σ(x_{t-1} * x_t) / Σ(x_{t-1}^2), for t = 1..m-1
        sum_uv = 0.0
        sum_uu = 0.0
        for i in range(1, m):
            u = data[i - 1]
            v = data[i]
            sum_uv += u * v
            sum_uu += u * u
        phi = sum_uv / sum_uu if sum_uu > 0 else 0.0
        phi = max(-0.99, min(0.99, phi))  # clip to stable range

        # Compute residuals
        residuals = []
        for i in range(1, m):
            predicted = phi * data[i - 1]
            residuals.append(data[i] - predicted)

        # Residual std (unbiased estimator)
        mean_res = sum(residuals) / len(residuals)
        var_res = sum((r - mean_res) ** 2 for r in residuals) / max(len(residuals) - 1, 1)
        std_res = math.sqrt(var_res) if var_res > 0 else 1e-8

        return phi, std_res, residuals[-1]

    def measure(self, observation: Any) -> Measurement:
        # Extract the numeric value from the observation.
        if hasattr(observation, "value") and observation.value is not None:
            x = float(observation.value)
        elif hasattr(observation, "artifact"):
            # L1: can't use AR(1) on text artifacts — return uncalibrated.
            return Measurement(
                value=0.0,
                meaning=Meaning.DEVIATION,
                confounds=("AR(1) requires a numeric channel; got a text observation",),
                provider=self.name,
            )
        else:
            return Measurement(
                value=0.0,
                meaning=Meaning.DEVIATION,
                confounds=("unrecognised observation shape",),
                provider=self.name,
            )

        self._values.append(x)
        n = len(self._values)

        if n <= self.burnin:
            return Measurement(
                value=0.0,
                meaning=Meaning.DEVIATION,
                standardized=0.0,
                decision=False,
                confounds=("AR(1) baseline still forming",),
                provider=self.name,
                detail={"n": n, "burnin": True, "value": x},
            )

        phi, std_res, last_res = self._fit_ar1()
        self._residuals.append(last_res)

        # Standardized residual
        if std_res == 0:
            z = 0.0
        else:
            z = last_res / std_res

        fired = abs(z) >= self.threshold

        return Measurement(
            value=abs(last_res),
            meaning=Meaning.DEVIATION,
            standardized=z,
            decision=fired,
            confounds=(
                "AR(1) model is linear-Gaussian: non-linear dynamics are mis-specified",
                "φ is estimated from a fixed window; cannot adapt to regime changes that "
                "are *within* the window",
                "autocorrelation transparent to slow drift (the model's intended purpose)",
            ),
            provider=self.name,
            detail={
                "phi": phi,
                "residual": last_res,
                "residual_std": std_res,
                "z": z,
                "n": n,
            },
        )

    def reset(self) -> None:
        self._values.clear()
        self._residuals.clear()