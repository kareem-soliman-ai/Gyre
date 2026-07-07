"""Common interfaces for loop monitors.

A loop monitor observes an iterating agent and reports on the quality of the loop
it is running: is the loop still generating information, has it plateaued, should
it exit or switch. Every pattern in the Gyre catalogue that *measures* something
(L1, L2, L3, L6) can be expressed against the ``LoopMonitor`` protocol below.

This module contains no detectors. It is the vocabulary layer: the types a
detector would produce, and the shape it would present. Build your detector to
this interface and it composes with the rest of the catalogue, including a future
meta-loop controller (L7) that consumes ``LoopSignal`` and ``LoopVerdict`` to
decide which loop runs next.

See ../../loops/INDEX.md for the catalogue and ../../docs/measurement-stance.md
for why the scoring internals are deliberately not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, Sequence, runtime_checkable


class Maturity(str, Enum):
    """How ready a pattern is, and how much its outputs can be trusted.

    See ../../loops/INDEX.md and ../../docs/measurement-stance.md.
    """

    FRAMING = "framing"
    """An idea and a naming. No code expected (e.g. L0 TOTE, L7 meta-loop)."""

    BUILDABLE = "buildable"
    """A working version is a small job, buildable straight from the pattern doc."""

    INSTRUMENT = "instrument"
    """Measures a latent property. Cannot state numbers until validated against
    ground truth. Method open, validated scoring held back."""


class ExitReason(str, Enum):
    """Why a loop should stop, escalate, or switch.

    A monitor does not itself act; it reports one of these so the surrounding
    scaffold (or an L7 controller) can decide what to do.
    """

    CONTINUE = "continue"
    """The loop is still paying. Keep going."""

    PLATEAU = "plateau"
    """Information gain has fallen below threshold for long enough that the loop
    has stopped learning. The L1 rumination signal. Route to reframe, escalate,
    or abandon-with-note."""

    REFRAME = "reframe"
    """Hand to an incubation / Einstellung break (L5): disengage, reset attention,
    return with reordered constraints."""

    ESCALATE = "escalate"
    """Surface to a human with a structured summary of what was tried and why it
    plateaued. Not a raw failure dump."""

    ABANDON = "abandon"
    """Record the impasse in a form a later loop or session can pick up (the L4
    Zeigarnik register), so the dead end is not silently re-entered."""

    RUPTURE = "rupture"
    """The human-agent alliance shows rupture markers (L3). Pre-empts object-level
    optimisation: initiate repair before continuing."""


@dataclass(frozen=True)
class LoopSignal:
    """A single measured signal about a loop, with its provenance attached.

    ``value`` is deliberately untyped as to its scale: it might be a diff-novelty
    ratio in [0, 1], a Brier score, a deviation magnitude. ``name`` and
    ``loop_id`` say what it is and which pattern produced it. ``confounds`` is not
    decoration: every signal in this catalogue is confounded, and a monitor that
    does not name its confounds is hiding the thing you most need to know.
    """

    loop_id: str
    """Which pattern produced this, e.g. "L1", "L6"."""

    name: str
    """What the signal is, e.g. "diff_novelty_ratio", "brier_score"."""

    value: float
    """The measured value. Scale is signal-specific; see the pattern doc."""

    confounds: Sequence[str] = field(default_factory=tuple)
    """Known ways this signal can mislead. Stated so callers can weight it."""

    detail: dict[str, Any] = field(default_factory=dict)
    """Optional extra context (window size, sample count, etc.)."""


@dataclass(frozen=True)
class LoopVerdict:
    """A monitor's read on the loop, as of the observations it has seen.

    A verdict is a *hypothesis*, not a fact, until the monitor producing it has
    been validated on labelled traces. ``confidence`` should reflect that, and
    ``maturity`` records whether this monitor is even allowed to make a claim yet.
    """

    exit_reason: ExitReason
    """What the surrounding scaffold should consider doing."""

    signals: Sequence[LoopSignal] = field(default_factory=tuple)
    """The signals this verdict rests on. Never hide the basis for a verdict."""

    confidence: float | None = None
    """Optional [0, 1] confidence. None means the monitor does not (yet) make a
    calibrated confidence claim, which for an unvalidated instrument is honest."""

    maturity: Maturity = Maturity.BUILDABLE
    """The maturity of the monitor issuing this verdict."""

    note: str = ""
    """Human-readable one-liner, e.g. for an ESCALATE summary."""


@runtime_checkable
class LoopMonitor(Protocol):
    """The shape every loop monitor shares.

    A monitor observes an iterating agent and, when asked, returns a verdict. It
    is intentionally passive: it watches, it reports, it does not act. Acting on
    the verdict is the job of the scaffold or the L7 controller, which keeps
    monitors composable and lets you add one to an existing agent without
    rewriting the agent.

    Minimal contract:
      - ``observe`` is fed each iteration's artefacts (a diff, a transcript slice,
        a log line, an outcome). Cheap; called often.
      - ``verdict`` returns the current read. May be called any time.

    Implement this for your L1 rumination detector, L6 habituation filter, etc.
    The catalogue describes *how*; this protocol describes the *shape*.
    """

    loop_id: str
    """Which pattern this monitor implements, e.g. "L1"."""

    def observe(self, iteration: Any) -> None:
        """Take in one iteration's worth of behaviour. Should be cheap."""
        ...

    def verdict(self) -> LoopVerdict:
        """Return the monitor's current read of the loop."""
        ...
