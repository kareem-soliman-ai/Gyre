"""Sequential-change sensors for L1 (rumination) and L6 (habituation).

These implement two standard sequential-detection machineries (A1, A2 from the
formal-machinery taxonomy) and deliver them behind the ``MeasurementProvider``
interface so any loop can swap them in:

- ``CusumSensor`` — cumulative-sum change detection. Monitors a scalar
  channel (e.g. per-step information gain) for a shift below a learned
  baseline. Fires when the cumulative deficit exceeds a decision interval *h*.
  After a true plateau, CUSUM fires faster than a naive level-threshold
  because it accumulates *evidence* rather than comparing one observation.

- ``SprtSensor`` — sequential probability ratio test. Maintains an
  accumulating log-likelihood ratio for the composite hypothesis "this
  channel has shifted." Decides in a fixed number of steps when evidence is
  decisive and keeps sampling when it is not, which is the optimal-stopping
  form: stop as soon as evidence is decisive, otherwise keep going.

Both sensors are *stateful* (they maintain a running statistic), so they
require ``reset()`` between independent runs. They are calibrated: they
produce a ``decision`` field on the ``Measurement`` so that the loop's
trigger policy can defer to them instead of guessing a threshold.

Dependencies: standard library only (math).

See docs/architecture.md for the measurement seam and the calibration ladder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gyre.measurement import Meaning, Measurement


# ---------------------------------------------------------------------------
# CUSUM — cumulative-sum change detection
# ---------------------------------------------------------------------------

@dataclass
class CusumSensor:
    """Detect a *downward* shift in a HIGHER_IS_HEALTHIER channel (e.g.
    per-step information gain). A CUSUM detects a *change*, not just a level;
    it is the correct sensor when you want to catch the *onset* of a plateau
    rather than waiting for the level to drop below a fixed floor.

    Parameters
    ----------
    loop_id : str
        Which loop this sensors. Default ``"L1"`` for rumination, but can be
        ``"L6"`` for habituation/orienting.
    k : float
        Slack parameter — half the magnitude of the shift you want to catch.
        A shift of 2k triggers a CUSUM alarm. Lower k = higher sensitivity
        but more false alarms on drift.
    h : float
        Decision interval. CUSUM fires when S_t > h. Derived from the
        target average run length (ARL₀) for the noise-only process. In
        practice, h ≈ 4·sigma for moderate ARL₀; the default of 5.0 is
        a reasonable middle ground.
    burnin : int
        Number of initial observations to use for estimating the noise
        baseline (running mean and variance). During burnin, the sensor
        returns ``standardized=0.0`` and ``decision=False``, so it never
        fires on cold data.
    """

    loop_id: str = "L1"
    name: str = "cusum:gain-shift"
    k: float = 0.5
    h: float = 5.0
    burnin: int = 5

    def __post_init__(self) -> None:
        self._values: list[float] = []
        self._S: float = 0.0  # cumulative statistic
        self._fired: bool = False

    def measure(self, observation: Any) -> Measurement:
        # Extract the value.  For L1, the observation is an IterationObservation
        # with a numeric ``value`` or a ``gain`` attribute; for L6, it is a
        # ChannelObservation with a ``value``.  We accept either shape and let
        # the caller pass whatever the provider expects.
        if hasattr(observation, "value") and observation.value is not None:
            x = float(observation.value)
        elif hasattr(observation, "artifact"):
            # L1 path: we need a numeric gain, not text.  If the caller gives us
            # raw text, we cannot run CUSUM — return an uncalibrated measurement.
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                confounds=("CUSUM requires a numeric channel; got a text observation",),
                provider=self.name,
            )
        else:
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                confounds=("unrecognised observation shape",),
                provider=self.name,
            )

        self._values.append(x)
        n = len(self._values)

        # --- burnin phase: estimate baseline and report zero deviation ---
        if n <= self.burnin:
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                standardized=0.0,
                decision=False,
                confounds=("CUSUM baseline still forming",),
                provider=self.name,
                detail={"n": n, "burnin": True},
            )

        # Compute baseline mean from the burnin window only.  We do NOT update
        # the mean from subsequent observations: the CUSUM detects a *shift*
        # from the learned baseline, so using the current mean defeats the
        # purpose.  This is a modelled baseline, not a rolling one.
        baseline = sum(self._values[: self.burnin]) / self.burnin
        # Compute baseline std from window only
        baseline_var = sum((v - baseline) ** 2 for v in self._values[: self.burnin]) / self.burnin
        sigma = baseline_var ** 0.5 if baseline_var > 0 else 1.0

        # CUSUM statistic: accumulate the deficit below baseline (normalised)
        deficit = (baseline - x) / sigma  # positive when x is below baseline
        self._S = max(0.0, self._S + deficit - self.k)

        fired = self._S > self.h
        if fired:
            self._fired = True

        return Measurement(
            value=self._S,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            standardized=self._S / self.h if self.h > 0 else self._S,
            decision=fired,
            confounds=(
                "detects shifts, not levels: a gradual decline is caught only when "
                "the cumulative deficit crosses the decision interval",
                "baseline is fixed to burnin; does not adapt to non-stationary environments",
            ),
            provider=self.name,
            detail={
                "S_t": self._S,
                "baseline": baseline,
                "sigma": sigma,
                "k": self.k,
                "h": self.h,
            },
        )

    def reset(self) -> None:
        self._values.clear()
        self._S = 0.0
        self._fired = False


# ---------------------------------------------------------------------------
# SPRT — sequential probability ratio test
# ---------------------------------------------------------------------------

@dataclass
class SprtSensor:
    """Sequential probability ratio test (Wald) for H₀: channel is at baseline
    vs. H₁: channel has shifted.

    The SPRT accumulates a log-likelihood ratio on each observation and stops
    as soon as the evidence is decisive. This is the *optimal* stopping rule
    for a binary hypothesis: given two hypotheses, it minimises the expected
    number of samples needed to reach a decision of a given accuracy.

    The sensor models the "normal" channel as a Gaussian(μ₀, σ²) and the
    "shifted" channel as a Gaussian(μ₁, σ²) where μ₁ < μ₁ for the
    HIGHER_IS_HEALTHIER case (we look for drift *downward*).  The
    log-likelihood ratio accumulates as:

        LLR_t = Σ log[ p(x_i | H₁) / p(x_i | H₀) ]

    Stop (conclude shift) when LLR_t >= log((1−β)/α).
    Stay silent (conclude normal) when LLR_t <= log(β/(1−α)).

    Parameters
    ----------
    loop_id : str
        Which loop this sensors. Default ``"L1"``.
    alpha : float
        Type I error probability (false alarm rate).
    beta : float
        Type II error probability (miss rate).
    shift_magnitude : float
        The sigma-normalised shift to detect. A shift of 1.0 means the
        "shifted" process has a mean one sigma below the baseline. Part of
        the sensor's *design*, not a threshold: the user declares what shift
        is worth detecting, and the SPRT tells you when it sees one.
    burnin : int
        Observations to use for estimating the baseline.
    """

    loop_id: str = "L1"
    name: str = "sprt:gain-shift"
    alpha: float = 0.05
    beta: float = 0.10
    shift_magnitude: float = 1.0
    burnin: int = 5

    def __post_init__(self) -> None:
        self._values: list[float] = []
        self._log_lr: float = 0.0
        self._decided: bool = False

    def _upper(self) -> float:
        import math
        return math.log((1 - self.beta) / self.alpha)

    def _lower(self) -> float:
        import math
        return math.log(self.beta / (1 - self.alpha))

    def measure(self, observation: Any) -> Measurement:
        # Extract the value from observation (same logic as CUSUM)
        if hasattr(observation, "value") and observation.value is not None:
            x = float(observation.value)
        elif hasattr(observation, "artifact"):
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                confounds=("SPRT requires a numeric channel; got a text observation",),
                provider=self.name,
            )
        else:
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                confounds=("unrecognised observation shape",),
                provider=self.name,
            )

        self._values.append(x)
        n = len(self._values)

        if n <= self.burnin:
            return Measurement(
                value=0.0,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                standardized=0.0,
                decision=False,
                confounds=("SPRT baseline still forming",),
                provider=self.name,
                detail={"n": n, "burnin": True},
            )

        # Estimate baseline from burnin
        baseline = sum(self._values[: self.burnin]) / self.burnin
        baseline_var = sum((v - baseline) ** 2 for v in self._values[: self.burnin]) / self.burnin
        sigma = baseline_var ** 0.5 if baseline_var > 0 else 1.0

        # H0: x ~ N(baseline, sigma²), H1: x ~ N(baseline - shift_magnitude * sigma, sigma²)
        mu0 = baseline
        mu1 = baseline - self.shift_magnitude * sigma

        # Log-likelihood ratio: log p(x|H1) - log p(x|H0)
        # For Gaussian: log p(x|μ,σ²) = -0.5 * ((x-μ)/σ)² - log(σ√(2π))
        # So diff = 0.5 * [((x-μ0)/σ)² - ((x-μ1)/σ)²]
        diff = 0.5 * (((x - mu0) / sigma) ** 2 - ((x - mu1) / sigma) ** 2)
        self._log_lr += diff

        upper = self._upper()
        lower = self._lower()
        fired = self._log_lr >= upper
        decided_normal = self._log_lr <= lower

        if fired:
            self._decided = True

        return Measurement(
            value=self._log_lr,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            standardized=self._log_lr / upper if upper > 0 else self._log_lr,
            decision=fired,
            confounds=(
                "assumes Gaussian noise; autocorrelated channels need AR correction",
                "early observations during burnin silently excluded from the test",
                "the test stops at the first decisive observation; does not continue "
                "monitoring after firing",
            ),
            provider=self.name,
            detail={
                "log_lr_t": self._log_lr,
                "upper": upper,
                "lower": lower,
                "decided_normal": decided_normal,
                "mu0": mu0,
                "mu1": mu1,
                "sigma": sigma,
            },
        )

    def reset(self) -> None:
        self._values.clear()
        self._log_lr = 0.0
        self._decided = False