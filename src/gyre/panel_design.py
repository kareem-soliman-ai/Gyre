"""What a verification panel must achieve — computed before spending anything.

A closed-form design calculator (no model calls, no data) for the outer loop.
Given the defect base rate in a stream of work products and a panel's
sensitivity and specificity, everything downstream follows analytically:

- how much human burden the panel removes,
- what fraction of the AUTO-APPROVED stratum still contains a defect,
- and how many auto-approved items must then be audited to bound that.

This exists because the alternative — running judges and seeing what happens —
costs money to learn things arithmetic already knows. Two facts that fall out
immediately and are easy to get wrong by intuition:

1. **A panel that never flags anything reports 100% burden reduction and an
   escape rate equal to the base rate.** Burden reduction alone cannot
   distinguish a perfect panel from a useless one.
2. **The escape rate is not comparable across operating points.** Sensitivity
   alone fixes which defects are missed; specificity only moves the
   auto-approved denominator. So a trigger-happy panel (low specificity) posts
   a WORSE escape rate than a selective one at identical sensitivity, having
   missed exactly the same defects — and a panel can improve its escape rate by
   flagging more clean work, which helps nobody. ``missed_per_100`` is
   invariant to specificity and is the number to compare panels on; the escape
   rate is what you must bound for a given deployment, not a league table.

The closed-form grid makes the metric-choice problem concrete: at 1% prevalence
Cohen's kappa
reads 0.14 where Gwet's AC1 reads 0.89 — a metric-choice argument settled for
$0 before any judge ran.

Dependencies: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from gyre.verification_audit import audit_sample_size_for


def _check(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


@dataclass(frozen=True)
class PanelOperatingPoint:
    """One (prevalence, sensitivity, specificity) cell and its consequences."""

    prevalence: float
    sensitivity: float
    specificity: float
    flagged_fraction: float
    auto_approved_fraction: float
    escape_rate: float
    missed_per_100: float

    @property
    def burden_reduction(self) -> float:
        """Fraction of items resolved without a human = the auto-approved share."""
        return self.auto_approved_fraction

    def audit_needed(self, *, ceiling: float) -> int | None:
        """Auto-approved items to audit to bound the escape rate at ``ceiling``.

        Returns None when the ceiling sits at or below the escape rate this
        operating point actually produces — no amount of auditing demonstrates a
        bound the panel does not meet. That is a design answer, not a failure:
        it says improve the panel, do not buy more audit."""
        if self.escape_rate >= ceiling:
            return None
        return audit_sample_size_for(ceiling)

    def summary(self) -> str:
        return (
            f"prev {self.prevalence:.0%} sens {self.sensitivity:.0%} "
            f"spec {self.specificity:.0%} -> burden reduction "
            f"{self.burden_reduction:.1%}, escape rate {self.escape_rate:.2%} "
            f"({self.missed_per_100:.2f} defects missed per 100 items)"
        )


def operating_point(
    *, prevalence: float, sensitivity: float, specificity: float
) -> PanelOperatingPoint:
    """Derive the consequences of a panel operating point, analytically.

    ``sensitivity`` is P(flag | defective), ``specificity`` is P(no flag | clean).
    Flagged items go to a human; everything else is auto-approved."""
    _check("prevalence", prevalence)
    _check("sensitivity", sensitivity)
    _check("specificity", specificity)

    true_positive = prevalence * sensitivity
    false_negative = prevalence * (1 - sensitivity)
    false_positive = (1 - prevalence) * (1 - specificity)
    true_negative = (1 - prevalence) * specificity

    flagged = true_positive + false_positive
    auto = false_negative + true_negative
    escape = false_negative / auto if auto > 0 else 0.0

    return PanelOperatingPoint(
        prevalence=prevalence,
        sensitivity=sensitivity,
        specificity=specificity,
        flagged_fraction=flagged,
        auto_approved_fraction=auto,
        escape_rate=escape,
        missed_per_100=false_negative * 100,
    )


def escape_frontier(
    *,
    prevalence: float,
    sensitivities: Sequence[float],
    specificity: float,
) -> list[PanelOperatingPoint]:
    """The burden/escape trade curve across a sensitivity sweep.

    This is the product artefact: an engineer does not buy "the panel", they buy
    a point on this curve. Read it to find the cheapest sensitivity that meets
    the escape ceiling you can defend."""
    return [
        operating_point(
            prevalence=prevalence, sensitivity=s, specificity=specificity
        )
        for s in sensitivities
    ]
