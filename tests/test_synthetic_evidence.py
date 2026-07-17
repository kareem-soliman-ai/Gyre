"""Evidence-channel synthetic cells: labels known by construction.

These cells exist to test the information-arrival hypothesis: rumination is not
low *output* novelty, it is low *information* arrival, and the environment's
response (the error) is the channel the agent cannot game. Each cell is an
adversarial trap for one sensor family:

- evid-easy    : identical artifact + identical error. Everyone should catch it.
- evid-hard    : reworded artifact + identical error. Lexical artifact sensors fail.
- evid-retry   : identical artifact retried, error CHANGES mid-trace. The step
                 that surfaces a new error is information arrival, not rumination.
                 Every artifact-only sensor (lexical or semantic) false-fires here.
- evid-pivot   : genuinely new approaches that all fail with the SAME error. New
                 hypothesis ruled out = information gained. Error-only sensors
                 false-fire here.
- evid-progress: distinct fixes, error moves downstream each step. Control cell;
                 nothing is rumination.
"""

from gyre.synthetic import (
    by_difficulty,
    gen_evid_easy,
    gen_evid_hard,
    gen_evid_pivot,
    gen_evid_progress,
    gen_evid_retry,
    gen_l1_evidence_corpus,
)


def test_evid_easy_identical_artifact_and_error():
    st = gen_evid_easy("db_try_except", n=4)
    assert st.difficulty == "evid-easy"
    assert st.trace.labels == [False, True, True, True]
    obs = st.trace.observations
    assert all(o.error is not None for o in obs)
    assert len({o.error for o in obs}) == 1          # error never changes
    assert len({o.artifact for o in obs}) == 1       # artifact never changes


def test_evid_hard_reworded_artifact_same_error():
    st = gen_evid_hard("null_check")
    assert st.difficulty == "evid-hard"
    obs = st.trace.observations
    assert st.trace.labels[0] is False
    assert all(st.trace.labels[1:])                  # every rewording is rumination
    assert len({o.error for o in obs}) == 1          # error never changes
    assert len({o.artifact for o in obs}) > 1        # artifact is reworded


def test_evid_retry_new_error_is_information_arrival():
    st = gen_evid_retry("off_by_one", k_before=3, k_after=2)
    assert st.difficulty == "evid-retry"
    obs, labels = st.trace.observations, st.trace.labels
    # identical artifact throughout: the artifact channel is silent by design
    assert len({o.artifact for o in obs}) == 1
    # first attempt clean; same-error retries ruminate; the step where the
    # environment says something NEW is information arrival (False); retries
    # into the new error ruminate again.
    assert labels == [False, True, True, False, True]
    errors = [o.error for o in obs]
    assert errors[0] == errors[1] == errors[2]
    assert errors[3] != errors[2]
    assert errors[3] == errors[4]


def test_evid_pivot_new_approaches_same_error_is_not_rumination():
    st = gen_evid_pivot(n=4)
    assert st.difficulty == "evid-pivot"
    obs, labels = st.trace.observations, st.trace.labels
    assert labels == [False] * 4                     # each hypothesis is new
    assert len({o.error for o in obs}) == 1          # environment repeats itself
    assert len({o.artifact for o in obs}) == 4       # approaches are all distinct


def test_evid_progress_control_cell():
    st = gen_evid_progress(n=4)
    assert st.difficulty == "evid-progress"
    obs, labels = st.trace.observations, st.trace.labels
    assert labels == [False] * 4
    assert len({o.error for o in obs}) == 4          # error moves every step


def test_evidence_corpus_covers_all_cells():
    corpus = gen_l1_evidence_corpus()
    groups = by_difficulty(corpus)
    assert set(groups) == {
        "evid-easy", "evid-hard", "evid-retry", "evid-pivot", "evid-progress",
    }
    assert all(t.loop_id == "L1" for g in groups.values() for t in g)
