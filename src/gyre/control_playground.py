"""Didactic control policies for the Gyre Loop Control Lab.

This module is intentionally a transparent baseline, not a validated controller.
It makes the policy path inspectable so developers can replace each rule and
test the replacement against declared objective and acceptance outcomes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "title",
    "description",
    "learning_goal",
    "decision_kind",
    "consequence",
    "ambiguity",
    "reversible",
    "independently_verifiable",
    "recovery_available",
    "capability_lead",
    "objective_outcome",
    "human_acceptance",
}

REQUIRED_RECEIPT_FIELDS = {
    "scenario_id",
    "policy",
    "action",
    "recommendation",
    "confidence",
    "rationale",
    "alternatives",
    "interrupt_human",
    "stop_current_action",
    "task_terminated",
    "authority_boundary",
    "signals",
    "human_controller",
    "human_measurement",
    "claim_boundary",
}


def _require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def validate_scenario(scenario: dict[str, Any]) -> None:
    """Validate the educational case schema.

    The schema forces objective outcome and human acceptance into separate
    objects. It does not establish that either criterion is valid.
    """

    missing = sorted(REQUIRED_FIELDS - scenario.keys())
    if missing:
        raise ValueError(f"scenario is missing required fields: {', '.join(missing)}")

    for field in ("id", "title", "description", "learning_goal"):
        _require_text(scenario[field], field)

    if scenario["decision_kind"] not in {"technical", "taste", "release"}:
        raise ValueError("decision_kind must be technical, taste, or release")
    if scenario["consequence"] not in {"low", "medium", "high"}:
        raise ValueError("consequence must be low, medium, or high")
    if scenario["ambiguity"] not in {"low", "medium", "high"}:
        raise ValueError("ambiguity must be low, medium, or high")
    if scenario["capability_lead"] not in {"human", "system", "unclear"}:
        raise ValueError("capability_lead must be human, system, or unclear")
    for field in ("reversible", "independently_verifiable", "recovery_available"):
        if not isinstance(scenario[field], bool):
            raise ValueError(f"{field} must be true or false")

    objective = scenario["objective_outcome"]
    acceptance = scenario["human_acceptance"]
    if objective is acceptance:
        raise ValueError("objective_outcome and human_acceptance must be separate objects")
    for label, channel in (
        ("objective_outcome", objective),
        ("human_acceptance", acceptance),
    ):
        if not isinstance(channel, dict):
            raise ValueError(f"{label} must be an object")
        for field in ("status", "criterion", "evidence"):
            if field not in channel:
                raise ValueError(f"{label}.{field} is required")
            _require_text(channel[field], f"{label}.{field}")

    if objective["status"] not in {"pass", "fail", "unknown", "verifier_untrusted"}:
        raise ValueError(
            "objective_outcome.status must be pass, fail, unknown, or verifier_untrusted"
        )
    if acceptance["status"] not in {"accepted", "rejected", "unknown"}:
        raise ValueError(
            "human_acceptance.status must be accepted, rejected, or unknown"
        )


def load_scenarios(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a JSON list of Loop Control Lab cases."""

    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("playground case file must contain a JSON list")
    seen: set[str] = set()
    for index, scenario in enumerate(data):
        if not isinstance(scenario, dict):
            raise ValueError(f"case {index} must be an object")
        validate_scenario(scenario)
        case_id = scenario["id"]
        if case_id in seen:
            raise ValueError(f"duplicate scenario id: {case_id}")
        seen.add(case_id)
    return data


def validate_receipt(receipt: dict[str, Any]) -> None:
    """Check that an external teaching policy preserves the lab's key seams."""

    if not isinstance(receipt, dict):
        raise ValueError("policy receipt must be an object")
    missing = sorted(REQUIRED_RECEIPT_FIELDS - receipt.keys())
    if missing:
        raise ValueError(f"policy receipt is missing required fields: {', '.join(missing)}")
    signals = receipt.get("signals")
    if not isinstance(signals, dict) or not {
        "objective_outcome",
        "human_acceptance",
    } <= signals.keys():
        raise ValueError(
            "policy receipt signals must separate objective_outcome and human_acceptance"
        )
    human_controller = receipt.get("human_controller")
    if not isinstance(human_controller, dict) or not human_controller.get("actions"):
        raise ValueError("policy receipt human_controller must expose actions")
    if not isinstance(receipt.get("human_measurement"), dict):
        raise ValueError("policy receipt human_measurement must be an object")


def _alternative(action: str, why_not: str) -> dict[str, str]:
    return {
        "action": action,
        "relative_support": "lower",
        "why_not": why_not,
    }


def _human_action(
    action_id: str,
    effect: str,
    *,
    next_state: str,
    reversibility: str,
    evidence_effect: str,
) -> dict[str, str]:
    return {
        "id": action_id,
        "effect": effect,
        "next_state": next_state,
        "reversibility": reversibility,
        "evidence_effect": evidence_effect,
    }


def _human_controller(
    interrupt_human: bool, task_terminated: bool
) -> dict[str, Any]:
    shared = [
        _human_action(
            "request_evidence",
            "Ask the system to gather or expose a named missing observation.",
            next_state="evidence_pending",
            reversibility="fully reversible",
            evidence_effect="Adds evidence; does not itself label the outcome.",
        ),
        _human_action(
            "revise_criterion",
            "Change what counts as success and invalidate routes tied to the old criterion.",
            next_state="contract_revision",
            reversibility="reversible before consequential action",
            evidence_effect="Changes the target; prior scores require re-interpretation.",
        ),
        _human_action(
            "pause_action",
            "Stop the affected action while preserving the task and checkpoint.",
            next_state="paused",
            reversibility="reversible",
            evidence_effect="No outcome claim is created by pausing.",
        ),
        _human_action(
            "terminate_goal",
            "End the whole goal and record why recovery or reframing is not worthwhile.",
            next_state="terminated",
            reversibility="usually not reversible without a new goal",
            evidence_effect="Records a control choice, not objective failure.",
        ),
    ]
    if task_terminated:
        actions = [
            _human_action(
                "inspect_evidence",
                "Inspect why the policy terminated the goal.",
                next_state="terminated",
                reversibility="fully reversible as an inspection",
                evidence_effect="Improves observability without changing the outcome record.",
            ),
            _human_action(
                "challenge_termination",
                "Reject the binary route and request a recovery or reframing policy.",
                next_state="contract_revision",
                reversibility="requires reopening the goal",
                evidence_effect="Records a controller defect hypothesis for later testing.",
            ),
            _human_action(
                "reopen_goal",
                "Create a new goal from the last verified checkpoint.",
                next_state="new_goal",
                reversibility="creates a new run",
                evidence_effect="Keeps the terminated run as an immutable receipt.",
            ),
        ]
        mode = "post_termination_only"
    elif interrupt_human:
        actions = [
            _human_action(
                "follow_recommendation",
                "Choose the system's recommended route under the displayed boundary.",
                next_state="recommended_route",
                reversibility="declared by the recommended action",
                evidence_effect="Records uptake; later outcome evidence must judge quality.",
            ),
            _human_action(
                "choose_alternative",
                "Select one of the surfaced alternatives and its declared trade-off.",
                next_state="alternative_route",
                reversibility="declared by the selected alternative",
                evidence_effect="Records route selection; it is not a correctness label.",
            ),
            *shared[:2],
            _human_action(
                "delegate_bounded",
                "Give the system temporary authority with an explicit budget and verifier.",
                next_state="bounded_system_authority",
                reversibility="reversible until the declared boundary",
                evidence_effect="Creates a prospective test of system capability.",
            ),
            *shared[2:],
        ]
        mode = "decision_required"
    else:
        actions = [
            _human_action(
                "let_system_continue",
                "Leave the current autonomous boundary unchanged.",
                next_state="system_route",
                reversibility="reversible until the next declared boundary",
                evidence_effect="Records no correction; silence is not acceptance.",
            ),
            _human_action(
                "inspect_evidence",
                "Open the decision and verification receipt without changing the route.",
                next_state="system_route",
                reversibility="fully reversible",
                evidence_effect="Improves observability without creating an outcome label.",
            ),
            shared[0],
            _human_action(
                "change_boundary",
                "Tighten or relax standing authority for the next safe transition.",
                next_state="contract_revision",
                reversibility="reversible before consequential action",
                evidence_effect="Changes policy scope; prior evidence remains scoped to the old boundary.",
            ),
            _human_action(
                "take_control",
                "Assume the next decision while leaving object-level work resumable.",
                next_state="human_route",
                reversibility="reversible",
                evidence_effect="Creates a human intervention event for later outcome comparison.",
            ),
            *shared[2:],
        ]
        mode = "available_without_interrupt"
    return {
        "mode": mode,
        "actions": actions,
        "choice_interpretation": (
            "A human choice is a control action. It can update the route, criterion, "
            "or authority, but it is not automatically evidence of objective quality."
        ),
        "framing_guard": (
            "Show the recommendation first, then all credible alternatives with "
            "consequences and uncertainty. Do not hide an option to manufacture consent."
        ),
    }


def _human_measurement(scenario: dict[str, Any]) -> dict[str, Any]:
    acceptance = scenario["human_acceptance"]
    return {
        "target": "human_acceptance",
        "observation": acceptance["evidence"],
        "criterion": acceptance["criterion"],
        "maturity": "raw",
        "capability_scope": scenario["id"],
        "measurement_error": (
            "Unknown until prospective judgements are compared with later outcomes "
            "across repeated cases."
        ),
        "confounds": [
            "courtesy or demand effects",
            "hindsight after seeing the system recommendation",
            "automation anchoring",
            "task-family drift",
        ],
        "not_evidence_for": [
            "objective_outcome",
            "general human capability",
            "general system capability",
        ],
        "calibration_path": [
            "Name the construct and criterion before deciding.",
            "Record the human prediction and confidence before the outcome.",
            "Use an independent objective outcome where one is available.",
            "Score prediction error across repeated cases in the same task family.",
            "Separate sensitivity from a cautious or permissive decision criterion.",
            "Retain authority claims only inside the evidenced scope.",
            "Demote or reset the claim when the task, criterion, or environment drifts.",
        ],
    }


def _receipt(
    scenario: dict[str, Any],
    *,
    policy: str,
    action: str,
    recommendation: str,
    rationale: list[str],
    alternatives: list[dict[str, str]],
    interrupt_human: bool,
    stop_current_action: bool,
    task_terminated: bool,
    authority_boundary: str,
    next_human_boundary: str | None = None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario["id"],
        "policy": policy,
        "action": action,
        "recommendation": recommendation,
        "confidence": {
            "status": "uncalibrated",
            "estimate": None,
            "basis": "transparent didactic rules; no prospective calibration receipt",
        },
        "rationale": rationale,
        "alternatives": alternatives,
        "interrupt_human": interrupt_human,
        "stop_current_action": stop_current_action,
        "task_terminated": task_terminated,
        "authority_boundary": authority_boundary,
        "next_human_boundary": next_human_boundary,
        "human_controller": _human_controller(interrupt_human, task_terminated),
        "human_measurement": _human_measurement(scenario),
        "signals": {
            "objective_outcome": dict(scenario["objective_outcome"]),
            "human_acceptance": dict(scenario["human_acceptance"]),
        },
        "capability_lesson": _capability_lesson(action),
        "claim_boundary": (
            "This receipt demonstrates a declared policy path. It does not prove "
            "that the sensor, policy, or route improves real outcomes."
        ),
    }


def _capability_lesson(action: str) -> str:
    lessons = {
        "system_act": (
            "Autonomy is supported here by reversibility, independent verification, "
            "low consequence, and task-local capability evidence."
        ),
        "recover": (
            "A failed outcome can trigger bounded repair without terminating the task "
            "or interrupting the user."
        ),
        "stop_and_reverify": (
            "Stopping the affected action is different from terminating the task or "
            "interrupting the human."
        ),
        "human_decide": (
            "High consequence plus unresolved ambiguity creates a human authority "
            "floor even when the system can still provide evidence and options."
        ),
        "generate_options": (
            "The system can do low-consequence option generation while preserving the "
            "human's stronger final taste boundary."
        ),
        "seek_info": (
            "An unknown objective state calls for more evidence, not a confident route."
        ),
        "joint_navigate": (
            "When capability evidence is inconclusive, expose the ambiguity and divide "
            "work by the evidence each party can supply."
        ),
        "continue": "A passing signal can support continuation within the declared budget.",
        "terminate_task": (
            "A binary stop policy discards recovery, reframing, and evidence-seeking "
            "options; it is included only as a teaching baseline."
        ),
    }
    return lessons[action]


def _binary_stop(scenario: dict[str, Any]) -> dict[str, Any]:
    objective_status = scenario["objective_outcome"]["status"]
    if objective_status == "pass":
        return _receipt(
            scenario,
            policy="binary-stop",
            action="continue",
            recommendation="Continue because the one blocking signal is clear.",
            rationale=["The binary baseline sees only pass versus block."],
            alternatives=[
                _alternative("terminate_task", "The declared objective currently passes.")
            ],
            interrupt_human=False,
            stop_current_action=False,
            task_terminated=False,
            authority_boundary="system",
        )
    return _receipt(
        scenario,
        policy="binary-stop",
        action="terminate_task",
        recommendation="Terminate the task because the blocking signal did not pass.",
        rationale=[
            "The binary baseline has no recovery, reframing, or escalation action."
        ],
        alternatives=[
            _alternative(
                "recover",
                "This policy cannot represent bounded recovery even when it exists.",
            )
        ],
        interrupt_human=False,
        stop_current_action=True,
        task_terminated=True,
        authority_boundary="none",
    )


def _control_menu(scenario: dict[str, Any]) -> dict[str, Any]:
    objective = scenario["objective_outcome"]["status"]
    consequence = scenario["consequence"]
    ambiguity = scenario["ambiguity"]
    lead = scenario["capability_lead"]
    recoverable = scenario["recovery_available"] and scenario["reversible"]

    if objective == "verifier_untrusted":
        if recoverable:
            return _receipt(
                scenario,
                policy="control-menu",
                action="stop_and_reverify",
                recommendation=(
                    "Stop the affected action, refresh the evidence boundary, and "
                    "re-verify within the recovery budget."
                ),
                rationale=[
                    "The verifier cannot currently support an outcome claim.",
                    "Bounded autonomous recovery is available and reversible.",
                ],
                alternatives=[
                    _alternative(
                        "human_decide",
                        "Human judgement cannot repair an invalid technical verifier.",
                    ),
                    _alternative(
                        "terminate_task",
                        "The task can remain recoverable while the affected action stops.",
                    ),
                ],
                interrupt_human=False,
                stop_current_action=True,
                task_terminated=False,
                authority_boundary="system",
            )
        return _receipt(
            scenario,
            policy="control-menu",
            action="human_decide",
            recommendation=(
                "Pause the affected action and ask the human to choose the next "
                "evidence or authority boundary."
            ),
            rationale=[
                "The verifier is untrusted.",
                "No bounded autonomous recovery route remains.",
            ],
            alternatives=[
                _alternative(
                    "terminate_task",
                    "Termination would discard the option to install a new verifier.",
                )
            ],
            interrupt_human=True,
            stop_current_action=True,
            task_terminated=False,
            authority_boundary="human",
        )

    if objective == "fail" and recoverable:
        return _receipt(
            scenario,
            policy="control-menu",
            action="recover",
            recommendation="Repair the named failure and run the independent check again.",
            rationale=[
                "The objective criterion failed even if the output was accepted.",
                "The work is reversible and a bounded recovery route exists.",
            ],
            alternatives=[
                _alternative(
                    "human_decide",
                    "The current defect is independently checkable and does not need taste.",
                ),
                _alternative(
                    "terminate_task",
                    "A recoverable failure is not yet a reason to abandon the task.",
                ),
            ],
            interrupt_human=False,
            stop_current_action=True,
            task_terminated=False,
            authority_boundary="system",
        )

    if consequence == "high" and (ambiguity == "high" or objective != "pass"):
        return _receipt(
            scenario,
            policy="control-menu",
            action="human_decide",
            recommendation=(
                "Keep the consequential decision human-owned while the system presents "
                "its recommendation, evidence, and alternatives."
            ),
            rationale=[
                "The consequence is high.",
                "The outcome remains uncertain or ambiguous.",
            ],
            alternatives=[
                _alternative(
                    "system_act",
                    "Task-local capability evidence does not remove the authority floor.",
                ),
                _alternative(
                    "terminate_task",
                    "The human may still choose a bounded route after reviewing the trade-off.",
                ),
            ],
            interrupt_human=True,
            stop_current_action=True,
            task_terminated=False,
            authority_boundary="human",
        )

    if scenario["decision_kind"] == "taste" and lead == "human":
        return _receipt(
            scenario,
            policy="control-menu",
            action="generate_options",
            recommendation=(
                "Generate a small set of low-consequence options, then preserve the "
                "user's final selection boundary."
            ),
            rationale=[
                "The system can cheaply widen the option set.",
                "The human has stronger task-local evidence for the taste criterion.",
            ],
            alternatives=[
                _alternative(
                    "human_decide",
                    "Interrupting now would ask for judgement before useful options exist.",
                ),
                _alternative(
                    "system_act",
                    "Objective checks do not establish the user's preference.",
                ),
            ],
            interrupt_human=False,
            stop_current_action=False,
            task_terminated=False,
            authority_boundary="joint",
            next_human_boundary="final_selection",
        )

    if objective == "pass" and all(
        (
            lead == "system",
            scenario["reversible"],
            scenario["independently_verifiable"],
            consequence in {"low", "medium"},
            ambiguity == "low",
        )
    ):
        return _receipt(
            scenario,
            policy="control-menu",
            action="system_act",
            recommendation=(
                "Proceed autonomously inside the declared boundary and surface the "
                "verification receipt."
            ),
            rationale=[
                "The action is reversible and independently verifiable.",
                "Consequence and ambiguity are bounded.",
                "The declared task-local capability evidence favours the system.",
            ],
            alternatives=[
                _alternative(
                    "human_decide",
                    "Human interruption adds little evidence at this boundary.",
                ),
                _alternative(
                    "terminate_task",
                    "The objective criterion currently passes.",
                ),
            ],
            interrupt_human=False,
            stop_current_action=False,
            task_terminated=False,
            authority_boundary="system",
        )

    if lead == "human":
        return _receipt(
            scenario,
            policy="control-menu",
            action="human_decide",
            recommendation=(
                "Surface the evidence and defer the route to the stronger task-local "
                "human capability."
            ),
            rationale=["The declared capability evidence favours the human."],
            alternatives=[
                _alternative(
                    "system_act",
                    "The system lacks stronger task-local capability evidence.",
                )
            ],
            interrupt_human=True,
            stop_current_action=True,
            task_terminated=False,
            authority_boundary="human",
        )

    if objective == "unknown" and scenario["independently_verifiable"]:
        return _receipt(
            scenario,
            policy="control-menu",
            action="seek_info",
            recommendation="Run the independent check before allocating final authority.",
            rationale=["The objective state is unknown but observable by the system."],
            alternatives=[
                _alternative(
                    "human_decide",
                    "The missing fact is system-observable rather than human-held.",
                )
            ],
            interrupt_human=False,
            stop_current_action=False,
            task_terminated=False,
            authority_boundary="system",
        )

    return _receipt(
        scenario,
        policy="control-menu",
        action="joint_navigate",
        recommendation=(
            "Expose the ambiguity, state what the system can verify, and ask the human "
            "only for the judgement or authority that remains."
        ),
        rationale=[
            "The current evidence does not establish a clear capability lead.",
            "No lower-interruption independent route resolves the decision.",
        ],
        alternatives=[
            _alternative(
                "system_act",
                "The evidence does not support unilateral system authority.",
            ),
            _alternative(
                "terminate_task",
                "Ambiguity can be navigated without abandoning the goal.",
            ),
        ],
        interrupt_human=True,
        stop_current_action=True,
        task_terminated=False,
        authority_boundary="joint",
    )


def evaluate_scenario(
    scenario: dict[str, Any], *, policy: str = "control-menu"
) -> dict[str, Any]:
    """Run a scenario through one transparent educational policy."""

    validate_scenario(scenario)
    if policy == "control-menu":
        receipt = _control_menu(scenario)
    elif policy == "binary-stop":
        receipt = _binary_stop(scenario)
    else:
        raise ValueError("policy must be control-menu or binary-stop")
    validate_receipt(receipt)
    return receipt
