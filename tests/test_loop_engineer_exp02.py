"""Contract tests for the EXP-02 version 1.1 qualification harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT / "experiments" / "EXP-02_LoopEngineerV11Qualification_2026-07-28"
)
SCRIPT = EXPERIMENT / "scripts" / "run_evaluation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("loop_skill_exp02", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _template() -> dict:
    return json.loads(
        (
            ROOT
            / "skills"
            / "loop-engineer"
            / "assets"
            / "loop-graph-spec.json"
        ).read_text(encoding="utf-8")
    )


def test_preregistration_freezes_independent_tasks_and_three_arms() -> None:
    assert (EXPERIMENT / "docs" / "PREREGISTRATION.md").is_file()
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))

    assert config["frozen"]["skill_version"] == "1.1.0"
    assert config["arms"] == ["bare", "template", "skill"]
    assert len(config["tasks"]) == 4
    assert len(config["generators"]["models"]) == 2
    assert config["generators"]["replicate_seeds"] == [311, 733]
    assert config["repair"]["max_repairs"] == 1
    assert config["judges"]["swap_order"] is True


def test_exp02_tasks_do_not_reuse_exp01_briefs() -> None:
    old = json.loads(
        (
            ROOT
            / "experiments"
            / "EXP-01_LoopEngineerSkillQualification_2026-07-28"
            / "config.json"
        ).read_text(encoding="utf-8")
    )
    new = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    old_briefs = {task["brief"] for task in old["tasks"]}

    assert not old_briefs.intersection(task["brief"] for task in new["tasks"])


def test_hidden_check_accepts_database_contract_and_rejects_missing_cap() -> None:
    module = _load_module()
    spec = _template()
    spec["task_constraints"] = [
        {
            "id": "concurrency",
            "requirement": "Run at most 5 tenant migrations concurrently.",
            "enforced_by": "scheduler semaphore",
            "on_violation": "blocked",
        },
        {
            "id": "window",
            "requirement": "Finish within the 25 minute maintenance window.",
            "enforced_by": "deadline guard",
            "on_violation": "rollback",
        },
        {
            "id": "retry",
            "requirement": "Stop after 2 failed verification attempts.",
            "enforced_by": "verification-loop budget",
            "on_violation": "rollback",
        },
    ]
    spec["nodes"][0].update(
        {
            "purpose": "Execute a live destructive schema migration.",
            "consequence": "high",
            "human_approval": True,
        }
    )
    spec["state"]["persistence"] = (
        "Persist an idempotent tenant migration ledger after every transition."
    )
    spec["loops"][0]["budget"]["max_cycles"] = 2
    spec["loops"][0]["terminal_states"].append("rolled_back")

    passed = module.run_hidden_checks("database_migration", spec)
    assert passed["passed"] is True, passed

    spec["task_constraints"][0]["requirement"] = "Bound concurrency."
    failed = module.run_hidden_checks("database_migration", spec)
    assert failed["passed"] is False
    assert "concurrency_cap_5" in failed["failed_ids"]


def test_hidden_check_rejects_active_dynamic_batch_topology() -> None:
    module = _load_module()
    spec = _template()
    spec["dynamic_topology"].update(
        {
            "enabled": True,
            "mode": "active",
            "switching_costs": ["worker startup"],
            "hysteresis": "two consecutive readings",
        }
    )

    result = module.run_hidden_checks("adaptive_batch", spec)

    assert "adaptive_route_shadowed" in result["failed_ids"]


def test_privacy_check_accepts_explicit_analytics_access_prohibition() -> None:
    module = _load_module()
    spec = _template()
    spec["task_constraints"] = [
        {
            "id": "retention",
            "requirement": "Retain documents for no more than 30 days.",
            "enforced_by": "retention timer",
            "on_violation": "delete",
        },
        {
            "id": "deletion",
            "requirement": "Delete within 24 hours of consent withdrawal.",
            "enforced_by": "deletion deadline",
            "on_violation": "human review",
        },
        {
            "id": "reminders",
            "requirement": "Send at most 2 reminder cycles.",
            "enforced_by": "reminder counter",
            "on_violation": "stop reminders",
        },
    ]
    spec["nodes"][0].update(
        {
            "id": "analytics",
            "purpose": "Process non-personal analytics data.",
            "authority": "May process anonymized data; may not access personal documents.",
        }
    )
    spec["nodes"][1]["authority"] = (
        "May validate documents; may not send personal data to analytics."
    )
    spec["nodes"].append(
        {
            "id": "activation",
            "kind": "human",
            "purpose": "Approve account activation.",
            "capability_evidence": "Compliance-owner assignment.",
            "consequence": "high",
            "authority": "May approve activation.",
            "human_approval": True,
            "inputs": ["review packet"],
            "outputs": ["approval decision"],
            "failure_policy": "Do not activate.",
        }
    )
    spec["state"]["reset_boundary"] = "Consent withdrawal or revocation."
    spec["loops"][0]["terminal_states"].append("documents_deleted")

    result = module.run_hidden_checks("privacy_onboarding", spec)

    assert "pii_isolated_from_analytics" not in result["failed_ids"]


def test_hidden_checker_is_total_over_wrong_shaped_optional_sections() -> None:
    module = _load_module()
    spec = _template()
    spec["evaluation"] = "compare with three judges"
    spec["dynamic_topology"] = "shadow"

    result = module.run_hidden_checks("evaluation_adjudication", spec)

    assert result["passed"] is False
    assert "fixed_three_judge_baseline" in result["failed_ids"]


def test_consistent_preference_requires_order_swap_agreement() -> None:
    module = _load_module()

    assert module.consistent_preference("A", "B", {"A": "skill", "B": "template"}) == "skill"
    assert module.consistent_preference("A", "A", {"A": "skill", "B": "template"}) == "inconsistent"
    assert module.consistent_preference("tie", "tie", {"A": "skill", "B": "template"}) == "tie"


def test_exact_mcnemar_uses_only_discordant_pairs() -> None:
    module = _load_module()

    result = module.exact_mcnemar(skill_only=6, baseline_only=1)

    assert result["discordant"] == 7
    assert 0.0 <= result["two_sided_p"] <= 1.0
