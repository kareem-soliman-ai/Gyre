"""Synthetic corpus tests: the labels are known by construction."""

from gyre.synthetic import (
    by_difficulty,
    gen_easy,
    gen_edge,
    gen_hard,
    gen_l1_corpus,
)


def test_easy_labels_first_clean_then_ruminating():
    st = gen_easy("db_try_except", n=4)
    assert st.difficulty == "easy"
    assert st.trace.labels == [False, True, True, True]


def test_hard_starts_clean_and_ends_on_a_new_approach():
    st = gen_hard("off_by_one", tail_new=True)
    assert st.difficulty == "hard"
    assert st.trace.labels[0] is False          # first statement of the fix
    assert st.trace.labels[-1] is False         # the genuine new approach at the tail
    assert any(st.trace.labels)                 # the reworded repeats are rumination


def test_edge_has_no_rumination():
    st = gen_edge(5)
    assert st.difficulty == "edge"
    assert st.trace.labels == [False] * 5       # genuine progress, nothing recycled


def test_corpus_covers_all_difficulties():
    corpus = gen_l1_corpus()
    groups = by_difficulty(corpus)
    assert set(groups) == {"easy", "hard", "edge"}
    assert all(t.loop_id == "L1" for g in groups.values() for t in g)
