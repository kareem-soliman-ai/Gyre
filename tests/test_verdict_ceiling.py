"""Non-compensatory verdict ceiling with separated poles.

Vendored from Criterion Labs' profile_code severity logic, including the bug it
documents: an earlier version took min(capability_credit, ceiling), which let a
single MINOR gap score BELOW an artefact containing a live critical defect — a
straight inversion. The fix is that the verdict IS the ceiling, with coverage
reported alongside and never multiplied or min'd in.

Applied to outer-loop verification: positive indicators (baseline named,
falsifiable criterion...) and negative indicators (silent degradation,
self-approval...) are counted separately and never netted. One demonstrated
BLOCKER defect caps the verdict at reject, regardless of how much good practice
sits next to it — and no majority of seats can vote it away.
"""

import pytest

from gyre.verdict_ceiling import (
    Severity,
    IndicatorFinding,
    ceiling_for,
    verdict_from_findings,
)


def _neg(name, severity, present=True, evidence="quoted text"):
    return IndicatorFinding(
        indicator=name, negative=True, present=present, severity=severity, evidence=evidence
    )


def _pos(name, present=True, severity=Severity.MAJOR, evidence="quoted text"):
    return IndicatorFinding(
        indicator=name, negative=False, present=present, severity=severity, evidence=evidence
    )


# --- the ceiling function --------------------------------------------------------


def test_ceiling_is_monotone_in_severity():
    ceilings = [ceiling_for(s) for s in
                (Severity.NONE, Severity.INFO, Severity.MINOR, Severity.MAJOR,
                 Severity.CRITICAL, Severity.BLOCKER)]
    assert ceilings == sorted(ceilings, reverse=True)
    assert ceiling_for(Severity.BLOCKER) == 0.0
    assert ceiling_for(Severity.NONE) == 1.0


# --- poles stay separated -------------------------------------------------------


def test_positives_and_negatives_are_counted_never_netted():
    v = verdict_from_findings([
        _pos("V1"), _pos("V2"), _pos("V5"),
        _neg("N1", Severity.MAJOR),
    ])
    assert v.capabilities_present == 3
    assert v.violations_present == 1
    assert "3" in v.summary() and "1" in v.summary()


def test_a_blocker_caps_the_verdict_at_zero_however_much_good_practice_exists():
    good = [_pos(f"V{i}") for i in range(1, 6)]
    v = verdict_from_findings(good + [_neg("N2", Severity.BLOCKER)])
    assert v.score == 0.0
    assert not v.acceptable
    assert "N2" in v.blocking_indicators


def test_the_min_inversion_bug_cannot_recur():
    # REGRESSION GUARD. A lone MINOR gap with no other coverage must NEVER score
    # below an artefact carrying a live BLOCKER.
    lone_minor_gap = verdict_from_findings([
        _pos("V1", present=False, severity=Severity.MINOR),  # applicable, absent
    ])
    live_blocker = verdict_from_findings([
        _pos("V1"), _pos("V2"), _neg("N1", Severity.BLOCKER),
    ])
    assert lone_minor_gap.score > live_blocker.score


def test_an_absent_applicable_protection_is_itself_a_risk():
    # the hardcoded-secret case: nothing "fires", a protection is simply missing
    v = verdict_from_findings([_pos("V3", present=False, severity=Severity.BLOCKER)])
    assert v.score == 0.0
    assert "V3" in v.blocking_indicators


def test_absent_negative_indicators_do_not_penalise():
    v = verdict_from_findings([_pos("V1"), _neg("N1", Severity.BLOCKER, present=False)])
    assert v.score == 1.0
    assert v.acceptable


# --- evidence discipline ---------------------------------------------------------


def test_a_negative_finding_without_evidence_cannot_block():
    v = verdict_from_findings([
        _pos("V1"),
        _neg("N1", Severity.BLOCKER, evidence=""),  # asserted, unquoted
    ])
    assert v.score == 1.0
    assert "N1" in v.unevidenced
    assert not v.blocking_indicators


def test_unqualified_indicators_can_never_gate():
    f = _neg("N9", Severity.BLOCKER)
    f = IndicatorFinding(**{**f.__dict__, "qualified": False})
    v = verdict_from_findings([_pos("V1"), f])
    assert v.score == 1.0
    assert "N9" in v.ignored_unqualified


# --- coverage is reported, never multiplied in -----------------------------------


def test_coverage_is_reported_alongside_and_does_not_change_the_score():
    # Same worst risk (a MAJOR violation) at very different coverage. The score
    # tracks the risk only; coverage is information for the reader.
    high = verdict_from_findings([
        _pos("V1"), _pos("V2"), _pos("V3"), _neg("N1", Severity.MAJOR),
    ])
    low = verdict_from_findings([
        _pos("V1"),
        _pos("V2", present=False, severity=Severity.INFO),  # a lesser gap
        _neg("N1", Severity.MAJOR),
    ])
    assert high.coverage == 1.0
    assert low.coverage == pytest.approx(0.5)
    assert high.score == low.score == ceiling_for(Severity.MAJOR)


def test_empty_findings_are_not_an_automatic_pass():
    v = verdict_from_findings([])
    assert not v.acceptable
    assert "no findings" in v.summary().lower()


def test_rejects_unknown_severity():
    with pytest.raises((ValueError, TypeError)):
        ceiling_for("catastrophic")
