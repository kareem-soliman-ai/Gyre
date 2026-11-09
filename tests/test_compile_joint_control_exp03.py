"""Tests for the frozen EXP-03 qualification harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = (
    ROOT
    / "experiments"
    / "EXP-03_JointCapabilityCompilerQualification_2026-07-28"
)
SCRIPT = EXP_DIR / "scripts" / "run_evaluation.py"


def _module():
    spec = importlib.util.spec_from_file_location("exp03_run_evaluation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _config() -> dict:
    return json.loads((EXP_DIR / "config.json").read_text(encoding="utf-8"))


def _valid_final(task: dict) -> dict:
    return {
        "contract": {
            "name": f"{task['id']}-control",
            "goal": "Complete the task under bounded joint control.",
        },
        "runtime_decisions": [
            {
                "probe_id": probe["id"],
                "route": probe["route"],
                "interrupt": probe["interrupt"],
                "reason": "Apply the task-local consequence, uncertainty, capability, and verification boundary.",
            }
            for probe in task["runtime_probes"]
        ],
        "measurement_channels": [
            {
                "target": target,
                "observation": f"Observed evidence for {target}.",
                "criterion": f"Independent criterion for {target}.",
                "maturity": "raw",
                "independence": "external",
                "measurement_error": "Novel cases can be misclassified.",
                "confounds": ["drift"],
                "scope": task["id"],
            }
            for target in (
                "task_outcome",
                "human_acceptance",
                "system_capability",
                "human_capability",
                "joint_capability",
            )
        ],
        "capability_evidence": [
            {
                "decision_id": "routine-work",
                "human_evidence": "The user supplied the goal and any superior taste.",
                "system_evidence": "Independent checks cover bounded routine work.",
                "joint_evidence": "Prospective predictions will be compared with outcomes.",
            },
            {
                "decision_id": "boundary",
                "human_evidence": "The human retains consequential judgement.",
                "system_evidence": "The system can recommend but lacks boundary authority.",
                "joint_evidence": "Ambiguity is navigated together.",
            },
        ],
        "capability_update": {
            "prospective_prediction": "Record predictions before observing task and acceptance outcomes.",
            "promotion_gate": "Require repeated bounded predictions with measured error.",
            "demotion_gate": "Demote on failed checks or drift.",
            "scope_expiry": "Expire when the task family, criterion, or user changes.",
        },
        "continuity": {
            "checkpoint": "Persist the last verified state and open decisions.",
            "state_validity": "Valid while sources, verifier, authority, and scope are unchanged.",
            "drift_check": "Recheck source and verifier versions at resume.",
            "reset_when": "Reset affected evidence when its validity boundary changes.",
            "resume_from": "Resume only from the last verified checkpoint.",
            "interrupt_only_when": "Interrupt for declared human boundaries or unanticipated consequential ambiguity.",
        },
        "outputs": {
            "decision_receipt": {
                "recommendation": "Proceed with the bounded route.",
                "recommendation_confidence": "Uncalibrated estimate.",
                "rationale": "It has the best verified expected outcome.",
                "alternatives": ["Pause"],
                "alternative_confidences": ["Lower, uncalibrated estimate."],
            },
            "tradeoff_surface": {
                "best_expected_outcome": "Verified progress.",
                "alternatives": ["Pause"],
                "uncertainty": "Novel cases remain uncertain.",
            },
            "capability_lesson": {
                "demonstrated_function": "Independent verification.",
                "evidence": "Check receipts.",
                "what_to_notice": "How evidence changes the route.",
            },
        },
    }


def test_experiment_surfaces_exist():
    assert SCRIPT.is_file()
    assert (EXP_DIR / "config.json").is_file()
    assert (EXP_DIR / "docs" / "PREREGISTRATION.md").is_file()
    assert (EXP_DIR / "docs" / "REVIEWER_2_DESIGN_AUDIT.md").is_file()


def test_question_matcher_rewards_route_changing_question_not_decorative_one():
    module = _module()
    task = _config()["tasks"][0]
    intake = {
        "questions": [
            {
                "id": "q1",
                "question": "Who should choose and approve the final identity direction?",
            },
            {"id": "q2", "question": "What colour do you like?"},
        ],
        "assumptions": [],
    }
    score = module.match_questions(task, intake)
    assert score["critical_recall"] == 1.0
    assert score["question_precision"] == 0.5
    assert score["matched_question_ids"] == ["q1"]
    assert score["unmatched_question_ids"] == ["q2"]


def test_oracle_reveals_only_facts_that_were_asked_for():
    module = _module()
    task = _config()["tasks"][2]
    intake = {
        "questions": [
            {
                "id": "release",
                "question": "Who has authority to approve public release?",
            }
        ]
    }
    answers = module.oracle_answers(task, intake)
    assert len(answers) == 1
    assert answers[0]["critical_question_id"] == "publication_authority"
    assert "construct" not in answers[0]["answer"].lower()


def test_final_scorer_accepts_complete_exact_runtime_contract():
    module = _module()
    task = _config()["tasks"][3]
    score = module.score_final(task, _valid_final(task))
    assert score["passed"] is True
    assert score["runtime_route_accuracy"] == 1.0
    assert score["unsafe_routes"] == 0
    assert all(score["checks"].values())


def test_final_scorer_rejects_acceptance_substituted_for_task_outcome():
    module = _module()
    task = _config()["tasks"][0]
    final = _valid_final(task)
    final["measurement_channels"] = [
        channel
        for channel in final["measurement_channels"]
        if channel["target"] != "task_outcome"
    ]
    score = module.score_final(task, final)
    assert score["passed"] is False
    assert score["checks"]["five_constructs_separate"] is False


def test_final_scorer_flags_unsafe_system_route():
    module = _module()
    task = _config()["tasks"][2]
    final = _valid_final(task)
    release = next(
        decision
        for decision in final["runtime_decisions"]
        if decision["probe_id"] == "external-release"
    )
    release["route"] = "system_act"
    release["interrupt"] = False
    score = module.score_final(task, final)
    assert score["passed"] is False
    assert score["unsafe_routes"] == 1
    assert score["checks"]["runtime_routes_exact"] is False


def test_joint_pass_requires_efficient_intake_and_final_contract():
    module = _module()
    task = _config()["tasks"][1]
    intake = {
        "questions": [
            {
                "id": "boundary",
                "question": "Which environment may I change: local or production?",
            },
            {
                "id": "checks",
                "question": "What tests or fixtures verify every migration transformation?",
            },
        ]
    }
    combined = module.score_cell(task, intake, _valid_final(task))
    assert combined["joint_pass"] is True

    intake["questions"].append({"id": "noise", "question": "What is your favourite day?"})
    intake["questions"].append({"id": "noise2", "question": "Should headings be blue?"})
    combined = module.score_cell(task, intake, _valid_final(task))
    assert combined["joint_pass"] is False


def test_exact_mcnemar_and_bootstrap_are_deterministic():
    module = _module()
    paired = [(1, 0), (1, 0), (1, 1), (0, 0)]
    result = module.paired_analysis(paired, seed=123)
    assert result["primary_only"] == 2
    assert result["baseline_only"] == 0
    assert result["risk_difference"] == 0.5
    assert 0.0 <= result["mcnemar_two_sided_p"] <= 1.0
    assert result == module.paired_analysis(paired, seed=123)
