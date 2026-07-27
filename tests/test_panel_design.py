"""Closed-form panel design calculator: what a panel must achieve, before spending.

Vendored pattern from Criterion Labs' agreement-sensitivity sweep, which derives
metrics analytically over a (prevalence x sensitivity x specificity) grid and
costs nothing to run. Re-parameterised for the outer loop: given a defect base
rate and a panel's sensitivity/specificity, what burden reduction and escape
rate FOLLOW, and how many auto-approved items must be audited to bound it?

This turns "how good does the panel need to be" from a guess into a table.
"""

import pytest

from gyre.panel_design import PanelOperatingPoint, escape_frontier, operating_point


# --- the closed form -------------------------------------------------------------


def test_perfect_panel_has_zero_escapes():
    op = operating_point(prevalence=0.2, sensitivity=1.0, specificity=1.0)
    assert op.escape_rate == 0.0
    assert op.burden_reduction == pytest.approx(0.8)  # only the flagged 20% reach a human


def test_blind_approve_everything_panel_has_escape_rate_equal_to_prevalence():
    op = operating_point(prevalence=0.1, sensitivity=0.0, specificity=1.0)
    assert op.burden_reduction == 1.0  # nothing routed to a human
    assert op.escape_rate == pytest.approx(0.1)  # ...and every defect escapes


def test_escape_rate_is_defects_among_auto_approved_not_overall_miss_rate():
    # 10% prevalence, catches 80% of defects, 10% false-flag rate on clean items
    op = operating_point(prevalence=0.1, sensitivity=0.8, specificity=0.9)
    # auto-approved = missed defects (0.1*0.2=0.02) + correctly passed clean (0.9*0.9=0.81)
    assert op.auto_approved_fraction == pytest.approx(0.83)
    assert op.escape_rate == pytest.approx(0.02 / 0.83)


def test_higher_sensitivity_lowers_escapes_but_costs_burden():
    lo = operating_point(prevalence=0.2, sensitivity=0.6, specificity=0.9)
    hi = operating_point(prevalence=0.2, sensitivity=0.95, specificity=0.9)
    assert hi.escape_rate < lo.escape_rate
    assert hi.burden_reduction < lo.burden_reduction  # the trade is explicit


def test_escape_rate_is_not_comparable_across_specificities():
    # Same sensitivity => the SAME defects are missed. Only the denominator moves.
    tight = operating_point(prevalence=0.2, sensitivity=0.8, specificity=0.95)
    loose = operating_point(prevalence=0.2, sensitivity=0.8, specificity=0.60)
    assert loose.burden_reduction < tight.burden_reduction  # false flags cost burden
    # A trigger-happy panel scores a WORSE escape rate purely because its
    # auto-approved pool shrank — the numerator never changed.
    assert loose.escape_rate > tight.escape_rate
    # missed_per_100 is invariant to specificity: the metric to compare panels on
    assert loose.missed_per_100 == pytest.approx(tight.missed_per_100)


def test_rejects_out_of_range_inputs():
    for bad in ({"prevalence": 1.5}, {"sensitivity": -0.1}, {"specificity": 2.0}):
        kwargs = {"prevalence": 0.2, "sensitivity": 0.8, "specificity": 0.9, **bad}
        with pytest.raises(ValueError):
            operating_point(**kwargs)


# --- required audit depth --------------------------------------------------------


def test_operating_point_reports_the_audit_needed_to_bound_its_own_escapes():
    op = operating_point(prevalence=0.05, sensitivity=0.9, specificity=0.9)
    # to demonstrate a ceiling at the point escape rate you must audit enough
    n = op.audit_needed(ceiling=0.05)
    assert n > 0
    assert isinstance(n, int)


def test_a_ceiling_below_the_expected_escape_rate_is_unreachable():
    op = operating_point(prevalence=0.5, sensitivity=0.1, specificity=0.9)
    assert op.escape_rate > 0.1
    assert op.audit_needed(ceiling=0.05) is None  # no audit size can prove it


# --- the frontier ----------------------------------------------------------------


def test_frontier_returns_one_row_per_sensitivity_and_is_ordered():
    rows = escape_frontier(prevalence=0.1, sensitivities=[0.5, 0.7, 0.9], specificity=0.9)
    assert [r.sensitivity for r in rows] == [0.5, 0.7, 0.9]
    assert all(isinstance(r, PanelOperatingPoint) for r in rows)
    assert rows[0].escape_rate > rows[-1].escape_rate


def test_frontier_finds_the_minimum_sensitivity_meeting_a_ceiling():
    rows = escape_frontier(
        prevalence=0.1, sensitivities=[i / 20 for i in range(21)], specificity=0.9
    )
    ok = [r for r in rows if r.escape_rate <= 0.01]
    assert ok, "some sensitivity should reach a 1% escape rate at 10% prevalence"
    assert ok[0].sensitivity < 1.0  # and it should not require perfection
