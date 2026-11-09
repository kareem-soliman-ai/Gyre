"""Outcome-calibrated reliability for measurement sources.

This public implementation estimates whether a named source has predicted
resolved outcomes
correctly. It does not infer intrinsic trust, inspect an unresolved claim, or
grant action authority.

Earlier experiments found the instrumentation useful while the controller that
acted on it failed its promotion gate. Gyre therefore ships only the passive
registry and lagged shift diagnostic here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReliabilityEstimate:
    """Posterior-mean correctness estimate and its evidence count."""

    source_id: str
    mean: float
    outcomes: int
    correct: int
    incorrect: int

    @property
    def is_empirical(self) -> bool:
        return self.outcomes > 0


@dataclass
class OutcomeReliabilityRegistry:
    """Beta-Bernoulli reliability updated only by resolved outcomes."""

    alpha_prior: float = 1.0
    beta_prior: float = 1.0
    _counts: dict[str, list[int]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.alpha_prior) or self.alpha_prior <= 0:
            raise ValueError("alpha_prior must be finite and positive")
        if not math.isfinite(self.beta_prior) or self.beta_prior <= 0:
            raise ValueError("beta_prior must be finite and positive")

    def record_outcome(self, source_id: str, *, correct: bool) -> None:
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        counts = self._counts.setdefault(source_id, [0, 0])
        counts[0 if correct else 1] += 1

    def estimate(self, source_id: str) -> ReliabilityEstimate:
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        correct, incorrect = self._counts.get(source_id, [0, 0])
        mean = (self.alpha_prior + correct) / (
            self.alpha_prior + self.beta_prior + correct + incorrect
        )
        return ReliabilityEstimate(
            source_id=source_id,
            mean=mean,
            outcomes=correct + incorrect,
            correct=correct,
            incorrect=incorrect,
        )


@dataclass(frozen=True)
class SourceShiftDiagnostic:
    """Lagged warning that a source's resolved-outcome reliability deteriorated."""

    source_id: str
    baseline_reliability: float
    recent_reliability: float
    baseline_outcomes: int
    recent_outcomes: int
    warning: bool


class SourceShiftMonitor:
    """Compare a recent resolved-outcome window with preceding history."""

    def __init__(
        self,
        *,
        recent_window: int = 5,
        min_baseline_outcomes: int = 5,
        deterioration_threshold: float = 0.35,
    ) -> None:
        if recent_window <= 0:
            raise ValueError("recent_window must be positive")
        if min_baseline_outcomes <= 0:
            raise ValueError("min_baseline_outcomes must be positive")
        if not 0 < deterioration_threshold <= 1:
            raise ValueError("deterioration_threshold must be in (0, 1]")
        self.recent_window = recent_window
        self.min_baseline_outcomes = min_baseline_outcomes
        self.deterioration_threshold = deterioration_threshold
        self._history: dict[str, list[bool]] = {}

    def record_outcome(self, source_id: str, *, correct: bool) -> None:
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        self._history.setdefault(source_id, []).append(correct)

    def diagnostic(self, source_id: str) -> SourceShiftDiagnostic:
        history = self._history.get(source_id, [])
        if len(history) <= self.recent_window:
            return SourceShiftDiagnostic(
                source_id, 0.5, 0.5, 0, len(history), False
            )
        baseline = history[: -self.recent_window]
        recent = history[-self.recent_window :]
        baseline_reliability = sum(baseline) / len(baseline)
        recent_reliability = sum(recent) / len(recent)
        warning = (
            len(baseline) >= self.min_baseline_outcomes
            and baseline_reliability - recent_reliability
            >= self.deterioration_threshold
        )
        return SourceShiftDiagnostic(
            source_id=source_id,
            baseline_reliability=baseline_reliability,
            recent_reliability=recent_reliability,
            baseline_outcomes=len(baseline),
            recent_outcomes=len(recent),
            warning=warning,
        )


__all__ = [
    "ReliabilityEstimate",
    "OutcomeReliabilityRegistry",
    "SourceShiftDiagnostic",
    "SourceShiftMonitor",
]
