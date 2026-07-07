"""Shared trigger policy: how a loop turns a Measurement into a fire/hold call.

Every loop faces the same question each observation: is this reading the trigger
state or not? The answer walks the calibration ladder of the Measurement, and it
is written once here so every loop inherits the same fallback and the same
teaching moment.

The teaching moment is the last branch. If a provider gives you nothing but a raw
value (a naive proxy), you land in ``_raw_trigger`` and you *must* have supplied a
threshold, which you will have guessed, probably badly. If a provider gives you a
calibrated decision or probability or a baseline-relative z-score, the earlier
branches handle it and you never touch a hand-tuned threshold. The quality of the
sensor decides how much guessing the loop has to do.
"""

from __future__ import annotations

from gyre.measurement import Meaning, Measurement


class ThresholdRequired(ValueError):
    """Raised when a naive provider offers no calibrated decision and the loop was
    not given a threshold to fall back on. The error is the point: an uncalibrated
    sensor cannot decide anything until *you* supply the boundary it lacks."""


def trigger_state(
    m: Measurement,
    *,
    threshold: float | None = None,
    prob_threshold: float = 0.5,
    z_threshold: float = 2.0,
) -> bool:
    """Return True if this reading is the loop's trigger state.

    Walks the calibration ladder, most-trustworthy first:

    1. ``decision`` — the provider made the call itself. Defer to it.
    2. ``probability`` — calibrated classifier; fire at ``prob_threshold``.
    3. ``standardized`` — baseline-relative; fire at ``z_threshold`` in the
       unhealthy direction.
    4. ``value`` — raw proxy; fire at the engineer-supplied ``threshold``, and if
       there is no threshold, refuse (``ThresholdRequired``).
    """
    if m.decision is not None:
        return m.decision

    if m.probability is not None:
        return m.probability >= prob_threshold

    if m.standardized is not None:
        return _directional(m.standardized, m.meaning, z_threshold)

    if threshold is None:
        raise ThresholdRequired(
            f"provider {m.provider!r} returned an uncalibrated value "
            f"(no decision/probability/standardized). Supply a threshold, or use "
            f"a provider that models its own decision boundary."
        )
    return _directional(m.value, m.meaning, threshold)


def _directional(x: float, meaning: Meaning, bound: float) -> bool:
    """Apply the directional trigger rule given what the value means.

    HIGHER_IS_HEALTHIER: unhealthy = low, so fire when x <= -bound (for z) or
      x <= bound (for a raw floor). We treat ``bound`` as the floor for raw values
      and as a magnitude for standardized values; callers pass the right one.
    LOWER_IS_HEALTHIER: unhealthy = high, fire when x >= bound.
    DEVIATION: unhealthy = far from zero, fire when abs(x) >= bound.
    """
    if meaning is Meaning.DEVIATION:
        return abs(x) >= bound
    if meaning is Meaning.LOWER_IS_HEALTHIER:
        return x >= bound
    # HIGHER_IS_HEALTHIER
    return x <= bound
