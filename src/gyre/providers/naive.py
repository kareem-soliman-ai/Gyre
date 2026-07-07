"""Naive reference providers. Public, honest, and deliberately crude.

These exist so every loop runs out of the box, and so you can *feel* what a naive
measurement gives you. They are real and usable; for a lot of low-stakes cases a
naive proxy is genuinely enough, and this file says so plainly. But watch what
they leave ``None`` on the ``Measurement``: no probability, no self-error, and
(mostly) no decision. That absence is the honest signal that these do not model
the latent construct they proxy, they only correlate with it, and where the
construct is subtle (rumination, calibration, rupture) the correlation frays in
ways you cannot see from the number alone.

If you want to know how much better a measurement *can* be, build one and score
it against a naive baseline with ``gyre.bench``. That comparison is the whole
argument for taking measurement seriously. See docs/building-measurements.md.

Dependencies: standard library only. No embeddings, no models. That ceiling is
intentional; a serious provider breaks it.
"""

from __future__ import annotations

import difflib
from collections import deque

from gyre.loops.calibration import PredictionOutcome
from gyre.loops.habituation import ChannelObservation
from gyre.loops.rumination import IterationObservation
from gyre.measurement import Meaning, Measurement


class DiffNoveltyProvider:
    """L1: lexical diff-novelty between consecutive artifacts.

    novelty = 1 - SequenceMatcher.ratio(previous, current). High novelty means the
    latest attempt differs a lot from the last one; low novelty means the agent is
    producing near-identical output, the lexical fingerprint of rumination.

    What it gets right: it is cheap, transparent, and a reasonable first proxy for
    "is anything changing." What it gets wrong, and cannot see: it is lexical, so
    renaming a variable reads as novelty; it rewards thrashing, because an agent
    that rewrites everything each pass looks maximally novel while getting nowhere;
    and it has no baseline, so it cannot tell you whether this much change is
    normal for this task. It returns a raw value and nothing else, which forces
    *you* to pick the threshold. You will pick it badly, because the right
    threshold depends on the task, and this provider does not know the task.
    """

    loop_id = "L1"
    name = "naive:diff-novelty"

    def __init__(self) -> None:
        self._previous: str | None = None

    def measure(self, observation: IterationObservation) -> Measurement:
        current = observation.artifact
        if self._previous is None:
            novelty = 1.0  # first attempt is maximally novel by definition
        else:
            ratio = difflib.SequenceMatcher(None, self._previous, current).ratio()
            novelty = 1.0 - ratio
        self._previous = current
        return Measurement(
            value=novelty,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            confounds=(
                "lexical, not semantic: renaming reads as novelty",
                "rewards thrashing: full rewrites look maximally novel",
                "no baseline: cannot tell if this much change is normal",
            ),
            provider=self.name,
        )

    def reset(self) -> None:
        self._previous = None


class RollingBrierProvider:
    """L2: rolling Brier score over recent (predicted, outcome) pairs.

    Brier = mean((predicted - outcome)^2) over a window. Lower is better. It is the
    standard proper scoring rule and it is genuinely fine as a calibration summary.

    What it does not do: it gives you a single scalar with no sense of its own
    reliability (a Brier of 0.2 over 5 samples and over 500 samples are not the
    same thing, and this cannot tell them apart), no over/under-confidence sign
    (is the agent overconfident or underconfident? this does not say), and no
    decision boundary. A serious L2 provider would report reliability, the sign of
    the miscalibration, and a validated threshold. Compare them with gyre.bench.
    """

    loop_id = "L2"
    name = "naive:rolling-brier"

    def __init__(self, window: int = 20) -> None:
        self._window: deque[float] = deque(maxlen=window)

    def measure(self, observation: PredictionOutcome) -> Measurement:
        outcome = 1.0 if observation.outcome else 0.0
        self._window.append((observation.predicted - outcome) ** 2)
        brier = sum(self._window) / len(self._window)
        return Measurement(
            value=brier,
            meaning=Meaning.LOWER_IS_HEALTHIER,
            confounds=(
                "no reliability: a Brier over 5 samples reads like one over 500",
                "no sign: does not say if the agent is over- or under-confident",
                "window-sensitive: the number moves with the window length you chose",
            ),
            provider=self.name,
            detail={"n": len(self._window)},
        )

    def reset(self) -> None:
        self._window.clear()


class ZScoreDeviationProvider:
    """L6: deviation of a numeric channel from its rolling mean, in std units.

    This one climbs one rung of the calibration ladder, on purpose, to show the
    ladder is real. It models a baseline (a rolling mean and standard deviation),
    so after a warmup it can report ``standardized`` (a z-score), which means a
    loop using it does not have to guess a raw threshold, it can fire at a
    principled number of standard deviations. During warmup it has no baseline yet,
    so it returns ``standardized=None`` and falls back to forcing a threshold, so
    you can watch the difference within one provider.

    What it still does not do: it models the baseline as a single Gaussian, which
    is wrong for most real channels (multi-modal, drifting, bursty). It has no
    dishabituation logic beyond the z-score, and it does not estimate its own
    error. It is a better naive than the other two, and still a naive.
    """

    loop_id = "L6"
    name = "naive:zscore-deviation"

    def __init__(self, window: int = 30, warmup: int = 8) -> None:
        self._window: deque[float] = deque(maxlen=window)
        self._warmup = warmup

    def measure(self, observation: ChannelObservation) -> Measurement:
        if observation.value is None:
            raise ValueError(
                "ZScoreDeviationProvider needs a numeric ChannelObservation.value"
            )
        x = observation.value
        n = len(self._window)
        if n < self._warmup:
            self._window.append(x)
            return Measurement(
                value=0.0,
                meaning=Meaning.DEVIATION,
                standardized=0.0,  # no baseline yet: report zero deviation, do not fire
                confounds=("cold: baseline still forming, treats everything as normal",),
                provider=self.name,
                detail={"warming_up": True, "n": n},
            )
        mean = sum(self._window) / n
        var = sum((v - mean) ** 2 for v in self._window) / n
        std = var ** 0.5
        z = 0.0 if std == 0 else (x - mean) / std
        self._window.append(x)
        return Measurement(
            value=abs(x - mean),
            meaning=Meaning.DEVIATION,
            standardized=z,
            confounds=(
                "single-Gaussian baseline: wrong for multi-modal/bursty channels",
                "no drift model: a slowly shifting baseline is read as deviation",
                "no self-error estimate",
            ),
            provider=self.name,
            detail={"mean": mean, "std": std, "n": n},
        )

    def reset(self) -> None:
        self._window.clear()
