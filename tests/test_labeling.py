"""Judge pipeline and judge-qualification tests (no API calls)."""

import pytest

from gyre.labeling import (
    AcquisitionCandidate,
    JudgeVerdict,
    _parse_verdict,
    binary_entropy,
    build_panel_labels,
    cohen_kappa,
    rank_acquisition,
    gwet_ac1,
    judge_trace,
    judge_trace_panel,
    minority_recall,
    panel_to_voi_inputs,
    qualify_judge,
    retest_agreement,
    select_steps_for_human,
    step_probs_from_verdicts,
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


# --- A3: minority-recall + test-retest bars ---


def test_minority_recall_rejects_majority_only_judge():
    human = [False, False, False, True, True]
    judge = [False, False, False, False, False]  # never fires the rare class
    q = qualify_judge(judge, human)
    assert q.minority_recall == 0.0
    assert q.qualified is False


def test_minority_recall_gates_even_when_agreement_is_high():
    # 16 negatives both agree on; judge catches only 1 of 4 ruminations.
    human = [False] * 16 + [True, True, True, True]
    judge = [False] * 16 + [True, False, False, False]
    q = qualify_judge(judge, human, minrec_floor=0.5)
    assert q.minority_recall == 0.25
    assert q.qualified is False  # non-compensatory: fails on minority recall alone


def test_retest_agreement_raw():
    p1 = [True, False, True, False, True]
    assert retest_agreement(p1, p1) == 1.0
    p2 = [True, False, False, False, True]  # one disagreement of five
    assert retest_agreement(p1, p2) == pytest.approx(0.8)


def test_qualify_judge_applies_retest_bar_when_supplied():
    labels = [False, True, False, True, True]
    q = qualify_judge(labels, labels, test_retest_score=0.85, retest_floor=0.9)
    assert q.qualified is False  # perfect agreement but repeatability below floor
    assert any("retest" in r for r in q.reasons)


# --- A1: value-of-information step selection ---


def test_binary_entropy_peaks_at_half():
    assert binary_entropy(0.5) == pytest.approx(1.0)
    assert binary_entropy(0.0) == 0.0
    assert binary_entropy(1.0) == 0.0
    assert binary_entropy(0.5) > binary_entropy(0.9)


def test_select_prioritises_uncertain_steps():
    probs = [0.99, 0.5, 0.02, 0.5, 0.5]  # steps 1,3,4 are the uncertain ones
    sel = select_steps_for_human(probs, budget=2)
    assert len(sel) == 2
    assert 0 not in sel and 2 not in sel


def test_select_respects_need_weights():
    probs = [0.5, 0.5, 0.5]
    sel = select_steps_for_human(probs, budget=1, needs=[1.0, 1.0, 5.0])
    assert sel == [2]


def test_select_skips_zero_information_steps():
    probs = [1.0, 0.0, 0.5]  # only step 2 carries any information
    sel = select_steps_for_human(probs, budget=3)
    assert sel == [2]


def test_step_probs_from_verdicts_maps_confidence():
    vs = [
        JudgeVerdict(is_ruminating=True, confidence=0.9),
        JudgeVerdict(is_ruminating=False, confidence=0.8),
    ]
    probs = step_probs_from_verdicts(vs)
    assert probs[0] == pytest.approx(0.9)
    assert probs[1] == pytest.approx(0.2)


# --- A2 (model-agnostic core): judge panel + credal disagreement ---


class NeverJudge:
    name = "fake:never"

    def score_step(self, step_text, prior_texts) -> JudgeVerdict:
        return JudgeVerdict(is_ruminating=False, confidence=0.9)


def test_panel_keeps_disagreement_as_a_credal_interval():
    trace = RawTrace(steps=[TraceStep("x", index=0)])
    panel = judge_trace_panel([NeverJudge(), _always_ruminating()], trace)
    s = panel[0]
    assert s.unanimous is False
    assert s.lower == pytest.approx(0.1)  # NeverJudge: 1 - 0.9
    assert s.upper == pytest.approx(0.9)  # always: 0.9
    assert s.width > 0.5


def test_panel_unanimous_has_zero_width():
    trace = RawTrace(steps=[TraceStep(t, index=i) for i, t in enumerate(["a", "b"])])
    panel = judge_trace_panel([NeverJudge(), NeverJudge()], trace)
    assert all(s.unanimous for s in panel)
    assert all(s.width == 0.0 for s in panel)


def test_panel_disagreement_drives_voi_selection():
    # step 0 "a": KeywordJudge and NeverJudge agree (not ruminating).
    # step 1 "a": KeywordJudge fires (repeat), NeverJudge does not -> they split.
    trace = RawTrace(steps=[TraceStep(t, index=i) for i, t in enumerate(["a", "a"])])
    panel = judge_trace_panel([KeywordJudge(), NeverJudge()], trace)
    assert panel[0].unanimous and not panel[1].unanimous
    probs, needs = panel_to_voi_inputs(panel)
    sel = select_steps_for_human(probs, budget=1, needs=needs)
    assert sel == [1]  # the disputed step is the one worth a human label


def _always_ruminating():
    class _J:
        name = "fake:always"

        def score_step(self, step_text, prior_texts) -> JudgeVerdict:
            return JudgeVerdict(is_ruminating=True, confidence=0.9)

    return _J()


# --- A4 orchestration: build_panel_labels (offline, fake judges) ---


def test_build_panel_labels_routes_disputes_to_human():
    traces = [
        RawTrace(steps=[TraceStep(t, index=i) for i, t in enumerate(["a", "a"])], trace_id="t0")
    ]
    records, summary = build_panel_labels(traces, [KeywordJudge(), NeverJudge()], human_budget=5)
    steps = records[0]["steps"]
    assert steps[0]["provenance"] == "auto"        # both judges agree: not ruminating
    assert steps[0]["is_ruminating"] is False
    assert steps[1]["provenance"] == "human_needed"  # keyword fires on the repeat, never doesn't
    assert steps[1]["is_ruminating"] is None
    assert summary["auto_unanimous"] == 1 and summary["human_needed"] == 1


def test_build_panel_labels_budget_forces_majority_fallback():
    traces = [
        RawTrace(
            steps=[TraceStep(t, index=i) for i, t in enumerate(["a", "a", "b", "b"])],
            trace_id="t0",
        )
    ]
    # steps 1 and 3 are disputed; budget 1 -> one human_needed, one auto_majority
    records, summary = build_panel_labels(traces, [KeywordJudge(), NeverJudge()], human_budget=1)
    provs = [s["provenance"] for s in records[0]["steps"]]
    assert provs.count("human_needed") == 1
    assert provs.count("auto_majority") == 1
    assert summary["human_needed"] == 1


# --- source-family quorum (vendored from Aurora EXP-UN-02) ---


class _FamilyJudge:
    def __init__(self, name, family, rum, conf=0.9):
        self.name = name
        self.source_family = family
        self._rum = rum
        self._conf = conf

    def score_step(self, step_text, prior_texts) -> JudgeVerdict:
        return JudgeVerdict(is_ruminating=self._rum, confidence=self._conf)


def test_panel_collapses_same_family_judges():
    # two of three judges share a lineage; the interval must be over 2 families,
    # not diluted/narrowed by the duplicate.
    trace = RawTrace(steps=[TraceStep("x", index=0)])
    judges = [
        _FamilyJudge("q-a", "qwen", True),
        _FamilyJudge("q-b", "qwen", True),   # copied evidence, not a third vote
        _FamilyJudge("l-c", "llama", False),
    ]
    panel = judge_trace_panel(judges, trace)
    assert panel[0].n_families == 2
    assert panel[0].lower == pytest.approx(0.1)  # llama family
    assert panel[0].upper == pytest.approx(0.9)  # qwen family


def test_single_family_agreement_is_not_auto_labelled():
    # two clones of one family agree -> looks unanimous but is single-source, so it
    # must NOT be trusted as an auto label under the family quorum.
    trace = RawTrace(steps=[TraceStep("x", index=0)], trace_id="t")
    judges = [_FamilyJudge("q-a", "qwen", False), _FamilyJudge("q-b", "qwen", False)]
    records, summary = build_panel_labels([trace], judges, human_budget=5, min_families=2)
    assert summary["source_families"] == ["qwen"]
    assert records[0]["steps"][0]["provenance"] != "auto"


# --- #2: factorised uncertainty axes ---


def test_uncertainty_axes_split_vs_ambiguous():
    trace = RawTrace(steps=[TraceStep("x", index=0)])
    # two confident camps -> high model_disagreement, low incompleteness
    split = judge_trace_panel(
        [_FamilyJudge("a", "fa", True, conf=0.9), _FamilyJudge("b", "fb", False, conf=0.9)], trace
    )
    ax = split[0].axes
    assert ax.model_disagreement > 0.5
    assert ax.incompleteness < 0.5
    # everyone at ~0.5 -> low disagreement, high incompleteness + evidence
    fuzzy = judge_trace_panel(
        [_FamilyJudge("a", "fa", True, conf=0.5), _FamilyJudge("b", "fb", False, conf=0.5)], trace
    )
    ax2 = fuzzy[0].axes
    assert ax2.model_disagreement < 0.5
    assert ax2.incompleteness > 0.5
    assert ax2.evidence > 0.5


def test_max_uncertainty_is_not_auto_labelled_and_flagged_for_rubric():
    # all families at ~0.5: votes read 'unanimous' but it is really 'nobody knows'.
    trace = RawTrace(steps=[TraceStep("x", index=0)], trace_id="t")
    judges = [_FamilyJudge("a", "fa", True, conf=0.5), _FamilyJudge("b", "fb", False, conf=0.5)]
    records, summary = build_panel_labels([trace], judges, human_budget=5, min_families=2)
    assert records[0]["steps"][0]["provenance"] == "human_needed"  # not auto
    assert summary["rubric_review_candidates"] == 1


# --- #3: decision-focused acquisition + admissibility gate ---


def test_acquisition_excludes_inadmissible_with_reason():
    cands = [
        AcquisitionCandidate(index=0, decision_gain=1.0),
        AcquisitionCandidate(index=1, decision_gain=9.0, admissible=False, exclusion_reason="empty"),
        AcquisitionCandidate(index=2, decision_gain=0.5),
    ]
    picked, excluded = rank_acquisition(cands, budget=5)
    assert 1 not in picked                 # excluded BEFORE ranking, not out-competed
    assert (1, "empty") in excluded
    assert picked == [0, 2]                # ranked by decision value


def test_acquisition_uses_model_discovery_to_break_ties():
    cands = [
        AcquisitionCandidate(index=0, decision_gain=0.5, model_discovery=0.0),
        AcquisitionCandidate(index=1, decision_gain=0.5, model_discovery=0.9),
    ]
    picked, _ = rank_acquisition(cands, budget=1)
    assert picked == [1]


def test_build_panel_labels_marks_inadmissible_steps():
    trace = RawTrace(
        steps=[TraceStep("", index=0), TraceStep("a genuine disputed step", index=1)],
        trace_id="t",
    )
    judges = [_FamilyJudge("a", "fa", True), _FamilyJudge("b", "fb", False)]
    records, summary = build_panel_labels([trace], judges, human_budget=5)
    assert records[0]["steps"][0]["provenance"] == "inadmissible"
    assert records[0]["steps"][0]["is_ruminating"] is None
    assert summary["inadmissible"] == 1


# --- design-tagged per-cell qualification (vendored from ConstructLens EQA) -----

from gyre.labeling import qualify_judge_by_cell  # noqa: E402


def test_per_cell_minority_recall_catches_a_cell_blind_judge():
    # pooled bars pass (easy cell carries them) but the judge is blind to
    # rumination in the depletion cell specifically
    human = [False, False, False, False, True, True, True, True] + [False, False, True, True]
    judge = [False, False, False, False, True, True, True, True] + [False, False, False, False]
    cells = ["easy"] * 8 + ["depletion"] * 4
    q = qualify_judge_by_cell(judge, human, cells, judge_name="cellblind")
    assert q.pooled.cohen_kappa >= 0.6  # pooled agreement is fine
    assert q.cell_minority_recall["depletion"] == 0.0
    assert not q.qualified
    assert any("depletion" in r for r in q.reasons)


def test_relational_trap_condition_fails_a_trap_happy_judge():
    # a judge must fire MORE on real rumination (hard cell) than on
    # healthy-but-superficially-pathological traps (progress cell)
    human = ([False] * 8 + [True] * 8) + [False, False, False] + [True, True, True]
    judge = ([False] * 8 + [True] * 8) + [True, True, False] + [True, False, False]
    cells = ["easy"] * 16 + ["progress"] * 3 + ["hard"] * 3
    q = qualify_judge_by_cell(
        judge, human, cells, judge_name="traphappy", relational=[("progress", "hard")]
    )
    assert q.pooled.qualified  # every pooled bar clears; only the relational gate bites
    assert not q.qualified
    assert any("relational" in r for r in q.reasons)


def test_clean_judge_qualifies_across_cells():
    human = [False, True, True, False, False, True]
    judge = list(human)
    cells = ["easy"] * 3 + ["depletion"] * 3
    q = qualify_judge_by_cell(judge, human, cells, judge_name="clean")
    assert q.qualified
    assert set(q.cell_minority_recall) == {"easy", "depletion"}


# --- verbatim-evidence validity + calibration gap (vendored from Firasa EQA) ----

from gyre.labeling import (  # noqa: E402
    JudgeVerdict as _JV,
    _parse_verdict as _pv,
    calibration_gap,
    evidence_validity_rate,
    quote_is_verbatim,
)


def test_quote_is_verbatim_is_whitespace_tolerant_substring():
    assert quote_is_verbatim("same  fix again", "tried the same fix again, twice")
    assert not quote_is_verbatim("a different claim", "tried the same fix again")
    assert not quote_is_verbatim("", "any text")
    assert not quote_is_verbatim("text", "")


def test_evidence_validity_rate_counts_only_positive_verdicts():
    verdicts = [
        _JV(True, 0.9, evidence="loop detected here"),
        _JV(True, 0.9, evidence="this quote is fabricated"),
        _JV(False, 0.9),
    ]
    texts = ["a loop detected here twice", "clean step", "fine"]
    assert evidence_validity_rate(verdicts, texts) == 0.5


def test_evidence_validity_rate_is_vacuous_without_positives():
    assert evidence_validity_rate([_JV(False, 0.9)], ["step"]) == 1.0


def test_calibration_gap_measures_overconfidence():
    verdicts = [_JV(True, 1.0), _JV(True, 1.0)]
    human = [True, False]
    assert calibration_gap(verdicts, human) == 0.5


def test_parse_verdict_reads_evidence_field():
    v = _pv('{"is_ruminating": true, "confidence": 0.8, "rationale": "r", "evidence": "the same edit"}')
    assert v.evidence == "the same edit"


def test_qualify_judge_applies_evidence_bar_when_supplied():
    labels = [True, False, True, False, True, False]
    q = qualify_judge(labels, labels, judge_name="fabricator", evidence_validity=0.4)
    assert not q.qualified
    assert any("evidence" in r for r in q.reasons)


# --- per-cell SWA judge profiles + router (vendored from Firasa EQA-replication) -

from gyre.labeling import (  # noqa: E402
    profile_judge_by_cell,
    rank_judge_profiles,
    reference_skew,
    route_judges_by_cell,
    skew_weighted_agreement,
)


def test_swa_equals_kappa_when_labels_are_balanced():
    human = [True, False, True, False, True, False]
    judge = [True, False, True, False, True, True]
    assert reference_skew(human) == 0.0
    from gyre.labeling import cohen_kappa
    assert skew_weighted_agreement(judge, human) == pytest.approx(cohen_kappa(judge, human))


def test_swa_leans_on_ac1_under_skew():
    human = [False] * 9 + [True]
    judge = [False] * 9 + [True]
    from gyre.labeling import cohen_kappa, gwet_ac1
    s = reference_skew(human)
    assert s > 0.5
    expected = (1 - s) * cohen_kappa(judge, human) + s * gwet_ac1(judge, human)
    assert skew_weighted_agreement(judge, human) == pytest.approx(expected)


def _two_judge_profiles():
    human = [False, False, False, True, True, True] * 2
    cells = ["easy"] * 6 + ["depletion"] * 6
    judge_a = [False, False, False, True, True, True] + [False] * 6  # blind on depletion
    judge_b = [False, False, False, True, True, False] + [False, False, False, True, True, True]
    return {
        "a": profile_judge_by_cell(judge_a, human, cells),
        "b": profile_judge_by_cell(judge_b, human, cells),
    }


def test_router_picks_the_best_qualified_judge_per_cell():
    routes = route_judges_by_cell(_two_judge_profiles())
    assert routes["easy"] == "a"
    assert routes["depletion"] == "b"


def test_router_fails_closed_when_no_judge_qualifies():
    human = [False, False, False, True, True, True]
    cells = ["hard"] * 6
    bad1 = profile_judge_by_cell([False] * 6, human, cells)
    bad2 = profile_judge_by_cell([True] * 6, human, cells)
    routes = route_judges_by_cell({"x": bad1, "y": bad2})
    assert routes["hard"] is None


def test_ranking_uses_floor_never_the_mean():
    profiles = {
        "spiky": {
            "a": {"swa": 1.0, "minority_recall": 1.0, "n": 6},
            "b": {"swa": 1.0, "minority_recall": 1.0, "n": 6},
            "c": {"swa": 0.0, "minority_recall": 0.0, "n": 6},
        },
        "steady": {
            "a": {"swa": 0.7, "minority_recall": 1.0, "n": 6},
            "b": {"swa": 0.7, "minority_recall": 1.0, "n": 6},
            "c": {"swa": 0.7, "minority_recall": 1.0, "n": 6},
        },
    }
    ranked = rank_judge_profiles(profiles)
    assert [name for name, *_ in ranked] == ["steady", "spiky"]


# --- judge-call resilience + panel assembly from precomputed panels -------------


def test_openrouter_judge_retries_transient_failures(monkeypatch):
    import io
    import urllib.request as ur

    from gyre.labeling import OpenRouterJudge

    calls = {"n": 0}

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def flaky_urlopen(req, timeout=0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("read timed out")
        body = b'{"choices": [{"message": {"content": "{\\"is_ruminating\\": true, \\"confidence\\": 0.9, \\"rationale\\": \\"r\\"}"}}]}'
        return FakeResp(body)

    monkeypatch.setattr(ur, "urlopen", flaky_urlopen)
    judge = OpenRouterJudge("test/model", api_key="k", retries=3, backoff=0.0)
    v = judge.score_step("step", [])
    assert v.is_ruminating is True
    assert calls["n"] == 3


def test_openrouter_judge_raises_after_retry_budget(monkeypatch):
    import urllib.request as ur

    from gyre.labeling import OpenRouterJudge

    def always_timeout(req, timeout=0):
        raise TimeoutError("read timed out")

    monkeypatch.setattr(ur, "urlopen", always_timeout)
    judge = OpenRouterJudge("test/model", api_key="k", retries=2, backoff=0.0)
    with pytest.raises(TimeoutError):
        judge.score_step("step", [])
    # a dead judge must raise, never silently return a verdict (silent
    # degradation is the dangerous failure class)


def test_build_panel_labels_accepts_precomputed_panels():
    from gyre.labeling import build_panel_labels, judge_trace_panel

    traces = [
        RawTrace(
            steps=[TraceStep("try the fix", index=0), TraceStep("try the fix", index=1)],
            trace_id="t1",
        )
    ]
    j1, j2 = KeywordJudge(), KeywordJudge()
    j1.name, j2.name = "fake:kw1", "fake:kw2"
    judges = [j1, j2]
    panels = [judge_trace_panel(judges, tr) for tr in traces]

    live_records, live_summary = build_panel_labels(traces, judges, human_budget=2)
    pre_records, pre_summary = build_panel_labels(
        traces, judges, human_budget=2, panels=panels
    )
    assert pre_records == live_records
    assert pre_summary == live_summary


# --- judge abstention: a judge that cannot answer must not get a vote -----------

from gyre.labeling import JudgeAbstained  # noqa: E402


def test_null_content_raises_abstention_not_attribute_error():
    import io
    import urllib.request as ur

    from gyre.labeling import OpenRouterJudge

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def null_content(req, timeout=0):
        # real OpenRouter behaviour: content can be null (filter, reasoning-only)
        return FakeResp(b'{"choices": [{"message": {"content": null}}]}')

    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as mp:
        mp.setattr(ur, "urlopen", null_content)
        judge = OpenRouterJudge("test/model", api_key="k", retries=2, backoff=0.0)
        with _pytest.raises(JudgeAbstained):
            judge.score_step("step", [])


class _AbstainingJudge:
    """A judge that raises on one specific step, as a dead API call would."""

    def __init__(self, name, fail_on_index):
        self.name = name
        self.source_family = name
        self._fail_on = fail_on_index
        self._i = 0

    def score_step(self, step_text, prior_texts):
        i, self._i = self._i, self._i + 1
        if i == self._fail_on:
            raise JudgeAbstained("no verdict")
        return JudgeVerdict(is_ruminating=True, confidence=0.9, rationale="r")


def test_panel_excludes_an_abstaining_judge_from_that_step_only():
    trace = RawTrace(
        steps=[TraceStep("a", index=0), TraceStep("b", index=1)], trace_id="t"
    )
    judges = [
        _AbstainingJudge("famA", fail_on_index=0),
        _AbstainingJudge("famB", fail_on_index=None),
        _AbstainingJudge("famC", fail_on_index=None),
    ]
    panel = judge_trace_panel(judges, trace)
    assert panel[0].n_families == 2  # one abstained on step 0
    assert panel[1].n_families == 3  # and is back for step 1


def test_step_where_everyone_abstains_is_not_auto_labelled():
    trace = RawTrace(steps=[TraceStep("a", index=0)], trace_id="t")
    judges = [_AbstainingJudge(f"fam{i}", fail_on_index=0) for i in "AB"]
    panel = judge_trace_panel(judges, trace)
    assert panel[0].n_families == 0
    records, summary = build_panel_labels([trace], judges, human_budget=5, panels=[panel])
    step = records[0]["steps"][0]
    assert step["is_ruminating"] is None  # never guessed
    assert summary["auto_unanimous"] == 0


def test_abstention_below_quorum_blocks_auto_label():
    # two judges agree but they are ONE family after the other abstains
    trace = RawTrace(steps=[TraceStep("a", index=0)], trace_id="t")
    judges = [
        _AbstainingJudge("famA", fail_on_index=None),
        _AbstainingJudge("famB", fail_on_index=0),
    ]
    panel = judge_trace_panel(judges, trace)
    assert panel[0].n_families == 1
    records, _ = build_panel_labels([trace], judges, human_budget=5, panels=[panel])
    assert records[0]["steps"][0]["provenance"] != "auto"


# --- leave-one-out consensus (vendored from Criterion consensus_delta_run) -------

from gyre.labeling import leave_one_out_consensus, qualify_panel_loo  # noqa: E402


def test_loo_consensus_excludes_the_judge_being_graded():
    # judge "odd" disagrees on item 1; its own vote must not soften the consensus
    votes = {
        "a": [True, True, False],
        "b": [True, True, False],
        "odd": [True, False, False],
    }
    loo = leave_one_out_consensus(votes)
    assert loo["odd"] == [True, True, False]  # consensus of a+b only
    assert loo["a"] == [True, False, False] or loo["a"] == [True, True, False]


def test_loo_consensus_makes_a_self_confirming_majority_impossible():
    # two clones of the same wrong answer cannot validate each other's error
    # once family lineage is declared
    votes = {"clone1": [True], "clone2": [True], "independent": [False]}
    families = {"clone1": "famX", "clone2": "famX", "independent": "famY"}
    loo = leave_one_out_consensus(votes, families=families)
    # grading clone1 excludes its whole FAMILY, leaving only the independent vote
    assert loo["clone1"] == [False]
    assert loo["clone2"] == [False]
    assert loo["independent"] == [True]


def test_loo_consensus_refuses_when_nothing_independent_remains():
    votes = {"only": [True, False]}
    loo = leave_one_out_consensus(votes)
    assert loo["only"] == [None, None]  # no consensus exists without the judge


def test_loo_consensus_single_family_leaves_no_grader():
    votes = {"a": [True], "b": [True]}
    families = {"a": "fam", "b": "fam"}
    loo = leave_one_out_consensus(votes, families=families)
    assert loo["a"] == [None]
    assert loo["b"] == [None]


def test_loo_consensus_rejects_ragged_input():
    with pytest.raises(ValueError):
        leave_one_out_consensus({"a": [True, False], "b": [True]})


def test_qualify_panel_loo_scores_each_judge_against_labels_it_did_not_set():
    # 'lazy' never fires; the others catch the rare class. Graded LOO, lazy fails.
    votes = {
        "good1": [False, False, True, True],
        "good2": [False, False, True, True],
        "good3": [False, False, True, True],
        "lazy": [False, False, False, False],
    }
    results = qualify_panel_loo(votes)
    assert results["lazy"].qualified is False
    assert results["lazy"].minority_recall == 0.0
    assert results["good1"].qualified is True


def test_qualify_panel_loo_skips_items_with_no_independent_consensus():
    votes = {"a": [True, True], "b": [True, True]}
    families = {"a": "fam", "b": "fam"}
    results = qualify_panel_loo(votes, families=families)
    assert results["a"].n == 0  # nothing gradeable; not a silent pass
    assert results["a"].qualified is False


# --- panel retains judge evidence quotes (needed to audit the construct) --------


class _QuotingJudge:
    def __init__(self, name, quote):
        self.name = name
        self.source_family = name
        self._quote = quote

    def score_step(self, step_text, prior_texts):
        return JudgeVerdict(
            is_ruminating=True, confidence=0.9, rationale="r", evidence=self._quote
        )


def test_panel_retains_evidence_quotes_per_family():
    trace = RawTrace(steps=[TraceStep("tried the same fix again", index=0)], trace_id="t")
    judges = [_QuotingJudge("famA", "the same fix"), _QuotingJudge("famB", "again")]
    panel = judge_trace_panel(judges, trace)
    assert set(panel[0].evidence) == {"the same fix", "again"}


def test_panel_evidence_is_empty_when_judges_supply_none():
    trace = RawTrace(steps=[TraceStep("x", index=0)], trace_id="t")
    panel = judge_trace_panel([NeverJudge(), NeverJudge()], trace)
    assert panel[0].evidence == ()


def test_panel_step_evidence_defaults_so_old_records_still_load():
    from gyre.labeling import PanelStep

    ps = PanelStep(index=0, text="t", p_rum=0.5, lower=0.4, upper=0.6, votes=(True,))
    assert ps.evidence == ()


def test_build_panel_labels_writes_evidence_into_the_record():
    trace = RawTrace(steps=[TraceStep("tried the same fix again", index=0)], trace_id="t")
    judges = [_QuotingJudge("famA", "the same fix"), _QuotingJudge("famB", "the same fix")]
    records, _ = build_panel_labels(trace_list := [trace], judges, human_budget=1)
    assert records[0]["steps"][0]["evidence"] == ["the same fix", "the same fix"]


# --- retry classification: 4xx is not transient ---------------------------------


def _fake_http_error(code):
    import urllib.error

    return urllib.error.HTTPError(
        url="http://x", code=code, msg="err", hdrs=None, fp=None
    )


def _judge_with(monkeypatch, exc, retries=4):
    import urllib.request as ur

    from gyre.labeling import OpenRouterJudge

    calls = {"n": 0}

    def boom(req, timeout=0):
        calls["n"] += 1
        raise exc

    monkeypatch.setattr(ur, "urlopen", boom)
    return OpenRouterJudge("m", api_key="k", retries=retries, backoff=0.0), calls


def test_403_is_not_retried(monkeypatch):
    # A permission/quota refusal is not transient. Retrying it amplifies load
    # against whatever refused, and turns a fast failure into a slow one.
    judge, calls = _judge_with(monkeypatch, _fake_http_error(403))
    with pytest.raises(Exception):
        judge.score_step("s", [])
    assert calls["n"] == 1


def test_400_and_404_are_not_retried(monkeypatch):
    for code in (400, 404, 422):
        judge, calls = _judge_with(monkeypatch, _fake_http_error(code))
        with pytest.raises(Exception):
            judge.score_step("s", [])
        assert calls["n"] == 1, f"{code} should not be retried"


def test_429_is_retried(monkeypatch):
    judge, calls = _judge_with(monkeypatch, _fake_http_error(429), retries=3)
    with pytest.raises(Exception):
        judge.score_step("s", [])
    assert calls["n"] == 3


def test_5xx_is_retried(monkeypatch):
    judge, calls = _judge_with(monkeypatch, _fake_http_error(503), retries=3)
    with pytest.raises(Exception):
        judge.score_step("s", [])
    assert calls["n"] == 3


def test_timeout_is_still_retried(monkeypatch):
    judge, calls = _judge_with(monkeypatch, TimeoutError("read timed out"), retries=3)
    with pytest.raises(TimeoutError):
        judge.score_step("s", [])
    assert calls["n"] == 3
