"""Propagate measurement unreliability into the decision, not just the estimate.

Every sensor reading is a noisy measurement of a latent state. Classical
measurement-error theory says what that noise does to an *estimate*: it
attenuates it toward zero, and you can correct the estimate if you know the
reliability. That correction is well-trodden — errors-in-variables regression,
disattenuated correlation, regression calibration.

What is far less trodden, and what a control loop actually needs, is the
consequence for a *decision*. A controller does not want a corrected slope. It
wants to know: given that this sensor is only so reliable, where should my
threshold sit, and when should I decline to decide at all?

For a standardized reading ``z`` with reliability ``r`` (the proportion of
observed variance that is true signal), classical theory gives three things:

    z_true_hat = r * z_obs                    shrinkage toward the mean
    tau_obs    = tau / r                      the observed-scale threshold
                                              equivalent to ``tau`` on the latent
    band       = tau/r ± k*sqrt((1-r)/r)      where the reading cannot decide

The first two are algebra. The third is the one that matters operationally:
**under unreliability there is a range of readings where the honest answer is
"I do not know", and a controller that fires anyway is manufacturing
confidence out of noise.** Gyre's stance elsewhere is that an unevidenced
verdict must not gate; this is the same rule expressed in continuous form.

**The guard that must ship with all of it.** A published sigma sweep on real
data (NHANES, BMI→systolic BP) shows the corrected slope moving roughly forty-
fold across a plausible range of assumed measurement error, and diverging
entirely at the top of that range. The correction is only ever as good as the
reliability estimate you feed it. So ``sensitivity_band`` is not optional
garnish: any correction whose value swings wildly when the reliability estimate
is perturbed is **not reportable as a point estimate**, and this module says so
in the return type rather than in a footnote.

Dependencies: standard library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence

_EPS = 1e-12


def _check_reliability(r: float) -> None:
    if not 0.0 <= r <= 1.0:
        raise ValueError(f"reliability must be in [0, 1], got {r}")


def reliability_from_retest(raw_agreement: float) -> float:
    """Turn a test-retest raw agreement into a reliability in [0, 1].

    For a binary verdict, 0.5 agreement is chance and carries no signal, so the
    scale is rebased: ``r = max(0, 2a - 1)``. Below-chance agreement clamps to
    zero rather than going negative — a sensor that disagrees with itself is
    not anti-informative, it is uninformative.

    ``gyre.labeling.retest_agreement`` produces exactly this input, which makes
    the repeatability check Gyre already runs the natural source of ``r``."""
    if not 0.0 <= raw_agreement <= 1.0:
        raise ValueError(f"raw_agreement must be in [0, 1], got {raw_agreement}")
    return max(0.0, 2.0 * raw_agreement - 1.0)


def shrink_standardized(z_obs: float, reliability: float) -> float:
    """Best estimate of the LATENT standardized value behind a noisy reading.

    ``E[z_true | z_obs] = r * z_obs``. An unreliable sensor's extreme readings
    are mostly noise, so they regress toward the mean; at ``r = 0`` the reading
    carries nothing and the estimate is the mean itself."""
    _check_reliability(reliability)
    return reliability * z_obs


def threshold_for_reliability(tau_latent: float, reliability: float) -> float:
    """The OBSERVED-scale threshold equivalent to ``tau_latent`` on the latent scale.

    Because the observed scale is inflated by measurement noise, concluding a
    latent departure of ``tau`` requires an observed departure of ``tau / r``.
    Using the latent threshold directly on an unreliable observed reading is
    the single most common way to over-fire.

    At ``r = 0`` the threshold is infinite: no observed reading, however
    extreme, licenses a conclusion about the latent state. That is the correct
    answer, and a controller should read it as "this sensor cannot gate."""
    _check_reliability(reliability)
    if reliability <= _EPS:
        return math.inf
    return tau_latent / reliability


class Verdict(str, Enum):
    ROBUST = "robust"
    CAUTION = "caution"
    FRAGILE = "fragile"


def decision_band(
    tau_latent: float, reliability: float, *, k: float = 1.0
) -> tuple[float, float]:
    """The range of observed readings that cannot decide, at this reliability.

    Width is ``k * sqrt((1-r)/r)``, the residual spread of the latent estimate
    given a standardized observation. Readings inside the band should produce an
    abstention — route to a human, gather more evidence, or keep sensing — not a
    coin flip dressed as a verdict. The band collapses to a point at ``r = 1``
    and spans everything as ``r`` approaches 0."""
    _check_reliability(reliability)
    centre = threshold_for_reliability(tau_latent, reliability)
    if not math.isfinite(centre):
        return (-math.inf, math.inf)
    half = k * math.sqrt((1.0 - reliability) / max(reliability, _EPS))
    return (centre - half, centre + half)


def deattenuate_effect(observed_effect: float, reliability: float) -> float:
    """Correct an effect estimate for unreliability in the predictor.

    ``beta_true = beta_obs / r``. This is the standard attenuation correction:
    a noisy predictor biases a regression slope toward zero, so an effect
    measured with an imperfect sensor UNDERSTATES the true relationship.

    Practical consequence for loop measurement: if you regress a sensor's
    readings onto task outcomes without correcting, you are reporting a floor
    on how much loop health matters, not an estimate of it.

    It also gives something the experimental design otherwise needs labels for
    — an estimate of the *sensor ceiling*, i.e. what the effect would be with a
    perfect sensor — which is the comparison that separates "my sensor is the
    bottleneck" from "my controller is the bottleneck".

    Always pair with ``sensitivity_band``: this quantity is highly sensitive to
    ``r`` and explodes as ``r`` approaches 0."""
    _check_reliability(reliability)
    if reliability <= _EPS:
        raise ValueError(
            "cannot de-attenuate at zero reliability: the correction is unbounded, "
            "which is the honest answer that no effect is identifiable"
        )
    return observed_effect / reliability


@dataclass(frozen=True)
class SensitivityBand:
    """How much a reliability-corrected quantity moves when ``r`` is perturbed."""

    centre: float
    low: float
    high: float
    relative_range: float
    verdict: Verdict
    note: str

    @property
    def reportable_as_point(self) -> bool:
        """A FRAGILE correction must be reported as an interval or not at all."""
        return self.verdict is not Verdict.FRAGILE


DEFAULT_DELTA = 0.05
"""How far to perturb a reliability estimate, ADDITIVELY.

The published sigma-sensitivity check this pattern comes from perturbs sigma
multiplicatively, which is right for an unbounded positive scale. Reliability is
bounded at 1, so a multiplicative perturbation is not comparable across the
range: scaling r = 0.95 by 0.75 yields 0.71, an enormous change in reliability
terms, while scaling r = 0.2 by the same factor barely moves it. Additive
perturbation asks the question a practitioner actually has an answer to —
"how many points of reliability am I unsure about?" — and a test-retest
bootstrap gives it directly."""


def sensitivity_band(
    quantity: Callable[[float], float],
    reliability: float,
    *,
    delta: float = DEFAULT_DELTA,
    caution_at: float = 0.25,
    fragile_at: float = 0.60,
) -> SensitivityBand:
    """Recompute ``quantity`` across perturbed reliabilities and grade the spread.

    Vendored in spirit from the PCR sigma-sensitivity check, which exists because
    a real published sweep showed a corrected slope moving ~40x across a
    plausible range of assumed measurement error. A correction is only as
    trustworthy as its reliability input, and the only honest way to show that
    is to perturb the input and publish the range.

    ``relative_range`` is ``(high - low) / |centre|``. ROBUST below
    ``caution_at``, FRAGILE above ``fragile_at``. Note that the SAME absolute
    uncertainty in ``r`` produces a wildly different swing depending on where
    ``r`` sits: 1/r is near-linear at 0.95 and explosive at 0.12. That is not a
    quirk of the check, it is the actual epistemic situation, and it is why a
    correction computed from a low reliability estimate should never be quoted
    as a single number."""
    _check_reliability(reliability)
    offsets = (-delta, -delta / 2, 0.0, delta / 2, delta)
    values = []
    for off in offsets:
        r = min(1.0, max(_EPS, reliability + off))
        try:
            values.append(quantity(r))
        except (ValueError, ZeroDivisionError):
            values.append(math.inf)
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return SensitivityBand(
            math.inf, math.inf, math.inf, math.inf, Verdict.FRAGILE,
            "every perturbation diverged: the reliability estimate is too low to correct at",
        )
    centre = quantity(reliability) if reliability > _EPS else math.inf
    low, high = min(finite), max(finite)
    denom = abs(centre) if math.isfinite(centre) and abs(centre) > _EPS else abs(low) or 1.0
    rel = (high - low) / denom
    if len(finite) < len(values) or rel > fragile_at:
        verdict = Verdict.FRAGILE
    elif rel > caution_at:
        verdict = Verdict.CAUTION
    else:
        verdict = Verdict.ROBUST
    return SensitivityBand(
        centre=centre,
        low=low,
        high=high,
        relative_range=rel,
        verdict=verdict,
        note=(
            f"reliability {reliability:.3f} +/- {delta}: "
            f"value spans [{low:.4g}, {high:.4g}] "
            f"({rel:.0%} of the point estimate) -> {verdict.value}"
        ),
    )


# --- split-conformal width floor ------------------------------------------------
#
# The one piece of this machinery that carries a DISTRIBUTION-FREE guarantee.
# Everything above assumes classical measurement error: additive, homoscedastic,
# independent of the true value. Split conformal assumes only exchangeability of
# the calibration residuals, which is a far weaker requirement.
#
# Provenance worth stating: this was implemented and validated on real data in a
# sibling project, which computed the quantile, reported it, and then never used
# it for anything. The unexploited step is the one below — using it as a FLOOR.
# A claimed interval narrower than the empirical coverage width is not a
# confident measurement, it is an incoherent one, and a controller should refuse
# to act on it rather than admire its precision.


def conformal_width_floor(
    abs_residuals: Sequence[float], *, alpha: float = 0.1
) -> float | None:
    """Narrowest two-sided interval width consistent with observed error.

    Split-conformal: sort the absolute residuals from a held-out calibration
    set, take the ``ceil((n+1)(1-alpha))``-th, and double it for a two-sided
    width. Under exchangeability this width has at least ``1 - alpha`` coverage,
    with no assumption about the error distribution.

    Returns ``None`` when the calibration set is too small for the quantile to
    exist (``n < 1/alpha - 1``). That is a refusal, not a zero: with four
    residuals you cannot make a 95% coverage statement, and pretending otherwise
    is how coverage claims become decoration."""
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    n = len(abs_residuals)
    if n == 0:
        return None
    rank = math.ceil((n + 1) * (1 - alpha))
    if rank > n:
        return None  # not enough calibration data to support this coverage level
    return 2.0 * sorted(abs(r) for r in abs_residuals)[rank - 1]


def interval_is_coherent(claimed_width: float, floor: float | None) -> bool:
    """Is a claimed uncertainty interval at least as wide as observed error allows?

    ``floor`` of ``None`` (no calibration data) makes this vacuously true: with
    no evidence about coverage there is no basis to call an interval incoherent.
    Absence of a bound is not a bound."""
    if floor is None:
        return True
    return claimed_width >= floor
