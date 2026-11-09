"""Propagating measurement unreliability into the decision, not just the estimate.

Error-in-variables methods can propagate reliability into a corrected effect
estimate (attenuation correction, disattenuated correlation, credal sigma
envelopes). This test asks a different question: given
that a sensor reading is noisy at a known rate, where should the controller's
threshold actually sit, and when should it decline to decide at all?

These tests pin that. The maths is classical measurement-error theory applied
to a standardized reading:

    z_true_hat = r * z_obs                  (shrinkage toward the mean)
    tau_obs    = tau / r                     (threshold on the observed scale)
    band       = tau/r +/- k*sqrt((1-r)/r)   (where the reading cannot decide)
"""

import pytest

from gyre.reliability import (
    Verdict,
    deattenuate_effect,
    decision_band,
    reliability_from_retest,
    sensitivity_band,
    shrink_standardized,
    threshold_for_reliability,
)


# --- reliability from repeatability ---------------------------------------------


def test_perfect_retest_is_full_reliability():
    assert reliability_from_retest(1.0) == 1.0


def test_chance_retest_is_zero_reliability():
    # 0.5 raw agreement on a binary call is chance: no signal at all
    assert reliability_from_retest(0.5) == 0.0


def test_retest_below_chance_clamps_to_zero():
    assert reliability_from_retest(0.2) == 0.0


def test_retest_outside_range_is_rejected():
    for bad in (-0.1, 1.1):
        with pytest.raises(ValueError):
            reliability_from_retest(bad)


# --- shrinkage -------------------------------------------------------------------


def test_perfect_reliability_leaves_the_reading_alone():
    assert shrink_standardized(2.0, 1.0) == 2.0


def test_unreliable_readings_shrink_toward_the_mean():
    assert shrink_standardized(2.0, 0.5) == 1.0
    assert shrink_standardized(-3.0, 0.5) == -1.5


def test_zero_reliability_destroys_the_reading():
    assert shrink_standardized(5.0, 0.0) == 0.0


# --- the threshold ---------------------------------------------------------------


def test_threshold_is_unchanged_at_perfect_reliability():
    assert threshold_for_reliability(2.0, 1.0) == 2.0


def test_unreliable_sensors_need_more_extreme_readings():
    # a latent 2-sigma departure needs a 4-sigma OBSERVED reading at r=0.5,
    # because the observed scale is inflated by noise
    assert threshold_for_reliability(2.0, 0.5) == pytest.approx(4.0)


def test_threshold_rises_monotonically_as_reliability_falls():
    ths = [threshold_for_reliability(2.0, r) for r in (0.9, 0.7, 0.5, 0.3)]
    assert ths == sorted(ths)


def test_zero_reliability_makes_the_threshold_unreachable():
    assert threshold_for_reliability(2.0, 0.0) == float("inf")


# --- the abstain band ------------------------------------------------------------


def test_band_is_a_point_at_perfect_reliability():
    lo, hi = decision_band(2.0, 1.0)
    assert lo == hi == 2.0


def test_band_widens_as_reliability_falls():
    narrow = decision_band(2.0, 0.9)
    wide = decision_band(2.0, 0.5)
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


def test_band_brackets_the_adjusted_threshold():
    lo, hi = decision_band(2.0, 0.6)
    assert lo < threshold_for_reliability(2.0, 0.6) < hi


def test_a_reading_inside_the_band_is_undecidable():
    lo, hi = decision_band(2.0, 0.6)
    mid = (lo + hi) / 2
    assert lo <= mid <= hi  # the controller should abstain here, not guess


# --- effect de-attenuation -------------------------------------------------------


def test_deattenuation_recovers_a_larger_true_effect():
    # an observed slope of 0.3 under reliability 0.5 implies a true slope of 0.6
    assert deattenuate_effect(0.3, 0.5) == pytest.approx(0.6)


def test_deattenuation_is_identity_at_perfect_reliability():
    assert deattenuate_effect(0.3, 1.0) == 0.3


def test_deattenuation_refuses_zero_reliability():
    with pytest.raises(ValueError):
        deattenuate_effect(0.3, 0.0)


# --- the sensitivity band: the guard the NHANES sweep demands --------------------


def test_a_stable_correction_is_robust():
    # reliability known well: the correction barely moves across the sweep
    band = sensitivity_band(lambda r: deattenuate_effect(0.3, r), 0.95)
    assert band.verdict is Verdict.ROBUST


def test_a_correction_that_swings_wildly_is_fragile():
    # near-zero reliability: 1/r explodes, the "corrected" number is meaningless
    band = sensitivity_band(lambda r: deattenuate_effect(0.3, r), 0.12)
    assert band.verdict is Verdict.FRAGILE
    assert band.relative_range > 1.0


def test_sensitivity_band_reports_its_range_and_endpoints():
    band = sensitivity_band(lambda r: deattenuate_effect(0.3, r), 0.6)
    assert band.low < band.high
    assert band.relative_range > 0
    assert "0.6" in band.note or "reliability" in band.note.lower()


def test_fragile_corrections_must_not_be_reported_as_point_estimates():
    band = sensitivity_band(lambda r: deattenuate_effect(0.3, r), 0.12)
    assert not band.reportable_as_point
    assert sensitivity_band(lambda r: deattenuate_effect(0.3, r), 0.95).reportable_as_point


# --- split-conformal width floor (the coverage guarantee) ------------------------

from gyre.reliability import conformal_width_floor, interval_is_coherent  # noqa: E402


def test_width_floor_grows_with_observed_error():
    tight = conformal_width_floor([0.01, 0.02, 0.01, 0.03] * 10, alpha=0.1)
    loose = conformal_width_floor([0.2, 0.3, 0.25, 0.4] * 10, alpha=0.1)
    assert loose > tight


def test_width_floor_needs_enough_residuals_to_guarantee_coverage():
    # split conformal needs ceil((n+1)(1-alpha)) <= n, i.e. n >= 1/alpha - 1
    assert conformal_width_floor([0.1, 0.2], alpha=0.05) is None


def test_width_floor_is_a_real_quantile_of_the_residuals():
    residuals = [i / 100 for i in range(1, 101)]
    floor = conformal_width_floor(residuals, alpha=0.1)
    assert floor is not None
    # ~90th percentile of |residual|, doubled to a two-sided width
    assert 1.6 < floor < 2.1


def test_an_interval_narrower_than_the_floor_is_incoherent():
    residuals = [0.2] * 50
    floor = conformal_width_floor(residuals, alpha=0.1)
    assert not interval_is_coherent(0.01, floor)   # absurdly confident
    assert interval_is_coherent(floor + 0.1, floor)


def test_coherence_is_vacuously_true_without_a_floor():
    # no calibration data -> no basis to call an interval incoherent
    assert interval_is_coherent(0.001, None)


def test_rejects_bad_alpha():
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError):
            conformal_width_floor([0.1] * 50, alpha=bad)
