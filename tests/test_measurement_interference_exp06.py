"""Contract tests for the EXP-06 qualification baseline."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from gyre.challenge.observer_effects import (
    InterferenceMechanism,
    ObserverEffectProfile,
)


ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = (
    ROOT
    / "experiments"
    / "EXP-06_MeasurementInterferenceQualification_2026-07-28"
)
SCRIPT = EXP_DIR / "scripts" / "run_qualification.py"


def _module():
    spec = importlib.util.spec_from_file_location("exp06_run_qualification", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_experiment_surfaces_and_receipt_exist():
    assert SCRIPT.is_file()
    assert (EXP_DIR / "docs" / "PREREGISTRATION.md").is_file()
    assert (EXP_DIR / "results" / "ANALYSIS.md").is_file()
    assert list((EXP_DIR / "results").glob("qualification_*.json"))


@pytest.mark.parametrize("mechanism", list(InterferenceMechanism))
def test_fitter_recovers_each_family_from_an_exact_curve(mechanism):
    module = _module()
    profile = ObserverEffectProfile(
        0.2,
        0.11,
        0.07,
        mechanism,
    )
    curve = {
        intensity: (
            effect.measurand_shift,
            effect.mechanism_shift,
            effect.instrument_bias_shift,
        )
        for intensity in module.CALIBRATION_INTENSITIES
        for effect in (profile.effect_at(intensity),)
    }
    fitted, _ = module.fit_profile(curve)
    assert fitted.mechanism is mechanism
    assert fitted.measurand_shift == pytest.approx(profile.measurand_shift)
    assert fitted.mechanism_shift == pytest.approx(profile.mechanism_shift)
    assert fitted.instrument_bias_shift == pytest.approx(
        profile.instrument_bias_shift
    )


def test_exact_accounting_beats_passive_assumption_for_high_interference():
    module = _module()
    profile = ObserverEffectProfile(
        0.35,
        0.18,
        0.14,
        InterferenceMechanism.LINEAR,
    )
    seed = 1907
    naive = module.evaluate_policy(profile, None, seed=seed)
    exact = module.evaluate_policy(profile, profile, seed=seed)
    assert exact < naive
