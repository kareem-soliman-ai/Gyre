"""L1 — Rumination vs Reflection, as a controller.

The controller owns one thing: the patience state machine. It asks its provider
"is this iteration still generating information?" each step, and when the answer
has been "no" for ``patience`` consecutive steps, it declares the loop plateaued
and routes. It does not know or care how the provider decides. Swap a difflib
diff-novelty provider for a validated information-gain instrument and this file
does not change; only when the loop fires, and how early, changes.

See ../../loops/L1-rumination-vs-reflection.md for the psychology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gyre.interfaces import ExitReason, LoopVerdict, Maturity
from gyre.loops._policy import trigger_state
from gyre.measurement import Measurement, MeasurementProvider


@dataclass
class IterationObservation:
    """One iteration of an iterating agent, as fed to an L1 provider.

    A provider decides for itself which fields it uses. A lexical proxy reads
    ``artifact``; a semantic one might embed it; an error-entropy proxy reads
    ``error``. The controller just passes this through.
    """

    artifact: str
    """The agent's output this iteration (a diff, a patch, a candidate answer)."""

    error: str | None = None
    """The environment's response this iteration (a failing test, a stack trace),
    if any. Sometimes a cleaner signal than the artifact, because the environment
    is harder to game than the agent's own text."""

    index: int = 0
    """Iteration number, for provenance."""


class RuminationMonitor:
    """Watches an iterating agent and reports when it has stopped learning.

    Args:
        provider: the sensor. Must have ``loop_id == "L1"``.
        patience: how many consecutive low-gain iterations before declaring a
            plateau. Higher is more conservative.
        threshold: only used as a fallback when the provider returns an
            uncalibrated raw value. A calibrated provider makes this irrelevant,
            which is exactly the difference you are meant to feel.
        on_plateau: what to route to when the plateau is declared. Defaults to
            REFRAME (hand to an L5 incubation break); ESCALATE and ABANDON are the
            other sensible choices.
    """

    loop_id = "L1"

    def __init__(
        self,
        provider: MeasurementProvider,
        *,
        patience: int = 3,
        threshold: float | None = None,
        on_plateau: ExitReason = ExitReason.REFRAME,
    ) -> None:
        if provider.loop_id != self.loop_id:
            raise ValueError(
                f"RuminationMonitor needs an L1 provider, got {provider.loop_id!r} "
                f"({provider.name!r})"
            )
        self.provider = provider
        self.patience = patience
        self.threshold = threshold
        self.on_plateau = on_plateau
        self._streak = 0
        self._history: list[Measurement] = []

    def observe(self, observation: IterationObservation | Any) -> None:
        m = self.provider.measure(observation)
        self._history.append(m)
        if trigger_state(m, threshold=self.threshold):
            self._streak += 1
        else:
            self._streak = 0

    def verdict(self) -> LoopVerdict:
        recent = tuple(self._history[-self.patience :])
        maturity = Maturity.INSTRUMENT if any(m.is_calibrated() for m in recent) else Maturity.BUILDABLE
        if self._streak >= self.patience:
            return LoopVerdict(
                exit_reason=self.on_plateau,
                loop_id=self.loop_id,
                measurements=recent,
                maturity=maturity,
                note=(
                    f"information gain below threshold for {self._streak} "
                    f"consecutive iterations; routing to {self.on_plateau.value}"
                ),
            )
        return LoopVerdict(
            exit_reason=ExitReason.CONTINUE,
            loop_id=self.loop_id,
            measurements=recent,
            maturity=maturity,
            note=f"loop still paying (low-gain streak {self._streak}/{self.patience})",
        )

    def reset(self) -> None:
        self._streak = 0
        self._history.clear()
        self.provider.reset()
