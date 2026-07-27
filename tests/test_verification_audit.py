"""Burden reduction paired with an escape-rate bound.

The claim "the panel removed X% of human verification" is gameable on its own —
a panel that auto-approves everything reports a 100% cut. It only means
something paired with a bound on what the auto-approved stratum got WRONG, and
that bound comes from auditing a random sample of auto-approved items, not the
disputed ones. These tests pin the arithmetic and the refusal behaviour.
"""

import pytest

from gyre.verification_audit import (
    AuditResult,
    audit_sample_size_for,
    burden_reduction,
    escape_rate_bound,
    wilson_upper,
)


# --- burden reduction ------------------------------------------------------------


def test_burden_reduction_is_fraction_resolved_without_a_human():
    assert burden_reduction(total=100, human_reviewed=10) == 0.9


def test_burden_reduction_rejects_impossible_counts():
    with pytest.raises(ValueError):
        burden_reduction(total=10, human_reviewed=11)
    with pytest.raises(ValueError):
        burden_reduction(total=0, human_reviewed=0)


# --- escape-rate bound -----------------------------------------------------------


def test_zero_escapes_bound_matches_the_closed_form():
    # at zero escapes the Wilson upper bound is z^2 / (n + z^2)
    b = escape_rate_bound(audited=30, escapes=0)
    assert b.point == 0.0
    assert b.upper == pytest.approx(1.96**2 / (30 + 1.96**2), abs=1e-9)
    # ...which is STRICTER than the folk rule of three (3/30 = 0.10)
    assert b.upper > 3 / 30


def test_more_audited_tightens_the_bound():
    assert escape_rate_bound(audited=60, escapes=0).upper < escape_rate_bound(
        audited=30, escapes=0
    ).upper


def test_observed_escapes_raise_the_bound_above_the_point_estimate():
    b = escape_rate_bound(audited=40, escapes=2)
    assert b.point == 0.05
    assert b.upper > 0.05


def test_wilson_upper_is_bounded_by_one():
    assert wilson_upper(0, 1) <= 1.0
    assert wilson_upper(5, 5) <= 1.0


def test_auditing_nothing_gives_no_bound_not_a_free_pass():
    b = escape_rate_bound(audited=0, escapes=0)
    assert b.upper == 1.0
    assert not b.claimable
    assert "no audit" in b.note.lower()


def test_escapes_cannot_exceed_audited():
    with pytest.raises(ValueError):
        escape_rate_bound(audited=5, escapes=6)


# --- sample-size planning --------------------------------------------------------


def test_sample_size_inverts_the_bound_the_gate_actually_enforces():
    # NOT the folk rule of three (30 / 60) — the planner must agree with the gate
    assert audit_sample_size_for(0.10) == 35
    assert audit_sample_size_for(0.05) == 73


@pytest.mark.parametrize("ceiling", [0.20, 0.10, 0.05, 0.02])
def test_planned_sample_size_actually_clears_its_ceiling(ceiling):
    n = audit_sample_size_for(ceiling)
    assert escape_rate_bound(audited=n, escapes=0).upper <= ceiling
    assert escape_rate_bound(audited=n - 1, escapes=0).upper > ceiling  # and is minimal


def test_sample_size_rejects_nonsense_targets():
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError):
            audit_sample_size_for(bad)


# --- the paired result -----------------------------------------------------------


def test_audit_result_is_promotable_only_when_the_bound_clears_the_ceiling():
    good = AuditResult.build(total=200, human_reviewed=20, audited=73, escapes=0, ceiling=0.05)
    assert good.burden_reduction == 0.9
    assert good.promotable

    thin = AuditResult.build(total=200, human_reviewed=20, audited=5, escapes=0, ceiling=0.05)
    assert thin.burden_reduction == 0.9  # same headline
    assert not thin.promotable  # ...but the bound does not support it
    assert "audit" in thin.blocking_reason.lower()


def test_auto_approving_everything_is_not_promotable_without_an_audit():
    r = AuditResult.build(total=200, human_reviewed=0, audited=0, escapes=0, ceiling=0.05)
    assert r.burden_reduction == 1.0
    assert not r.promotable


def test_summary_always_reports_both_numbers():
    r = AuditResult.build(total=100, human_reviewed=12, audited=30, escapes=1, ceiling=0.15)
    s = r.summary()
    assert "88.0%" in s  # burden reduction
    assert "escape" in s.lower()
    assert "audited 30" in s


# --- cluster bootstrap + evidence depth (vendored from Criterion bootstrap_gate_cis) --

from gyre.verification_audit import (  # noqa: E402
    MIN_CLUSTERS,
    cluster_bootstrap_upper,
    escape_rate_bound_clustered,
)


def test_cluster_bootstrap_resamples_whole_clusters():
    # 10 work products, 5 items each; all defects concentrated in ONE product.
    # Resampling items independently would understate the uncertainty badly;
    # resampling products keeps the correlation and widens the interval.
    clusters = [[1] * 5] + [[0] * 5 for _ in range(9)]
    clustered = cluster_bootstrap_upper(clusters, iterations=400, seed=3)
    flat_n = sum(len(c) for c in clusters)
    flat_escapes = sum(sum(c) for c in clusters)
    assert clustered > wilson_upper(flat_escapes, flat_n)


def test_clustering_never_narrows_the_bound():
    # SAFETY INVARIANT. With identical clusters the raw bootstrap sees zero
    # between-cluster variance and reports a NARROWER interval than the
    # item-level one; a clustering correction that tightens a safety bound is
    # backwards, so the reported bound is floored at the cluster level.
    clusters = [[1, 0, 0, 0, 0] for _ in range(10)]
    raw = cluster_bootstrap_upper(clusters, iterations=400, seed=3)
    reported = escape_rate_bound_clustered(clusters, iterations=400).upper
    item_level = wilson_upper(10, 50)
    assert raw < item_level  # the trap this guards against
    assert reported >= item_level


def test_thin_cluster_count_refuses_to_bound():
    clusters = [[0] * 5 for _ in range(MIN_CLUSTERS - 1)]
    b = escape_rate_bound_clustered(clusters)
    assert not b.claimable
    assert b.upper == 1.0
    assert "cluster" in b.note.lower()


def test_clustered_bound_is_claimable_at_sufficient_depth():
    clusters = [[0] * 8 for _ in range(MIN_CLUSTERS)]
    b = escape_rate_bound_clustered(clusters)
    assert b.claimable
    assert b.point == 0.0
    assert 0.0 < b.upper < 1.0


def test_clustered_bound_rejects_non_binary_items():
    with pytest.raises(ValueError):
        escape_rate_bound_clustered([[2, 0], [0, 0]])
