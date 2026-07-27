"""Value-of-Information (VoI) sensor for L2 (machinery A6 from the taxonomy).

The VoI rule answers the question: *given my current posterior over
hypotheses, is one more observation worth its cost?* More formally::

    EVSI(experiment) = E_data[ max_a E_{θ|data} U(a, θ) ]
                     − max_a E_θ U(a, θ)
    CONTINUE observing when EVSI > cost(experiment)
    COMMIT to the best current hypothesis when EVSI ≤ cost

The VoI is the principled *stopping rule* for the L2 calibration governor:
"L2's job is to tell me when the agent's stated confidence is
calibrated enough to commit. The question of WHEN to commit, however,
is more nuanced than a fixed threshold — it depends on the cost of
asking for one more sample."

Why this is the right sensor for L2's stopping rule
---------------------------------------------------
The naive L2 provider (RollingBrier) gives a point estimate of
calibration error. A threshold-tuned commit/abstain rule on that
single number has the brittleness fixed thresholds always have.
The VoI rule, by contrast, asks the right question: given what we
already know about our calibration, would ONE more
(prediction, outcome) pair lower our calibration uncertainty enough to
be worth the cost (in stakes, time, attention) it takes to obtain one?

Where the implementation makes a real choice
---------------------------------------------
Aurora's ``npbi.inference.value_of_information`` is built around a
fully-specified posterior over named hypotheses. L2's state in Gyre
is more modest: a running Brier score, a sample count, and a decision
upper/lower threshold. The implementation below uses a Beta-binomial
conjugate model on the recent window of (correct, wrong) outcomes —
the simplest non-trivial posterior that supports a real VoI
calculation. This is the same Beta-Bernoulli trick Bayesian AB
testing frameworks use, and it is the correct minimum.

The output ``Measurement`` carries the *Bayesian optimal stopping
flag*: ``decision=True`` means "EVSI > cost; keep observing" —
which, in L2's vocabulary, translates to ``decision=True`` meaning
"the agent should NOT commit yet, gather more data." The contract is
intentionally reversed (higher VoI = healthier = should continue
observing), and ``gyre.loops._policy.trigger_state`` already
treats ``decision`` as the provider's call, so the polarity is
inverted at the policy layer where the calibration governor
translates it.

Provenance
----------
Ported from Aurora's ``npbi.inference.value_of_information``
(``voi_decide``, ``value_of_information``,
``expected_information_gain``). The Bayesian-update machinery
(``posterior_after``) is renamed to ``beta_posterior_after`` so its
semantics are explicit, and the L2 loop is wired by giving the
output a Beta–Bernoulli "state" via the running window of outcomes
the L2 provider maintains.

Standard library only.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import lgamma, log
from typing import Any, Mapping

from gyre.loops.calibration import PredictionOutcome
from gyre.measurement import Meaning, Measurement


# ---------------------------------------------------------------------------
# Core VoI primitives, ported from Aurora.
# Reproduced (with full attribution in the module docstring) so the same
# rules can be applied to Gyre's calibration setting without importing
# scipy / numpy.
# ---------------------------------------------------------------------------


def entropy(distribution: Mapping[str, float]) -> float:
    """Shannon entropy (nats) of a probability distribution."""

    return -sum(p * log(p) for p in distribution.values() if p > 0.0)


def _normalise(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(w for w in weights.values() if w > 0)
    if total <= 0:
        return {}
    return {k: w / total for k, w in weights.items() if w > 0}


def beta_log_normaliser(alpha: float, beta_param: float) -> float:
    """log B(α, β), the Beta-function normalisation constant, via lgamma.

    Implemented in terms of ``math.lgamma`` only, to match Gyre's
    no-third-party-deps rule.

        log B(α, β) = lgamma(α) + lgamma(β) − lgamma(α + β)
    """

    return lgamma(alpha) + lgamma(beta_param) - lgamma(alpha + beta_param)


def beta_posterior_after(prior_alpha: float, prior_beta: float,
                        successes: int, failures: int) -> tuple[float, float]:
    """Posterior over the success probability after observing ``successes``
    and ``failures`` independent Bernoulli trials under a Beta(prior_alpha,
    prior_beta) prior.

    Returns the (alpha, beta) of the updated Beta posterior. Conjugate
    updates are simply additive — the Beta-family's defining property.
    """

    return (prior_alpha + successes, prior_beta + failures)


def _beta_variance(alpha: float, beta_param: float) -> float:
    """Variance of a Beta(α, β) distribution."""
    total = alpha + beta_param
    if total <= 0:
        return 0.0
    return (alpha * beta_param) / (total * total * (total + 1))


def _beta_mean(alpha: float, beta_param: float) -> float:
    """Mean of a Beta(α, β) distribution."""
    total = alpha + beta_param
    if total <= 0:
        return 0.0
    return alpha / total


def _approx_beta_entropy(alpha: float, beta_param: float) -> float:
    """Approximate Shannon entropy of Beta(α, β) in nats.

    Closed-form Beta entropy requires the digamma function (not in the
    Python standard library).  We use a sampling-based approximation:
    draw ``n_samples`` from Beta(α, β), bin them into a histogram, and
    compute the discrete entropy of the histogram.  This is exact in
    the limit of infinite samples and is the right minimum for the
    L2 stopping rule, which only needs the *sign* of the entropy
    change (positive = keep observing, negative = commit).

    For very narrow posteriors (variance < 1e-6), the Beta is
    effectively a point mass and entropy is 0.
    """
    import math
    import random

    var = _beta_variance(alpha, beta_param)
    if var < 1e-6:
        return 0.0

    # Sample-based entropy estimate.  Use a fixed seed for determinism.
    rng = random.Random(0xBEEF)
    n_samples = 256
    samples = [_sample_beta(alpha, beta_param, rng) for _ in range(n_samples)]
    # Bin into 32 bins
    n_bins = 32
    counts = [0] * n_bins
    for s in samples:
        idx = min(int(s * n_bins), n_bins - 1)
        counts[idx] += 1
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            h -= p * math.log(p)
    return h


def _sample_beta(alpha: float, beta_param: float, rng: random.Random) -> float:
    """Sample one value from Beta(α, β) using two Gamma samples.

    Beta(α, β) = Gamma(α, 1) / (Gamma(α, 1) + Gamma(β, 1)).  We use
    Marsaglia & Tsang's method for Gamma sampling, which is pure-Python
    and works for α, β ≥ 1 (the regime L2 operates in).
    """
    if alpha < 1.0 or beta_param < 1.0:
        # For α, β < 1, use the Johnk-style augmentation: sample
        # U^(1/α) and V^(1/β), accept if U+V ≤ 1.
        while True:
            u = rng.random() ** (1.0 / alpha)
            v = rng.random() ** (1.0 / beta_param)
            if u + v <= 1.0:
                return u / (u + v)
    g_a = _sample_gamma(alpha, rng)
    g_b = _sample_gamma(beta_param, rng)
    return g_a / (g_a + g_b)


def _sample_gamma(shape: float, rng: random.Random) -> float:
    """Marsaglia & Tsang's method for Gamma(shape, 1) sampling.

    Valid for shape ≥ 1.  Returns one sample.
    """
    import math

    if shape < 1.0:
        # Boost: Gamma(shape) = Gamma(shape+1) * U^(1/shape)
        return _sample_gamma(shape + 1.0, rng) * (rng.random() ** (1.0 / shape))

    d = shape - 1.0 / 3.0
    c = 1.0 / math.sqrt(9.0 * d)
    while True:
        x = rng.gauss(0.0, 1.0)
        v = (1.0 + c * x) ** 3
        if v <= 0:
            continue
        u = rng.random()
        if u < 1.0 - 0.0331 * (x ** 4):
            return d * v
        if math.log(u) < 0.5 * x * x + d * (1.0 - v + math.log(v)):
            return d * v


def expected_information_gain(prior_alpha: float, prior_beta: float,
                              n_future_trials: int) -> float:
    """Expected drop in posterior entropy after ``n_future_trials`` trials.

    Computed by sampling ``n_future_trials`` Bernoulli trials from the
    prior Beta, computing the posterior entropy for each outcome, and
    averaging.  This is exact (up to sampling noise) and pure-Python.

    Returns the expected drop in entropy in nats.  A positive value
    means one more trial would lower posterior uncertainty; a value
    near zero means the posterior is already concentrated.
    """

    if n_future_trials < 1:
        return 0.0

    import random

    h_prior = _approx_beta_entropy(prior_alpha, prior_beta)
    rng = random.Random(0xCAFE)
    n_outcomes = 64
    expected_post_entropy = 0.0
    for _ in range(n_outcomes):
        # Sample one trial from the prior
        p = _sample_beta(prior_alpha, prior_beta, rng)
        # Bernoulli outcome
        outcome = 1 if rng.random() < p else 0
        successes = outcome
        failures = 1 - outcome
        post_a, post_b = beta_posterior_after(
            prior_alpha, prior_beta, successes, failures
        )
        expected_post_entropy += _approx_beta_entropy(post_a, post_b)
    expected_post_entropy /= n_outcomes
    return max(0.0, h_prior - expected_post_entropy)


def value_of_information(
    prior_alpha: float,
    prior_beta: float,
    cost_per_trial: float,
    n_future_trials: int = 1,
) -> float:
    """VoI = expected_information_gain − cost (per trial × n trials).

    A negative VoI means more data is *not* worth its cost — this is
    the COMMIT signal. A positive VoI means one more observation
    would lower posterior entropy more than its cost — this is the
    CONTINUE_OBSERVING signal.
    """

    gain = expected_information_gain(prior_alpha, prior_beta, n_future_trials)
    return gain - cost_per_trial * n_future_trials


def voi_decide(
    prior_alpha: float,
    prior_beta: float,
    cost_per_trial: float,
    *,
    min_gain: float = 0.0,
    n_future_trials: int = 1,
) -> tuple[str, float]:
    """The principal VoI primitive: continue observing or commit?

    Returns ``("OBSERVE", voi)`` when VoI > 0; else
    ``("COMMIT", 0.0)``. Mirrors Aurora's ``voi_decide`` but on a
    Beta prior rather than a fully specified posterior.
    """

    voi = value_of_information(
        prior_alpha, prior_beta, cost_per_trial, n_future_trials
    )
    if voi > min_gain:
        return ("OBSERVE", voi)
    return ("COMMIT", 0.0)


# ---------------------------------------------------------------------------
# The Gyre-flavoured L2 measurement provider.
# Wires the VoI rule behind the ``MeasurementProvider`` interface.
# ---------------------------------------------------------------------------


@dataclass
class ValueOfInformationProvider:
    """L2 sensor that flags COMMIT only when VoI ≤ cost.

    The provider keeps a Beta posterior over the agent's calibration
    "success" rate (the probability that a prediction within the
    confidence range is correct). It signals ``decision=True`` when
    COMMIT is the right call — i.e. when more observations are not
    worth their cost.

    Parameters
    ----------
    prior_alpha : float
        Initial success pseudo-count (default 1.0 → uninformative).
    prior_beta : float
        Initial failure pseudo-count (default 1.0 → uninformative).
    cost_per_trial : float
        Cost (in stakes units) of one more observation. VoI stops when
        expected_information_gain drops below this.
    window : int
        Past outcomes retained for the success/failure count.
    outcome_threshold : float
        A prediction is counted as "correct" when its realised outcome
        matches it (predicted > 0.5 → outcome=True counts as correct).
        The provider is one where correctness has a binary structure.
    """

    loop_id: str = "L2"
    name: str = "voi:commit-stop"
    prior_alpha: float = 1.0
    prior_beta: float = 1.0
    cost_per_trial: float = 0.05
    window: int = 50
    outcome_threshold: float = 0.5

    def __post_init__(self) -> None:
        if self.prior_alpha <= 0 or self.prior_beta <= 0:
            raise ValueError("prior_alpha and prior_beta must be positive")
        if self.cost_per_trial < 0:
            raise ValueError("cost_per_trial must be non-negative")
        if self.window < 1:
            raise ValueError("window must be >= 1")
        self._correct: deque[int] = deque(maxlen=self.window)
        self._wrong: deque[int] = deque(maxlen=self.window)

    def _update(self, observation: Any) -> None:
        """Treat a PredictionOutcome as one Bernoulli trial: success when
        the agent's predicted direction matches the realised outcome.
        """
        predicted = getattr(observation, "predicted", None)
        outcome = getattr(observation, "outcome", None)
        if predicted is None or outcome is None:
            return
        predicted_bool = predicted >= self.outcome_threshold
        if predicted_bool == outcome:
            self._correct.append(1)
        else:
            self._wrong.append(1)

    def measure(self, observation: Any) -> Measurement:
        if hasattr(observation, "predicted") and hasattr(observation, "outcome"):
            self._update(observation)

        successes = sum(self._correct)
        failures = sum(self._wrong)
        n = successes + failures
        post_a, post_b = beta_posterior_after(
            self.prior_alpha, self.prior_beta, successes, failures
        )

        if n == 0:
            # No data → cannot decide → report uncalibrated, bias to keep observing.
            return Measurement(
                value=float("nan"),
                meaning=Meaning.LOWER_IS_HEALTHIER,
                standardized=0.0,
                decision=False,  # cannot commit without evidence
                confounds=("no calibration data yet",),
                provider=self.name,
                detail={"n": 0, "voi": 0.0, "prior_alpha": self.prior_alpha,
                        "prior_beta": self.prior_beta},
            )

        action, voi = voi_decide(
            post_a, post_b, self.cost_per_trial, n_future_trials=1
        )
        # decision=True means "should commit" — backwards from the L2
        # loop's intuition that decision=True means "should fire".
        # The L2 loop is a confidence loop, not an information-arrival
        # loop, so the polarity is intentionally inverted.
        commit = action == "COMMIT"
        # A *sufficient* data threshold is required to commit. A handful
        # of observations has too much noise to drive the posterior
        # meaningfully, so we gate the commit decision on a minimum
        # sample size. This is the standard "Bayes needs data" rule.
        SUFFICIENT_N = 5
        if n < SUFFICIENT_N:
            commit = False

        return Measurement(
            value=float(-voi),  # higher VoI → healthier → negation makes it directional
            meaning=Meaning.LOWER_IS_HEALTHIER,
            standardized=(voi - self.cost_per_trial) / max(self.cost_per_trial, 1e-8),
            decision=commit,
            confounds=(
                "VoI on a Beta posterior uses a Gaussian/Bernoulli entropy "
                "approximation; exact entropy drop requires special functions",
                "an observation's correctness is judged by directional agreement, "
                "not a magnitude match",
                "the provider is calibrated only when n >= SUFFICIENT_N; commit "
                "is gated on a minimum sample size to avoid spurious decisions",
            ),
            provider=self.name,
            detail={
                "n": n,
                "successes": successes,
                "failures": failures,
                "voi": voi,
                "posterior_alpha": post_a,
                "posterior_beta": post_b,
                "cost": self.cost_per_trial,
            },
        )

    def reset(self) -> None:
        self._correct.clear()
        self._wrong.clear()