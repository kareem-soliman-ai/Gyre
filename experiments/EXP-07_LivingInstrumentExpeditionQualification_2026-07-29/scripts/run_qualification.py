"""Run the frozen EXP-07 public-development mechanics qualification."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.living_expedition import (
    LivingInstrumentExpedition,
    ShiftPlan,
    SurveyMode,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SEEDS = tuple(range(200))


def _plan(policy: str, mission: LivingInstrumentExpedition) -> ShiftPlan:
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
    """Apply the preregistered low-charge fallback without hidden state."""

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
        if fabrication > 0:
            fabrication -= 1
        elif cultivation > 0:
            cultivation -= 1
        elif shelter > 0:
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
    mission = LivingInstrumentExpedition(seed=seed)
    while mission.status().shifts_remaining:
        plan = _fit_to_charge(_plan(policy, mission), mission.status().stores.charge)
        mission.advance(plan)
    outcome = mission.finish()
    return {
        "policy": policy,
        "seed": seed,
        "mission_accomplished": outcome.mission_accomplished,
        "mission_score": outcome.mission_score,
        "gates": outcome.gates,
        "food_produced": outcome.food_produced,
        "cargo_produced": outcome.cargo_produced,
        "final_charge": outcome.final_charge,
        "final_spares": outcome.final_spares,
        "final_rations": outcome.final_rations,
        "minimum_crew_condition": outcome.minimum_crew_condition,
        "minimum_shelter_integrity": outcome.minimum_shelter_integrity,
        "instrument_fidelity": outcome.revealed_state.instrument_fidelity,
        "disturbance_burden": outcome.disturbance_burden,
        "active_surveys": outcome.active_surveys,
        "quiet_surveys": outcome.quiet_surveys,
        "repairs": outcome.repairs,
        "salvages": outcome.salvages,
    }


def _summarise(rows: list[dict[str, object]]) -> dict[str, object]:
    scores = [float(row["mission_score"]) for row in rows]
    gate_names = tuple(rows[0]["gates"])
    return {
        "episodes": len(rows),
        "mission_accomplishment_rate": sum(
            bool(row["mission_accomplished"]) for row in rows
        )
        / len(rows),
        "mean_mission_score": statistics.fmean(scores),
        "mission_score_sd": statistics.stdev(scores),
        "gate_pass_rates": {
            gate: sum(bool(row["gates"][gate]) for row in rows) / len(rows)
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
        "mean_final_charge": statistics.fmean(
            float(row["final_charge"]) for row in rows
        ),
        "mean_instrument_fidelity": statistics.fmean(
            float(row["instrument_fidelity"]) for row in rows
        ),
    }


def main() -> Path:
    policies = (
        "idle",
        "production_rush",
        "balanced_fixed",
        "balanced_quiet",
        "balanced_active",
    )
    rows = [
        run_policy(policy, seed)
        for policy in policies
        for seed in SEEDS
    ]
    by_policy = {
        policy: [row for row in rows if row["policy"] == policy]
        for policy in policies
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
        "active_more_disturbing_than_quiet": (
            summaries["balanced_active"]["mean_disturbance_burden"]
            > summaries["balanced_quiet"]["mean_disturbance_burden"]
        ),
        "active_quiet_terminal_difference_at_least_20_percent": (
            paired_differences / len(SEEDS) >= 0.20
        ),
        "balanced_fixed_score_sd_at_least_2": (
            summaries["balanced_fixed"]["mission_score_sd"] >= 2.0
        ),
    }
    result = {
        "experiment": "EXP-07",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "frozen_parameters": {
            "seeds": [SEEDS[0], SEEDS[-1]],
            "seed_count": len(SEEDS),
            "policies": policies,
            "world_defaults": {
                "max_shifts": 14,
                "power_ceiling": 8.0,
                "food_quota": 18.0,
                "cargo_quota": 15.0,
            },
        },
        "policy_summaries": summaries,
        "paired_active_quiet_terminal_difference_rate": (
            paired_differences / len(SEEDS)
        ),
        "gates": gates,
        "qualification_passed": all(gates.values()),
        "contract_test_gate": (
            "Evaluated separately by tests/test_living_instrument_expedition.py"
        ),
        "claim_boundary": (
            "Synthetic public-development mechanics only. No ecological "
            "parameter, real-world transfer, or human-AI capability claim."
        ),
        "rows": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "qualification_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()

