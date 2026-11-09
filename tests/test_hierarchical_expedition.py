"""Contract tests for persistent within-variant heterogeneity in v2.2."""

from __future__ import annotations

import pytest

from gyre.challenge.hierarchical_expedition import (
    HierarchicalShiftPlan,
    LivingInstrumentExpeditionV22,
    LivingInstrumentExpeditionV221,
    OperationalFamily,
    ResponseDirection,
)
from gyre.challenge.living_expedition import ShiftPlan, SurveyMode


def _catalogue_signature(mission: LivingInstrumentExpeditionV22) -> tuple:
    status = mission.status()
    return tuple(
        (
            family.value,
            tuple(
                (variant.variant_id, variant.cue, variant.unit_ids)
                for variant in status.variants[family]
            ),
        )
        for family in OperationalFamily
    )


def test_v22_exposes_a_three_by_four_hierarchy_without_latent_coefficients():
    mission = LivingInstrumentExpeditionV22(seed=17)
    status = mission.status()
    assert mission.version == "2.2"
    for family in OperationalFamily:
        variants = status.variants[family]
        assert len(variants) == 3
        assert all(len(variant.unit_ids) == 4 for variant in variants)
    public_text = repr(status.variants).lower()
    for forbidden in (
        "base_multiplier",
        "weather_slope",
        "persistent_offset",
        "exception_to_variant_rule",
    ):
        assert forbidden not in public_text


def test_same_seed_and_hierarchical_sequence_are_deterministic():
    first = LivingInstrumentExpeditionV22(seed=33)
    second = LivingInstrumentExpeditionV22(seed=33)
    assert _catalogue_signature(first) == _catalogue_signature(second)
    plan = HierarchicalShiftPlan(
        allocation=ShiftPlan(cultivation=3, fabrication=3, shelter=2)
    )
    for _ in range(4):
        assert first.advance(plan) == second.advance(plan)
    assert first.finish() == second.finish()


def test_unit_choices_change_actual_receipts_under_a_matched_base_plan():
    first = LivingInstrumentExpeditionV22(seed=49)
    second = LivingInstrumentExpeditionV22(seed=49)
    variants = first.status().variants
    food_units = variants[OperationalFamily.FOOD][0].unit_ids
    base = ShiftPlan(cultivation=4, fabrication=2, shelter=2)
    receipt_a = first.advance(
        HierarchicalShiftPlan(allocation=base, food_unit=food_units[0])
    )
    receipt_b = second.advance(
        HierarchicalShiftPlan(allocation=base, food_unit=food_units[1])
    )
    assert receipt_a.food_delta != pytest.approx(receipt_b.food_delta)
    assert receipt_a.stores.food_produced == pytest.approx(receipt_a.food_delta)
    assert receipt_b.stores.food_produced == pytest.approx(receipt_b.food_delta)


def test_invalid_or_cross_family_unit_is_rejected():
    mission = LivingInstrumentExpeditionV22(seed=51)
    cargo_unit = mission.status().variants[OperationalFamily.CARGO][0].unit_ids[0]
    with pytest.raises(KeyError, match="food unit"):
        mission.advance(
            HierarchicalShiftPlan(
                allocation=ShiftPlan(cultivation=1),
                food_unit=cargo_unit,
            )
        )


def test_terminal_reveal_has_persistent_variance_and_one_exception_per_variant():
    outcome = LivingInstrumentExpeditionV22(seed=63).finish()
    for family, variants in outcome.revealed_variants.items():
        assert family in OperationalFamily
        for variant in variants:
            offsets = {unit.persistent_offset for unit in variant.units}
            assert len(offsets) == 4
            assert sum(unit.exception_to_variant_rule for unit in variant.units) == 1
            majority = variant.majority_weather_response
            assert sum(
                unit.weather_response is majority for unit in variant.units
            ) == 3


def test_each_organism_family_has_a_majority_and_persistent_exception():
    outcome = LivingInstrumentExpeditionV22(seed=71).finish()
    for trace_id, family in outcome.revealed_organisms.items():
        assert trace_id.startswith("trace-")
        assert len(family.individuals) == 4
        assert sum(
            individual.exception_to_family_rule
            for individual in family.individuals
        ) == 1
        assert sum(
            individual.orientation is family.majority_orientation
            and individual.adaptation is family.majority_adaptation
            for individual in family.individuals
        ) == 3


def test_targeting_an_ecological_exception_changes_the_signed_response():
    reference = LivingInstrumentExpeditionV22(seed=79)
    reveal = reference.finish()
    trace_id, family = next(iter(reveal.revealed_organisms.items()))
    majority_id = next(
        item.unit_id
        for item in family.individuals
        if not item.exception_to_family_rule
    )
    exception_id = next(
        item.unit_id
        for item in family.individuals
        if item.exception_to_family_rule
    )
    majority = LivingInstrumentExpeditionV22(seed=79)
    exception = LivingInstrumentExpeditionV22(seed=79)
    allocation = ShiftPlan(
        cultivation=2,
        fabrication=2,
        shelter=1,
        survey_mode=SurveyMode.ACTIVE,
        survey_focus=trace_id,
        survey_intensity=0.7,
    )
    majority_receipt = majority.advance(
        HierarchicalShiftPlan(
            allocation=allocation,
            organism_subject=majority_id,
        )
    )
    exception_receipt = exception.advance(
        HierarchicalShiftPlan(
            allocation=allocation,
            organism_subject=exception_id,
        )
    )
    assert majority_receipt.organism_subject == majority_id
    assert exception_receipt.organism_subject == exception_id
    assert majority_receipt.ecology_shift * exception_receipt.ecology_shift <= 0
    assert majority_receipt.ecology_shift != pytest.approx(
        exception_receipt.ecology_shift
    )


def test_majority_rule_and_exception_calibration_are_scored_separately():
    mission = LivingInstrumentExpeditionV22(seed=91)
    revealed = LivingInstrumentExpeditionV22(seed=91).finish()
    variant = revealed.revealed_variants[OperationalFamily.POWER][0]
    mission.submit_variant_estimate(
        variant.variant_id,
        weather_response=variant.majority_weather_response,
        exception_fraction=0.25,
        confidence=0.8,
    )
    outcome = mission.finish()
    assert outcome.majority_rule_score > 0.0
    assert outcome.exception_calibration_score > 0.0
    assert outcome.hierarchical_recovery_score > 0.0


def test_variant_labels_are_useful_but_do_not_fully_determine_unit_effects():
    outcome = LivingInstrumentExpeditionV22(seed=103).finish()
    variant = outcome.revealed_variants[OperationalFamily.DRIVE][0]
    effects = [
        unit.effect_at(weather=0.8, load=0.75)
        for unit in variant.units
    ]
    assert len(set(effects)) == 4
    assert variant.majority_weather_response in {
        ResponseDirection.DECREASES,
        ResponseDirection.STABLE,
        ResponseDirection.INCREASES,
    }


def test_participant_names_do_not_change_v22_outcomes():
    named = LivingInstrumentExpeditionV22(seed=109)
    unnamed = LivingInstrumentExpeditionV22(seed=109)
    named.name_variable("trace-17", "possible shelter grazer")
    plan = HierarchicalShiftPlan(
        allocation=ShiftPlan(cultivation=3, fabrication=3, shelter=2)
    )
    for _ in range(3):
        named.advance(plan)
        unnamed.advance(plan)
    named_outcome = named.finish()
    unnamed_outcome = unnamed.finish()
    assert named_outcome.base.mission_score == pytest.approx(
        unnamed_outcome.base.mission_score
    )


def test_v221_strengthens_between_variant_separation_without_erasing_v22():
    original = LivingInstrumentExpeditionV22(seed=127).finish()
    recovered = LivingInstrumentExpeditionV221(seed=127).finish()
    assert LivingInstrumentExpeditionV22(seed=127).version == "2.2"
    assert LivingInstrumentExpeditionV221(seed=127).version == "2.2.1"
    for family in OperationalFamily:
        for original_variant, recovered_variant in zip(
            original.revealed_variants[family],
            recovered.revealed_variants[family],
        ):
            assert original_variant.variant_id == recovered_variant.variant_id
            assert [
                unit.persistent_offset for unit in original_variant.units
            ] == [
                unit.persistent_offset for unit in recovered_variant.units
            ]
            assert [
                unit.weather_slope for unit in original_variant.units
            ] == [
                unit.weather_slope for unit in recovered_variant.units
            ]
            original_distance = abs(
                original_variant.units[0].base_multiplier - 1.0
            )
            recovered_distance = abs(
                recovered_variant.units[0].base_multiplier - 1.0
            )
            assert recovered_distance == pytest.approx(1.5 * original_distance)
