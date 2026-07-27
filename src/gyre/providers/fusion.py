"""Sensor fusion gate: combine two complementary sensors.

Implements machinery B4 from the formal-machinery taxonomy: a weighted gate
that merges two measurements so the ensemble beats either sensor alone.

The fusion strategies (in order of sophistication):

1. **Weighted average** — linear combination with user-supplied weights.
2. **Bayesian model averaging** — weight each sensor by its self-reported
   calibration confidence (overriding the hard-coded weights).
3. **Logical gates** (OR/AND) — simple: fire if either fires, or if both
   fire.  Too crude for production, but perfect for head-to-head comparison
   with the learned gate.

The purpose of this module is to answer the question: *does combining
two sensors actually improve on the best single sensor on held-out traces?*
If the fusion gate never beats the best single sensor, the sensors are
not complementary (a result worth knowing and worth showing).

The sensor fusion gate is NOT a MeasurementProvider: it wraps two
MeasurementProviders and returns a new Measurement.  It sits at the
measurement layer, not the loop layer, and is meant to be used as a
drop-in provider by a loop (via the `as_provider` property).

Dependencies: standard library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from gyre.measurement import Meaning, Measurement
from gyre.measurement import MeasurementProvider


class _MeasureCallable(Protocol):
    """Protocol for an object that has a ``measure`` method."""
    def measure(self, observation: Any) -> Measurement: ...


@runtime_checkable
class _HasLoopId(Protocol):
    loop_id: str
    name: str
    def reset(self) -> None: ...


@dataclass
class SensorFusionGate:
    """Merge two sensors' outputs into a single measurement.

    Parameters
    ----------
    sensor_a : MeasurementProvider
        The first sensor (e.g. a CUSUM sensor).
    sensor_b : MeasurementProvider
        The second sensor (e.g. an AR(1) sensor).
    strategy : str
        One of ``"weighted"``, ``"bayesian"``, ``"or"``, ``"and"``.
        ``"weighted"`` uses the weights in ``weights``.
        ``"bayesian"`` weights each sensor by its own calibration confidence.
        ``"or"`` fires if either fires; ``"and"`` fires if both fire.

    weights : tuple[float, float]
        Weight for sensor_a and sensor_b respectively (used with
        ``strategy="weighted"``). Defaults to equal weight.
    fusion_name : str
        The `provider` field for the fused Measurement.  Parent loops
        can see which sensors were combined.
    """

    sensor_a: Any  # MeasurementProvider
    sensor_b: Any  # MeasurementProvider
    strategy: str = "weighted"
    weights: tuple[float, float] = (0.5, 0.5)
    fusion_name: str = "fusion:weighted"

    @property
    def loop_id(self) -> str:
        """Return the loop_id from the first sensor (they should match)."""
        return self.sensor_a.loop_id

    @property
    def name(self) -> str:
        return self.fusion_name

    def measure(self, observation: Any) -> Measurement:
        mA = self.sensor_a.measure(observation)
        mB = self.sensor_b.measure(observation)
        return self._fuse(mA, mB)

    def _fuse(self, mA: Measurement, mB: Measurement) -> Measurement:
        # Determine which direction "healthy" is (both should be the same)
        # Take sensor_a's meaning as canonical
        meaning = mA.meaning

        if self.strategy == "weighted":
            wA, wB = self.weights
            fused_value = wA * mA.value + wB * mB.value
            # Standardized: weighted average of the two, if both present
            sA = mA.standardized or 0.0
            sB = mB.standardized or 0.0
            if mA.standardized is not None and mB.standardized is not None:
                standardized = wA * sA + wB * sB
            else:
                standardized = None

            # Decision: fuse the two decisions with a majority rule
            # If both are calibrated, a decision exists; weight them
            if mA.decision is not None and mB.decision is not None:
                # Weighted average of the two decision signals, then compare
                dA = 1.0 if mA.decision else 0.0
                dB = 1.0 if mB.decision else 0.0
                fused_decision = (wA * dA + wB * dB) >= 0.5
            elif mA.decision is not None:
                fused_decision = mA.decision
            elif mB.decision is not None:
                fused_decision = mB.decision
            else:
                fused_decision = None

            # Measurement error: use the minimum of the two if both present
            me = None
            if mA.measurement_error is not None and mB.measurement_error is not None:
                me = min(mA.measurement_error, mB.measurement_error)
            elif mA.measurement_error is not None:
                me = mA.measurement_error
            elif mB.measurement_error is not None:
                me = mB.measurement_error

        elif self.strategy == "bayesian":
            # Weight by each sensor's calibration confidence
            cA = self._calibration_confidence(mA)
            cB = self._calibration_confidence(mB)
            total = cA + cB
            wA = cA / total if total > 0 else 0.5
            wB = cB / total if total > 0 else 0.5
            fused_value = wA * mA.value + wB * mB.value
            sA = mA.standardized or 0.0
            sB = mB.standardized or 0.0
            standardized = wA * sA + wB * sB if (mA.standardized is not None or mB.standardized is not None) else None
            fused_decision = None
            if mA.decision is not None and mB.decision is not None:
                dA = 1.0 if mA.decision else 0.0
                dB = 1.0 if mB.decision else 0.0
                fused_decision = (wA * dA + wB * dB) >= 0.5
            elif mA.decision is not None:
                fused_decision = mA.decision
            elif mB.decision is not None:
                fused_decision = mB.decision
            me = None
            if mA.measurement_error is not None and mB.measurement_error is not None:
                me = min(mA.measurement_error, mB.measurement_error)
        elif self.strategy == "or":
            fused_value = max(mA.value, mB.value)
            standardized = None
            fused_decision = bool(mA.decision or mB.decision)
            me = None
        elif self.strategy == "and":
            fused_value = min(mA.value, mB.value)
            standardized = None
            if mA.decision is not None and mB.decision is not None:
                fused_decision = bool(mA.decision and mB.decision)
            else:
                fused_decision = None
            me = None
        else:
            raise ValueError(f"unknown.strategy={self.strategy!r}")

        return Measurement(
            value=fused_value,
            meaning=meaning,
            standardized=standardized,
            decision=fused_decision,
            measurement_error=me,
            confounds=(
                f"fusion strategy: {self.strategy}",
                f"sensor_a: {mA.provider}, sensor_b: {mB.provider}",
            ) + mA.confounds + mB.confounds,
            provider=self.fusion_name,
            detail={
                "strategy": self.strategy,
                "sensor_a_value": mA.value,
                "sensor_b_value": mB.value,
            },
        )

    @staticmethod
    def _calibration_confidence(m: Measurement) -> float:
        """Compute a calibration confidence for the measurement: the more
        calibrated the field is, the higher the confidence."""
        conf = 0.0
        if m.decision is not None:
            conf += 0.5
        if m.probability is not None:
            conf += 0.25
        if m.standardized is not None:
            conf += 0.15
        if m.measurement_error is not None:
            conf += 0.10
        return conf

    def reset(self) -> None:
        self.sensor_a.reset()
        self.sensor_b.reset()

    def as_provider(self) -> MeasurementProvider:
        """Return this gate as a MeasurementProvider for use with loops.
        This is a lightweight protocol adapter that just delegates measure/reset."""
        gate = self

        class _FusedProvider:
            loop_id = gate.loop_id
            name = gate.fusion_name

            def measure(self, observation):
                return gate.measure(observation)

            def reset(self):
                gate.reset()

        return _FusedProvider()