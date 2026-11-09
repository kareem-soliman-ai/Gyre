"""Loop-health scoring: one call that turns a trace into a loop-health verdict.

This is Gyre's integration surface. A caller (a control plane, an agent's MCP
tool, or a loop-economics dashboard) hands over the ordered steps of an agent's
loop, either tool-call steps OR reasoning/thinking segments, and gets back a
structured verdict: is the loop still paying, when did it stop adding information,
and how many tokens are at risk in the plateaued tail. Rumination does not need
tool calls; it happens in the thinking stream too, which is where the tokens are
pure cost.

It composes the L1 rumination controller with a ``MeasurementProvider``. The public
default is a naive sensor (honest but crude); pass a qualified provider and the
verdict sharpens without the caller changing a line. That separation is the whole
architecture: a controller is only as good as its sensor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from gyre.interfaces import ExitReason
from gyre.loops.rumination import IterationObservation, RuminationMonitor
from gyre.measurement import MeasurementProvider


@dataclass
class StepHealth:
    index: int
    ruminating: bool
    est_tokens: int


@dataclass
class LoopHealthResult:
    """A loop-health verdict over one trace. JSON-safe via ``to_dict``."""

    ruminating: bool
    onset_step: int | None
    n_steps: int
    rumination_fraction: float
    tokens_total: int
    tokens_at_risk: int
    exit_reason: str
    provider: str
    steps: list[StepHealth] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruminating": self.ruminating,
            "onset_step": self.onset_step,
            "n_steps": self.n_steps,
            "rumination_fraction": round(self.rumination_fraction, 3),
            "tokens_total": self.tokens_total,
            "tokens_at_risk": self.tokens_at_risk,
            "exit_reason": self.exit_reason,
            "provider": self.provider,
            "steps": [
                {"index": s.index, "ruminating": s.ruminating, "est_tokens": s.est_tokens}
                for s in self.steps
            ],
        }


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~1.3 tokens/word). Callers with a real tokenizer can
    override the accounting; this keeps the default dependency-free."""
    return max(1, round(len(text.split()) * 1.3))


def _to_observation(step: Any, index: int) -> IterationObservation:
    if isinstance(step, IterationObservation):
        return step
    if isinstance(step, dict):
        return IterationObservation(
            artifact=str(step.get("artifact", step.get("text", ""))),
            error=step.get("error"),
            index=index,
        )
    return IterationObservation(artifact=str(step), index=index)


def score_loop_health(
    steps: Sequence[Any],
    *,
    provider: MeasurementProvider | None = None,
    patience: int = 2,
    threshold: float = 0.55,
    on_plateau: ExitReason = ExitReason.REFRAME,
) -> LoopHealthResult:
    """Score one loop trace for health. ``steps`` may be plain strings (thinking
    segments / step texts), dicts (``{artifact, error}``), or ``IterationObservation``.

    ``provider`` defaults to the public ``EvidenceNoveltyProvider`` (novelty vs all
    prior steps — the crude-but-honest baseline). Pass a validated L1 instrument to
    sharpen the verdict; nothing else changes. ``tokens_at_risk`` is the estimated
    thinking/output tokens in the plateaued tail — the saveable cost."""
    if provider is None:
        from gyre.providers import EvidenceNoveltyProvider

        provider = EvidenceNoveltyProvider()
    if provider.loop_id != "L1":
        raise ValueError(f"score_loop_health needs an L1 provider, got {provider.loop_id!r}")

    monitor = RuminationMonitor(
        provider, patience=patience, threshold=threshold, on_plateau=on_plateau
    )
    obs = [_to_observation(s, i) for i, s in enumerate(steps)]

    onset: int | None = None
    exit_reason = ExitReason.CONTINUE
    per_step: list[StepHealth] = []
    for i, o in enumerate(obs):
        monitor.observe(o)
        fired = monitor.verdict().exit_reason is not ExitReason.CONTINUE
        if fired and onset is None:
            onset = i
            exit_reason = monitor.verdict().exit_reason
        per_step.append(StepHealth(index=i, ruminating=fired, est_tokens=estimate_tokens(o.artifact)))

    tokens_total = sum(s.est_tokens for s in per_step)
    tokens_at_risk = sum(s.est_tokens for s in per_step[onset:]) if onset is not None else 0
    frac = (len(per_step) - onset) / len(per_step) if (onset is not None and per_step) else 0.0

    return LoopHealthResult(
        ruminating=onset is not None,
        onset_step=onset,
        n_steps=len(per_step),
        rumination_fraction=frac,
        tokens_total=tokens_total,
        tokens_at_risk=tokens_at_risk,
        exit_reason=exit_reason.value,
        provider=provider.name,
        steps=per_step,
    )
