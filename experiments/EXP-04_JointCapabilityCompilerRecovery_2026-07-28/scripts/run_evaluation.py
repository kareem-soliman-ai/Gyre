#!/usr/bin/env python3
"""Run EXP-04 using the frozen EXP-03 transport and aggregation machinery."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_RUNNER_PATH = (
    REPO_ROOT
    / "experiments"
    / "EXP-03_JointCapabilityCompilerQualification_2026-07-28"
    / "scripts"
    / "run_evaluation.py"
)


def _load_base():
    spec = importlib.util.spec_from_file_location("exp03_frozen_runner", BASE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load frozen EXP-03 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()
base.EXPERIMENT_DIR = EXPERIMENT_DIR
base.CONFIG_PATH = EXPERIMENT_DIR / "config.json"
base.RESULTS_DIR = EXPERIMENT_DIR / "results"
base.RAW_DIR = base.RESULTS_DIR / "raw"
base.STAGE1_DIR = base.RAW_DIR / "stage1"
base.STAGE2_DIR = base.RAW_DIR / "stage2"
base.__file__ = str(Path(__file__).resolve())

INTAKE_ENVELOPE = """Before designing the control loop, identify missing facts
whose answers would change topology, authority, verification, success
criterion, stopping, delivery, state validity, or learning. Every other
object-level task fact is already supplied. Ask all and only route-changing
questions now in one batch.

Return exactly:
{
  "questions": [
    {
      "id": "short-id",
      "question": "one route-changing question",
      "route_dimension": "topology|authority|verification|success_criterion|stopping|delivery|state_validity|learning"
    }
  ],
  "assumptions": ["safe default applied instead of asking"]
}
Use each route dimension at most once. Use an empty list only when no
route-changing information is missing."""

base.FINAL_ENVELOPE = base.FINAL_ENVELOPE.replace(
    '    "interrupt_only_when": "..."\n',
    '    "interrupt_only_when": "...",\n'
    '    "recover_without_interrupt_when": "...",\n'
    '    "interrupt_when_recovery_fails": "..."\n',
) + """

Keep `contract` compact: include only the task-specific decision, loop, action,
and verification core that is not already represented elsewhere in the
envelope. A control-flow pause is not automatically a human interruption.
Attempt bounded autonomous recovery first when authority and verification allow
it."""


def _question_rows(intake: Any) -> list[dict[str, str]]:
    if not isinstance(intake, dict) or not isinstance(intake.get("questions"), list):
        return []
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(intake["questions"]):
        if not isinstance(raw, dict) or not isinstance(raw.get("question"), str):
            continue
        identifier = raw.get("id")
        dimension = raw.get("route_dimension")
        rows.append(
            {
                "id": identifier if isinstance(identifier, str) else f"q{index + 1}",
                "question": raw["question"],
                "route_dimension": dimension if isinstance(dimension, str) else "",
            }
        )
    return rows


def match_questions(task: dict[str, Any], intake: Any) -> dict[str, Any]:
    questions = _question_rows(intake)
    critical_by_dimension = {
        critical["dimension"]: critical for critical in task["critical_questions"]
    }
    covered_dimensions: set[str] = set()
    covered_ids: list[str] = []
    matched_ids: list[str] = []
    unmatched_ids: list[str] = []
    for question in questions:
        dimension = question["route_dimension"]
        critical = critical_by_dimension.get(dimension)
        if critical is not None and dimension not in covered_dimensions:
            covered_dimensions.add(dimension)
            covered_ids.append(critical["id"])
            matched_ids.append(question["id"])
        else:
            unmatched_ids.append(question["id"])
    recall = len(covered_ids) / len(task["critical_questions"])
    precision = len(matched_ids) / len(questions) if questions else 0.0
    f1 = (
        2 * recall * precision / (recall + precision)
        if recall + precision
        else 0.0
    )
    return {
        "critical_recall": recall,
        "question_precision": precision,
        "question_f1": f1,
        "covered_critical_ids": covered_ids,
        "matched_question_ids": matched_ids,
        "unmatched_question_ids": unmatched_ids,
        "question_count": len(questions),
    }


def oracle_answers(task: dict[str, Any], intake: Any) -> list[dict[str, str]]:
    covered = set(match_questions(task, intake)["covered_critical_ids"])
    return [
        {
            "critical_question_id": critical["id"],
            "route_dimension": critical["dimension"],
            "answer": critical["answer"],
        }
        for critical in task["critical_questions"]
        if critical["id"] in covered
    ]


_base_score_final = base.score_final


def score_final(task: dict[str, Any], final: Any) -> dict[str, Any]:
    score = _base_score_final(task, final)
    continuity = final.get("continuity") if isinstance(final, dict) else None
    recovery_complete = all(
        base._nonempty_text(continuity, key)
        for key in (
            "recover_without_interrupt_when",
            "interrupt_when_recovery_fails",
        )
    )
    score["checks"]["bounded_recovery_before_interrupt"] = recovery_complete
    score["passed"] = all(score["checks"].values())
    return score


def intake_messages(task: dict[str, Any], arm: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": base.INTAKE_SYSTEM + base._arm_material(arm, 1),
        },
        {
            "role": "user",
            "content": (
                f"Task: {task['title']}\n\n{task['initial_brief']}\n\n"
                + INTAKE_ENVELOPE
            ),
        },
    ]


_base_verify = base.verify_frozen_inputs


def verify_frozen_inputs(config: dict[str, Any]) -> None:
    _base_verify(config)
    actual = hashlib.sha256(BASE_RUNNER_PATH.read_bytes()).hexdigest()
    expected = config["frozen"]["base_runner_sha256"]
    if actual != expected:
        raise RuntimeError(
            f"frozen base runner mismatch: expected {expected}, got {actual}"
        )


_base_render_summary = base.render_summary


def render_summary(summary: dict[str, Any]) -> str:
    return _base_render_summary(summary).replace(
        "# EXP-03 summary",
        "# EXP-04 summary",
        1,
    )


base.match_questions = match_questions
base.oracle_answers = oracle_answers
base.score_final = score_final
base.intake_messages = intake_messages
base.verify_frozen_inputs = verify_frozen_inputs
base.render_summary = render_summary

score_cell = base.score_cell
paired_analysis = base.paired_analysis


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
