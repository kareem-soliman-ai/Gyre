"""Contract tests for the versioned Living Instrument Expedition."""

from __future__ import annotations

import pytest

from gyre.challenge.living_expedition import (
    Adaptation,
    control_efficiency,
    LivingInstrumentExpedition,
    LivingInstrumentExpeditionV21,
    Orientation,
    RepairTarget,
    SalvageTarget,
    ShiftPlan,
    SurveyMode,
)


def test_public_status_uses_stable_ids_and_narrative_cues_not_latent_names():
    mission = LivingInstrumentExpedition(seed=17)
    status = mission.status()
    assert tuple(entry.variable_id for entry in status.phenomena) == (
        "trace-17",
        "trace-42",
        "trace-88",
    )
    assert all(entry.alias is None for entry in status.phenomena)
    assert status.cues
    public_text = " ".join(cue.description for cue in status.cues).lower()
    for latent_name in (
        "crew_condition",
        "shelter_integrity",
        "crop_vitality",
        "fabricator_readiness",
        "instrument_fidelity",
    ):
        assert latent_name not in public_text


def test_same_seed_and_plan_sequence_are_deterministic():
    first = LivingInstrumentExpedition(seed=33)
    second = LivingInstrumentExpedition(seed=33)
    plan = ShiftPlan(cultivation=3, fabrication=3, shelter=2)
    for _ in range(4):
        assert first.advance(plan) == second.advance(plan)
    assert first.finish() == second.finish()


def test_shift_power_is_bounded_and_cannot_exceed_known_charge():
    mission = LivingInstrumentExpedition(seed=7)
    with pytest.raises(ValueError, match="power ceiling"):
        mission.advance(ShiftPlan(cultivation=4, fabrication=4, shelter=1))
    with pytest.raises(ValueError, match="non-negative"):
        ShiftPlan(cultivation=-1)


def test_active_survey_changes_ecology_and_degrades_instrument_more_than_quiet():
    active = LivingInstrumentExpedition(seed=19)
    quiet = LivingInstrumentExpedition(seed=19)
    active.advance(
        ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            survey_mode=SurveyMode.ACTIVE,
            survey_focus="trace-17",
            survey_intensity=0.7,
        )
    )
    quiet.advance(
        ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            survey_mode=SurveyMode.QUIET,
            survey_focus="trace-17",
        )
    )
    active_outcome = active.finish()
    quiet_outcome = quiet.finish()
    assert active_outcome.disturbance_burden > quiet_outcome.disturbance_burden
    assert active_outcome.revealed_state.instrument_fidelity < (
        quiet_outcome.revealed_state.instrument_fidelity
    )
    assert (
        active_outcome.revealed_ecology["trace-17"].abundance
        != quiet_outcome.revealed_ecology["trace-17"].abundance
    )


def test_world_contains_varied_orientation_and_adaptation_classes():
    outcome = LivingInstrumentExpedition(seed=23).finish()
    profiles = tuple(outcome.revealed_ecology.values())
    assert {profile.orientation for profile in profiles} == set(Orientation)
    assert {profile.adaptation for profile in profiles} == set(Adaptation)


def test_repeated_exposure_habituates_one_profile_and_sensitises_another():
    mission = LivingInstrumentExpedition(seed=23, max_shifts=8)
    revealed = mission.finish().revealed_ecology
    habituating_id = next(
        variable_id
        for variable_id, profile in revealed.items()
        if profile.adaptation is Adaptation.HABITUATION
    )
    sensitising_id = next(
        variable_id
        for variable_id, profile in revealed.items()
        if profile.adaptation is Adaptation.SENSITISATION
    )

    habituating = LivingInstrumentExpedition(seed=23, max_shifts=8)
    sensitising = LivingInstrumentExpedition(seed=23, max_shifts=8)
    receipts = []
    for _ in range(3):
        receipts.append(
            habituating.advance(
                ShiftPlan(
                    survey_mode=SurveyMode.ACTIVE,
                    survey_focus=habituating_id,
                    survey_intensity=0.6,
                )
            )
        )
    sens_receipts = []
    for _ in range(3):
        sens_receipts.append(
            sensitising.advance(
                ShiftPlan(
                    survey_mode=SurveyMode.ACTIVE,
                    survey_focus=sensitising_id,
                    survey_intensity=0.6,
                )
            )
        )
    hab_effects = [abs(receipt.ecology_shift) for receipt in receipts]
    sens_effects = [abs(receipt.ecology_shift) for receipt in sens_receipts]
    assert hab_effects[-1] < hab_effects[0]
    assert sens_effects[-1] > sens_effects[0]


def test_repair_consumes_spares_and_salvage_is_irreversible():
    repaired = LivingInstrumentExpedition(seed=41)
    before = repaired.status().stores.spares
    repaired.advance(
        ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            repair_target=RepairTarget.INSTRUMENT,
            repair_units=2,
        )
    )
    repaired_outcome = repaired.finish()
    assert repaired.status().stores.spares == before - 2
    assert repaired_outcome.repairs == 2

    salvaged = LivingInstrumentExpedition(seed=41)
    salvage_before = salvaged.status().stores.spares
    salvaged.advance(ShiftPlan(salvage_target=SalvageTarget.FABRICATOR))
    assert salvaged.status().stores.spares == salvage_before + 3
    with pytest.raises(ValueError, match="already been salvaged"):
        salvaged.advance(ShiftPlan(salvage_target=SalvageTarget.FABRICATOR))
    assert (
        salvaged.finish().revealed_state.fabrication_capacity
        < repaired_outcome.revealed_state.fabrication_capacity
    )


def test_names_do_not_change_outcomes_and_estimates_score_separately():
    named = LivingInstrumentExpedition(seed=59)
    unnamed = LivingInstrumentExpedition(seed=59)
    named.name_variable("trace-17", "possible night pollinator")
    named.add_hypothesis(
        "trace-17",
        "Strong scans reduce later visits.",
        confidence=0.65,
    )
    revealed = LivingInstrumentExpedition(seed=59).finish().revealed_ecology
    profile = revealed["trace-17"]
    named.submit_estimate(
        "trace-17",
        orientation=profile.orientation,
        adaptation=profile.adaptation,
        confidence=0.8,
    )
    plan = ShiftPlan(cultivation=3, fabrication=3, shelter=2)
    for _ in range(3):
        named.advance(plan)
        unnamed.advance(plan)
    named_outcome = named.finish()
    unnamed_outcome = unnamed.finish()
    assert named_outcome.mission_score == pytest.approx(
        unnamed_outcome.mission_score
    )
    assert named_outcome.causal_recovery_score > unnamed_outcome.causal_recovery_score


def test_idle_policy_cannot_pass_fixed_production_quotas():
    mission = LivingInstrumentExpedition(seed=83, max_shifts=4)
    for _ in range(mission.max_shifts):
        mission.advance(ShiftPlan())
    outcome = mission.finish()
    assert not outcome.mission_accomplished
    assert not outcome.gates["food_quota"]
    assert not outcome.gates["cargo_quota"]


def test_finished_mission_rejects_new_actions():
    mission = LivingInstrumentExpedition(seed=101)
    mission.finish()
    with pytest.raises(RuntimeError, match="finished"):
        mission.advance(ShiftPlan())


def test_v21_tightens_both_production_gates_without_mutating_v20():
    v20 = LivingInstrumentExpedition(seed=3)
    v21 = LivingInstrumentExpeditionV21(seed=3)
    assert v20.version == "2.0"
    assert v20.quotas.food == pytest.approx(18.0)
    assert v20.quotas.cargo == pytest.approx(15.0)
    assert v21.version == "2.1"
    assert v21.quotas.food == pytest.approx(22.0)
    assert v21.quotas.cargo == pytest.approx(22.0)


def test_efficiency_is_separate_from_mission_attainment():
    efficient = LivingInstrumentExpeditionV21(seed=29)
    wasteful = LivingInstrumentExpeditionV21(seed=29)
    for _ in range(4):
        efficient.advance(ShiftPlan(cultivation=2, fabrication=2, shelter=1))
        wasteful.advance(
            ShiftPlan(
                cultivation=2,
                fabrication=2,
                shelter=1,
                survey_mode=SurveyMode.ACTIVE,
                survey_focus="trace-17",
                survey_intensity=0.5,
            )
        )
    efficient_outcome = efficient.finish()
    wasteful_outcome = wasteful.finish()
    assert 0.0 <= control_efficiency(efficient_outcome).score <= 100.0
    assert (
        control_efficiency(efficient_outcome).score
        > control_efficiency(wasteful_outcome).score
    )
