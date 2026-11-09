"""Measure your measurement.

A loop is only as good as its sensor, so the natural question is: how good is my
sensor? This module answers it. Give it a provider and a set of labelled traces
(sequences of observations where a human has marked which steps were the
pathological state) and it reports how well the provider's readings agree with the
labels.

This is the neutral proving ground. It is public, and it is the same harness a
naive baseline and a protected candidate both get scored on. That is what makes
the value gap empirical rather than asserted: you do not have to take anyone's
word that a better measurement helps, you run both through ``evaluate_provider``
and read the numbers.

Two honest limits, stated up front:

1. The scores are only as meaningful as the labels. Garbage ground truth gives
   garbage agreement numbers. Building a defensible labelled corpus is itself real
   work, and a separate asset from any single detector.
2. This harness reports agreement, not validity in the full psychometric sense.
   Agreement with labels is necessary, not sufficient. See
   docs/measurement-stance.md.

Dependencies: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from gyre.loops._policy import ThresholdRequired, trigger_state
from gyre.measurement import MeasurementProvider


@dataclass
class LabelledTrace:
    """A sequence of observations with per-step ground-truth labels.

    ``observations`` is fed to the provider one at a time (order matters; many
    providers are stateful). ``labels[i]`` is True when observation ``i`` is the
    pathological state the provider is meant to catch (e.g. this iteration was part
    of a ruminative episode).
    """

    observations: Sequence[Any]
    labels: Sequence[bool]
    loop_id: str
    name: str = "trace"

    def __post_init__(self) -> None:
        if len(self.observations) != len(self.labels):
            raise ValueError("observations and labels must be the same length")


@dataclass
class ProviderScore:
    """How well a provider's readings agreed with the labels."""

    provider: str
    loop_id: str
    n: int
    positives: int
    calibrated: bool
    """True if the provider made its own decisions (or gave probabilities); False
    if it only gave raw values and the harness had to sweep a threshold for it."""
    precision: float
    recall: float
    f1: float
    accuracy: float
    best_threshold: float | None = None
    """The threshold that maximised F1, if the harness had to sweep one. ``None``
    when the provider decided for itself. That a naive provider *needs* this swept
    for it, and a calibrated one does not, is itself a result."""
    notes: tuple[str, ...] = field(default_factory=tuple)


def _decisions_calibrated(
    provider: MeasurementProvider, traces: Sequence[Sequence[Any]]
) -> list[bool]:
    out = []
    for obs in traces:
        provider.reset()
        for o in obs:
            m = provider.measure(o)
            out.append(trigger_state(m))  # calibrated: uses decision/probability
    return out


def _decisions_at_threshold(
    provider: MeasurementProvider, traces: Sequence[Sequence[Any]], threshold: float
) -> list[bool]:
    out = []
    for obs in traces:
        provider.reset()
        for o in obs:
            m = provider.measure(o)
            try:
                out.append(trigger_state(m, threshold=threshold))
            except ThresholdRequired:
                out.append(False)
    return out


def _prf(pred: Sequence[bool], truth: Sequence[bool]) -> tuple[float, float, float, float]:
    tp = sum(p and t for p, t in zip(pred, truth))
    fp = sum(p and not t for p, t in zip(pred, truth))
    fn = sum((not p) and t for p, t in zip(pred, truth))
    tn = sum((not p) and (not t) for p, t in zip(pred, truth))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(pred) if pred else 0.0
    return precision, recall, f1, accuracy


def evaluate_provider(
    provider: MeasurementProvider,
    traces: Sequence[LabelledTrace],
    *,
    threshold_grid: Sequence[float] | None = None,
) -> ProviderScore:
    """Score one provider against labelled traces.

    If the provider makes calibrated decisions (its Measurements carry a
    ``decision`` or ``probability``), it is scored on those directly. If it only
    returns raw values, the harness sweeps ``threshold_grid`` and reports the
    provider's *best-case* F1, which is generous to the naive provider, and it
    still usually loses to a calibrated one. That generosity is the point: even
    handed its best threshold in hindsight, a proxy that does not model the
    construct tends to trail a measurement that does.

    Providers are reset between traces: each trace is an independent episode,
    and a stateful provider's baseline from one episode must not bleed into the
    next. (One threshold is still swept across ALL traces for uncalibrated
    providers — the threshold is a deployment-time constant, the state is not.)
    """
    per_trace_obs = [list(tr.observations) for tr in traces]
    obs = [o for tr in per_trace_obs for o in tr]
    truth = [bool(l) for tr in traces for l in tr.labels]
    if not obs:
        raise ValueError("no observations to evaluate")

    # Probe once to see whether the provider calibrates itself.
    provider.reset()
    sample = provider.measure(obs[0])
    provider.reset()

    if sample.is_calibrated():
        pred = _decisions_calibrated(provider, per_trace_obs)
        precision, recall, f1, accuracy = _prf(pred, truth)
        return ProviderScore(
            provider=provider.name,
            loop_id=provider.loop_id,
            n=len(obs),
            positives=sum(truth),
            calibrated=True,
            precision=precision,
            recall=recall,
            f1=f1,
            accuracy=accuracy,
            notes=("provider made its own decisions; no threshold needed",),
        )

    grid = threshold_grid if threshold_grid is not None else [i / 20 for i in range(1, 20)]
    best: tuple[float, tuple[float, float, float, float]] | None = None
    for th in grid:
        pred = _decisions_at_threshold(provider, per_trace_obs, th)
        scores = _prf(pred, truth)
        if best is None or scores[2] > best[1][2]:  # compare F1
            best = (th, scores)
    assert best is not None
    th, (precision, recall, f1, accuracy) = best
    return ProviderScore(
        provider=provider.name,
        loop_id=provider.loop_id,
        n=len(obs),
        positives=sum(truth),
        calibrated=False,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        best_threshold=th,
        notes=(
            "uncalibrated: harness swept a threshold and reports best-case F1",
            "in production you would not know this threshold in advance",
        ),
    )


def compare_providers(
    providers: Sequence[MeasurementProvider],
    traces: Sequence[LabelledTrace],
    *,
    threshold_grid: Sequence[float] | None = None,
) -> list[ProviderScore]:
    """Score several providers on the same traces, sorted best F1 first.

    This is the head-to-head that makes the argument. Put a naive baseline and a
    serious provider in the same call and read the gap.
    """
    scores = [evaluate_provider(p, traces, threshold_grid=threshold_grid) for p in providers]
    return sorted(scores, key=lambda s: s.f1, reverse=True)
