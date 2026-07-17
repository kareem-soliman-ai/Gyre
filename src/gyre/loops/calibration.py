"""L2 — Metacognitive Calibration, as a standing governor.

Unlike the other loops this one does not terminate. It watches the agent's
predictions against outcomes, keeps a running read of how calibrated the agent
is, and exposes a policy: when confidence is low (and, ideally, when the running
calibration says low-confidence predictions have been unreliable), route to
information-seeking instead of committing to an action.

The measurement (how well do stated probabilities match observed frequencies) is
the provider's job. A naive provider returns a rolling Brier score. A serious one
returns calibration error with its own reliability estimate, over/under-confidence
sign, and a decision boundary it has earned. The governor consumes whichever it
is given.

See ../../loops/L2-metacognitive-calibration.md for the psychology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from gyre.interfaces import ExitReason, LoopVerdict, Maturity
from gyre.measurement import Measurement, MeasurementProvider

Route = Literal["act", "seek_info"]


@dataclass
class PredictionOutcome:
    """One (predicted probability, realised outcome) pair, fed after an attempt.

    ``predicted`` is the agent's stated P(success) before the attempt;
    ``outcome`` is whether it succeeded. The provider turns a stream of these
    into a calibration reading.
    """

    predicted: float
    outcome: bool


class CalibrationGovernor:
    """A standing governor that turns calibration into a routing policy.

    Args:
        provider: an L2 provider that measures calibration error
            (``Meaning.LOWER_IS_HEALTHIER``). Fed one ``PredictionOutcome`` per
            resolved attempt.
        min_confidence: below this stated confidence, route to information-seeking
            rather than acting. This is the object-level control knob; the
            provider's calibration read modulates how much to trust the confidence
            in the first place.
    """

    loop_id = "L2"

    def __init__(
        self,
        provider: MeasurementProvider,
        *,
        min_confidence: float = 0.5,
    ) -> None:
        if provider.loop_id != self.loop_id:
            raise ValueError(
                f"CalibrationGovernor needs an L2 provider, got {provider.loop_id!r} "
                f"({provider.name!r})"
            )
        self.provider = provider
        self.min_confidence = min_confidence
        self._last: Measurement | None = None

    def observe(self, observation: PredictionOutcome | Any) -> None:
        """Record one resolved prediction and update the calibration read."""
        self._last = self.provider.measure(observation)

    def policy(self, next_confidence: float) -> Route:
        """Given the agent's confidence for the *next* action, route it.

        Base rule: low stated confidence routes to information-seeking. If the
        provider reports that the agent is currently overconfident (its stated
        confidence runs ahead of its accuracy), tighten the bar: an overconfident
        agent's "high confidence" should be trusted less, so the seek-info region
        widens. A well-calibrated agent gets the plain threshold.
        """
        bar = self.min_confidence
        m = self._last
        if m is not None and m.standardized is not None and m.meaning.value == "lower_is_healthier":
            # standardized > 0 here means calibration error is worse than baseline;
            # treat that as a reason to demand more confidence before acting.
            bar = min(0.95, self.min_confidence + 0.1 * max(0.0, m.standardized))
        return "act" if next_confidence >= bar else "seek_info"

    def verdict(self) -> LoopVerdict:
        """A read on calibration health. Not an exit; a standing report."""
        if self._last is None:
            return LoopVerdict(
                exit_reason=ExitReason.CONTINUE,
                loop_id=self.loop_id,
                note="no predictions resolved yet",
            )
        maturity = Maturity.INSTRUMENT if self._last.is_calibrated() else Maturity.BUILDABLE
        return LoopVerdict(
            exit_reason=ExitReason.CONTINUE,
            loop_id=self.loop_id,
            measurements=(self._last,),
            confidence=self._last.probability,
            maturity=maturity,
            note=f"calibration error {self._last.value:.3f} ({self._last.provider})",
        )

    def reset(self) -> None:
        self._last = None
        self.provider.reset()
