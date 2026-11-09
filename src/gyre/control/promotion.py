"""Evidence receipts that govern whether a controller may be promoted.

This develops a strategy-promotion gate from earlier uncertainty-control
experiments. It is
deliberately separate from controller dispatch: a report can say that a
strategy is eligible, but cannot activate it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationReceipt:
    """One pre-declared, independently evaluated strategy comparison."""

    strategy_id: str
    domain_family: str
    endpoint_id: str
    effect_lower_bound: float
    harm_delta_upper_bound: float
    validated_counterfactual: bool
    independent_evaluation: bool
    matched_budget: bool
    strong_baseline: bool

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        if not self.domain_family.strip():
            raise ValueError("domain_family must be non-empty")
        if not self.endpoint_id.strip():
            raise ValueError("endpoint_id must be non-empty")
        for field_name in ("effect_lower_bound", "harm_delta_upper_bound"):
            if not math.isfinite(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be finite")


@dataclass(frozen=True)
class PromotionReport:
    """Eligibility evidence only; this object has no dispatch authority."""

    strategy_id: str
    qualifying_domain_families: tuple[str, ...]
    eligible: bool
    reasons: tuple[str, ...]


def assess_strategy_promotion(
    strategy_id: str,
    receipts: tuple[EvaluationReceipt, ...],
    *,
    required_domains: int = 2,
) -> PromotionReport:
    """Require replicated benefit, no harm regression, and fair comparison."""

    if not strategy_id.strip():
        raise ValueError("strategy_id must be non-empty")
    if required_domains < 2:
        raise ValueError("required_domains must be at least two")

    relevant = tuple(r for r in receipts if r.strategy_id == strategy_id)
    independently_validated = tuple(
        r
        for r in relevant
        if r.validated_counterfactual
        and r.independent_evaluation
        and r.matched_budget
        and r.strong_baseline
    )
    qualifying = tuple(
        r
        for r in independently_validated
        if r.effect_lower_bound > 0 and r.harm_delta_upper_bound <= 0
    )
    families = tuple(sorted({r.domain_family for r in qualifying}))
    reasons: list[str] = []
    if not independently_validated:
        reasons.append("no_independent_matched_counterfactual_receipts")
    elif not qualifying:
        reasons.append("no_positive_harmless_receipts")
    if len(families) < required_domains:
        reasons.append("insufficient_independent_domains")
    return PromotionReport(
        strategy_id=strategy_id,
        qualifying_domain_families=families,
        eligible=not reasons,
        reasons=tuple(reasons),
    )


__all__ = [
    "EvaluationReceipt",
    "PromotionReport",
    "assess_strategy_promotion",
]
