"""Run the first measured-control mechanics pilot and preserve its receipts."""

from __future__ import annotations

import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.scoring import RescueScorer
from gyre.control.promotion import EvaluationReceipt, assess_strategy_promotion
from gyre.outcome_reliability import OutcomeReliabilityRegistry

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FORECAST = ROOT / "prospective-forecast.json"
SUBMISSION = ROOT / "scripts" / "submission.py"
FINAL_SEEDS = (2909, 3251, 4001)


def _load_submission():
    spec = importlib.util.spec_from_file_location("rescue_submission", SUBMISSION)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load submission")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reconcile


def main() -> Path:
    forecast = json.loads(FORECAST.read_text(encoding="utf-8"))
    if not forecast.get("locked_before_final_evaluation"):
        raise RuntimeError("forecast was not locked")

    candidate = _load_submission()
    reliability = OutcomeReliabilityRegistry()
    started = time.perf_counter()
    receipts = []
    for seed in FINAL_SEEDS:
        receipt = RescueScorer(seed=seed).score(candidate)
        receipts.append(receipt)
        reliability.record_outcome(
            "sealed-category-scorer",
            correct=receipt.score == 100.0,
        )
    wall_seconds = time.perf_counter() - started
    mean_score = sum(receipt.score for receipt in receipts) / len(receipts)

    forecast_band = (
        "95-100" if mean_score >= 95 else "80-94" if mean_score >= 80 else "0-79"
    )
    forecast_brier = sum(
        (probability - (1.0 if band == forecast_band else 0.0)) ** 2
        for band, probability in forecast["score_band_probabilities"].items()
    )

    synthetic_receipt = EvaluationReceipt(
        strategy_id="measured-control",
        domain_family="repository-rescue",
        endpoint_id="verified-outcome-score",
        effect_lower_bound=0.0,
        harm_delta_upper_bound=0.0,
        validated_counterfactual=False,
        independent_evaluation=False,
        matched_budget=False,
        strong_baseline=True,
    )
    promotion = assess_strategy_promotion("measured-control", (synthetic_receipt,))
    source_estimate = reliability.estimate("sealed-category-scorer")

    result = {
        "experiment": "EXP-05B",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "condition": "measured-control mechanics pilot",
        "final_seed_receipts": [
            {
                "seed": receipt.seed,
                "score": receipt.score,
                "categories": receipt.category_scores,
                "elapsed_seconds": receipt.elapsed_seconds,
            }
            for receipt in receipts
        ],
        "verified_outcome_score": {
            "mean": mean_score,
            "min": min(receipt.score for receipt in receipts),
            "max": max(receipt.score for receipt in receipts),
        },
        "prospective_forecast": forecast,
        "forecast_result": {
            "observed_band": forecast_band,
            "multiclass_brier": forecast_brier,
            "calibration_claim": "none; one forecast is not calibration evidence",
        },
        "control_receipts": [
            {
                "action": "do_not_probe",
                "basis": forecast["probe_value_estimate"],
            },
            {
                "action": "submit",
                "basis": "fresh deterministic contract tests passed and no unresolved high-stakes ambiguity remained",
            },
            {
                "action": "do_not_promote_controller",
                "basis": list(promotion.reasons),
            },
        ],
        "source_reliability": {
            "source_id": source_estimate.source_id,
            "posterior_mean": source_estimate.mean,
            "resolved_outcomes": source_estimate.outcomes,
            "claim": "descriptive only; three same-family outcomes do not establish transfer",
        },
        "promotion_report": {
            "eligible": promotion.eligible,
            "qualifying_domains": list(promotion.qualifying_domain_families),
            "reasons": list(promotion.reasons),
        },
        "efficiency": {
            "wall_seconds": wall_seconds,
            "final_scorer_calls": len(receipts),
            "validation_probes": 0,
            "active_human_minutes": None,
            "api_cost_usd": None,
        },
        "joint_capability": {
            "score_available": mean_score,
            "joint_capability_gain": None,
            "reason": (
                "No matched human-only, system-only, or ordinary-chat baselines; "
                "the user's design contribution is real but not separately estimable."
            ),
        },
        "claim_boundary": (
            "Preliminary mechanics score on development seeds. The candidate and "
            "scorer were built in the same session, so this is not independent "
            "benchmark evidence."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "pilot_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()

