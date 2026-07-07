"""Judge pipeline and judge-qualification tests (no API calls)."""

from gyre.labeling import (
    JudgeVerdict,
    _parse_verdict,
    cohen_kappa,
    gwet_ac1,
    judge_trace,
    qualify_judge,
)
from gyre.traces import RawTrace, TraceStep


class KeywordJudge:
    """A deterministic fake judge: flags a step ruminating if it repeats a keyword
    that appeared in a prior step. Stands in for an LLM so tests need no API."""

    name = "fake:keyword"

    def score_step(self, step_text, prior_texts) -> JudgeVerdict:
        rum = any(step_text.strip() == p.strip() for p in prior_texts)
        return JudgeVerdict(is_ruminating=rum, confidence=0.9, rationale="repeat" if rum else "new")


def test_judge_trace_labels_each_step_with_context():
    trace = RawTrace(steps=[TraceStep(t, index=i) for i, t in enumerate(["a", "b", "a", "a"])])
    scored = judge_trace(KeywordJudge(), trace)
    assert [s.is_ruminating for s in scored.steps] == [False, False, True, True]
    assert scored.steps[2].scorer == "fake:keyword"


def test_parse_verdict_tolerates_surrounding_prose():
    v = _parse_verdict('Sure! {"is_ruminating": true, "confidence": 0.8, "rationale": "x"} done')
    assert v.is_ruminating is True and v.confidence == 0.8


def test_parse_verdict_falls_back_safely_on_garbage():
    v = _parse_verdict("no json here")
    assert v.is_ruminating is False and v.confidence == 0.0


def test_perfect_agreement_qualifies():
    labels = [False, True, False, True, False]
    q = qualify_judge(labels, labels)
    assert q.qualified is True
    assert q.cohen_kappa == 1.0
    assert q.gwet_ac1 == 1.0


def test_majority_class_only_judge_is_rejected():
    # Judge never fires; human has some rumination. Raw agreement looks okay, but
    # kappa collapses and AC1 should not carry it over the floor here.
    human = [False, False, False, True, True]
    judge = [False, False, False, False, False]
    q = qualify_judge(judge, human)
    assert q.qualified is False
    assert q.cohen_kappa < 0.6


def test_gwet_ac1_stays_defined_under_imbalance():
    # Heavy majority class where both raters mostly agree; AC1 should be high and
    # finite where kappa is unstable.
    a = [False] * 18 + [True, True]
    b = [False] * 18 + [True, True]
    assert gwet_ac1(a, b) == 1.0
    assert cohen_kappa(a, b) == 1.0
