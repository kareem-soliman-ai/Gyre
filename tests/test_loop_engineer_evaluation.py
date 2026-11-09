from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT / "experiments" / "EXP-01_LoopEngineerSkillQualification_2026-07-28"
)
SCRIPT = EXPERIMENT / "scripts" / "run_evaluation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("loop_skill_eval", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preregistration_and_config_are_present() -> None:
    assert (EXPERIMENT / "docs" / "PREREGISTRATION.md").exists()
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    assert len(config["tasks"]) == 3
    assert config["generator"]["replicate_seeds"] == [101, 202]
    assert config["max_cost_usd"] == 0.5
    assert config["judges"]["request_overrides"]["openai/gpt-5.4-mini"] == {
        "response_format": {"type": "json_object"}
    }


def test_extract_json_accepts_fenced_object() -> None:
    module = _load_module()
    parsed = module.extract_json('before\\n```json\\n{"ok": true}\\n```\\nafter')
    assert parsed == {"ok": True}


def test_structural_audit_rewards_bounded_external_control() -> None:
    module = _load_module()
    output = json.dumps(
        {
            "design_note": "Use a fixed baseline before graph promotion.",
            "manifest": {
                "nodes": ["worker", "external deterministic sensor", "human"],
                "edges": ["typed handoff with provenance and failure route"],
                "loop": {
                    "observation": "pytest receipt",
                    "sensor": "external deterministic test runner",
                    "confounds": ["flaky test", "service unavailable"],
                    "decision_rule": "continue only with information gain",
                    "actions": ["reframe", "seek evidence", "escalate", "stop"],
                    "terminal_states": ["passed", "blocked", "budget exhausted"],
                    "budget": {"cycles": 3, "minutes": 10},
                    "checkpoint": "last good commit",
                },
                "authority": "human approval for deployment",
                "adaptation": {
                    "mode": "shadow",
                    "switching_cost": "worker startup",
                    "hysteresis": "two observations",
                    "matched_budget": "compare with fixed route",
                },
            },
            "prompts": {
                "generator": "work",
                "sensor": "report evidence",
                "controller": "choose an action",
            },
        }
    )
    audit = module.structural_audit(output)
    assert audit["parseable_json"] is True
    assert audit["score"] >= 0.75
    assert audit["unsafe_authority"] is False


def test_blind_assignment_is_deterministic_and_hides_conditions() -> None:
    module = _load_module()
    first = module.blind_assignment("ci_repair", 101, "judge-a", 20260728)
    second = module.blind_assignment("ci_repair", 101, "judge-a", 20260728)
    assert first == second
    assert set(first) == {"A", "B"}
    assert set(first.values()) == {"no_skill", "skill"}


def test_cost_estimate_uses_frozen_prices() -> None:
    module = _load_module()
    price = {"prompt": 0.000001, "completion": 0.000002}
    assert module.estimate_cost({"prompt_tokens": 100, "completion_tokens": 50}, price) == 0.0002


def test_payload_applies_reasoning_override_without_changing_token_ceiling() -> None:
    module = _load_module()
    payload = module.build_payload(
        model="stepfun/step-3.7-flash",
        messages=[{"role": "user", "content": "judge"}],
        temperature=0.0,
        max_tokens=1000,
        seed=7,
        request_overrides={"reasoning": {"effort": "low", "exclude": True}},
    )
    assert payload["max_tokens"] == 1000
    assert payload["reasoning"] == {"effort": "low", "exclude": True}


def test_held_out_tasks_do_not_repeat_embedded_prompts() -> None:
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    cases = (
        ROOT / "skills" / "loop-engineer" / "references" / "evaluation-cases.md"
    ).read_text(encoding="utf-8").lower()
    for task in config["tasks"]:
        assert task["brief"].lower() not in cases
