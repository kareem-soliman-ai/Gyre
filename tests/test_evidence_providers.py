"""Tests for the public evidence-arrival sensor."""

from gyre.loops.rumination import IterationObservation
from gyre.providers import EvidenceNoveltyProvider, available
from gyre.synthetic import gen_evid_pivot, gen_evid_retry


def _feed(provider, trace):
    provider.reset()
    return [provider.measure(o) for o in trace.observations]


def test_evidence_novelty_registered():
    assert "naive:evidence-novelty" in available("L1")


def test_evidence_novelty_sees_information_arrival_on_retry():
    """Identical artifact retried: gain collapses while the error repeats and
    jumps back up on the step where the environment says something new."""
    st = gen_evid_retry("db_try_except", k_before=3, k_after=2)
    readings = _feed(EvidenceNoveltyProvider(), st.trace)
    values = [m.value for m in readings]
    assert values[0] == 1.0                      # first attempt maximally novel
    assert values[1] < 0.05 and values[2] < 0.05  # same artifact, same error
    # New error = information arrival. Errors share traceback boilerplate by
    # design, so lexical novelty is moderate in absolute terms; the signal is
    # the CONTRAST against the same-error readings.
    assert values[3] > 4 * max(values[1], values[2])
    assert values[3] > 0.2
    assert values[4] < 0.05                       # retry into the new error


def test_evidence_novelty_holds_on_new_hypotheses_same_error():
    """Distinct approaches into the same error: the artifact channel keeps the
    gain high, so ruling out hypotheses is not read as rumination."""
    st = gen_evid_pivot(4)
    readings = _feed(EvidenceNoveltyProvider(), st.trace)
    assert all(m.value > 0.3 for m in readings)


def test_evidence_novelty_degrades_to_artifact_only_without_errors():
    p = EvidenceNoveltyProvider()
    p.measure(IterationObservation(artifact="add a null check", index=0))
    m = p.measure(IterationObservation(artifact="add a null check", index=1))
    assert m.value < 0.05
    assert m.detail["evidence_novelty"] is None
