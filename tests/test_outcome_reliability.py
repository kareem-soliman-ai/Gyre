import pytest

from gyre.outcome_reliability import OutcomeReliabilityRegistry, SourceShiftMonitor


def test_new_source_starts_at_prior_mean_and_reports_no_evidence():
    registry = OutcomeReliabilityRegistry()
    estimate = registry.estimate("visible-tests")
    assert estimate.mean == pytest.approx(0.5)
    assert estimate.outcomes == 0
    assert not estimate.is_empirical


def test_reliability_updates_only_from_resolved_outcomes():
    registry = OutcomeReliabilityRegistry()
    registry.record_outcome("visible-tests", correct=True)
    registry.record_outcome("visible-tests", correct=True)
    registry.record_outcome("visible-tests", correct=False)
    estimate = registry.estimate("visible-tests")
    assert estimate.mean == pytest.approx(3 / 5)
    assert estimate.correct == 2
    assert estimate.incorrect == 1
    assert estimate.is_empirical


def test_source_shift_monitor_warns_only_after_lagged_outcomes():
    monitor = SourceShiftMonitor(
        recent_window=3,
        min_baseline_outcomes=4,
        deterioration_threshold=0.5,
    )
    for correct in [True, True, True, True, False, False]:
        monitor.record_outcome("scorer", correct=correct)
    assert not monitor.diagnostic("scorer").warning
    monitor.record_outcome("scorer", correct=False)
    diagnostic = monitor.diagnostic("scorer")
    assert diagnostic.warning
    assert diagnostic.baseline_reliability == 1.0
    assert diagnostic.recent_reliability == 0.0


def test_source_ids_are_required():
    registry = OutcomeReliabilityRegistry()
    with pytest.raises(ValueError):
        registry.record_outcome("", correct=True)

