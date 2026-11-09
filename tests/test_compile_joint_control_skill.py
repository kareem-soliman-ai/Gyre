"""Contract tests for the experimental Joint Capability Compiler skill."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "compile-joint-control"
VALIDATOR = SKILL_ROOT / "scripts" / "validate.py"


def _valid_intake(status: str = "ready") -> dict:
    questions = []
    if status == "needs_input":
        questions = [
            {
                "id": "publication-authority",
                "question": "May the system publish, or may it only prepare a draft?",
                "decisions_affected": ["publish"],
                "route_effect": "Changes the publish decision from human-owned to eligible for bounded system action.",
                "default_if_unanswered": "prepare a draft and require human approval",
                "risk_of_default": "slower delivery without an unauthorized external action",
                "answer_source": "human",
            }
        ]
    preflight_checks = []
    if status == "needs_preflight":
        preflight_checks = [
            {
                "id": "fixture-inventory",
                "check": "Inspect the repository for deterministic fixtures and their scope.",
                "decisions_affected": ["publish"],
                "route_effect": "Determines whether routine draft checks may run autonomously.",
                "on_failure": "Use the conservative human-review route.",
            }
        ]
    return {
        "kind": "joint-control-intake",
        "status": status,
        "goal": {
            "outcome": "Produce a defensible research brief.",
            "done_when": "Claims are source-backed and the approved brief is delivered.",
        },
        "known": {
            "stakes": "Publishing is high consequence; drafting is reversible.",
            "human_strengths": ["audience taste", "final publication judgement"],
            "system_evidence": ["previous source audits passed deterministic citation checks"],
            "verification_available": ["citation checker", "human publication approval"],
            "ambiguity_policy": "navigate consequential ambiguity jointly",
            "interruption_policy": "interrupt only for boundary crossings or unanticipated consequential ambiguity",
            "learning_preference": "explain unfamiliar research functions while demonstrating them",
        },
        "anticipated_decisions": [
            {
                "id": "publish",
                "description": "Whether to publish the final brief.",
                "consequence": "high",
                "uncertainty": "medium",
                "reversibility": "low",
                "missing": (
                    ["publication authority"]
                    if status == "needs_input"
                    else ["fixture coverage"]
                    if status == "needs_preflight"
                    else []
                ),
            }
        ],
        "questions": questions,
        "preflight_checks": preflight_checks,
        "assumptions": ["The system may create local drafts."],
    }


def _signal(
    signal_id: str,
    target: str,
    *,
    maturity: str = "raw",
    calibration_evidence: dict | None = None,
) -> dict:
    signal = {
        "id": signal_id,
        "target": target,
        "observation": f"Prospective and observed evidence for {target}.",
        "criterion": f"Compare {target} prediction with its declared outcome channel.",
        "maturity": maturity,
        "independence": "external",
        "measurement_error": "False positives remain possible on novel task families.",
        "confounds": ["distribution shift", "criterion noise"],
        "scope": "research briefs for this user",
    }
    if calibration_evidence is not None:
        signal["calibration_evidence"] = calibration_evidence
    return signal


def _valid_contract() -> dict:
    return {
        "kind": "joint-control-contract",
        "name": "research-brief-control",
        "goal": {
            "outcome": "Produce a defensible research brief while improving joint capability.",
            "done_when": "All claims pass checks and the human approves publication.",
            "failure_cost": "A bad draft is reversible; an erroneous publication is consequential.",
        },
        "topology": {
            "selected": "single-loop",
            "simpler_baseline": "one model call plus citation checks",
            "why_more_structure_is_needed": "Long-horizon work needs checkpoints and a separate publication boundary.",
        },
        "decisions": [
            {
                "id": "draft",
                "scope": "Research, write, and locally revise the brief.",
                "consequence": "low",
                "uncertainty": "low",
                "reversibility": "high",
                "default_lead": "system",
                "capability_basis": {
                    "human_evidence": "The user supplied the research objective.",
                    "system_evidence": "Prior citation audits passed on this task family.",
                    "joint_evidence": "Prior drafts were accepted after deterministic checks.",
                },
                "system_may_act_when": "Checks are available and no publication action is attempted.",
                "human_required_when": "A taste choice materially changes the thesis.",
                "verification_refs": ["citation-check"],
            },
            {
                "id": "publish",
                "scope": "Release the brief outside the workspace.",
                "consequence": "high",
                "uncertainty": "medium",
                "reversibility": "low",
                "default_lead": "human",
                "capability_basis": {
                    "human_evidence": "The user owns audience and reputational judgement.",
                    "system_evidence": "The system can report checks but has no publication authority.",
                    "joint_evidence": "No prospective publication calibration exists.",
                },
                "system_may_act_when": "Never without explicit approval.",
                "human_required_when": "Before every external publication.",
                "verification_refs": ["citation-check", "human-publication-review"],
            },
        ],
        "signals": [
            _signal("task-quality", "task_outcome"),
            _signal("human-acceptance", "human_acceptance"),
            _signal("system-capability", "system_capability"),
            _signal("human-capability", "human_capability"),
            _signal("joint-capability", "joint_capability"),
        ],
        "actions": [
            {
                "id": "revise",
                "decision": "draft",
                "execution_authority": "system",
                "description": "Revise the local draft and rerun checks.",
            },
            {
                "id": "request-publication",
                "decision": "publish",
                "execution_authority": "human",
                "description": "Present the recommendation and request an explicit decision.",
            },
        ],
        "rules": [
            {
                "id": "revise-on-defect",
                "when": "A named defect remains and the revision budget is available.",
                "using_signals": ["task-quality", "system-capability"],
                "action": "revise",
                "authority_limit": "Local reversible edits only.",
            },
            {
                "id": "publication-boundary",
                "when": "The checked draft is ready for external release.",
                "using_signals": ["task-quality", "human-acceptance", "joint-capability"],
                "action": "request-publication",
                "authority_limit": "The system recommends; the human decides and acts.",
            },
        ],
        "loop": {
            "steps": [
                {
                    "id": "produce",
                    "operation": "Research or revise the brief.",
                    "owner": "system",
                    "input": "goal, evidence, and named defects",
                    "output": "draft plus change receipt",
                },
                {
                    "id": "measure",
                    "operation": "Run independent outcome and capability checks.",
                    "owner": "deterministic",
                    "input": "draft plus prospective predictions",
                    "output": "signal observations",
                },
                {
                    "id": "control",
                    "operation": "Select a declared action under the authority policy.",
                    "owner": "system",
                    "input": "signals, decision boundaries, and remaining budget",
                    "output": "action or terminal state",
                },
            ],
            "transitions": [
                {
                    "from": "produce",
                    "to": "measure",
                    "when": "A new draft checkpoint exists.",
                },
                {
                    "from": "measure",
                    "to": "control",
                    "when": "Required signals have observations.",
                },
                {
                    "from": "control",
                    "to": "produce",
                    "when": "The selected action is revise.",
                },
            ],
            "terminal_states": ["accepted", "human_decision", "blocked", "budget_exhausted"],
            "budgets": {"max_cycles": 4, "max_cost_usd": 2.0, "max_minutes": 30},
        },
        "verification": [
            {
                "id": "citation-check",
                "subject": "Every factual claim in the brief.",
                "method": "Resolve citations and compare claim text with source evidence.",
                "criterion": "No unsupported material factual claims.",
                "on_fail": "Return named defects to the revision loop.",
            },
            {
                "id": "human-publication-review",
                "subject": "The external publication decision.",
                "method": "Present the recommendation, uncertainty, and alternatives.",
                "criterion": "Explicit human approval.",
                "on_fail": "Keep the draft private.",
            },
        ],
        "capability_learning": {
            "prediction_receipt": "Record prospective probabilities before observing outcomes.",
            "outcome_channels": ["task-quality", "human-acceptance"],
            "promotion_gate": "Promote only from repeated prospective predictions with measured error in a bounded task family.",
            "demotion_gate": "Demote on drift, failed verification, or calibration outside tolerance.",
        },
        "prospective_value": {
            "forecast_lock": "Record human and system forecasts independently before either sees the other forecast or the outcome.",
            "forecast_sources": ["human", "system"],
            "target_outcomes": ["task-quality", "human-acceptance"],
            "value_components": [
                "objective_outcome",
                "cost",
                "risk",
                "learning_value",
            ],
            "action_value_rule": "Estimate expected declared outcome utility for each allowed action, then subtract cost and risk and add declared learning value.",
            "value_of_information_rule": "Seek evidence only when its expected change in the best allowed action value exceeds measurement and delay cost.",
            "combination_rule": "Do not fuse human and system forecasts without task-local calibration and dependence evidence; otherwise surface their range and disagreement.",
            "dependence_rule": "Treat shared context, model family, data, or disclosure as correlated evidence.",
            "measurement_disturbance_rule": "Record whether asking, testing, explaining, or verifying changes human attention, confidence, the source, evaluator, task state, or future evidence.",
            "future_observation_value_rule": "Price how the current action changes the quality and availability of later observations, not only immediate information gain.",
            "counterfactual_rule": "Label disturbance or action effects causal only with randomisation, paired twins, a defensible causal model, or explicit partial-identification bounds.",
            "conservative_budget_rule": "Apply disturbance and authority caps to a declared upper uncertainty bound, not only a point estimate.",
            "fixed_weak_baseline": "Compare adaptive control with the simplest low-disturbance fixed policy under matched budgets.",
            "negative_control": "Include a setting where the measurement cannot disturb the source and reject a built-in policy advantage there.",
            "uncalibrated_behavior": "Label estimates uncalibrated and keep them in shadow mode.",
            "low_ceiling_behavior": "Surface that every route has low predicted value; do not turn a relative winner into an absolute quality claim.",
            "hard_constraints": [
                "External publication remains human-owned.",
                "Safety and authority constraints are applied before value optimisation.",
            ],
            "leakage_guards": [
                "No feature computed from the outcome or future trace may drive prospective control.",
                "Lock forecasts before disclosing another controller's forecast.",
            ],
            "promotion_gate": "Promote only when the value-aware policy improves objective outcomes against a matched baseline without more unsafe autonomy.",
        },
        "continuity": {
            "checkpoint": "Persist the draft, evidence ledger, predictions, and open decisions after each cycle.",
            "state_validity": "Valid only while sources, task scope, and authority remain unchanged.",
            "drift_check": "Recheck source freshness and calibration scope at resume.",
            "reset_when": "Reset capability claims when the task family or outcome criterion changes.",
            "resume_from": "The last verified checkpoint, never an unverified partial action.",
            "interrupt_only_when": "A declared boundary is crossed or consequential ambiguity was not anticipated.",
            "recover_without_interrupt_when": "A bounded recovery action can restore independent verification.",
            "interrupt_when_recovery_fails": "The recovery budget is exhausted or the remaining choice crosses a human authority boundary.",
        },
        "human_controller": {
            "observes": [
                "decision_receipt",
                "tradeoff_surface",
                "capability_lesson",
            ],
            "available_actions": [
                {
                    "id": action_id,
                    "effect": f"Apply the declared {action_id} control transition.",
                    "next_state": f"state after {action_id}",
                    "reversibility": "Declared per decision.",
                    "evidence_effect": "Record the choice separately from objective outcome.",
                }
                for action_id in (
                    "follow_recommendation",
                    "choose_alternative",
                    "request_evidence",
                    "revise_criterion",
                    "change_authority",
                    "delegate_bounded",
                    "pause_action",
                    "terminate_goal",
                )
            ],
            "choice_interpretation": "A human choice is a control action, not proof of objective quality.",
            "framing_guard": "Present consequences and uncertainty without hiding or preselecting alternatives.",
            "human_measurement_rule": "Treat every human observation as a scoped signal with a construct, criterion, error, confounds, and maturity.",
            "calibration_path": [
                "name the construct and criterion",
                "record a prospective prediction and confidence",
                "observe an independent outcome where possible",
                "score error across repeated cases",
                "retain capability only inside the evidenced scope",
                "demote on drift or criterion change",
            ],
        },
        "outputs": {
            "decision_receipt": {
                "required_fields": [
                    "recommendation",
                    "recommendation_confidence",
                    "rationale",
                    "alternatives",
                    "alternative_confidences",
                ]
            },
            "tradeoff_surface": {
                "required_fields": ["best_expected_outcome", "alternatives", "uncertainty"]
            },
            "capability_lesson": {
                "required_fields": ["demonstrated_function", "evidence", "what_to_notice"]
            },
        },
        "evaluation": {
            "matched_baseline": "one model call plus citation checks",
            "metrics": [
                "task outcome",
                "unsafe autonomy",
                "human interruptions",
                "calibration error",
                "joint capability change",
            ],
            "trap_cases": [
                "human taste exceeds system capability",
                "system expertise exceeds user knowledge",
                "corrupted verifier",
                "unanticipated high-consequence ambiguity",
            ],
        },
    }


def _run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_skill_package_has_compact_required_surfaces():
    assert (SKILL_ROOT / "SKILL.md").is_file()
    assert (SKILL_ROOT / "agents" / "openai.yaml").is_file()
    assert (SKILL_ROOT / "assets" / "intake-state.json").is_file()
    assert (SKILL_ROOT / "assets" / "joint-control-contract.json").is_file()
    assert (SKILL_ROOT / "references" / "evaluation-cases.md").is_file()
    assert VALIDATOR.is_file()


def test_validator_accepts_ready_and_needs_input_intakes(tmp_path: Path):
    for status in ("ready", "needs_input", "needs_preflight"):
        result = _run_validator(_write(tmp_path, f"{status}.json", _valid_intake(status)))
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS" in result.stdout


def test_intake_requires_one_route_effect_for_every_question(tmp_path: Path):
    intake = _valid_intake("needs_input")
    intake["questions"][0]["route_effect"] = ""
    result = _run_validator(_write(tmp_path, "decorative-question.json", intake))
    assert result.returncode == 1
    assert "route_effect" in result.stdout


def test_intake_question_must_reference_an_anticipated_decision(tmp_path: Path):
    intake = _valid_intake("needs_input")
    intake["questions"][0]["decisions_affected"] = ["unknown"]
    result = _run_validator(_write(tmp_path, "unknown-decision.json", intake))
    assert result.returncode == 1
    assert "anticipated decision" in result.stdout.lower()


def test_ready_intake_cannot_retain_questions(tmp_path: Path):
    intake = _valid_intake("needs_input")
    intake["status"] = "ready"
    result = _run_validator(_write(tmp_path, "ready-with-questions.json", intake))
    assert result.returncode == 1
    assert "ready intake" in result.stdout.lower()


def test_human_questions_and_system_preflights_are_separate(tmp_path: Path):
    intake = _valid_intake("needs_input")
    intake["questions"][0]["answer_source"] = "system_observable"
    result = _run_validator(_write(tmp_path, "ask-system-fact.json", intake))
    assert result.returncode == 1
    assert "answer_source" in result.stdout

    preflight = _valid_intake("needs_preflight")
    preflight["questions"] = [
        {
            "id": "bad-question",
            "question": "Can you inspect the repository for me?",
            "decisions_affected": ["publish"],
            "route_effect": "Determines fixture coverage.",
            "default_if_unanswered": "Use human review.",
            "risk_of_default": "Slower work.",
            "answer_source": "human",
        }
    ]
    result = _run_validator(_write(tmp_path, "preflight-with-question.json", preflight))
    assert result.returncode == 1
    assert "needs_preflight" in result.stdout


def test_validator_accepts_complete_joint_control_contract(tmp_path: Path):
    result = _run_validator(_write(tmp_path, "valid-contract.json", _valid_contract()))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_contract_separates_acceptance_from_task_outcome(tmp_path: Path):
    contract = _valid_contract()
    contract["signals"] = [
        signal for signal in contract["signals"] if signal["target"] != "task_outcome"
    ]
    result = _run_validator(_write(tmp_path, "acceptance-is-not-quality.json", contract))
    assert result.returncode == 1
    assert "task_outcome" in result.stdout
    assert "human_acceptance" in result.stdout


def test_contract_requires_separate_capability_constructs(tmp_path: Path):
    contract = _valid_contract()
    contract["signals"] = [
        signal for signal in contract["signals"] if signal["target"] != "joint_capability"
    ]
    result = _run_validator(_write(tmp_path, "collapsed-capability.json", contract))
    assert result.returncode == 1
    assert "joint_capability" in result.stdout


def test_self_deciding_signal_requires_prospective_calibration_receipt(tmp_path: Path):
    contract = _valid_contract()
    contract["signals"][0]["maturity"] = "self-deciding"
    result = _run_validator(_write(tmp_path, "unearned-self-control.json", contract))
    assert result.returncode == 1
    assert "calibration_evidence" in result.stdout

    corrected = copy.deepcopy(contract)
    corrected["signals"][0]["calibration_evidence"] = {
        "prediction_count": 40,
        "criterion": "independently adjudicated brief quality",
        "observed_error": "Brier 0.11; 90% CI [0.08, 0.15]",
        "scope": "research briefs for this user",
        "valid_until": "2026-10-28",
    }
    result = _run_validator(_write(tmp_path, "earned-self-control.json", corrected))
    assert result.returncode == 0, result.stdout + result.stderr


def test_high_consequence_decision_remains_human_owned(tmp_path: Path):
    contract = _valid_contract()
    contract["decisions"][1]["default_lead"] = "system"
    result = _run_validator(_write(tmp_path, "unsafe-high-stakes.json", contract))
    assert result.returncode == 1
    assert "high-consequence" in result.stdout.lower()


def test_system_owned_decision_requires_reversibility_and_verification(tmp_path: Path):
    contract = _valid_contract()
    contract["decisions"][0]["reversibility"] = "low"
    contract["decisions"][0]["verification_refs"] = []
    result = _run_validator(_write(tmp_path, "unverified-autonomy.json", contract))
    assert result.returncode == 1
    assert "system-led" in result.stdout.lower()
    assert "verification" in result.stdout.lower()


def test_rules_reference_declared_signals_actions_and_decisions(tmp_path: Path):
    contract = _valid_contract()
    contract["rules"][0]["using_signals"] = ["imaginary-signal"]
    contract["rules"][0]["action"] = "imaginary-action"
    result = _run_validator(_write(tmp_path, "dangling-policy.json", contract))
    assert result.returncode == 1
    assert "unknown signal" in result.stdout.lower()
    assert "unknown action" in result.stdout.lower()


def test_output_channels_remain_distinct_and_explanatory(tmp_path: Path):
    contract = _valid_contract()
    contract["outputs"].pop("capability_lesson")
    contract["outputs"]["decision_receipt"]["required_fields"].remove("alternatives")
    result = _run_validator(_write(tmp_path, "collapsed-output.json", contract))
    assert result.returncode == 1
    assert "capability_lesson" in result.stdout
    assert "alternatives" in result.stdout


def test_long_horizon_contract_requires_resume_and_drift_controls(tmp_path: Path):
    contract = _valid_contract()
    contract["continuity"]["drift_check"] = ""
    contract["continuity"]["resume_from"] = ""
    result = _run_validator(_write(tmp_path, "fragile-resume.json", contract))
    assert result.returncode == 1
    assert "drift_check" in result.stdout
    assert "resume_from" in result.stdout


def test_contract_separates_system_recovery_from_human_interruption(tmp_path: Path):
    contract = _valid_contract()
    contract["continuity"]["recover_without_interrupt_when"] = ""
    contract["continuity"]["interrupt_when_recovery_fails"] = ""
    result = _run_validator(_write(tmp_path, "interrupt-everything.json", contract))
    assert result.returncode == 1
    assert "recover_without_interrupt_when" in result.stdout
    assert "interrupt_when_recovery_fails" in result.stdout


def test_contract_models_the_human_as_a_controller_with_more_than_accept_reject(
    tmp_path: Path,
):
    contract = _valid_contract()
    contract["human_controller"]["available_actions"] = [
        item
        for item in contract["human_controller"]["available_actions"]
        if item["id"] not in {"request_evidence", "revise_criterion"}
    ]
    result = _run_validator(_write(tmp_path, "binary-human-gate.json", contract))
    assert result.returncode == 1
    assert "request_evidence" in result.stdout
    assert "revise_criterion" in result.stdout


def test_human_control_choice_is_not_treated_as_objective_outcome_evidence(
    tmp_path: Path,
):
    contract = _valid_contract()
    contract["human_controller"]["choice_interpretation"] = ""
    result = _run_validator(_write(tmp_path, "choice-is-ground-truth.json", contract))
    assert result.returncode == 1
    assert "choice_interpretation" in result.stdout


def test_human_controller_requires_a_measurement_and_calibration_path(
    tmp_path: Path,
):
    contract = _valid_contract()
    contract["human_controller"]["human_measurement_rule"] = ""
    contract["human_controller"]["calibration_path"] = []
    result = _run_validator(_write(tmp_path, "unmeasured-human-controller.json", contract))
    assert result.returncode == 1
    assert "human_measurement_rule" in result.stdout
    assert "calibration_path" in result.stdout


def test_capability_promotion_and_demotion_gates_are_explicit(tmp_path: Path):
    contract = _valid_contract()
    contract["capability_learning"]["promotion_gate"] = ""
    contract["capability_learning"]["demotion_gate"] = ""
    result = _run_validator(_write(tmp_path, "silent-promotion.json", contract))
    assert result.returncode == 1
    assert "promotion_gate" in result.stdout
    assert "demotion_gate" in result.stdout


def test_contract_requires_prospective_signal_and_value_rules(tmp_path: Path):
    contract = _valid_contract()
    contract.pop("prospective_value")
    result = _run_validator(_write(tmp_path, "no-prospective-value.json", contract))
    assert result.returncode == 1
    assert "prospective_value" in result.stdout


def test_value_layer_requires_independent_lock_leakage_and_no_earned_fusion(
    tmp_path: Path,
):
    contract = _valid_contract()
    contract["prospective_value"]["forecast_lock"] = ""
    contract["prospective_value"]["leakage_guards"] = []
    contract["prospective_value"]["combination_rule"] = ""
    result = _run_validator(_write(tmp_path, "unsafe-value-layer.json", contract))
    assert result.returncode == 1
    assert "forecast_lock" in result.stdout
    assert "leakage_guards" in result.stdout
    assert "combination_rule" in result.stdout


def test_value_layer_prices_measurement_disturbance_and_future_observations(
    tmp_path: Path,
):
    contract = _valid_contract()
    contract["prospective_value"]["measurement_disturbance_rule"] = ""
    contract["prospective_value"]["future_observation_value_rule"] = ""
    contract["prospective_value"]["fixed_weak_baseline"] = ""
    result = _run_validator(_write(tmp_path, "myopic-observer.json", contract))
    assert result.returncode == 1
    assert "measurement_disturbance_rule" in result.stdout
    assert "future_observation_value_rule" in result.stdout
    assert "fixed_weak_baseline" in result.stdout
