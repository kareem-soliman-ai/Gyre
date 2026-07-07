"""L5 — Incubation / Einstellung Breaker, as a policy.

L5 is not a monitor. It owns no signal of its own; it is invoked by another
loop's exit (usually L1 declaring a plateau) and decides what to do about the
fixation. Its whole value is grounding that decision in Sio & Ormerod's
meta-analysis: a reset helps specifically for *divergent* problems reached at a
*genuine impasse*, and on a convergent problem the better move is to escalate.

So this policy does one honest thing: it refuses to reset at random. It resets
when the literature says a reset should pay, and escalates otherwise.

See ../../loops/L5-incubation-einstellung-breaker.md for the psychology.
"""

from __future__ import annotations

from dataclasses import dataclass

from gyre.interfaces import ExitReason, LoopVerdict


@dataclass(frozen=True)
class ResetDirective:
    """What an incubation break actually does to the agent when it fires.

    The benefit for an agent is not the passage of time (agents get nothing from
    wall-clock delay) but the attention reset: coming back to the problem without
    the accumulated context that installed the mental set. Dropping that context
    is free for an agent, which is why L5 is cheaper to run well in an agent than
    in a person.
    """

    fresh_context: bool = True
    """Re-present the problem in a clean context rather than resuming mid-thrash.
    This is the load-bearing move: it drops the stuck reasoning."""

    reorder_constraints: bool = True
    """Present the constraints in a different order, to disrupt the set that prior
    ordering installed."""

    detour_subtask: str | None = None
    """An unrelated subtask to work before returning, if one is available. The
    return, not the detour, is what matters."""


class EinstellungBreaker:
    """Decides whether a plateaued loop should reset or escalate, per the
    incubation literature's moderators.

    This is deliberately a small, grounded decision rather than a detector. The
    sophistication that could go here (a real fixation *measurement*: is the
    solution space still open, is the agent circling one basin) belongs in a
    measurement provider feeding richer input than a single ``divergent`` flag.
    See docs/building-measurements.md.
    """

    loop_id = "L5"

    def decide(self, plateau: LoopVerdict | bool, *, divergent: bool) -> ExitReason:
        """Return REFRAME (reset) or ESCALATE.

        Args:
            plateau: the upstream verdict (or a bool) indicating an impasse was
                reached. A reset is only appropriate *after* a genuine impasse,
                per the meta-analysis; do not call this on a healthy loop.
            divergent: whether the problem has an open solution space (many
                possible answers). Resets help divergent problems; convergent
                problems with one correct answer are better escalated.
        """
        reached_impasse = plateau if isinstance(plateau, bool) else plateau.exit_reason in (
            ExitReason.PLATEAU,
            ExitReason.REFRAME,
        )
        if not reached_impasse:
            # No impasse: incubation has nothing to break. Keep going.
            return ExitReason.CONTINUE
        if divergent:
            return ExitReason.REFRAME
        return ExitReason.ESCALATE

    def directive(self, *, detour_subtask: str | None = None) -> ResetDirective:
        """The concrete reset to apply when ``decide`` returns REFRAME."""
        return ResetDirective(detour_subtask=detour_subtask)

    def reset(self) -> None:  # stateless; here for interface symmetry
        return None
