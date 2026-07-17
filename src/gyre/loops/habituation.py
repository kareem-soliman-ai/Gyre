"""L6 — Habituation / Orienting, as a filter.

The filter suppresses response to a channel that matches its learned baseline and
fires only when the channel deviates. All of the modelling (what "normal" looks
like, how to measure departure from it) lives in the provider. The controller
just decides how many deviating observations to require before it orients, which
for a good deviation sensor is usually one.

See ../../loops/L6-habituation-orienting.md for the psychology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gyre.interfaces import ExitReason, LoopVerdict, Maturity
from gyre.loops._policy import trigger_state
from gyre.measurement import Measurement, MeasurementProvider


@dataclass
class ChannelObservation:
    """One reading from a monitored channel (a log line, a metric sample).

    A numeric provider reads ``value``; a content provider embeds or parses
    ``content``. Deviation is defined by the provider against whatever baseline it
    maintains, which is the whole point of L6.
    """

    content: str | None = None
    value: float | None = None
    channel: str = "default"


class HabituationFilter:
    """Absorbs the expected, orients on the novel.

    Args:
        provider: the sensor. Must have ``loop_id == "L6"`` and return a
            ``Meaning.DEVIATION`` measurement.
        patience: consecutive deviating observations before orienting. Defaults to
            1: dishabituation should be prompt.
        threshold: fallback deviation magnitude, used only if the provider does
            not model its own decision boundary.
    """

    loop_id = "L6"

    def __init__(
        self,
        provider: MeasurementProvider,
        *,
        patience: int = 1,
        threshold: float | None = None,
    ) -> None:
        if provider.loop_id != self.loop_id:
            raise ValueError(
                f"HabituationFilter needs an L6 provider, got {provider.loop_id!r} "
                f"({provider.name!r})"
            )
        self.provider = provider
        self.patience = patience
        self.threshold = threshold
        self._streak = 0
        self._last: Measurement | None = None

    def observe(self, observation: ChannelObservation | Any) -> None:
        m = self.provider.measure(observation)
        self._last = m
        if trigger_state(m, threshold=self.threshold):
            self._streak += 1
        else:
            self._streak = 0

    def orienting(self) -> bool:
        """True if the filter is currently oriented (deviation detected). The
        cheap boolean an ambient agent polls to decide whether to look."""
        return self._streak >= self.patience

    def verdict(self) -> LoopVerdict:
        measurements = (self._last,) if self._last is not None else ()
        maturity = (
            Maturity.INSTRUMENT if self._last is not None and self._last.is_calibrated() else Maturity.BUILDABLE
        )
        if self.orienting():
            return LoopVerdict(
                exit_reason=ExitReason.DEVIATION,
                loop_id=self.loop_id,
                measurements=measurements,
                maturity=maturity,
                note=f"channel deviated from baseline (streak {self._streak})",
            )
        return LoopVerdict(
            exit_reason=ExitReason.CONTINUE,
            loop_id=self.loop_id,
            measurements=measurements,
            maturity=maturity,
            note="channel matches baseline; habituated, staying silent",
        )

    def reset(self) -> None:
        self._streak = 0
        self._last = None
        self.provider.reset()
