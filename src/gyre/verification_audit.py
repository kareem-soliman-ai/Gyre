"""Human-verification burden reduction, paired with an escape-rate bound.

When a judge panel absorbs part of an outer loop — deciding which work products
a human still has to review — the tempting headline is "we removed 86% of the
review burden". That number alone is worthless, and worse than worthless if
published: a panel that auto-approves everything scores 100%.

The number that makes it a claim is the ESCAPE RATE: how often the
auto-approved stratum contained a defect the panel missed. It cannot be
estimated from the disputed items (those went to a human by construction); it
requires auditing a RANDOM SAMPLE OF THE AUTO-APPROVED items, blind to the
panel's confidence. That is the stratum nobody looks at, because the humans are
already busy with the disputed one.

So this module refuses to report one number without the other. ``AuditResult``
carries both, and ``promotable`` is false whenever the audit is too thin to
support the ceiling — including the degenerate "audited nothing" case, which
returns an upper bound of 1.0 rather than a free pass.

Bounds use the Wilson score interval (one-sided upper, 95%), which behaves
correctly at zero observed escapes where the normal approximation collapses. At
zero escapes it reproduces the familiar rule of three (n=30 -> ~0.10,
n=60 -> ~0.05), which is also what ``audit_sample_size_for`` plans against.

Dependencies: standard library only.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

Z95 = 1.96  # two-sided 95% -> used as the one-sided upper bound multiplier


def burden_reduction(*, total: int, human_reviewed: int) -> float:
    """Fraction of items resolved without a human. Meaningless alone — pair it
    with ``escape_rate_bound`` over the auto-approved stratum."""
    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= human_reviewed <= total:
        raise ValueError("human_reviewed must be between 0 and total")
    return (total - human_reviewed) / total


def wilson_upper(successes: int, n: int, z: float = Z95) -> float:
    """Upper end of the Wilson score interval for a proportion.

    Chosen over the normal approximation because the interesting case here is
    zero observed escapes, where the normal interval degenerates to [0, 0] and
    would license an unbounded claim."""
    if n <= 0:
        return 1.0
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return min(1.0, (centre + margin) / denom)


@dataclass(frozen=True)
class EscapeBound:
    audited: int
    escapes: int
    point: float
    upper: float
    note: str
    claimable: bool = True
    """False when the evidence is too thin to assert a bound at all — no audit,
    or too few independent clusters. Set explicitly rather than derived from
    ``audited``, because a large item count spread over three work products is
    still not enough to bound anything."""


def escape_rate_bound(*, audited: int, escapes: int) -> EscapeBound:
    """Defect rate in the AUTO-APPROVED stratum, with a 95% upper bound.

    ``audited`` is the number of auto-approved items an expert re-checked;
    ``escapes`` is how many of those turned out to be defective. Auditing
    nothing yields upper=1.0 and ``claimable=False`` — the absence of evidence
    is reported as such, never as a pass."""
    if audited < 0 or escapes < 0:
        raise ValueError("audited and escapes must be non-negative")
    if escapes > audited:
        raise ValueError("escapes cannot exceed audited")
    if audited == 0:
        return EscapeBound(
            0, 0, 0.0, 1.0, "no audit performed: escape rate unbounded", claimable=False
        )
    point = escapes / audited
    upper = wilson_upper(escapes, audited)
    note = (
        f"{escapes}/{audited} audited auto-approved items were defective; "
        f"95% upper bound {upper:.3f}"
    )
    return EscapeBound(audited, escapes, point, upper, note)


MIN_CLUSTERS = 10
"""Minimum independent work products before a clustered bound may be asserted at
all. A structural refusal, not a caveat in prose: with fewer clusters the
resampling distribution is too coarse for the interval to mean anything.
(Vendored from Criterion Labs' bootstrap_gate_cis MIN_CLUSTERS precondition.)"""


def cluster_bootstrap_upper(
    clusters: Sequence[Sequence[int]],
    *,
    iterations: int = 2000,
    seed: int = 20260726,
    z: float = Z95,
) -> float:
    """One-sided 95% upper bound on the escape rate, resampling WHOLE CLUSTERS.

    ``clusters`` is one list of 0/1 escape flags per independent unit — a work
    product, a trace, an authored artefact. Audited items from the same unit are
    not independent (one bad spec yields several correlated defects), so
    resampling items individually understates uncertainty. Resampling units with
    replacement keeps the correlation where it belongs.

    Returns the 95th percentile of the bootstrap distribution of the pooled
    rate."""
    if not clusters:
        return 1.0
    rng = random.Random(seed)
    n = len(clusters)
    rates: list[float] = []
    for _ in range(iterations):
        picked = [clusters[rng.randrange(n)] for _ in range(n)]
        items = sum(len(c) for c in picked)
        if not items:
            continue
        rates.append(sum(sum(c) for c in picked) / items)
    if not rates:
        return 1.0
    rates.sort()
    idx = min(len(rates) - 1, int(math.ceil(0.95 * len(rates))) - 1)
    return min(1.0, rates[max(0, idx)])


def escape_rate_bound_clustered(
    clusters: Sequence[Sequence[int]],
    *,
    iterations: int = 2000,
    seed: int = 20260726,
) -> EscapeBound:
    """Escape bound over clustered audit data, refusing thin evidence.

    Use this whenever the audited items group under a smaller number of
    independent sources — which is the normal case for work-product review."""
    for c in clusters:
        for v in c:
            if v not in (0, 1):
                raise ValueError("cluster items must be 0/1 escape flags")
    n_clusters = len(clusters)
    audited = sum(len(c) for c in clusters)
    escapes = sum(sum(c) for c in clusters)
    if n_clusters < MIN_CLUSTERS:
        return EscapeBound(
            audited,
            escapes,
            escapes / audited if audited else 0.0,
            1.0,
            f"only {n_clusters} independent clusters (need >= {MIN_CLUSTERS}): "
            "too few to bound; audit more work products, not more items each",
            claimable=False,
        )
    point = escapes / audited if audited else 0.0
    boot = cluster_bootstrap_upper(clusters, iterations=iterations, seed=seed)
    # A nonparametric cluster bootstrap sees only BETWEEN-cluster variance, so
    # when every cluster looks alike it reports near-zero uncertainty and can
    # come out NARROWER than the item-level interval. For a safety bound that is
    # backwards: clustering may only ever widen. Floor it with the maximally
    # conservative design effect — Wilson at the CLUSTER level, i.e. treating
    # intra-cluster correlation as total.
    cluster_level = wilson_upper(round(point * n_clusters), n_clusters)
    upper = max(boot, cluster_level)
    return EscapeBound(
        audited,
        escapes,
        point,
        upper,
        f"{escapes}/{audited} escapes across {n_clusters} clusters; "
        f"95% upper bound {upper:.3f} (bootstrap {boot:.3f}, "
        f"cluster-level Wilson floor {cluster_level:.3f})",
    )


def audit_sample_size_for(ceiling: float, z: float = Z95) -> int:
    """How many auto-approved items to audit to support a given escape ceiling,
    assuming zero escapes are found.

    Solves the SAME bound the promotion gate enforces, rather than the folk
    rule of three (n ≈ 3/ceiling). At zero escapes the Wilson upper bound
    reduces to ``z²/(n + z²)``, so ``n = z²(1 − ceiling)/ceiling``. That is
    strictly larger than 3/ceiling — 35 rather than 30 for a 10% ceiling, 73
    rather than 60 for 5% — and using the folk number would plan an audit the
    gate then rejects.

    This is the number that actually sets claim strength, not the corpus size.
    Finding an escape means you need more, not fewer."""
    if not 0 < ceiling < 1:
        raise ValueError("ceiling must be in (0, 1)")
    return math.ceil(z**2 * (1 - ceiling) / ceiling)


@dataclass(frozen=True)
class AuditResult:
    """Burden reduction and escape bound, reported together or not at all."""

    total: int
    human_reviewed: int
    burden_reduction: float
    escape: EscapeBound
    ceiling: float

    @classmethod
    def build(
        cls,
        *,
        total: int,
        human_reviewed: int,
        audited: int,
        escapes: int,
        ceiling: float,
    ) -> "AuditResult":
        return cls(
            total=total,
            human_reviewed=human_reviewed,
            burden_reduction=burden_reduction(total=total, human_reviewed=human_reviewed),
            escape=escape_rate_bound(audited=audited, escapes=escapes),
            ceiling=ceiling,
        )

    @property
    def promotable(self) -> bool:
        """True only when the audited escape bound clears the pre-registered
        ceiling. A large burden reduction never compensates for a thin audit."""
        return self.escape.claimable and self.escape.upper <= self.ceiling

    @property
    def blocking_reason(self) -> str:
        if self.promotable:
            return ""
        if not self.escape.claimable:
            return "no audit of the auto-approved stratum: the reduction is unclaimable"
        needed = audit_sample_size_for(self.ceiling)
        return (
            f"escape bound {self.escape.upper:.3f} exceeds ceiling {self.ceiling:.3f}; "
            f"audit at least {needed} auto-approved items (found {self.escape.escapes} "
            f"escapes in {self.escape.audited})"
        )

    def summary(self) -> str:
        verdict = "PROMOTABLE" if self.promotable else "NOT PROMOTABLE"
        line = (
            f"burden reduction {self.burden_reduction:.1%} "
            f"({self.human_reviewed}/{self.total} items reached a human); "
            f"escape rate {self.escape.point:.1%} "
            f"(audited {self.escape.audited} auto-approved, "
            f"{self.escape.escapes} defective, 95% upper {self.escape.upper:.3f} "
            f"vs ceiling {self.ceiling:.3f}) — {verdict}"
        )
        if not self.promotable:
            line += f"\n  blocked: {self.blocking_reason}"
        return line
