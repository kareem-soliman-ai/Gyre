"""Self-calibrating decision layer: each trace is its own baseline.

The real-trace finding this encodes (EXP-SC-01, 2026-07-26): on real agent
traces, fixed thresholds tuned on one domain saturate on another, while the raw
signals underneath still discriminate. The cheapest honest fix needs no labels
and no fitted constants at all — score every reading against the trace's OWN
opening steps.

``SelfBaselineProvider`` wraps any provider. It passes the inner measurement
through untouched except for one addition: ``standardized``, the z-score of the
current value against a baseline frozen from the first ``baseline_steps``
readings of this trace. That fills the calibration-ladder rung the architecture
always had (``trigger_state`` fires on ``standardized`` at |z| >= 2 with no
hand-picked threshold) but which no public provider previously supplied.

What this is: the strongest PUBLIC decision layer — domain-shift-robust because
the baseline travels with the trace. What it is not: a validated instrument. Its
structural blind spot is rumination-from-start (if the opening steps ARE the
pathology, the baseline is the pathology), and a frozen five-step baseline is a
noisy estimate. A fitted instrument knows the construct's operating point;
this only knows the trace's opening behaviour. Beating it is the bar a
validated instrument has to clear — see the challenge harness.

Dependencies: standard library only.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from gyre.measurement import Measurement, MeasurementProvider

_MIN_STD = 1e-6


class SelfBaselineProvider:
    """Wrap any provider; add a per-trace self-calibrated z-score.

    The first ``baseline_steps`` readings are burn-in: they build the baseline
    and report ``standardized = 0.0`` (healthy — nothing to compare against
    yet). From then on the baseline is FROZEN (mean and std of the burn-in
    values) and every reading reports its signed z against it, in the value's
    own direction, so ``trigger_state`` needs no threshold from anyone.
    """

    def __init__(self, inner: MeasurementProvider, *, baseline_steps: int = 5) -> None:
        if baseline_steps < 2:
            raise ValueError("baseline_steps must be >= 2 (a baseline needs variance)")
        self._inner = inner
        self._baseline_steps = baseline_steps
        self.loop_id = inner.loop_id
        inner_name = inner.name
        if inner_name.startswith("naive:"):
            inner_name = inner_name[len("naive:") :]
        self.name = f"selfcal:{inner_name}"
        self._head: list[float] = []
        self._frozen: tuple[float, float] | None = None

    def measure(self, observation: Any) -> Measurement:
        m = self._inner.measure(observation)
        if self._frozen is None:
            self._head.append(m.value)
            if len(self._head) >= self._baseline_steps:
                mean = sum(self._head) / len(self._head)
                var = sum((v - mean) ** 2 for v in self._head) / len(self._head)
                self._frozen = (mean, max(var**0.5, _MIN_STD))
            z = 0.0
        else:
            mean, std = self._frozen
            z = (m.value - mean) / std
        return replace(
            m,
            standardized=z,
            provider=self.name,
            confounds=m.confounds
            + (
                "self-baseline: blind to rumination-from-start (a pathological "
                "opening becomes the baseline); pair with an absolute sensor",
                "frozen head baseline: a noisy estimate on short or erratic openings",
            ),
        )

    def reset(self) -> None:
        self._inner.reset()
        self._head = []
        self._frozen = None
