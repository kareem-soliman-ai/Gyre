"""Run the frozen EXP-09 hierarchical-variation qualification."""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.hierarchical_expedition import (
    HierarchicalShiftPlan,
    LivingInstrumentExpeditionV22,
    OperationalFamily,
)
from gyre.challenge.living_expedition import ShiftPlan, SurveyMode


EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
RESULTS = EXPERIMENT / "results"
SEEDS = tuple(range(200))
WEATHER_CONTEXTS = (0.2, 0.5, 0.8)
LOAD_CONTEXTS = (0.25, 0.75)
POLICIES = ("idle", "fixed_first", "rotating_units")


def _r_squared(actual: list[float], predicted: list[float]) -> float:
    mean = statistics.fmean(actual)
    total = sum((value - mean) ** 2 for value in actual)
    residual = sum(
        (observed - estimate) ** 2
        for observed, estimate in zip(actual, predicted)
    )
    return 1.0 - residual / total


def _mae(actual: list[float], predicted: list[float]) -> float:
    return statistics.fmean(
        abs(observed - estimate)
        for observed, estimate in zip(actual, predicted)
    )


def _probe_hierarchy() -> dict[str, object]:
    actual: list[float] = []
    variant_predictions: list[float] = []
    unit_predictions: list[float] = []
    variant_minimum_sds: list[float] = []
    exception_flags: list[bool] = []
    family_shapes: dict[str, set[tuple[int, int]]] = {
        family.value: set() for family in OperationalFamily
    }

    for seed in SEEDS:
        outcome = LivingInstrumentExpeditionV22(seed=seed).finish()
        for family, variants in outcome.revealed_variants.items():
            family_shapes[family.value].add(
                (len(variants), len(variants[0].units))
            )
            for variant in variants:
                majority_slope = statistics.median(
                    unit.weather_slope for unit in variant.units
                )
                base_multiplier = statistics.median(
                    unit.base_multiplier for unit in variant.units
                )
                load_slope = statistics.median(
                    unit.load_slope for unit in variant.units
                )
                context_sds: list[float] = []
                for weather in WEATHER_CONTEXTS:
                    for load in LOAD_CONTEXTS:
                        effects = [
                            unit.effect_at(weather=weather, load=load)
                            for unit in variant.units
                        ]
                        context_sds.append(statistics.stdev(effects))
                        for unit, effect in zip(variant.units, effects):
                            actual.append(effect)
                            variant_predictions.append(
                                max(
                                    0.45,
                                    min(
                                        1.55,
                                        base_multiplier
                                        + majority_slope * (weather - 0.5)
                                        + load_slope * (load - 0.5),
                                    ),
                                )
                            )
                            unit_predictions.append(effect)
                variant_minimum_sds.append(min(context_sds))
                exception_flags.extend(
                    unit.exception_to_variant_rule for unit in variant.units
                )

    global_mean = statistics.fmean(actual)
    global_predictions = [global_mean] * len(actual)
    variant_r2 = _r_squared(actual, variant_predictions)
    unit_r2 = _r_squared(actual, unit_predictions)
    global_mae = _mae(actual, global_predictions)
    variant_mae = _mae(actual, variant_predictions)
    return {
        "probe_rows": len(actual),
        "family_shapes": {
            family: sorted(list(shapes))
            for family, shapes in family_shapes.items()
        },
        "minimum_within_variant_sd": min(variant_minimum_sds),
        "median_within_variant_sd": statistics.median(variant_minimum_sds),
        "global_r_squared": _r_squared(actual, global_predictions),
        "variant_context_r_squared": variant_r2,
        "unit_identity_r_squared": unit_r2,
        "unit_identity_incremental_r_squared": unit_r2 - variant_r2,
        "global_mae": global_mae,
        "variant_context_mae": variant_mae,
        "variant_mae_improvement": 1.0 - variant_mae / global_mae,
        "operational_exception_fraction": statistics.fmean(exception_flags),
    }


def _ecology_probe() -> dict[str, object]:
    shape_ok = True
    exception_ok = True
    signed_differences = 0
    nonzero_differences = 0
    for seed in SEEDS:
        revealed = LivingInstrumentExpeditionV22(seed=seed).finish()
        for family in revealed.revealed_organisms.values():
            shape_ok &= len(family.individuals) == 4
            exception_ok &= (
                sum(
                    individual.exception_to_family_rule
                    for individual in family.individuals
                )
                == 1
            )
        trace_id, family = next(iter(revealed.revealed_organisms.items()))
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
        allocation = ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            survey_mode=SurveyMode.ACTIVE,
            survey_focus=trace_id,
            survey_intensity=0.7,
        )
        majority = LivingInstrumentExpeditionV22(seed=seed).advance(
            HierarchicalShiftPlan(
                allocation=allocation,
                organism_subject=majority_id,
            )
        )
        exception = LivingInstrumentExpeditionV22(seed=seed).advance(
            HierarchicalShiftPlan(
                allocation=allocation,
                organism_subject=exception_id,
            )
        )
        signed_differences += (
            majority.ecology_shift * exception.ecology_shift <= 0.0
        )
        nonzero_differences += (
            abs(majority.ecology_shift - exception.ecology_shift) > 1e-12
        )
    return {
        "families_have_four_individuals": shape_ok,
        "families_have_one_exception": exception_ok,
        "opposite_or_zero_signed_response_rate": signed_differences / len(SEEDS),
        "nonzero_response_difference_rate": nonzero_differences / len(SEEDS),
    }


def _fit_to_charge(plan: ShiftPlan, charge: float) -> ShiftPlan:
    cultivation = plan.cultivation
    fabrication = plan.fabrication
    shelter = plan.shelter
    while cultivation + fabrication + shelter > charge:
        if fabrication:
            fabrication -= 1
        elif cultivation:
            cultivation -= 1
        elif shelter:
            shelter -= 1
        else:
            break
    return ShiftPlan(
        cultivation=cultivation,
        fabrication=fabrication,
        shelter=shelter,
    )


def _policy_plan(
    policy: str,
    mission: LivingInstrumentExpeditionV22,
) -> HierarchicalShiftPlan:
    allocation = (
        ShiftPlan()
        if policy == "idle"
        else _fit_to_charge(
            ShiftPlan(cultivation=3, fabrication=3, shelter=2),
            mission.status().stores.charge,
        )
    )
    if policy != "rotating_units":
        return HierarchicalShiftPlan(allocation=allocation)
    index = mission.status().shift
    selections = {}
    for family in OperationalFamily:
        units = tuple(
            unit_id
            for variant in mission.status().variants[family]
            for unit_id in variant.unit_ids
        )
        selections[family] = units[index % len(units)]
    return HierarchicalShiftPlan(
        allocation=allocation,
        food_unit=selections[OperationalFamily.FOOD],
        cargo_unit=selections[OperationalFamily.CARGO],
        crew_unit=selections[OperationalFamily.CREW],
        power_unit=selections[OperationalFamily.POWER],
        drive_unit=selections[OperationalFamily.DRIVE],
    )


def _run_missions() -> dict[str, object]:
    rows: dict[str, list[dict[str, object]]] = {
        policy: [] for policy in POLICIES
    }
    for policy in POLICIES:
        for seed in SEEDS:
            mission = LivingInstrumentExpeditionV22(seed=seed)
            while mission.status().shifts_remaining:
                mission.advance(_policy_plan(policy, mission))
            outcome = mission.finish().base
            rows[policy].append(
                {
                    "accomplished": outcome.mission_accomplished,
                    "score": outcome.mission_score,
                    "food": outcome.food_produced,
                    "cargo": outcome.cargo_produced,
                    "crew": outcome.minimum_crew_condition,
                    "shelter": outcome.minimum_shelter_integrity,
                }
            )
    summaries = {}
    for policy, policy_rows in rows.items():
        summaries[policy] = {
            "mission_accomplishment_rate": statistics.fmean(
                bool(row["accomplished"]) for row in policy_rows
            ),
            "mean_mission_score": statistics.fmean(
                float(row["score"]) for row in policy_rows
            ),
            "mission_score_sd": statistics.stdev(
                float(row["score"]) for row in policy_rows
            ),
            "mean_food": statistics.fmean(
                float(row["food"]) for row in policy_rows
            ),
            "mean_cargo": statistics.fmean(
                float(row["cargo"]) for row in policy_rows
            ),
        }
    paired_differences = sum(
        any(
            abs(float(fixed[key]) - float(rotating[key])) > 1e-12
            for key in ("food", "cargo", "crew", "shelter")
        )
        for fixed, rotating in zip(
            rows["fixed_first"],
            rows["rotating_units"],
        )
    )
    return {
        "summaries": summaries,
        "fixed_rotating_terminal_difference_rate": (
            paired_differences / len(SEEDS)
        ),
    }


def _run_contract_tests() -> dict[str, object]:
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "-q",
        "tests/test_living_instrument_expedition.py",
        "tests/test_hierarchical_expedition.py",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> Path:
    hierarchy = _probe_hierarchy()
    ecology = _ecology_probe()
    missions = _run_missions()
    contract_tests = _run_contract_tests()
    shapes_pass = all(
        shapes == [(3, 4)]
        for shapes in hierarchy["family_shapes"].values()
    )
    gates = {
        "five_families_are_three_by_four": shapes_pass,
        "minimum_within_variant_sd_at_least_0_04": (
            hierarchy["minimum_within_variant_sd"] >= 0.04
        ),
        "variant_model_r2_between_0_50_and_0_95": (
            0.50 <= hierarchy["variant_context_r_squared"] < 0.95
        ),
        "unit_identity_adds_at_least_0_08_r2": (
            hierarchy["unit_identity_incremental_r_squared"] >= 0.08
        ),
        "variant_model_mae_improves_at_least_15_percent": (
            hierarchy["variant_mae_improvement"] >= 0.15
        ),
        "operational_exception_fraction_between_0_20_and_0_30": (
            0.20 <= hierarchy["operational_exception_fraction"] <= 0.30
        ),
        "ecology_is_four_with_one_exception": (
            ecology["families_have_four_individuals"]
            and ecology["families_have_one_exception"]
        ),
        "ecological_signed_difference_at_least_0_95": (
            ecology["opposite_or_zero_signed_response_rate"] >= 0.95
            and ecology["nonzero_response_difference_rate"] >= 0.95
        ),
        "idle_accomplishes_zero": (
            missions["summaries"]["idle"]["mission_accomplishment_rate"] == 0.0
        ),
        "fixed_rotating_terminal_difference_at_least_0_80": (
            missions["fixed_rotating_terminal_difference_rate"] >= 0.80
        ),
        "version_contract_tests_pass": contract_tests["passed"],
    }
    result = {
        "experiment": "EXP-09",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "version": "2.2",
        "frozen_parameters": {
            "seeds": [SEEDS[0], SEEDS[-1]],
            "seed_count": len(SEEDS),
            "weather_contexts": WEATHER_CONTEXTS,
            "load_contexts": LOAD_CONTEXTS,
            "policies": POLICIES,
            "variants_per_family": 3,
            "units_per_variant": 4,
            "intended_exception_fraction": 0.25,
        },
        "hierarchy": hierarchy,
        "ecology": ecology,
        "missions": missions,
        "contract_tests": contract_tests,
        "gates": gates,
        "qualification_passed": all(gates.values()),
        "claim_boundary": (
            "Synthetic mechanics qualification on public development seeds. "
            "This does not establish ecological validity, real-world transfer, "
            "or improved human-AI joint capability."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "qualification_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()
