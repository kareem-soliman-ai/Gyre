"""Loop-side interfaces: what a loop *is*, independent of how it measures.

A loop here is a controller. It is constructed with a ``MeasurementProvider``
(see ``gyre.measurement``), fed observations, and asked for a verdict. It owns
the control policy (the state machine: how long a signal has to stay bad before
acting, how to route when it does) and nothing about measurement. Swap the
provider and the control policy is unchanged; that is the whole design.

This module has no dependency on any concrete provider, and must never gain one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, Sequence, runtime_checkable

from gyre.measurement import Measurement


class Maturity(str, Enum):
    """How ready a pattern (or a provider) is, and how far its claims can be
    trusted. See docs/measurement-stance.md."""

    FRAMING = "framing"
    """An idea and a naming. No code expected (e.g. L0 TOTE, L7 meta-loop)."""

    BUILDABLE = "buildable"
    """A working version is a small job, buildable straight from the pattern doc."""

    INSTRUMENT = "instrument"
    """Measures a latent property. Cannot state performance numbers until
    validated against ground truth. Method open, validated scoring held back."""


class ExitReason(str, Enum):
    """Why a loop should continue, stop, escalate, or switch.

    A loop reports one of these; it does not act. Acting is the job of the
    surrounding scaffold or an L7 controller, which keeps loops composable.
    """

    CONTINUE = "continue"
    """The loop is still paying. Keep going."""

    PLATEAU = "plateau"
    """The measured signal says the loop has stopped learning (the L1 case).
    Route to reframe, escalate, or abandon-with-note."""

    REFRAME = "reframe"
    """Hand to an incubation / Einstellung break (L5): disengage, reset attention,
    return with reordered constraints."""

    ESCALATE = "escalate"
    """Surface to a human with a structured summary of what was tried and why it
    plateaued. Not a raw failure dump."""

    ABANDON = "abandon"
    """Record the impasse where a later loop or session can pick it up (the L4
    register), so the dead end is not silently re-entered."""

    RUPTURE = "rupture"
    """The human-agent alliance shows rupture markers (L3). Pre-empts object-level
    optimisation: initiate repair before continuing."""

    DEVIATION = "deviation"
    """A monitored channel departed from its learned baseline (the L6 case).
    Allocate attention; the steady state should stay silent."""


@dataclass(frozen=True)
class LoopVerdict:
    """A loop's read on itself, resting on the measurements it has seen.

    A verdict is a hypothesis, not a fact, until the provider that fed it has been
    validated. ``confidence`` should reflect that, and ``maturity`` records how
    far the underlying measurement is allowed to speak.
    """

    exit_reason: ExitReason
    """What the surrounding scaffold should consider doing."""

    measurements: Sequence[Measurement] = field(default_factory=tuple)
    """The readings this verdict rests on. Never hide the basis for a verdict; the
    confounds ride along inside each Measurement."""

    confidence: float | None = None
    """Optional [0, 1] confidence in the verdict. ``None`` means the loop does not
    make a calibrated confidence claim, which for an unvalidated provider is the
    honest answer."""

    maturity: Maturity = Maturity.BUILDABLE
    """Maturity of the least-mature provider this verdict depends on."""

    note: str = ""
    """Human-readable one-liner, e.g. for an ESCALATE summary."""


@runtime_checkable
class LoopMonitor(Protocol):
    """The shape every loop controller shares.

    Construct it with a provider, feed it observations, ask for a verdict. It is
    intentionally passive: it watches and reports, it does not act. That is what
    lets you bolt one onto an existing agent without rewriting the agent, and what
    lets an L7 controller consume many loops' verdicts to decide what runs next.
    """

    loop_id: str
    """Which pattern this implements, e.g. "L1"."""

    def observe(self, observation: Any) -> None:
        """Take in one observation. Delegates measurement to the provider; should
        stay cheap."""
        ...

    def verdict(self) -> LoopVerdict:
        """Return the loop's current read."""
        ...

    def reset(self) -> None:
        """Clear control state and the provider's state for an independent run."""
        ...
