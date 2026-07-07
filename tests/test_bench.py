"""Benchmark-harness tests, including the head-to-head that makes the argument.

``test_calibrated_beats_naive_on_a_labelled_trace`` builds a small labelled trace
where rumination is hidden under lexical novelty, then scores a naive lexical
sensor and a better one on the same trace. The better sensor wins, and the naive
one is exposed as needing a hand-swept threshold it would not have in production.
"""

from gyre import Meaning, Measurement
from gyre.bench import LabelledTrace, compare_providers, evaluate_provider
from gyre.providers import DiffNoveltyProvider


class _Obs:
    def __init__(self, artifact: str, concept: int) -> None:
        self.artifact = artifact
        self.concept = concept


class FakeSemanticL1:
    loop_id = "L1"
    name = "fake:semantic"

    def __init__(self) -> None:
        self._prev = None

    def measure(self, obs) -> Measurement:
        ruminating = self._prev is not None and obs.concept == self._prev
        self._prev = obs.concept
        return Measurement(
            value=0.0 if ruminating else 1.0,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            decision=ruminating,
            provider=self.name,
        )

    def reset(self) -> None:
        self._prev = None


def _trace() -> LabelledTrace:
    surfaces = [
        "alpha bravo charlie",
        "xray yankee zulu",
        "one two three four",
        "crimson viridian cerulean",
        "north south east west",
    ]
    concepts = [0, 1, 1, 1, 1]
    # ground truth: steps where the agent is stuck on the repeated concept
    labels = [False, False, True, True, True]
    obs = [_Obs(s, c) for s, c in zip(surfaces, concepts)]
    return LabelledTrace(observations=obs, labels=labels, loop_id="L1", name="hidden-rumination")


def test_calibrated_provider_is_scored_without_a_threshold():
    score = evaluate_provider(FakeSemanticL1(), [_trace()])
    assert score.calibrated is True
    assert score.best_threshold is None
    assert score.recall > 0.0


def test_naive_provider_is_scored_with_a_swept_threshold():
    score = evaluate_provider(DiffNoveltyProvider(), [_trace()])
    assert score.calibrated is False
    assert score.best_threshold is not None  # the harness had to guess for it


def test_calibrated_beats_naive_on_a_labelled_trace():
    ranked = compare_providers([DiffNoveltyProvider(), FakeSemanticL1()], [_trace()])
    # Sorted best-F1 first; the sensor that models the construct wins.
    assert ranked[0].provider == "fake:semantic"
    assert ranked[0].f1 >= ranked[1].f1
