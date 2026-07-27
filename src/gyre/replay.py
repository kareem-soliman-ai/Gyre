"""Exact-counterfactual replay: what acting on a sensor would actually have cost.

Detection accuracy is evidence about a sensor. It is not evidence that acting on
the sensor helps. Closing that gap normally requires either a live A/B test or a
simulator, and a simulator can only tell you about the world you built.

There is a third option that most people miss, and it is exact. On a run that
**failed**, stopping early costs you nothing: the run failed anyway, so every
step after the intervention point was pure waste, and the saving is a fact about
the log rather than an assumption about a counterfactual world. The only place
an assumption is needed is on runs that **succeeded**, where stopping early
forfeits the success — and that is charged at full price, which is the
conservative direction.

So, over a corpus of logged runs with outcomes and costs:

    net value = sum(cost saved on failed runs) - value_of_success * successes_lost

``value_of_success`` is the one free parameter, and it is not a nuisance: it is
the cost regime. A cheap task where another attempt costs pennies and a run
where a lost success means a missed deadline are different worlds, and a policy
that only wins in one of them is not robust. Sweeping it produces the trade
curve, and the honest headline is worst-case regret across the sweep rather than
the best number in the regime you happened to pick.

Works on any corpus you can express as ``ReplayRun``: ordered step texts, a
boolean outcome, and a cost. If you have logs from your own agents with a
verifier, a test suite, or a human acceptance decision, you have what this needs.

Dependencies: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from gyre.loops._policy import ThresholdRequired, trigger_state
from gyre.loops.rumination import IterationObservation
from gyre.measurement import MeasurementProvider


@dataclass
class ReplayRun:
    """One logged agent run with an independently determined outcome."""

    steps: Sequence[str]
    succeeded: bool
    cost: float
    run_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayResult:
    policy: str
    value_of_success: float
    n_runs: int
    n_failed: int
    cost_total: float
    cost_saved: float
    successes_kept: int
    successes_lost: int
    net_value: float
    fired_on_failed: int
    fired_on_passed: int
    per_run: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.policy}: saved {self.cost_saved:.3f} of {self.cost_total:.3f} "
            f"({self.cost_saved / self.cost_total:.1%}) on failed runs; "
            f"truncated {self.successes_lost}/{self.successes_kept + self.successes_lost} "
            f"successes; net {self.net_value:+.3f} at value_of_success="
            f"{self.value_of_success:g}"
        )


def _onset(provider: MeasurementProvider, steps: Sequence[str],
           patience: int, threshold: float | None) -> int | None:
    """First step index at which the policy would intervene, or None."""
    streak = 0
    for i, text in enumerate(steps):
        m = provider.measure(IterationObservation(artifact=text, index=i))
        try:
            fired = trigger_state(m, threshold=threshold)
        except ThresholdRequired:
            fired = False
        streak = streak + 1 if fired else 0
        if streak >= patience:
            return i
    return None


def replay_policy(
    runs: Sequence[ReplayRun],
    provider_factory: Callable[[], MeasurementProvider],
    *,
    value_of_success: float,
    patience: int = 1,
    threshold: float | None = None,
    policy_name: str = "",
) -> ReplayResult:
    """Replay a corpus under one sensor-driven stop policy.

    Cost is prorated by step position, which is the honest default when the log
    records a single run-level cost: the alternative, assuming the tail is
    disproportionately expensive, would flatter the result."""
    if not runs:
        raise ValueError("no runs to replay")

    probe = provider_factory()
    name = policy_name or f"{probe.name}(patience={patience})"

    cost_total = cost_saved = 0.0
    kept = lost = fired_f = fired_p = 0
    per_run: list[dict[str, Any]] = []

    for run in runs:
        n = len(run.steps)
        cost_total += run.cost
        onset = _onset(provider_factory(), run.steps, patience, threshold) if n else None

        truncated = onset is not None and onset < n - 1
        saved = run.cost * (n - onset - 1) / n if truncated else 0.0

        if run.succeeded:
            if truncated:
                lost += 1
            else:
                kept += 1
            if onset is not None:
                fired_p += 1
        else:
            # the run failed regardless, so the tail was pure waste: exact saving
            cost_saved += saved
            if onset is not None:
                fired_f += 1

        per_run.append(
            {
                "run_id": run.run_id,
                "succeeded": run.succeeded,
                "n_steps": n,
                "onset": onset,
                "cost": run.cost,
                "cost_saved": round(saved, 6) if not run.succeeded else 0.0,
                "success_lost": bool(run.succeeded and truncated),
            }
        )

    return ReplayResult(
        policy=name,
        value_of_success=value_of_success,
        n_runs=len(runs),
        n_failed=sum(1 for r in runs if not r.succeeded),
        cost_total=cost_total,
        cost_saved=cost_saved,
        successes_kept=kept,
        successes_lost=lost,
        net_value=cost_saved - value_of_success * lost,
        fired_on_failed=fired_f,
        fired_on_passed=fired_p,
        per_run=per_run,
    )


def net_value_curve(
    runs: Sequence[ReplayRun],
    provider_factory: Callable[[], MeasurementProvider],
    *,
    values: Sequence[float],
    patience: int = 1,
    threshold: float | None = None,
    policy_name: str = "",
) -> list[ReplayResult]:
    """The policy's net value across cost regimes.

    A policy that wins at ``value_of_success = 0`` and collapses at high values
    is not a good policy, it is a policy that was evaluated in a convenient
    regime. Read the whole curve."""
    return [
        replay_policy(
            runs,
            provider_factory,
            value_of_success=v,
            patience=patience,
            threshold=threshold,
            policy_name=policy_name,
        )
        for v in values
    ]


def worst_case_regret(curves: dict[str, list[ReplayResult]]) -> dict[str, float]:
    """Per policy, the worst shortfall against the best policy in any regime.

    This is the robustness statistic. A policy with low worst-case regret is one
    you can deploy without knowing which regime you are in — which is the actual
    situation, because you usually do not."""
    if not curves:
        return {}
    n = len(next(iter(curves.values())))
    best_per_regime = [
        max(c[i].net_value for c in curves.values()) for i in range(n)
    ]
    return {
        name: max(best_per_regime[i] - c[i].net_value for i in range(n))
        for name, c in curves.items()
    }
