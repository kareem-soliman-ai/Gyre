"""Contract tests for the public loop-engineer skill package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "loop-engineer"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_spec.py"


def _valid_spec() -> dict:
    return {
        "name": "review-and-revise",
        "objective": "Improve a draft until evidence says another revision will not pay.",
        "task_constraints": [
            {
                "id": "bounded-scope",
                "requirement": "Do not publish the draft.",
                "enforced_by": "generate.authority",
                "on_violation": "block and request human review",
            }
        ],
        "topology_decision": {
            "selected": "single-loop",
            "simpler_baseline": "one generator pass followed by deterministic checks",
            "why_more_structure_is_needed": "A revision is useful only when a check finds a named defect.",
        },
        "mode": "shadow",
        "state": {
            "fields": ["draft", "checks", "revision_count", "evidence_added"],
            "persistence": "checkpoint after each completed revision",
            "reset_boundary": "new user task",
        },
        "nodes": [
            {
                "id": "generate",
                "kind": "agent",
                "purpose": "Produce or revise the draft.",
                "capability_evidence": "Passes the task-specific draft rubric in pilot cases.",
                "consequence": "medium",
                "authority": "May edit the draft but cannot publish it.",
                "human_approval": False,
                "inputs": ["task", "current draft", "named defects"],
                "outputs": ["revised draft", "change summary"],
                "failure_policy": "Return a blocked result with the missing input.",
            },
            {
                "id": "review",
                "kind": "deterministic",
                "purpose": "Check the draft against executable requirements.",
                "capability_evidence": "Unit-tested checks with known fixtures.",
                "consequence": "low",
                "authority": "May report defects but cannot edit or publish.",
                "human_approval": False,
                "inputs": ["revised draft"],
                "outputs": ["checks", "evidence added"],
                "failure_policy": "Fail closed and preserve the prior checkpoint.",
            },
        ],
        "edges": [
            {
                "from": "generate",
                "to": "review",
                "mechanism": "typed packet",
                "guard": "draft exists and change summary is non-empty",
                "handoff_contract": "draft plus identifiers for every claimed change",
                "on_failure": "block and request the missing field",
            },
            {
                "from": "review",
                "to": "generate",
                "mechanism": "typed packet",
                "guard": "a named defect remains and budget is available",
                "handoff_contract": "defect id, evidence, and acceptance criterion",
                "on_failure": "exit to human review",
            },
        ],
        "loops": [
            {
                "id": "revision-loop",
                "controlled_variable": "unresolved named defects",
                "observation": "check results and evidence added by the latest revision",
                "sensor": {
                    "name": "deterministic-check-plus-evidence-gain",
                    "maturity": "raw",
                    "independence": "external",
                    "confounds": ["checks can miss semantic defects"],
                },
                "decision_rule": "continue only when a defect remains and the last cycle added evidence",
                "actions": ["continue", "reframe", "seek_info", "escalate", "stop"],
                "terminal_states": ["passed", "budget_exhausted", "human_review", "no_information_gain"],
                "budget": {"max_cycles": 3, "max_cost_usd": 1.0, "max_minutes": 10},
                "escalation": "send the last good draft, open defects, and attempted fixes to a human",
                "persistence": "store each accepted draft and its check results",
            }
        ],
        "dynamic_topology": {
            "enabled": False,
            "mode": "fixed",
            "switching_costs": [],
            "hysteresis": "not applicable while topology is fixed",
            "promotion_gate": "shadow recommendations must beat the fixed route under matched budget",
        },
        "evaluation": {
            "link_a_sensor": "compare loop-state calls with independently labelled trace states",
            "link_b_policy": "hold the sensor fixed and compare response menus",
            "link_c_outcome": "compare task quality, cost, and latency with the simpler baseline",
            "matched_baseline": "one generator pass followed by deterministic checks",
            "trap_cases": ["healthy repeated checking", "unsolvable task", "corrupted sensor"],
        },
        "prompt_contracts": {
            "generator": "Revise only the named defects and report evidence for each change.",
            "sensor": "Report observable evidence added; do not choose the next action.",
            "controller": "Choose from the declared action menu using the sensor report and budget.",
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


def test_skill_package_has_required_surfaces():
    assert (SKILL_ROOT / "SKILL.md").is_file()
    assert (SKILL_ROOT / "CHANGELOG.md").is_file()
    assert (SKILL_ROOT / "assets" / "loop-graph-spec.json").is_file()
    assert VALIDATOR.is_file()


def test_validator_accepts_a_complete_spec(tmp_path: Path):
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(_valid_spec()), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_validator_rejects_an_edge_to_an_unknown_node(tmp_path: Path):
    spec = _valid_spec()
    spec["edges"][0]["to"] = "missing-node"
    path = tmp_path / "unknown-node.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 1
    assert "unknown node" in result.stdout.lower()


def test_validator_rejects_active_adaptation_without_switching_controls(tmp_path: Path):
    spec = _valid_spec()
    spec["mode"] = "active"
    spec["dynamic_topology"] = {
        "enabled": True,
        "mode": "active",
        "switching_costs": [],
        "hysteresis": "",
        "promotion_gate": "",
    }
    path = tmp_path / "unsafe-active.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 1
    assert "switching" in result.stdout.lower()
    assert "hysteresis" in result.stdout.lower()
    assert "promotion" in result.stdout.lower()


def test_validator_rejects_high_consequence_node_without_human_approval(tmp_path: Path):
    spec = _valid_spec()
    spec["nodes"][0]["consequence"] = "high"
    spec["nodes"][0]["human_approval"] = False
    path = tmp_path / "ungoverned.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 1
    assert "human approval" in result.stdout.lower()


def test_validator_requires_machine_checkable_task_constraints(tmp_path: Path):
    spec = _valid_spec()
    spec.pop("task_constraints")
    path = tmp_path / "missing-constraints.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 1
    assert "task_constraints" in result.stdout


def test_validator_rejects_calibrated_sensor_without_evidence(tmp_path: Path):
    spec = _valid_spec()
    spec["loops"][0]["sensor"]["maturity"] = "calibrated"
    path = tmp_path / "unearned-calibration.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 1
    assert "calibration_evidence" in result.stdout


def test_corrected_high_consequence_contract_passes(tmp_path: Path):
    spec = _valid_spec()
    spec["nodes"][0]["consequence"] = "high"
    spec["nodes"][0]["human_approval"] = True
    spec["loops"][0]["sensor"]["maturity"] = "standardized"
    path = tmp_path / "corrected-incident.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_validator_warns_when_the_generator_is_its_own_sensor(tmp_path: Path):
    spec = _valid_spec()
    spec["loops"][0]["sensor"]["independence"] = "same_context"
    path = tmp_path / "same-context.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = _run_validator(path)

    assert result.returncode == 0
    assert "WARN" in result.stdout
    assert "same context" in result.stdout.lower()


def test_skill_uses_validator_canonical_maturity_spelling_and_prompt_location():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "standardized" in skill
    assert "standardised" not in skill
    assert "inside `loop-graph-spec.json` under `prompt_contracts`" in skill
