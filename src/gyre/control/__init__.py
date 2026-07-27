"""The control seam: L7's interface, and reference controllers.

This is the second seam in Gyre, and it mirrors the first. ``gyre.measurement``
separates a loop from its sensor so you can swap sensors and watch the same
controller behave differently. This module separates the loops from the
**meta-controller** — the L7 layer that decides which route the agent takes when
a loop fires — so you can swap controllers and watch the same sensors get used
differently. Hold the sensor constant, compare controllers: that is the second
runnable value gap (see scripts/exp_controller_gap.py for the experiment that
motivated it).

The shape:

- ``ControlContext`` — what the surrounding scaffold knows that no loop does:
  stakes, reversibility, budgets, costs, problem type. Context enters HERE,
  above the verdicts. It never goes inside ``Measurement``; a sensor reports
  what is happening, a controller decides what it is worth.
- ``MetaController`` — the protocol. Consume the loops' verdicts plus the
  context, return one ``ExitReason``.
- Reference controllers — ``FixedRouteController`` and ``L5RouteController``,
  the control-tier equivalents of the naive sensors: real, usable, honest about
  their ceiling. A fixed route is brittle across contexts in a way that is
  measurable (the experiment above puts numbers on it), which is exactly the
  point of shipping them: they are the baseline a better controller has to beat.

Like validated sensors, a validated adaptive controller does not ship here; the
fence is ``gyre.control.proprietary``, mirroring ``gyre.providers.proprietary``.
A controller that decides an agent's mode-switching needs to be built and
validated carefully, not sketched confidently (see loops/L7-meta-loop.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence, runtime_checkable

from gyre.interfaces import ExitReason, LoopVerdict
from gyre.loops.incubation import EinstellungBreaker


@dataclass(frozen=True)
class ControlContext:
    """What the scaffold knows that no individual loop does.

    Every field is optional-by-default on purpose: a controller must degrade
    gracefully when context is missing, the same way a loop degrades when a
    measurement leaves its calibration fields ``None``.
    """

    stakes: float = 1.0
    """Value of success, in whatever unit the caller thinks in. Only ratios
    against the costs below matter."""

    reversibility: float = 1.0
    """How cheaply the next action can be undone: 1.0 freely reversible,
    0.0 irreversible. Low reversibility should make a controller demand more
    confidence before committing (the L2 connection)."""

    steps_remaining: int | None = None
    """Iteration budget left, if the scaffold enforces one. ``None`` = unknown."""

    step_cost: float = 0.05
    """Cost of one more iteration (tokens, time), in units of ``stakes``."""

    reframe_cost: float = 0.1
    """Cost of a context reset (L5), in units of ``stakes``."""

    escalation_cost: float = 0.6
    """Cost of interrupting a human, in units of ``stakes``. The E2 experiment's
    headline: the best fixed route under one value of this is nearly the worst
    under another. This field is why context must reach the controller."""

    divergent: bool | None = None
    """Problem type, if known: open solution space (divergent) or single correct
    answer (convergent). Drives the L5 reset-vs-escalate call. ``None`` = unknown."""


@runtime_checkable
class MetaController(Protocol):
    """The L7 shape: verdicts + context in, one route out.

    A controller is passive like a loop: it recommends, the scaffold acts.
    Call ``route`` once per iteration with the current verdicts from whichever
    loops are running; the controller owns any cross-iteration state (beliefs,
    streaks) and ``reset`` clears it for an independent episode.
    """

    name: str

    def route(
        self, verdicts: Sequence[LoopVerdict], context: ControlContext
    ) -> ExitReason: ...

    def reset(self) -> None: ...


def dominant_verdict(verdicts: Sequence[LoopVerdict]) -> LoopVerdict | None:
    """The verdict a controller should attend to first, or None if all quiet.

    RUPTURE pre-empts everything: there is no point optimising the object-level
    loop when the human has disengaged from it (the L7 doc's one hard rule).
    Otherwise the first non-CONTINUE verdict wins, in the order given.
    """
    for v in verdicts:
        if v.exit_reason is ExitReason.RUPTURE:
            return v
    for v in verdicts:
        if v.exit_reason is not ExitReason.CONTINUE:
            return v
    return None


class FixedRouteController:
    """Gyre today, made explicit: whatever fired, take the configured route.

    This is what a ``RuminationMonitor(on_plateau=...)`` bakes into the loop,
    lifted to the controller layer where it belongs. It is deliberately the
    simplest possible controller, and its brittleness is measurable: the best
    fixed route under one cost regime is among the worst under another
    (scripts/exp_controller_gap.py). Ship it, use it, and know its ceiling.
    """

    def __init__(self, route: ExitReason = ExitReason.REFRAME) -> None:
        self.route_choice = route
        self.name = f"fixed:{route.value}"

    def route(
        self, verdicts: Sequence[LoopVerdict], context: ControlContext
    ) -> ExitReason:
        v = dominant_verdict(verdicts)
        if v is None:
            return ExitReason.CONTINUE
        if v.exit_reason is ExitReason.RUPTURE:
            return ExitReason.RUPTURE
        return self.route_choice

    def reset(self) -> None:  # stateless
        return None


class L5RouteController:
    """One bit of context-conditioning: reset divergent problems, escalate
    convergent ones, per the incubation literature (Sio & Ormerod via
    ``EinstellungBreaker``). Unknown problem type is treated as convergent,
    because a reset only earns its cost when the solution space is open.

    This is the strongest controller Gyre ships openly, and the E2 experiment
    is honest about its limit: one bit of context is not enough when the cost
    regime shifts (it keeps escalating convergent problems even when human
    attention is the expensive resource).
    """

    name = "l5-informed"

    def __init__(self) -> None:
        self._breaker = EinstellungBreaker()

    def route(
        self, verdicts: Sequence[LoopVerdict], context: ControlContext
    ) -> ExitReason:
        v = dominant_verdict(verdicts)
        if v is None:
            return ExitReason.CONTINUE
        if v.exit_reason is ExitReason.RUPTURE:
            return ExitReason.RUPTURE
        return self._breaker.decide(True, divergent=bool(context.divergent))

    def reset(self) -> None:  # stateless
        return None


# --- controller registry, mirroring gyre.providers -----------------------------

_REGISTRY: dict[str, Callable[[], MetaController]] = {}


def register(name: str, factory: Callable[[], MetaController]) -> None:
    """Register a controller factory (a zero-arg callable returning a fresh one)."""
    _REGISTRY[name] = factory


def get_controller(name: str) -> MetaController:
    """Construct a fresh controller by registered name."""
    if name not in _REGISTRY:
        raise KeyError(f"no controller named {name!r}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    """List registered controller names."""
    return sorted(_REGISTRY)


register("fixed:reframe", lambda: FixedRouteController(ExitReason.REFRAME))
register("fixed:escalate", lambda: FixedRouteController(ExitReason.ESCALATE))
register("fixed:abandon", lambda: FixedRouteController(ExitReason.ABANDON))
register("l5-informed", L5RouteController)

# --- register the meta-bandit L7 controller (F1 from the taxonomy) ---
try:
    from gyre.control.meta_bandit import register_controllers as _register_bandit
    _register_bandit(register)
except Exception:
    pass

# --- best-effort: let a gitignored proprietary layer register itself ------------
try:  # pragma: no cover - present only in a checkout that has the private layer
    from gyre.control import proprietary as _proprietary

    if hasattr(_proprietary, "register_all"):
        _proprietary.register_all(register)
except Exception:  # noqa: BLE001 - a missing/broken private layer must never break the public package
    pass


__all__ = [
    "ControlContext",
    "MetaController",
    "dominant_verdict",
    "FixedRouteController",
    "L5RouteController",
    "register",
    "get_controller",
    "available",
]
