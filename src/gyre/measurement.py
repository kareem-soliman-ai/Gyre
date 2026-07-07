"""The measurement seam.

This is the most important module in Gyre, and the smallest. It defines the
boundary between a **loop** (a controller: it decides when to act and how to
route) and a **measurement** (a sensor: it produces the signal the controller
acts on). Loops depend only on the ``MeasurementProvider`` protocol here. They
never import a concrete measurement. That one rule is what makes measurement
pluggable, and it is what lets you run the same loop with a throwaway sensor and
with a carefully validated one and watch it behave differently.

Why this boundary matters, in one line of control theory: a controller is only
as good as its sensor. The loops in this catalogue are decent controllers. What
separates a system that works from one that thrashes is almost always the
quality of the measurement feeding it, not the control logic. Gyre makes that
separation explicit so you can feel it.

The ``Measurement`` type is designed so that *the shape of what a provider
returns tells you how good the provider is*. A naive sensor fills in ``value``
and ``meaning`` and leaves the calibration and self-error fields ``None``, which
forces you to guess a threshold and gives you no sense of the reading's
reliability. A well-built sensor fills in ``standardized``, ``probability``,
``decision``, and ``measurement_error``, because it knows its own baseline and
its own error. You can read a provider's maturity straight off its output.

See docs/architecture.md for the full picture and docs/building-measurements.md
if you want to build your own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Meaning(str, Enum):
    """What a measurement's value *means*, directionally.

    A loop needs to know which way is healthy before it can route on a value. A
    provider declares this so the loop stays measurement-agnostic: the same
    controller can consume an information-gain signal (higher is healthier) and a
    Brier score (lower is healthier) without special-casing either.
    """

    HIGHER_IS_HEALTHIER = "higher_is_healthier"
    """Large values are good; the loop triggers when the value drops.
    Example: information gain per iteration (L1)."""

    LOWER_IS_HEALTHIER = "lower_is_healthier"
    """Small values are good; the loop triggers when the value rises.
    Example: calibration error / Brier score (L2)."""

    DEVIATION = "deviation"
    """The value is a magnitude of departure from an expected baseline; the loop
    triggers when it is large regardless of sign. Example: habituation /
    orienting deviation (L6)."""


@dataclass(frozen=True)
class Measurement:
    """A single sensor reading, with its own honesty attached.

    The required fields (``value``, ``meaning``) are what any sensor can produce.
    The optional fields are where measurement quality lives, and leaving them
    ``None`` is not a defect, it is an honest signal that this provider does not
    model that property. Read them as a maturity ladder:

    - ``value`` + ``meaning`` only: a raw proxy. You must supply the threshold,
      and you have no estimate of how noisy this reading is.
    - ``standardized`` present: the provider models a baseline, so it can tell you
      how far from normal this reading is (e.g. a z-score), not just its raw size.
    - ``probability`` present: the provider is a calibrated classifier of the
      latent state (e.g. P(this loop is ruminating)).
    - ``decision`` present: the provider is confident enough in its own
      validation to make the fire/hold call itself, so the loop can defer to it.
    - ``measurement_error`` present: the provider estimates its *own* reliability
      (a standard error). This is the psychometric signature. A difflib ratio
      will never give it to you; a fitted latent-variable model can.

    A loop should use the most-calibrated field available and fall back
    gracefully. See ``loops`` for how that fallback is implemented once, so every
    loop inherits it.
    """

    value: float
    """The raw scalar reading. Scale is provider-specific; ``meaning`` says which
    direction is healthy."""

    meaning: Meaning
    """Directional interpretation of ``value``."""

    # --- calibration ladder (optional; presence signals provider quality) ---

    standardized: float | None = None
    """The reading expressed relative to a modelled baseline, e.g. a z-score.
    Requires the provider to model what "normal" looks like for this channel."""

    probability: float | None = None
    """Calibrated probability of the pathological latent state in [0, 1], if the
    provider is a validated classifier. ``None`` if it does not make this claim."""

    decision: bool | None = None
    """The provider's own fire/hold call. ``True`` means "the loop should treat
    this as the trigger state." Only set this if the provider has earned the
    right to decide, i.e. it has been validated. ``None`` means "I give you a
    number, you decide," which is the honest default for a naive proxy."""

    # --- honesty ---

    measurement_error: float | None = None
    """The provider's estimate of its own uncertainty (a standard error on
    ``value`` or ``probability``). The reliability signature. ``None`` means the
    provider does not model its own error, which is itself worth knowing."""

    confounds: tuple[str, ...] = ()
    """Known ways this reading can mislead. Never hide these; they are the thing a
    downstream loop most needs in order to weight the signal."""

    provider: str = ""
    """Identifier of the provider that produced this, for provenance."""

    detail: dict[str, Any] = field(default_factory=dict)
    """Optional extra context (window size, sample count, baseline age, etc.)."""

    def is_calibrated(self) -> bool:
        """True if this provider offers a principled decision boundary, so a loop
        does not have to invent a threshold. Used by loops to decide whether to
        trust the provider's own call or apply a configured threshold."""
        return self.decision is not None or self.probability is not None

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe representation, for sending a reading over the wire.

        This is what makes a measurement transport-agnostic: a provider can run
        the scoring on a remote server and return the result as JSON, and a loop
        cannot tell the difference. See ``gyre.providers.remote``.
        """
        return {
            "value": self.value,
            "meaning": self.meaning.value,
            "standardized": self.standardized,
            "probability": self.probability,
            "decision": self.decision,
            "measurement_error": self.measurement_error,
            "confounds": list(self.confounds),
            "provider": self.provider,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Measurement":
        """Reconstruct a Measurement from its ``to_dict`` form."""
        return cls(
            value=d["value"],
            meaning=Meaning(d["meaning"]),
            standardized=d.get("standardized"),
            probability=d.get("probability"),
            decision=d.get("decision"),
            measurement_error=d.get("measurement_error"),
            confounds=tuple(d.get("confounds", ())),
            provider=d.get("provider", ""),
            detail=d.get("detail", {}),
        )


@runtime_checkable
class MeasurementProvider(Protocol):
    """The pluggable sensor interface. Implement this and any loop can use you.

    A provider is a sensor for exactly one loop's construct (rumination,
    calibration error, deviation, ...). It is fed observations of the shape that
    loop produces and returns a ``Measurement``. It may be stateful (most useful
    ones are: they model a baseline, a rolling window, a running calibration), so
    ``reset`` exists to clear that state between independent runs.

    The contract is deliberately tiny. Everything hard about measurement lives
    *inside* your implementation, not in this interface, which is the point: the
    interface is free and obvious, and the quality of what you put behind it is
    the entire game.
    """

    loop_id: str
    """Which loop's construct this measures, e.g. "L1". A loop will refuse a
    provider whose ``loop_id`` does not match, to catch wiring mistakes early."""

    name: str
    """Human-readable identifier for this provider, used in provenance and in the
    benchmark harness so results are attributable."""

    def measure(self, observation: Any) -> Measurement:
        """Produce a reading from one observation.

        ``observation`` is whatever the loop feeds (a diff and error for L1, a log
        line for L6, a prediction and outcome for L2). The provider knows how to
        interpret it because it is written for that loop. Should be cheap; loops
        call it every iteration.
        """
        ...

    def reset(self) -> None:
        """Clear any accumulated state (baseline, window, calibration curve) so
        the provider can be reused on an independent run. Stateless providers may
        make this a no-op.
        """
        ...
