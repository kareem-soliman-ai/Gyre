"""Run the frozen EXP-08 recovery qualification."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.living_expedition import (
    LivingInstrumentExpeditionV21,
    ShiftPlan,
    SurveyMode,
    control_efficiency,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SEEDS = tuple(range(200))
POLICIES = (
    "idle",
    "production_rush",
    "balanced_fixed",
    "balanced_quiet",
    "balanced_active",
)


def _plan(policy: str, mission: LivingInstrumentExpeditionV21) -> ShiftPlan:
    focus = mission.variable_ids[mission.status().shift % len(mission.variable_ids)]
    if policy == "idle":
        return ShiftPlan()
    if policy == "production_rush":
        return ShiftPlan(cultivation=4, fabrication=4)
    if policy == "balanced_fixed":
        return ShiftPlan(cultivation=3, fabrication=3, shelter=2)
    if policy == "balanced_quiet":
        return ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            survey_mode=SurveyMode.QUIET,
            survey_focus=focus,
        )
    if policy == "balanced_active":
        return ShiftPlan(
            cultivation=2,
            fabrication=2,
            shelter=1,
            survey_mode=SurveyMode.ACTIVE,
            survey_focus=focus,
            survey_intensity=0.5,
        )
    raise KeyError(policy)


def _fit_to_charge(plan: ShiftPlan, charge: float) -> ShiftPlan:
    survey_cost = (
        0.0
        if plan.survey_mode is SurveyMode.NONE
        else 0.25
        if plan.survey_mode is SurveyMode.QUIET
        else 0.8 + 1.7 * plan.survey_intensity
    )
    cultivation = plan.cultivation
    fabrication = plan.fabrication
    shelter = plan.shelter
    while cultivation + fabrication + shelter + survey_cost > charge:
        if fabrication:
            fabrication -= 1
        elif cultivation:
            cultivation -= 1
        elif shelter:
            shelter -= 1
        else:
            return ShiftPlan()
    return ShiftPlan(
        cultivation=cultivation,
        fabrication=fabrication,
        shelter=shelter,
        survey_mode=plan.survey_mode,
        survey_focus=plan.survey_focus,
        survey_intensity=plan.survey_intensity,
    )


def run_policy(policy: str, seed: int) -> dict[str, object]:
    mission = LivingInstrumentExpeditionV21(seed=seed)
    while mission.status().shifts_remaining:
        plan = _fit_to_charge(_plan(policy, mission), mission.status().stores.charge)
        mission.advance(plan)
    outcome = mission.finish()
    efficiency = control_efficiency(outcome)
    return {
        "policy": policy,
        "seed": seed,
        "mission_accomplished": outcome.mission_accomplished,
        "mission_score": outcome.mission_score,
        "control_efficiency": efficiency.score,
        "efficiency_components": {
            "energy_reserve": efficiency.energy_reserve,
            "parts_reserve": efficiency.parts_reserve,
            "evidence_tax": efficiency.evidence_tax,
            "reversibility": efficiency.reversibility,
        },
        "gates": outcome.gates,
        "food_produced": outcome.food_produced,
        "cargo_produced": outcome.cargo_produced,
        "final_charge": outcome.final_charge,
        "final_spares": outcome.final_spares,
        "minimum_crew_condition": outcome.minimum_crew_condition,
        "minimum_shelter_integrity": outcome.minimum_shelter_integrity,
        "instrument_fidelity": outcome.revealed_state.instrument_fidelity,
        "disturbance_burden": outcome.disturbance_burden,
    }


def _summarise(rows: list[dict[str, object]]) -> dict[str, object]:
    scores = [float(row["mission_score"]) for row in rows]
    gate_names = tuple(rows[0]["gates"])
    return {
        "episodes": len(rows),
        "mission_accomplishment_rate": statistics.fmean(
            bool(row["mission_accomplished"]) for row in rows
        ),
        "mean_mission_score": statistics.fmean(scores),
        "mission_score_sd": statistics.stdev(scores),
        "mean_control_efficiency": statistics.fmean(
            float(row["control_efficiency"]) for row in rows
        ),
        "gate_pass_rates": {
            gate: statistics.fmean(bool(row["gates"][gate]) for row in rows)
            for gate in gate_names
        },
        "mean_food_produced": statistics.fmean(
            float(row["food_produced"]) for row in rows
        ),
        "mean_cargo_produced": statistics.fmean(
            float(row["cargo_produced"]) for row in rows
        ),
        "mean_disturbance_burden": statistics.fmean(
            float(row["disturbance_burden"]) for row in rows
        ),
        "mean_instrument_fidelity": statistics.fmean(
            float(row["instrument_fidelity"]) for row in rows
        ),
    }


def main() -> Path:
    rows = [
        run_policy(policy, seed)
        for policy in POLICIES
        for seed in SEEDS
    ]
    by_policy = {
        policy: [row for row in rows if row["policy"] == policy]
        for policy in POLICIES
    }
    summaries = {
        policy: _summarise(policy_rows)
        for policy, policy_rows in by_policy.items()
    }
    paired_differences = sum(
        any(
            abs(float(quiet[key]) - float(active[key])) > 1e-12
            for key in (
                "food_produced",
                "cargo_produced",
                "minimum_shelter_integrity",
                "instrument_fidelity",
            )
        )
        for quiet, active in zip(
            by_policy["balanced_quiet"],
            by_policy["balanced_active"],
        )
    )
    gates = {
        "idle_accomplishes_zero": (
            summaries["idle"]["mission_accomplishment_rate"] == 0.0
        ),
        "balanced_fixed_between_25_and_95_percent": (
            0.25
            <= summaries["balanced_fixed"]["mission_accomplishment_rate"]
            <= 0.95
        ),
        "balanced_fixed_beats_production_rush": (
            summaries["balanced_fixed"]["mission_accomplishment_rate"]
            > summaries["production_rush"]["mission_accomplishment_rate"]
        ),
        "balanced_fixed_score_sd_at_least_2": (
            summaries["balanced_fixed"]["mission_score_sd"] >= 2.0
        ),
        "active_more_disturbing_than_quiet": (
            summaries["balanced_active"]["mean_disturbance_burden"]
            > summaries["balanced_quiet"]["mean_disturbance_burden"]
        ),
        "active_quiet_terminal_difference_at_least_20_percent": (
            paired_differences / len(SEEDS) >= 0.20
        ),
    }
    result = {
        "experiment": "EXP-08",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "recovery_from": "EXP-07",
        "version": "2.1",
        "frozen_parameters": {
            "seeds": [SEEDS[0], SEEDS[-1]],
            "seed_count": len(SEEDS),
            "policies": POLICIES,
            "food_quota": 22.0,
            "cargo_quota": 22.0,
        },
        "policy_summaries": summaries,
        "paired_active_quiet_terminal_difference_rate": (
            paired_differences / len(SEEDS)
        ),
        "gates": gates,
        "qualification_passed": all(gates.values()),
        "claim_boundary": (
            "Recovery on reused public development seeds. This is not "
            "independent confirmation and supports no ecological or dyad claim."
        ),
        "rows": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "recovery_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()

