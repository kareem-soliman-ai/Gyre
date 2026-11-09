"""Marginal Value Theorem (MVT) sensor for L1 (machinery A4 from the taxonomy).

The MVT (Charnov 1976) answers a deceptively simple question: when should an
agent LEAVE the patch it is currently exploiting? The answer is one of the
cleanest in optimal-foraging theory:

    Leave when the marginal gain from the current patch drops below the
    long-run average gain across the environment.

Mathematically::

    threshold = environment_gain_rate + switch_cost_rate
    LEAVE if  marginal_gain_rate < threshold  (and after minimum dwell)
    STAY  otherwise.

Why MVT for L1
--------------
An L1 loop's question is "is the loop still generating information?" The
naive reading compares each step's gain to a fixed threshold (a fixed floor,
a z-score, a novelty score). The MVT reading compares each step's marginal
gain to the *running average gain across the episode*.  The two coincide
when the agent has been productive the whole episode, and diverge precisely
when a productive-prefix pattern has tipped into a depleted tail — i.e. the
exact time the loop should reroute. The MVT sensor is, by construction,
the right sensor for the depletion morphology Gyre's plant cells model.

Provenance
----------
This implementation adapts an earlier marginal-value prototype. The shape and
semantics are preserved; what changes is the *output*: the original module returned a
``MarginalValueDecision`` for a dispatch layer to consume, while this one
returns a ``Measurement`` so a ``RuminationMonitor`` can drive it
transparently.  The controller-side decision is unchanged: STAY <-> CONTINUE,
LEAVE <-> PLATEAU.

Standard library only.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import isfinite
from typing import Any

from gyre.loops.rumination import IterationObservation
from gyre.measurement import Meaning, Measurement


# ---------------------------------------------------------------------------
# Snapshot data structures — the MVT's domain model.
# Kept explicit so downstream code can construct ``MarginalValueContext``s
# directly.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarginalValueContext:
    """Domain-estimated rates required by the MVT patch-leaving rule.

    All rates are non-negative; ``dwell_steps`` is the steps spent in
    the current patch; ``min_dwell_steps`` is the minimum dwell before
    LEAVE is allowed (Charnov's travel-cost analogue).
    """

    marginal_gain_rate: float
    environment_gain_rate: float
    dwell_steps: int
    min_dwell_steps: int = 0
    switch_cost_rate: float = 0.0

    def __post_init__(self) -> None:
        for name in ("marginal_gain_rate", "environment_gain_rate", "switch_cost_rate"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.dwell_steps < 0 or self.min_dwell_steps < 0:
            raise ValueError("dwell steps must be non-negative")


@dataclass(frozen=True)
class MarginalValueDecision:
    """Auditable leave/stay proposal with no dispatch authority."""

    action: str  # "stay" | "leave"
    threshold: float
    reasons: tuple[str, ...]


def marginal_value_decision(context: MarginalValueContext) -> MarginalValueDecision:
    """The actual MVT rule. Pure function; no state.

    ``threshold = environment_gain_rate + switch_cost_rate``. The patch
    is left once the marginal gain drops below this threshold AND the
    minimum dwell has been served.
    """
    threshold = context.environment_gain_rate + context.switch_cost_rate
    if context.dwell_steps < context.min_dwell_steps:
        return MarginalValueDecision("stay", threshold, ("minimum_dwell",))
    if context.marginal_gain_rate < threshold:
        return MarginalValueDecision("leave", threshold, ("marginal_gain_depleted",))
    return MarginalValueDecision("stay", threshold, ("marginal_gain_sufficient",))


# ---------------------------------------------------------------------------
# The Gyre-flavoured measurement provider.
# ---------------------------------------------------------------------------


@dataclass
class MvtRuminationSensor:
    """L1 rumination sensor built on the Marginal Value Theorem.

    Tracks a running "environment" gain rate (the long-run mean across the
    episode) and a "current marginal" gain rate (a rolling mean over a
    short window). Fires when the marginal rate drops below the environment
    rate, *after* the configured minimum dwell.

    Parameters
    ----------
    short_window : int
        Window length for the "marginal" (current-patch) gain estimate.
        Small = reactive; large = smoothed.
    long_window : int
        Window length for the "environment" (habitat-average) gain estimate.
        Should be much larger than ``short_window`` for the threshold to
        be meaningful — the MVT only earns its keep when the two views
        disagree.
    min_dwell : int
        Minimum steps before LEAVE is allowed. Translates Charnov's
        travel-cost into Gyre's iterate-until-novel signal.
    burnin : int
        Observations before producing a calibrated decision. During
        burnin the habitat-average is still forming and firing would be
        a false-alarm risk.
    """

    loop_id: str = "L1"
    name: str = "mvt:rumination"
    short_window: int = 3
    long_window: int = 30
    min_dwell: int = 2
    burnin: int = 5

    def __post_init__(self) -> None:
        if self.short_window < 1:
            raise ValueError("short_window must be >= 1")
        if self.long_window <= self.short_window:
            raise ValueError("long_window must exceed short_window")
        if self.min_dwell < 0:
            raise ValueError("min_dwell must be >= 0")
        if self.burnin < 0:
            raise ValueError("burnin must be >= 0")
        self._gains: deque[float] = deque(maxlen=self.long_window)
        self._dwell = 0
        self._prior_artifact: str | None = None  # sensor-level prior for lexical gain proxy

    def _gain_for(self, observation: Any) -> float:
        """Per-observation gain: ``1 - SequenceMatcher.ratio`` on the
        artifact text.  For L1 the cell wants a per-step "did the agent
        add information" reading, and this is the standard lexical proxy.
        A calibrated provider can override by wrapping the sensor with
        a numeric value first; for sensors that return text artifacts
        (the common case for ``IterationObservation``) this lexical
        proxy is the right default. The confounds field tells downstream
        loops it is lexical, so any value-gap compared against a
        semantic provider is honest.
        """
        import difflib

        if not hasattr(observation, "artifact"):
            return 1.0  # first observation, maximised gain by convention
        if self._prior_artifact is None:
            return 1.0
        ratio = difflib.SequenceMatcher(
            None, self._prior_artifact, observation.artifact
        ).ratio()
        return 1.0 - ratio

    def measure(self, observation: Any) -> Measurement:
        # If the observation carries a numeric value attribute (e.g. from
        # another sensor treating this sensor as a downstream), use it.
        if hasattr(observation, "value") and observation.value is not None:
            gain = float(observation.value)
        else:
            gain = self._gain_for(observation)

        # Update the sensor-level prior for the lexical gain proxy.
        # Tracked at the sensor level (not on each observation) so that
        # the prior persists across new ``IterationObservation`` instances.
        if hasattr(observation, "artifact"):
            self._prior_artifact = observation.artifact

        # On the very first observation there is no prior artifact.
        # The "gain = 1.0" convention would inflate the habitat estimate
        # by 25%+ once it ages out, biasing the rule. We treat the first
        # observation as a cold-start sample without committing it to
        # either buffer; both windows start empty and grow together.
        is_first = len(self._gains) == 0 and self._dwell == 0
        if not is_first:
            self._gains.append(gain)
        self._dwell += 1

        n = len(self._gains)
        if n <= self.burnin:
            return Measurement(
                value=gain,
                meaning=Meaning.HIGHER_IS_HEALTHIER,
                standardized=0.0,
                decision=False,
                confounds=("MVT baseline still forming",),
                provider=self.name,
                detail={
                    "n": n,
                    "burnin": True,
                    "dwell": self._dwell,
                    "marginal": self._marginal_rate(),
                    "environment": self._environment_rate(),
                    "threshold": self._threshold(),
                },
            )

        marginal = self._marginal_rate()
        habitat = self._environment_rate()
        threshold = self._threshold()

        ctx = MarginalValueContext(
            marginal_gain_rate=marginal,
            environment_gain_rate=habitat,
            dwell_steps=self._dwell,
            min_dwell_steps=self.min_dwell,
        )
        decision = marginal_value_decision(ctx)
        leave = decision.action == "leave"

        return Measurement(
            value=gain,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            standardized=(marginal - threshold) / max(abs(threshold), 1e-8),
            decision=leave,
            confounds=(
                "MVT compares marginal-vs-environment rates, not raw levels",
                "lexical gain proxy ignores semantic distinction between rewordings",
                "baseline is shaped by whatever the current episode's gains have been",
            ),
            provider=self.name,
            detail={
                "marginal": marginal,
                "environment": habitat,
                "threshold": threshold,
                "dwell": self._dwell,
                "reasons": decision.reasons,
            },
        )

    # ----- internals ----------------------------------------------

    def _marginal_rate(self) -> float:
        """Recent-window mean gain."""
        if not self._gains:
            return 0.0
        window = list(self._gains)[-self.short_window:]
        return sum(window) / len(window)

    def _environment_rate(self) -> float:
        """Habitat-average gain (across the entire window)."""
        if not self._gains:
            return 0.0
        return sum(self._gains) / len(self._gains)

    def _threshold(self) -> float:
        return self._environment_rate()

    def reset(self) -> None:
        self._gains.clear()
        self._dwell = 0
        self._prior_artifact = None
