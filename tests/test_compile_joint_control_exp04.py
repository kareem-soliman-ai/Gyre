"""Tests for the corrected EXP-04 qualification wrapper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "EXP-04_JointCapabilityCompilerRecovery_2026-07-28"
SCRIPT = EXP_DIR / "scripts" / "run_evaluation.py"


def _module():
    spec = importlib.util.spec_from_file_location("exp04_run_evaluation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _config() -> dict:
    return json.loads((EXP_DIR / "config.json").read_text(encoding="utf-8"))


def _valid_final(task: dict) -> dict:
    exp03_path = (
        ROOT
        / "tests"
        / "test_compile_joint_control_exp03.py"
    )
    spec = importlib.util.spec_from_file_location("exp03_tests_fixture", exp03_path)
    assert spec is not None and spec.loader is not None
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    final = fixture._valid_final(task)
    final["continuity"]["recover_without_interrupt_when"] = (
        "A bounded system recovery can restore independent verification."
    )
    final["continuity"]["interrupt_when_recovery_fails"] = (
        "The recovery budget is exhausted or human authority is required."
    )
    return final


def test_experiment_surfaces_exist():
    assert SCRIPT.is_file()
    assert (EXP_DIR / "config.json").is_file()
    assert (EXP_DIR / "docs" / "PREREGISTRATION.md").is_file()
    assert (EXP_DIR / "docs" / "REVIEWER_2_DESIGN_AUDIT.md").is_file()


def test_dimension_matcher_is_exact_and_deterministic():
    module = _module()
    task = _config()["tasks"][1]
    intake = {
        "questions": [
            {
                "id": "boundary",
                "question": "May I publish or only edit locally?",
                "route_dimension": "authority",
            },
            {
                "id": "checks",
                "question": "Which fixtures independently verify the transformations?",
                "route_dimension": "verification",
            },
        ]
    }
    score = module.match_questions(task, intake)
    assert score["critical_recall"] == 1.0
    assert score["question_precision"] == 1.0
    assert score["covered_critical_ids"] == [
        "execution_boundary",
        "verification_coverage",
    ]


def test_duplicate_dimension_counts_as_unmatched_question():
    module = _module()
    task = _config()["tasks"][0]
    intake = {
        "questions": [
            {
                "id": "first",
                "question": "Who chooses the final option?",
                "route_dimension": "authority",
            },
            {
                "id": "duplicate",
                "question": "Who approves that choice?",
                "route_dimension": "authority",
            },
        ]
    }
    score = module.match_questions(task, intake)
    assert score["critical_recall"] == 1.0
    assert score["question_precision"] == 0.5
    assert score["matched_question_ids"] == ["first"]
    assert score["unmatched_question_ids"] == ["duplicate"]


def test_oracle_reveals_only_covered_dimensions():
    module = _module()
    task = _config()["tasks"][2]
    intake = {
        "questions": [
            {
                "id": "criterion",
                "question": "What criterion resolves the latent construct?",
                "route_dimension": "success_criterion",
            }
        ]
    }
    answers = module.oracle_answers(task, intake)
    assert [answer["critical_question_id"] for answer in answers] == [
        "coordination_criterion"
    ]


def test_final_scorer_requires_bounded_recovery_before_interrupt():
    module = _module()
    task = _config()["tasks"][3]
    final = _valid_final(task)
    score = module.score_final(task, final)
    assert score["passed"] is True
    assert score["checks"]["bounded_recovery_before_interrupt"] is True

    final["continuity"]["recover_without_interrupt_when"] = ""
    score = module.score_final(task, final)
    assert score["passed"] is False
    assert score["checks"]["bounded_recovery_before_interrupt"] is False


def test_every_brief_fixes_nonmanipulated_object_level_scope():
    config = _config()
    briefs = {task["id"]: task["initial_brief"] for task in config["tasks"]}
    assert "exactly four" in briefs["poster_directions"]
    assert "Python JSONL parser" in briefs["parser_refactor"]
    assert "two fixed office days" in briefs["policy_brief"]
    assert "10,000-document" in briefs["archive_audit"]
