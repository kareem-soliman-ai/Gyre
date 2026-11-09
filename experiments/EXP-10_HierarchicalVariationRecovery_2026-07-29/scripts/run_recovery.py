"""Run the frozen EXP-10 v2.2.1 recovery qualification."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.hierarchical_expedition import (
    LivingInstrumentExpeditionV221,
)


EXPERIMENT = Path(__file__).resolve().parents[1]
RESULTS = EXPERIMENT / "results"
EXP09_RUNNER = (
    Path(__file__).resolve().parents[2]
    / "EXP-09_HierarchicalVariationQualification_2026-07-29"
    / "scripts"
    / "run_qualification.py"
)


def _load_frozen_harness():
    spec = importlib.util.spec_from_file_location(
        "exp09_frozen_harness",
        EXP09_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen harness: {EXP09_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.LivingInstrumentExpeditionV22 = LivingInstrumentExpeditionV221
    return module


def main() -> Path:
    harness = _load_frozen_harness()
    hierarchy = harness._probe_hierarchy()
    ecology = harness._ecology_probe()
    missions = harness._run_missions()
    contract_tests = harness._run_contract_tests()
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
        "experiment": "EXP-10",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "recovery_from": "EXP-09",
        "version": "2.2.1",
        "frozen_repair": (
            "base_multiplier = 1 + 1.5 * (v2.2 base_multiplier - 1)"
        ),
        "frozen_parameters": {
            "seeds": [harness.SEEDS[0], harness.SEEDS[-1]],
            "seed_count": len(harness.SEEDS),
            "weather_contexts": harness.WEATHER_CONTEXTS,
            "load_contexts": harness.LOAD_CONTEXTS,
            "policies": harness.POLICIES,
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
            "Recovery on reused public development seeds after observing "
            "EXP-09. This is not independent confirmation and does not "
            "establish ecological validity or improved joint capability."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "recovery_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()
