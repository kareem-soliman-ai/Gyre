from __future__ import annotations

import json
from pathlib import Path

import pytest

from gyre.control_playground import (
    evaluate_scenario,
    load_scenarios,
    validate_receipt,
    validate_scenario,
)


def scenario(**overrides):
    base = {
        "id": "case",
        "title": "A test case",
        "description": "Exercise one controller boundary.",
        "learning_goal": "Keep evidence and policy separate.",
        "decision_kind": "technical",
        "consequence": "low",
        "ambiguity": "low",
        "reversible": True,
        "independently_verifiable": True,
        "recovery_available": True,
        "capability_lead": "system",
        "objective_outcome": {
            "status": "pass",
            "criterion": "Independent tests pass.",
            "evidence": "test receipt",
        },
        "human_acceptance": {
            "status": "unknown",
            "criterion": "The user accepts the result.",
            "evidence": "not yet observed",
        },
    }
    base.update(overrides)
    return base


def test_acceptance_does_not_override_failed_objective_outcome():
    case = scenario(
        objective_outcome={
            "status": "fail",
            "criterion": "Independent tests pass.",
            "evidence": "2 tests failed",
        },
        human_acceptance={
            "status": "accepted",
            "criterion": "The user accepts the result.",
            "evidence": "user said it looked good",
        },
    )

    receipt = evaluate_scenario(case)

    assert receipt["signals"]["objective_outcome"]["status"] == "fail"
    assert receipt["signals"]["human_acceptance"]["status"] == "accepted"
    assert receipt["action"] == "recover"
    assert receipt["task_terminated"] is False


def test_verifier_drift_stops_the_action_without_interrupting_the_human():
    case = scenario(
        objective_outcome={
            "status": "verifier_untrusted",
            "criterion": "The source and verifier versions match.",
            "evidence": "source hash changed",
        }
    )

    receipt = evaluate_scenario(case)

    assert receipt["action"] == "stop_and_reverify"
    assert receipt["stop_current_action"] is True
    assert receipt["interrupt_human"] is False
    assert receipt["task_terminated"] is False


def test_high_stakes_ambiguity_keeps_the_decision_human_owned():
    case = scenario(
        consequence="high",
        ambiguity="high",
        capability_lead="unclear",
        objective_outcome={
            "status": "unknown",
            "criterion": "The release causes no material harm.",
            "evidence": "conflicting evidence",
        },
    )

    receipt = evaluate_scenario(case)

    assert receipt["action"] == "human_decide"
    assert receipt["interrupt_human"] is True
    assert receipt["authority_boundary"] == "human"


def test_low_stakes_verified_reversible_work_can_remain_autonomous():
    receipt = evaluate_scenario(scenario())

    assert receipt["action"] == "system_act"
    assert receipt["interrupt_human"] is False
    assert receipt["authority_boundary"] == "system"


def test_taste_case_generates_options_before_requesting_the_final_choice():
    case = scenario(
        decision_kind="taste",
        capability_lead="human",
        human_acceptance={
            "status": "unknown",
            "criterion": "The user prefers the final option.",
            "evidence": "preference not yet elicited",
        },
    )

    receipt = evaluate_scenario(case)

    assert receipt["action"] == "generate_options"
    assert receipt["interrupt_human"] is False
    assert receipt["next_human_boundary"] == "final_selection"


def test_public_policy_never_presents_its_confidence_as_calibrated():
    receipt = evaluate_scenario(scenario())

    assert receipt["confidence"]["status"] == "uncalibrated"
    assert receipt["confidence"]["estimate"] is None
    assert receipt["alternatives"]


def test_human_is_given_a_control_menu_not_a_binary_accept_reject_gate():
    case = scenario(
        consequence="high",
        ambiguity="high",
        capability_lead="unclear",
        objective_outcome={
            "status": "unknown",
            "criterion": "The release causes no material harm.",
            "evidence": "conflicting evidence",
        },
    )

    receipt = evaluate_scenario(case)
    menu = receipt["human_controller"]
    action_ids = {item["id"] for item in menu["actions"]}

    assert menu["mode"] == "decision_required"
    assert {
        "follow_recommendation",
        "choose_alternative",
        "request_evidence",
        "revise_criterion",
        "delegate_bounded",
        "pause_action",
        "terminate_goal",
    } <= action_ids
    assert "accept" not in action_ids
    assert "reject" not in action_ids


def test_autonomy_keeps_non_interrupting_human_controls_available():
    receipt = evaluate_scenario(scenario())
    menu = receipt["human_controller"]
    action_ids = {item["id"] for item in menu["actions"]}

    assert menu["mode"] == "available_without_interrupt"
    assert {"inspect_evidence", "change_boundary", "take_control"} <= action_ids


def test_human_observation_is_a_scoped_raw_measurement_not_ground_truth():
    case = scenario(
        objective_outcome={
            "status": "fail",
            "criterion": "Independent tests pass.",
            "evidence": "2 tests failed",
        },
        human_acceptance={
            "status": "accepted",
            "criterion": "The user accepts the result.",
            "evidence": "user said it looked good",
        },
    )

    measurement = evaluate_scenario(case)["human_measurement"]

    assert measurement["target"] == "human_acceptance"
    assert measurement["maturity"] == "raw"
    assert measurement["capability_scope"] == "case"
    assert "objective_outcome" in measurement["not_evidence_for"]
    assert len(measurement["calibration_path"]) >= 5


def test_binary_stop_policy_is_available_as_an_explicit_teaching_baseline():
    case = scenario(
        objective_outcome={
            "status": "fail",
            "criterion": "Independent tests pass.",
            "evidence": "2 tests failed",
        }
    )

    receipt = evaluate_scenario(case, policy="binary-stop")

    assert receipt["action"] == "terminate_task"
    assert receipt["task_terminated"] is True
    assert receipt["policy"] == "binary-stop"


def test_scenario_validation_rejects_conflated_outcome_channels():
    case = scenario()
    case["human_acceptance"] = case["objective_outcome"]

    with pytest.raises(ValueError, match="separate objects"):
        validate_scenario(case)


def test_scenario_validation_requires_objective_criterion():
    case = scenario(
        objective_outcome={
            "status": "pass",
            "criterion": "",
            "evidence": "test receipt",
        }
    )

    with pytest.raises(ValueError, match="objective_outcome.criterion"):
        validate_scenario(case)


def test_repo_playground_cases_load_and_have_unique_ids():
    path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "examples"
        / "loop-control-cases.json"
    )

    cases = load_scenarios(path)

    assert len(cases) >= 5
    assert len({case["id"] for case in cases}) == len(cases)


def test_receipts_are_json_serializable():
    receipt = evaluate_scenario(scenario())

    assert json.loads(json.dumps(receipt))["scenario_id"] == "case"


def test_external_policy_receipt_must_preserve_measurement_and_control_surfaces():
    receipt = evaluate_scenario(scenario())
    receipt.pop("human_measurement")

    with pytest.raises(ValueError, match="human_measurement"):
        validate_receipt(receipt)
