"""Non-compensatory verdict ceiling: a demonstrated defect cannot be outvoted.

For outer-loop verification, a panel's verdict on a work product must not be an
average. Averaging lets five satisfied seats bury one seat's demonstration that
the spec approves its own output. So:

- **Poles stay separated.** Positive indicators (a baseline is named, a
  criterion is falsifiable) and negative indicators (silent degradation,
  self-approval) are counted independently and NEVER netted. A feature-rich
  spec with a live defect and a thin clean one must not collapse to the same
  number.
- **The verdict IS the worst risk's ceiling.** BLOCKER caps at 0.0 — fail
  closed. Good practice elsewhere cannot buy it back.
- **A risk is a violation PRESENT or an applicable protection ABSENT.** The
  hardcoded-secret case has nothing firing; a protection is simply missing.
  Treating only "present violations" as risks silently passes it.
- **Coverage is reported alongside, never folded in.** An earlier implementation
  took ``min(capability_credit, ceiling)``; a lone MINOR gap with
  no other coverage then scored BELOW an artefact carrying a live critical
  exploit — a straight inversion. ``test_the_min_inversion_bug_cannot_recur``
  is the regression guard so this is not rediscovered.
- **Unevidenced and unqualified findings cannot gate.** A seat asserting a
  BLOCKER without a verbatim quote has made a claim, not a demonstration; and
  an indicator that has not itself passed qualification may never fail a work
  product. Both are reported, neither blocks.

Dependencies: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class Severity(Enum):
    """Severity ordinals double, so one step up outweighs any number below it."""

    NONE = 0
    INFO = 1
    MINOR = 2
    MAJOR = 4
    CRITICAL = 8
    BLOCKER = 16


_CEILINGS: tuple[tuple[int, float], ...] = (
    (16, 0.0),
    (8, 0.2),
    (4, 0.5),
    (2, 0.75),
    (1, 0.9),
)


def ceiling_for(severity: Severity) -> float:
    """The highest verdict score still available once a risk of this severity is
    demonstrated. BLOCKER -> 0.0 (fail closed)."""
    if not isinstance(severity, Severity):
        raise ValueError(f"unknown severity: {severity!r}")
    for threshold, ceiling in _CEILINGS:
        if severity.value >= threshold:
            return ceiling
    return 1.0


@dataclass
class IndicatorFinding:
    """One seat's call on one indicator for one work product."""

    indicator: str
    negative: bool
    present: bool
    severity: Severity = Severity.MAJOR
    evidence: str = ""
    qualified: bool = True

    @property
    def is_risk(self) -> bool:
        """A risk is a negative indicator PRESENT, or a positive one ABSENT.

        The asymmetry is load-bearing: 'the spec names no baseline' is a risk
        even though no rule 'fired'."""
        return self.present if self.negative else not self.present

    @property
    def can_gate(self) -> bool:
        """Only an evidenced finding on a qualified indicator may cap a verdict."""
        return self.qualified and bool(self.evidence.strip())


@dataclass
class Verdict:
    score: float
    acceptable: bool
    capabilities_present: int
    violations_present: int
    coverage: float
    worst_severity: Severity
    blocking_indicators: tuple[str, ...] = field(default_factory=tuple)
    unevidenced: tuple[str, ...] = field(default_factory=tuple)
    ignored_unqualified: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""

    def summary(self) -> str:
        if self.note:
            return self.note
        parts = [
            f"score {self.score:.2f} ({'ACCEPT' if self.acceptable else 'REJECT'})",
            f"{self.capabilities_present} capabilities present",
            f"{self.violations_present} violations present",
            f"coverage {self.coverage:.0%}",
        ]
        if self.blocking_indicators:
            parts.append("blocked by " + ", ".join(self.blocking_indicators))
        if self.unevidenced:
            parts.append("unevidenced (ignored): " + ", ".join(self.unevidenced))
        if self.ignored_unqualified:
            parts.append("unqualified (ignored): " + ", ".join(self.ignored_unqualified))
        return "; ".join(parts)


def verdict_from_findings(
    findings: Sequence[IndicatorFinding], *, accept_at: float = 1.0
) -> Verdict:
    """Combine indicator findings into a non-compensatory verdict.

    ``accept_at`` is the score a work product must reach to be acceptable
    without a human; it defaults to 1.0 (no demonstrated risk at all), which is
    the right default for an auto-approval gate."""
    if not findings:
        return Verdict(
            score=0.0,
            acceptable=False,
            capabilities_present=0,
            violations_present=0,
            coverage=0.0,
            worst_severity=Severity.NONE,
            note="no findings: nothing was actually checked, so nothing is approved",
        )

    positives = [f for f in findings if not f.negative]
    capabilities_present = sum(1 for f in positives if f.present)
    violations_present = sum(1 for f in findings if f.negative and f.present)
    coverage = capabilities_present / len(positives) if positives else 0.0

    risks = [f for f in findings if f.is_risk]
    gating = [f for f in risks if f.can_gate]
    unevidenced = tuple(
        f.indicator for f in risks if f.qualified and not f.evidence.strip()
    )
    ignored = tuple(f.indicator for f in risks if not f.qualified)

    worst = Severity.NONE
    for f in gating:
        if f.severity.value > worst.value:
            worst = f.severity
    # The verdict IS the ceiling. Coverage rides alongside and is never min'd or
    # multiplied in — see the module docstring for the inversion this prevents.
    score = ceiling_for(worst)
    blocking = tuple(f.indicator for f in gating if f.severity is worst) if worst is not Severity.NONE else ()

    return Verdict(
        score=score,
        acceptable=score >= accept_at,
        capabilities_present=capabilities_present,
        violations_present=violations_present,
        coverage=coverage,
        worst_severity=worst,
        blocking_indicators=blocking,
        unevidenced=unevidenced,
        ignored_unqualified=ignored,
    )
