#!/usr/bin/env python3
"""Validate Joint Capability Compiler intake states and control contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_LEVELS = {"low", "medium", "high"}
SIGNAL_TARGETS = {
    "task_outcome",
    "human_acceptance",
    "system_capability",
    "human_capability",
    "joint_capability",
}
MATURITY_LEVELS = {"raw", "standardized", "calibrated", "self-deciding"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class Checks:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def need_text(self, obj: dict[str, Any], key: str, where: str) -> None:
        if not _text(obj.get(key)):
            self.errors.append(f"{where}.{key} must be non-empty text")

    def need_list(self, obj: dict[str, Any], key: str, where: str) -> None:
        if not _items(obj.get(key)):
            self.errors.append(f"{where}.{key} must be a non-empty list")


def _validate_intake(data: dict[str, Any], checks: Checks) -> None:
    status = data.get("status")
    if status not in {"needs_input", "needs_preflight", "ready"}:
        checks.errors.append(
            "intake.status must be needs_input, needs_preflight, or ready"
        )

    goal = _mapping(data.get("goal"))
    for key in ("outcome", "done_when"):
        checks.need_text(goal, key, "goal")

    known = _mapping(data.get("known"))
    for key in (
        "stakes",
        "ambiguity_policy",
        "interruption_policy",
        "learning_preference",
    ):
        checks.need_text(known, key, "known")
    for key in (
        "human_strengths",
        "system_evidence",
        "verification_available",
    ):
        checks.need_list(known, key, "known")

    decisions = _items(data.get("anticipated_decisions"))
    if not decisions:
        checks.errors.append("anticipated_decisions must be a non-empty list")
    decision_ids: set[str] = set()
    for index, raw in enumerate(decisions):
        decision = _mapping(raw)
        where = f"anticipated_decisions[{index}]"
        for key in ("id", "description"):
            checks.need_text(decision, key, where)
        decision_id = decision.get("id")
        if _text(decision_id):
            if decision_id in decision_ids:
                checks.errors.append(f"{where}.id duplicates {decision_id}")
            decision_ids.add(decision_id)
        for key in ("consequence", "uncertainty", "reversibility"):
            if decision.get(key) not in ALLOWED_LEVELS:
                checks.errors.append(f"{where}.{key} must be low, medium, or high")
        if not isinstance(decision.get("missing"), list):
            checks.errors.append(f"{where}.missing must be a list")
        if status == "ready" and _items(decision.get("missing")):
            checks.errors.append(f"ready intake cannot leave {where}.missing unresolved")

    questions = _items(data.get("questions"))
    if not isinstance(data.get("questions"), list):
        checks.errors.append("questions must be one list containing the upfront batch")
    if status == "needs_input" and not questions:
        checks.errors.append("needs_input intake requires an upfront question batch")
    if status == "ready" and questions:
        checks.errors.append("ready intake cannot retain questions")
    if status == "needs_preflight" and questions:
        checks.errors.append(
            "needs_preflight intake cannot ask the human before system preflight"
        )

    for index, raw in enumerate(questions):
        question = _mapping(raw)
        where = f"questions[{index}]"
        for key in (
            "id",
            "question",
            "route_effect",
            "default_if_unanswered",
            "risk_of_default",
        ):
            checks.need_text(question, key, where)
        if question.get("answer_source") != "human":
            checks.errors.append(
                f"{where}.answer_source must be human; system-observable facts belong in preflight_checks"
            )
        affected = _items(question.get("decisions_affected"))
        if not affected:
            checks.errors.append(f"{where}.decisions_affected must be non-empty")
        for decision_id in affected:
            if decision_id not in decision_ids:
                checks.errors.append(
                    f"{where} references unknown anticipated decision {decision_id!r}"
                )

    preflights = _items(data.get("preflight_checks"))
    if not isinstance(data.get("preflight_checks"), list):
        checks.errors.append("preflight_checks must be a list")
    if status == "needs_preflight" and not preflights:
        checks.errors.append("needs_preflight intake requires preflight_checks")
    if status in {"needs_input", "ready"} and preflights:
        checks.errors.append(
            f"{status} intake cannot retain unresolved preflight_checks"
        )
    for index, raw in enumerate(preflights):
        preflight = _mapping(raw)
        where = f"preflight_checks[{index}]"
        for key in ("id", "check", "route_effect", "on_failure"):
            checks.need_text(preflight, key, where)
        affected = _items(preflight.get("decisions_affected"))
        if not affected:
            checks.errors.append(f"{where}.decisions_affected must be non-empty")
        for decision_id in affected:
            if decision_id not in decision_ids:
                checks.errors.append(
                    f"{where} references unknown anticipated decision {decision_id!r}"
                )


def _validate_signal(
    signal: dict[str, Any],
    index: int,
    checks: Checks,
) -> None:
    where = f"signals[{index}]"
    for key in (
        "id",
        "observation",
        "criterion",
        "measurement_error",
        "scope",
    ):
        checks.need_text(signal, key, where)
    checks.need_list(signal, "confounds", where)
    if signal.get("target") not in SIGNAL_TARGETS:
        checks.errors.append(
            f"{where}.target must be one of {', '.join(sorted(SIGNAL_TARGETS))}"
        )
    maturity = signal.get("maturity")
    if maturity not in MATURITY_LEVELS:
        checks.errors.append(
            f"{where}.maturity must be one of {', '.join(sorted(MATURITY_LEVELS))}"
        )
    if signal.get("independence") not in {"external", "same_context", "human"}:
        checks.errors.append(f"{where}.independence must be external, same_context, or human")
    if signal.get("independence") == "same_context":
        checks.warnings.append(
            f"{where} is same_context self-report; do not treat it as independent verification"
        )
    if maturity in {"calibrated", "self-deciding"}:
        evidence = _mapping(signal.get("calibration_evidence"))
        for key in ("criterion", "observed_error", "scope", "valid_until"):
            checks.need_text(evidence, key, f"{where}.calibration_evidence")
        count = evidence.get("prediction_count")
        if not isinstance(count, int) or count <= 0:
            checks.errors.append(
                f"{where}.calibration_evidence.prediction_count must be a positive integer"
            )


def _validate_contract(data: dict[str, Any], checks: Checks) -> None:
    checks.need_text(data, "name", "contract")

    goal = _mapping(data.get("goal"))
    for key in ("outcome", "done_when", "failure_cost"):
        checks.need_text(goal, key, "goal")

    topology = _mapping(data.get("topology"))
    for key in ("selected", "simpler_baseline", "why_more_structure_is_needed"):
        checks.need_text(topology, key, "topology")

    decisions = _items(data.get("decisions"))
    if not decisions:
        checks.errors.append("decisions must be a non-empty list")
    decision_ids: set[str] = set()
    decision_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(decisions):
        decision = _mapping(raw)
        where = f"decisions[{index}]"
        for key in (
            "id",
            "scope",
            "system_may_act_when",
            "human_required_when",
        ):
            checks.need_text(decision, key, where)
        decision_id = decision.get("id")
        if _text(decision_id):
            if decision_id in decision_ids:
                checks.errors.append(f"{where}.id duplicates {decision_id}")
            decision_ids.add(decision_id)
            decision_by_id[decision_id] = decision
        for key in ("consequence", "uncertainty", "reversibility"):
            if decision.get(key) not in ALLOWED_LEVELS:
                checks.errors.append(f"{where}.{key} must be low, medium, or high")
        if decision.get("default_lead") not in {"human", "system", "joint"}:
            checks.errors.append(f"{where}.default_lead must be human, system, or joint")
        basis = _mapping(decision.get("capability_basis"))
        for key in ("human_evidence", "system_evidence", "joint_evidence"):
            checks.need_text(basis, key, f"{where}.capability_basis")
        if not isinstance(decision.get("verification_refs"), list):
            checks.errors.append(f"{where}.verification_refs must be a list")
        if decision.get("consequence") == "high" and decision.get("default_lead") != "human":
            checks.errors.append(f"{where}: a high-consequence decision must remain human-owned")
        if decision.get("default_lead") == "system":
            if decision.get("reversibility") == "low":
                checks.errors.append(
                    f"{where}: a system-led decision must be reversible or human-owned"
                )
            if not _items(decision.get("verification_refs")):
                checks.errors.append(
                    f"{where}: a system-led decision requires independent verification"
                )
            if (
                decision.get("uncertainty") == "high"
                and decision.get("consequence") != "low"
            ):
                checks.errors.append(
                    f"{where}: high uncertainty requires human or joint ownership unless consequence is low"
                )

    signals = _items(data.get("signals"))
    if not signals:
        checks.errors.append("signals must be a non-empty list")
    signal_ids: set[str] = set()
    observed_targets: set[str] = set()
    for index, raw in enumerate(signals):
        signal = _mapping(raw)
        _validate_signal(signal, index, checks)
        signal_id = signal.get("id")
        if _text(signal_id):
            if signal_id in signal_ids:
                checks.errors.append(f"signals[{index}].id duplicates {signal_id}")
            signal_ids.add(signal_id)
        if signal.get("target") in SIGNAL_TARGETS:
            observed_targets.add(signal["target"])
    missing_targets = SIGNAL_TARGETS - observed_targets
    if missing_targets:
        checks.errors.append(
            "signals must keep task_outcome, human_acceptance, system_capability, "
            "human_capability, and joint_capability distinct; missing "
            + ", ".join(sorted(missing_targets))
        )

    verifications = _items(data.get("verification"))
    if not verifications:
        checks.errors.append("verification must be a non-empty list")
    verification_ids: set[str] = set()
    for index, raw in enumerate(verifications):
        verification = _mapping(raw)
        where = f"verification[{index}]"
        for key in ("id", "subject", "method", "criterion", "on_fail"):
            checks.need_text(verification, key, where)
        if _text(verification.get("id")):
            verification_ids.add(verification["id"])
    for index, decision in enumerate(decisions):
        for reference in _items(_mapping(decision).get("verification_refs")):
            if reference not in verification_ids:
                checks.errors.append(
                    f"decisions[{index}].verification_refs contains unknown verification {reference!r}"
                )

    actions = _items(data.get("actions"))
    if not actions:
        checks.errors.append("actions must be a non-empty list")
    action_ids: set[str] = set()
    for index, raw in enumerate(actions):
        action = _mapping(raw)
        where = f"actions[{index}]"
        for key in ("id", "decision", "description"):
            checks.need_text(action, key, where)
        if action.get("execution_authority") not in {"human", "system", "joint"}:
            checks.errors.append(
                f"{where}.execution_authority must be human, system, or joint"
            )
        if _text(action.get("id")):
            action_ids.add(action["id"])
        decision_id = action.get("decision")
        if decision_id not in decision_ids:
            checks.errors.append(f"{where} references unknown decision {decision_id!r}")
        elif (
            action.get("execution_authority") == "system"
            and decision_by_id[decision_id].get("consequence") == "high"
        ):
            checks.errors.append(f"{where}: system action cannot execute a high-consequence decision")

    rules = _items(data.get("rules"))
    if not rules:
        checks.errors.append("rules must be a non-empty list")
    for index, raw in enumerate(rules):
        rule = _mapping(raw)
        where = f"rules[{index}]"
        for key in ("id", "when", "authority_limit"):
            checks.need_text(rule, key, where)
        used = _items(rule.get("using_signals"))
        if not used:
            checks.errors.append(f"{where}.using_signals must be non-empty")
        for signal_id in used:
            if signal_id not in signal_ids:
                checks.errors.append(f"{where} references unknown signal {signal_id!r}")
        if rule.get("action") not in action_ids:
            checks.errors.append(f"{where} references unknown action {rule.get('action')!r}")

    loop = _mapping(data.get("loop"))
    for key in ("steps", "transitions", "terminal_states"):
        checks.need_list(loop, key, "loop")
    budgets = _mapping(loop.get("budgets"))
    for key in ("max_cycles", "max_cost_usd", "max_minutes"):
        value = budgets.get(key)
        if not isinstance(value, (int, float)) or value <= 0:
            checks.errors.append(f"loop.budgets.{key} must be positive")
    step_ids = {
        step.get("id")
        for step in _items(loop.get("steps"))
        if isinstance(step, dict) and _text(step.get("id"))
    }
    for index, raw in enumerate(_items(loop.get("steps"))):
        step = _mapping(raw)
        where = f"loop.steps[{index}]"
        for key in ("id", "operation", "owner", "input", "output"):
            checks.need_text(step, key, where)
    for index, raw in enumerate(_items(loop.get("transitions"))):
        transition = _mapping(raw)
        where = f"loop.transitions[{index}]"
        checks.need_text(transition, "when", where)
        for endpoint in ("from", "to"):
            if transition.get(endpoint) not in step_ids:
                checks.errors.append(
                    f"{where}.{endpoint} references unknown step {transition.get(endpoint)!r}"
                )

    learning = _mapping(data.get("capability_learning"))
    for key in ("prediction_receipt", "promotion_gate", "demotion_gate"):
        checks.need_text(learning, key, "capability_learning")
    outcome_channels = _items(learning.get("outcome_channels"))
    for required in ("task-quality", "human-acceptance"):
        if required not in outcome_channels:
            checks.errors.append(
                f"capability_learning.outcome_channels must include {required}"
            )

    prospective_value = _mapping(data.get("prospective_value"))
    if not prospective_value:
        checks.errors.append("prospective_value is required")
    for key in (
        "forecast_lock",
        "action_value_rule",
        "value_of_information_rule",
        "combination_rule",
        "dependence_rule",
        "measurement_disturbance_rule",
        "future_observation_value_rule",
        "counterfactual_rule",
        "conservative_budget_rule",
        "fixed_weak_baseline",
        "negative_control",
        "uncalibrated_behavior",
        "low_ceiling_behavior",
        "promotion_gate",
    ):
        checks.need_text(prospective_value, key, "prospective_value")
    for key in (
        "forecast_sources",
        "target_outcomes",
        "value_components",
        "hard_constraints",
        "leakage_guards",
    ):
        checks.need_list(prospective_value, key, "prospective_value")
    forecast_sources = set(_items(prospective_value.get("forecast_sources")))
    for required in ("human", "system"):
        if required not in forecast_sources:
            checks.errors.append(
                f"prospective_value.forecast_sources must include {required}"
            )
    target_outcomes = set(_items(prospective_value.get("target_outcomes")))
    for required in ("task-quality", "human-acceptance"):
        if required not in target_outcomes:
            checks.errors.append(
                f"prospective_value.target_outcomes must include {required}"
            )
    value_components = set(_items(prospective_value.get("value_components")))
    for required in ("objective_outcome", "cost", "risk", "learning_value"):
        if required not in value_components:
            checks.errors.append(
                f"prospective_value.value_components must include {required}"
            )

    continuity = _mapping(data.get("continuity"))
    for key in (
        "checkpoint",
        "state_validity",
        "drift_check",
        "reset_when",
        "resume_from",
        "interrupt_only_when",
        "recover_without_interrupt_when",
        "interrupt_when_recovery_fails",
    ):
        checks.need_text(continuity, key, "continuity")

    human_controller = _mapping(data.get("human_controller"))
    checks.need_list(human_controller, "observes", "human_controller")
    for key in (
        "choice_interpretation",
        "framing_guard",
        "human_measurement_rule",
    ):
        checks.need_text(human_controller, key, "human_controller")
    checks.need_list(human_controller, "calibration_path", "human_controller")
    human_actions = _items(human_controller.get("available_actions"))
    if not human_actions:
        checks.errors.append(
            "human_controller.available_actions must be a non-empty list"
        )
    human_action_ids: set[str] = set()
    for index, raw in enumerate(human_actions):
        action = _mapping(raw)
        where = f"human_controller.available_actions[{index}]"
        for key in (
            "id",
            "effect",
            "next_state",
            "reversibility",
            "evidence_effect",
        ):
            checks.need_text(action, key, where)
        action_id = action.get("id")
        if _text(action_id):
            if action_id in human_action_ids:
                checks.errors.append(f"{where}.id duplicates {action_id}")
            human_action_ids.add(action_id)
    required_human_actions = {
        "follow_recommendation",
        "choose_alternative",
        "request_evidence",
        "revise_criterion",
        "change_authority",
        "delegate_bounded",
        "pause_action",
        "terminate_goal",
    }
    for action_id in sorted(required_human_actions - human_action_ids):
        checks.errors.append(
            "human_controller.available_actions must include " + action_id
        )

    outputs = _mapping(data.get("outputs"))
    required_output_fields = {
        "decision_receipt": {
            "recommendation",
            "recommendation_confidence",
            "rationale",
            "alternatives",
            "alternative_confidences",
        },
        "tradeoff_surface": {"best_expected_outcome", "alternatives", "uncertainty"},
        "capability_lesson": {"demonstrated_function", "evidence", "what_to_notice"},
    }
    for channel, required_fields in required_output_fields.items():
        output = _mapping(outputs.get(channel))
        fields = set(_items(output.get("required_fields")))
        if not output:
            checks.errors.append(f"outputs.{channel} is required")
        for field in sorted(required_fields - fields):
            checks.errors.append(f"outputs.{channel}.required_fields must include {field}")

    evaluation = _mapping(data.get("evaluation"))
    checks.need_text(evaluation, "matched_baseline", "evaluation")
    checks.need_list(evaluation, "metrics", "evaluation")
    checks.need_list(evaluation, "trap_cases", "evaluation")


def validate(data: Any) -> Checks:
    checks = Checks()
    if not isinstance(data, dict):
        checks.errors.append("document root must be an object")
        return checks
    kind = data.get("kind")
    if kind == "joint-control-intake":
        _validate_intake(data, checks)
    elif kind == "joint-control-contract":
        _validate_contract(data, checks)
    else:
        checks.errors.append(
            "kind must be joint-control-intake or joint-control-contract"
        )
    return checks


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate.py <intake-or-contract.json>")
        return 2
    path = Path(argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    checks = validate(data)
    for warning in checks.warnings:
        print(f"WARN: {warning}")
    if checks.errors:
        for error in checks.errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
