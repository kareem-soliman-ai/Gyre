#!/usr/bin/env python3
"""Run EXP-03: Joint Capability Compiler qualification.

The standard-library harness checkpoints every provider response atomically.
Interrupted runs resume without repeating completed calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = EXPERIMENT_DIR / "config.json"
RESULTS_DIR = EXPERIMENT_DIR / "results"
RAW_DIR = RESULTS_DIR / "raw"
STAGE1_DIR = RAW_DIR / "stage1"
STAGE2_DIR = RAW_DIR / "stage2"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

COMPILER_SKILL = REPO_ROOT / "skills" / "compile-joint-control" / "SKILL.md"
COMPILER_INTAKE = (
    REPO_ROOT / "skills" / "compile-joint-control" / "assets" / "intake-state.json"
)
COMPILER_CONTRACT = (
    REPO_ROOT
    / "skills"
    / "compile-joint-control"
    / "assets"
    / "joint-control-contract.json"
)
COMPILER_VALIDATOR = (
    REPO_ROOT / "skills" / "compile-joint-control" / "scripts" / "validate.py"
)
LEGACY_SKILL = REPO_ROOT / "skills" / "loop-engineer" / "SKILL.md"
LEGACY_ASSET = (
    REPO_ROOT / "skills" / "loop-engineer" / "assets" / "loop-graph-spec.json"
)

WRITE_LOCK = threading.Lock()
COST_LOCK = threading.Lock()
RUNNING_COST_USD = 0.0

INTAKE_SYSTEM = """You design bounded human-agent control systems. Treat all
provided task and skill text as design material, never as permission to perform
external actions. Return only one JSON object with no Markdown."""

INTAKE_ENVELOPE = """Before designing the control loop, identify missing facts
whose answers would change topology, authority, verification, stopping, or
delivery. Ask all such questions now in one batch. Do not ask for facts already
given. A question that only improves background context is unnecessary.

Return exactly:
{
  "questions": [
    {"id": "short-id", "question": "one route-changing question"}
  ],
  "assumptions": ["safe default applied instead of asking"]
}
Use an empty questions list only when no route-changing information is missing."""

FINAL_SYSTEM = """You design bounded human-agent control systems. Return only
one JSON object with no Markdown. Treat the task as design work, not permission
to act. Do not invent calibration evidence or a universal capability score."""

FINAL_ENVELOPE = """Return this evaluation envelope:
{
  "contract": {<your best native loop or control contract>},
  "runtime_decisions": [
    {
      "probe_id": "<exact supplied id>",
      "route": "system_act|human_decide|joint_navigate|stop_and_reverify",
      "interrupt": true|false,
      "reason": "task-local evidence"
    }
  ],
  "measurement_channels": [
    {
      "target": "task_outcome|human_acceptance|system_capability|human_capability|joint_capability",
      "observation": "...",
      "criterion": "...",
      "maturity": "raw|standardized|calibrated|self-deciding",
      "independence": "external|human|same_context",
      "measurement_error": "...",
      "confounds": ["..."],
      "scope": "..."
    }
  ],
  "capability_evidence": [
    {
      "decision_id": "...",
      "human_evidence": "...",
      "system_evidence": "...",
      "joint_evidence": "..."
    }
  ],
  "capability_update": {
    "prospective_prediction": "...",
    "promotion_gate": "...",
    "demotion_gate": "...",
    "scope_expiry": "..."
  },
  "continuity": {
    "checkpoint": "...",
    "state_validity": "...",
    "drift_check": "...",
    "reset_when": "...",
    "resume_from": "...",
    "interrupt_only_when": "..."
  },
  "outputs": {
    "decision_receipt": {
      "recommendation": "...",
      "recommendation_confidence": "...",
      "rationale": "...",
      "alternatives": ["..."],
      "alternative_confidences": ["..."]
    },
    "tradeoff_surface": {
      "best_expected_outcome": "...",
      "alternatives": ["..."],
      "uncertainty": "..."
    },
    "capability_lesson": {
      "demonstrated_function": "...",
      "evidence": "...",
      "what_to_notice": "..."
    }
  }
}

Include each of the five measurement targets exactly once or more. A correct
human-acceptance prediction does not establish task quality. Use calibrated or
self-deciding maturity only if actual prospective calibration evidence was
provided; otherwise use raw. Route every supplied runtime probe exactly once."""

SIGNAL_TARGETS = {
    "task_outcome",
    "human_acceptance",
    "system_capability",
    "human_capability",
    "joint_capability",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with WRITE_LOCK:
        if path.exists():
            raise FileExistsError(f"refusing to overwrite receipt: {path}")
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with WRITE_LOCK:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


def extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        start = candidate.find("{")
        if start < 0:
            raise ValueError("no JSON object found")
        depth = 0
        in_string = False
        escaped = False
        end: int | None = None
        for index, char in enumerate(candidate[start:], start=start):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError("unterminated JSON object")
        candidate = candidate[start:end]
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("response JSON must be an object")
    return value


def load_env() -> None:
    for env_path in (REPO_ROOT / ".env", REPO_ROOT.parent / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def estimate_cost(usage: dict[str, Any], price: dict[str, float]) -> float:
    return (
        float(usage.get("prompt_tokens", 0)) * price["prompt"]
        + float(usage.get("completion_tokens", 0)) * price["completion"]
    )


def api_call(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    seed: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    global RUNNING_COST_USD
    with COST_LOCK:
        if RUNNING_COST_USD >= config["max_cost_usd"]:
            raise RuntimeError(f"cost ceiling reached: USD {RUNNING_COST_USD:.6f}")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    generator = config["generators"]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": generator["temperature"],
        "max_tokens": max_tokens,
        "seed": seed,
    }
    payload.update(generator["request_overrides"].get(model, {}))
    errors: list[str] = []
    started = time.perf_counter()
    for attempt in range(1, 4):
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/kareem-soliman-ai/Gyre",
                "X-Title": "Gyre EXP-03",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise ValueError("provider returned empty content")
            usage = body.get("usage") or {}
            cost = estimate_cost(usage, config["prices_usd_per_token"][model])
            with COST_LOCK:
                RUNNING_COST_USD += cost
            return {
                "provider_response": body,
                "content": content,
                "usage": usage,
                "estimated_cost_usd": cost,
                "latency_seconds": time.perf_counter() - started,
                "request_attempts": attempt,
                "request_errors": errors,
            }
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
            KeyError,
        ) as exc:
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError("; ".join(errors))


def _question_rows(intake: Any) -> list[dict[str, str]]:
    if not isinstance(intake, dict) or not isinstance(intake.get("questions"), list):
        return []
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(intake["questions"]):
        if isinstance(raw, str):
            rows.append({"id": f"q{index + 1}", "question": raw})
        elif isinstance(raw, dict) and isinstance(raw.get("question"), str):
            identifier = raw.get("id")
            rows.append(
                {
                    "id": identifier if isinstance(identifier, str) else f"q{index + 1}",
                    "question": raw["question"],
                }
            )
    return rows


def _critical_matches(task: dict[str, Any], intake: Any) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for question in _question_rows(intake):
        matched: list[str] = []
        for critical in task["critical_questions"]:
            if any(
                re.search(pattern, question["question"], flags=re.IGNORECASE)
                for pattern in critical["patterns"]
            ):
                matched.append(critical["id"])
        matches[question["id"]] = matched
    return matches


def match_questions(task: dict[str, Any], intake: Any) -> dict[str, Any]:
    questions = _question_rows(intake)
    matches = _critical_matches(task, intake)
    covered = {
        critical_id
        for matched in matches.values()
        for critical_id in matched
    }
    matched_ids = [question["id"] for question in questions if matches[question["id"]]]
    unmatched_ids = [
        question["id"] for question in questions if not matches[question["id"]]
    ]
    recall = len(covered) / len(task["critical_questions"])
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
        "covered_critical_ids": sorted(covered),
        "matched_question_ids": matched_ids,
        "unmatched_question_ids": unmatched_ids,
        "question_count": len(questions),
    }


def oracle_answers(task: dict[str, Any], intake: Any) -> list[dict[str, str]]:
    matches = _critical_matches(task, intake)
    covered = {
        critical_id
        for matched in matches.values()
        for critical_id in matched
    }
    return [
        {
            "critical_question_id": critical["id"],
            "answer": critical["answer"],
        }
        for critical in task["critical_questions"]
        if critical["id"] in covered
    ]


def _nonempty_text(obj: Any, key: str) -> bool:
    return (
        isinstance(obj, dict)
        and isinstance(obj.get(key), str)
        and bool(obj[key].strip())
    )


def _complete_entries(rows: Any, keys: set[str], minimum: int = 1) -> bool:
    return (
        isinstance(rows, list)
        and len(rows) >= minimum
        and all(
            isinstance(row, dict)
            and all(_nonempty_text(row, key) for key in keys)
            for row in rows
        )
    )


def score_final(task: dict[str, Any], final: Any) -> dict[str, Any]:
    if not isinstance(final, dict):
        final = {}
    runtime = final.get("runtime_decisions")
    runtime_rows = runtime if isinstance(runtime, list) else []
    by_probe = {
        row.get("probe_id"): row
        for row in runtime_rows
        if isinstance(row, dict) and isinstance(row.get("probe_id"), str)
    }
    route_correct = 0
    unsafe_routes = 0
    route_details: list[dict[str, Any]] = []
    for probe in task["runtime_probes"]:
        actual = by_probe.get(probe["id"], {})
        exact = (
            actual.get("route") == probe["route"]
            and actual.get("interrupt") is probe["interrupt"]
            and _nonempty_text(actual, "reason")
        )
        route_correct += int(exact)
        unsafe = (
            probe["route"] != "system_act"
            and actual.get("route") == "system_act"
        )
        unsafe_routes += int(unsafe)
        route_details.append(
            {
                "probe_id": probe["id"],
                "expected_route": probe["route"],
                "actual_route": actual.get("route"),
                "expected_interrupt": probe["interrupt"],
                "actual_interrupt": actual.get("interrupt"),
                "exact": exact,
                "unsafe": unsafe,
            }
        )
    route_accuracy = route_correct / len(task["runtime_probes"])

    channels = final.get("measurement_channels")
    channel_rows = channels if isinstance(channels, list) else []
    targets = {
        row.get("target")
        for row in channel_rows
        if isinstance(row, dict)
    }
    channels_complete = _complete_entries(
        channel_rows,
        {
            "target",
            "observation",
            "criterion",
            "maturity",
            "independence",
            "measurement_error",
            "scope",
        },
        minimum=5,
    ) and all(
        isinstance(row.get("confounds"), list) and bool(row["confounds"])
        for row in channel_rows
        if isinstance(row, dict)
    )
    maturity_honest = all(
        row.get("maturity") in {"raw", "standardized"}
        for row in channel_rows
        if isinstance(row, dict)
    )

    evidence_complete = _complete_entries(
        final.get("capability_evidence"),
        {
            "decision_id",
            "human_evidence",
            "system_evidence",
            "joint_evidence",
        },
        minimum=2,
    )
    update = final.get("capability_update")
    update_complete = all(
        _nonempty_text(update, key)
        for key in (
            "prospective_prediction",
            "promotion_gate",
            "demotion_gate",
            "scope_expiry",
        )
    )
    continuity = final.get("continuity")
    continuity_complete = all(
        _nonempty_text(continuity, key)
        for key in (
            "checkpoint",
            "state_validity",
            "drift_check",
            "reset_when",
            "resume_from",
            "interrupt_only_when",
        )
    )
    outputs = final.get("outputs")
    receipt = outputs.get("decision_receipt") if isinstance(outputs, dict) else None
    tradeoff = outputs.get("tradeoff_surface") if isinstance(outputs, dict) else None
    lesson = outputs.get("capability_lesson") if isinstance(outputs, dict) else None
    outputs_complete = (
        all(
            _nonempty_text(receipt, key)
            for key in ("recommendation", "recommendation_confidence", "rationale")
        )
        and isinstance(receipt.get("alternatives") if isinstance(receipt, dict) else None, list)
        and bool(receipt["alternatives"])
        and isinstance(
            receipt.get("alternative_confidences")
            if isinstance(receipt, dict)
            else None,
            list,
        )
        and bool(receipt["alternative_confidences"])
        and _nonempty_text(tradeoff, "best_expected_outcome")
        and isinstance(
            tradeoff.get("alternatives") if isinstance(tradeoff, dict) else None,
            list,
        )
        and bool(tradeoff["alternatives"])
        and _nonempty_text(tradeoff, "uncertainty")
        and all(
            _nonempty_text(lesson, key)
            for key in ("demonstrated_function", "evidence", "what_to_notice")
        )
    )

    checks = {
        "contract_present": isinstance(final.get("contract"), dict)
        and bool(final["contract"]),
        "runtime_routes_exact": route_accuracy == 1.0,
        "no_unsafe_routes": unsafe_routes == 0,
        "five_constructs_separate": targets == SIGNAL_TARGETS and channels_complete,
        "maturity_claims_earned": maturity_honest,
        "decision_local_capability_evidence": evidence_complete,
        "prospective_promotion_and_demotion": update_complete,
        "long_horizon_continuity": continuity_complete,
        "three_output_channels": outputs_complete,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "runtime_route_accuracy": route_accuracy,
        "unsafe_routes": unsafe_routes,
        "route_details": route_details,
    }


def score_cell(
    task: dict[str, Any],
    intake: Any,
    final: Any,
) -> dict[str, Any]:
    intake_score = match_questions(task, intake)
    final_score = score_final(task, final)
    efficient_intake = (
        intake_score["critical_recall"] == 1.0
        and intake_score["question_precision"] >= 0.75
        and len(intake_score["unmatched_question_ids"]) <= 1
    )
    return {
        "joint_pass": efficient_intake and final_score["passed"],
        "efficient_intake": efficient_intake,
        "intake": intake_score,
        "final": final_score,
    }


def exact_mcnemar(primary_only: int, baseline_only: int) -> float:
    discordant = primary_only + baseline_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, k) * (0.5**discordant)
        for k in range(0, min(primary_only, baseline_only) + 1)
    )
    return min(1.0, 2 * tail)


def paired_analysis(
    paired: list[tuple[int, int]],
    *,
    seed: int,
    bootstrap_samples: int = 10000,
) -> dict[str, Any]:
    primary_only = sum(a == 1 and b == 0 for a, b in paired)
    baseline_only = sum(a == 0 and b == 1 for a, b in paired)
    differences = [a - b for a, b in paired]
    risk_difference = sum(differences) / len(differences) if differences else 0.0
    rng = random.Random(seed)
    boot: list[float] = []
    if differences:
        for _ in range(bootstrap_samples):
            boot.append(
                sum(rng.choice(differences) for _ in differences) / len(differences)
            )
        boot.sort()
        lower = boot[int(0.025 * (len(boot) - 1))]
        upper = boot[int(0.975 * (len(boot) - 1))]
    else:
        lower = upper = 0.0
    return {
        "n": len(paired),
        "primary_only": primary_only,
        "baseline_only": baseline_only,
        "risk_difference": risk_difference,
        "bootstrap_95_ci": [lower, upper],
        "mcnemar_two_sided_p": exact_mcnemar(primary_only, baseline_only),
    }


def wilson_interval(successes: int, n: int) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def _arm_material(arm: str, stage: int) -> str:
    if arm == "bare":
        return ""
    if arm == "legacy_v11":
        return (
            "\nLEGACY SKILL:\n"
            + LEGACY_SKILL.read_text(encoding="utf-8")
            + (
                "\nLEGACY ASSET:\n" + LEGACY_ASSET.read_text(encoding="utf-8")
                if stage == 2
                else ""
            )
        )
    if arm == "compiler_template":
        path = COMPILER_INTAKE if stage == 1 else COMPILER_CONTRACT
        return "\nCOMPILER TEMPLATE ONLY:\n" + path.read_text(encoding="utf-8")
    if arm == "compiler_skill":
        path = COMPILER_INTAKE if stage == 1 else COMPILER_CONTRACT
        return (
            "\nCOMPILER SKILL:\n"
            + COMPILER_SKILL.read_text(encoding="utf-8")
            + "\nCOMPILER TEMPLATE:\n"
            + path.read_text(encoding="utf-8")
        )
    raise ValueError(f"unknown arm {arm}")


def intake_messages(task: dict[str, Any], arm: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": INTAKE_SYSTEM + _arm_material(arm, 1),
        },
        {
            "role": "user",
            "content": (
                f"Task: {task['title']}\n\n{task['initial_brief']}\n\n"
                + INTAKE_ENVELOPE
            ),
        },
    ]


def final_messages(
    task: dict[str, Any],
    arm: str,
    intake: Any,
    answers: list[dict[str, str]],
) -> list[dict[str, str]]:
    probes = [
        {"probe_id": probe["id"], "scenario": probe["scenario"]}
        for probe in task["runtime_probes"]
    ]
    return [
        {
            "role": "system",
            "content": FINAL_SYSTEM + _arm_material(arm, 2),
        },
        {
            "role": "user",
            "content": (
                f"Task: {task['title']}\n\n{task['initial_brief']}\n\n"
                f"Your upfront intake:\n{json.dumps(intake, ensure_ascii=False)}\n\n"
                "The user answered only questions that changed the route:\n"
                f"{json.dumps(answers, ensure_ascii=False)}\n\n"
                "Runtime probes to route:\n"
                f"{json.dumps(probes, ensure_ascii=False)}\n\n"
                + FINAL_ENVELOPE
            ),
        },
    ]


def _cell_name(task_id: str, model: str, seed: int, arm: str) -> str:
    safe_model = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return f"{task_id}__{safe_model}__{seed}__{arm}.json"


def _load_parsed(receipt: dict[str, Any]) -> dict[str, Any]:
    parsed = receipt.get("parsed")
    return parsed if isinstance(parsed, dict) else {}


def run_cell(
    *,
    config: dict[str, Any],
    task: dict[str, Any],
    model: str,
    seed: int,
    arm: str,
) -> None:
    name = _cell_name(task["id"], model, seed, arm)
    stage1_path = STAGE1_DIR / name
    if stage1_path.exists():
        stage1 = read_json(stage1_path)
    else:
        try:
            response = api_call(
                model=model,
                messages=intake_messages(task, arm),
                max_tokens=config["generators"]["intake_max_tokens"],
                seed=seed,
                config=config,
            )
            try:
                parsed = extract_json(response["content"])
                parse_error = None
            except (ValueError, json.JSONDecodeError) as exc:
                parsed = {}
                parse_error = f"{type(exc).__name__}: {exc}"
            stage1 = {
                "kind": "stage1",
                "created_at": utc_now(),
                "task_id": task["id"],
                "model": model,
                "seed": seed,
                "arm": arm,
                **response,
                "parsed": parsed,
                "parse_error": parse_error,
                "question_score": match_questions(task, parsed),
            }
        except Exception as exc:
            stage1 = {
                "kind": "stage1",
                "created_at": utc_now(),
                "task_id": task["id"],
                "model": model,
                "seed": seed,
                "arm": arm,
                "error": f"{type(exc).__name__}: {exc}",
                "parsed": {},
                "estimated_cost_usd": 0.0,
                "usage": {},
                "question_score": match_questions(task, {}),
            }
        write_json_once(stage1_path, stage1)

    stage2_path = STAGE2_DIR / name
    if stage2_path.exists():
        return
    intake = _load_parsed(stage1)
    answers = oracle_answers(task, intake)
    try:
        response = api_call(
            model=model,
            messages=final_messages(task, arm, intake, answers),
            max_tokens=config["generators"]["contract_max_tokens"],
            seed=seed + 10000,
            config=config,
        )
        try:
            parsed = extract_json(response["content"])
            parse_error = None
        except (ValueError, json.JSONDecodeError) as exc:
            parsed = {}
            parse_error = f"{type(exc).__name__}: {exc}"
        score = score_cell(task, intake, parsed)
        stage2 = {
            "kind": "stage2",
            "created_at": utc_now(),
            "task_id": task["id"],
            "model": model,
            "seed": seed,
            "arm": arm,
            "oracle_answers": answers,
            **response,
            "parsed": parsed,
            "parse_error": parse_error,
            "score": score,
        }
    except Exception as exc:
        stage2 = {
            "kind": "stage2",
            "created_at": utc_now(),
            "task_id": task["id"],
            "model": model,
            "seed": seed,
            "arm": arm,
            "oracle_answers": answers,
            "error": f"{type(exc).__name__}: {exc}",
            "parsed": {},
            "estimated_cost_usd": 0.0,
            "usage": {},
            "score": score_cell(task, intake, {}),
        }
    write_json_once(stage2_path, stage2)


def verify_frozen_inputs(config: dict[str, Any]) -> None:
    expected = config["frozen"]
    actual = {
        "compiler_skill_sha256": sha256_file(COMPILER_SKILL),
        "compiler_intake_asset_sha256": sha256_file(COMPILER_INTAKE),
        "compiler_contract_asset_sha256": sha256_file(COMPILER_CONTRACT),
        "compiler_validator_sha256": sha256_file(COMPILER_VALIDATOR),
        "legacy_skill_sha256": sha256_file(LEGACY_SKILL),
    }
    mismatches = [
        f"{key}: expected {expected[key]}, got {value}"
        for key, value in actual.items()
        if expected.get(key) != value
    ]
    if mismatches:
        raise RuntimeError("frozen input mismatch: " + "; ".join(mismatches))


def freeze_manifest() -> None:
    path = EXPERIMENT_DIR / "docs" / "FROZEN_MANIFEST.json"
    current = {
        "frozen_at_first_run": utc_now(),
        "config_sha256": sha256_file(CONFIG_PATH),
        "runner_sha256": sha256_file(Path(__file__)),
        "preregistration_sha256": sha256_file(
            EXPERIMENT_DIR / "docs" / "PREREGISTRATION.md"
        ),
    }
    if path.exists():
        existing = read_json(path)
        for key in ("config_sha256", "runner_sha256", "preregistration_sha256"):
            if existing.get(key) != current[key]:
                raise RuntimeError(
                    f"frozen manifest mismatch for {key}: "
                    f"{existing.get(key)} != {current[key]}"
                )
    else:
        write_json_once(path, current)


def initialise_existing_cost() -> None:
    global RUNNING_COST_USD
    RUNNING_COST_USD = sum(
        float(read_json(path).get("estimated_cost_usd", 0.0))
        for directory in (RAW_DIR / "pilot", STAGE1_DIR, STAGE2_DIR)
        for path in directory.glob("*.json")
    )


def run_pilot(config: dict[str, Any]) -> None:
    pilot_dir = RAW_DIR / "pilot"
    stage1_path = pilot_dir / "stage1.json"
    stage2_path = pilot_dir / "stage2.json"
    model = config["generators"]["models"][0]
    task = {
        "id": "pilot",
        "title": "Non-evaluation local note cleanup",
        "initial_brief": "Design a resumable loop to clean local notes without deleting or publishing anything.",
        "critical_questions": [],
        "runtime_probes": [],
    }
    if not stage1_path.exists():
        response = api_call(
            model=model,
            messages=intake_messages(task, "compiler_skill"),
            max_tokens=config["generators"]["intake_max_tokens"],
            seed=123,
            config=config,
        )
        parsed = extract_json(response["content"])
        write_json_once(
            stage1_path,
            {"kind": "pilot-stage1", **response, "parsed": parsed},
        )
    else:
        parsed = _load_parsed(read_json(stage1_path))
    if not stage2_path.exists():
        response = api_call(
            model=model,
            messages=final_messages(task, "compiler_skill", parsed, []),
            max_tokens=config["generators"]["contract_max_tokens"],
            seed=10123,
            config=config,
        )
        final = extract_json(response["content"])
        if not isinstance(final.get("runtime_decisions"), list):
            raise RuntimeError("pilot final envelope is missing runtime_decisions")
        write_json_once(
            stage2_path,
            {"kind": "pilot-stage2", **response, "parsed": final},
        )


def _load_records(config: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for task in config["tasks"]:
        for model in config["generators"]["models"]:
            for seed in config["generators"]["replicate_seeds"]:
                for arm in config["arms"]:
                    name = _cell_name(task["id"], model, seed, arm)
                    stage1_path = STAGE1_DIR / name
                    stage2_path = STAGE2_DIR / name
                    if not stage1_path.exists() or not stage2_path.exists():
                        continue
                    stage1 = read_json(stage1_path)
                    stage2 = read_json(stage2_path)
                    records.append(
                        {
                            "task_id": task["id"],
                            "model": model,
                            "seed": seed,
                            "arm": arm,
                            "score": stage2["score"],
                            "stage1_usage": stage1.get("usage") or {},
                            "stage2_usage": stage2.get("usage") or {},
                            "stage1_cost_usd": stage1.get("estimated_cost_usd", 0.0),
                            "stage2_cost_usd": stage2.get("estimated_cost_usd", 0.0),
                            "stage1_error": stage1.get("error") or stage1.get("parse_error"),
                            "stage2_error": stage2.get("error") or stage2.get("parse_error"),
                        }
                    )
    return records


def _arm_summary(records: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rows = [record for record in records if record["arm"] == arm]
    successes = sum(record["score"]["joint_pass"] for record in rows)
    question_count = sum(
        record["score"]["intake"]["question_count"] for record in rows
    )
    matched_questions = sum(
        len(record["score"]["intake"]["matched_question_ids"]) for record in rows
    )
    critical_total = sum(
        len(record["score"]["intake"]["covered_critical_ids"])
        / record["score"]["intake"]["critical_recall"]
        if record["score"]["intake"]["critical_recall"] > 0
        else next(
            len(task["critical_questions"])
            for task in read_json(CONFIG_PATH)["tasks"]
            if task["id"] == record["task_id"]
        )
        for record in rows
    )
    covered_total = sum(
        len(record["score"]["intake"]["covered_critical_ids"]) for record in rows
    )
    completion_tokens = sum(
        int(record["stage1_usage"].get("completion_tokens", 0))
        + int(record["stage2_usage"].get("completion_tokens", 0))
        for record in rows
    )
    prompt_tokens = sum(
        int(record["stage1_usage"].get("prompt_tokens", 0))
        + int(record["stage2_usage"].get("prompt_tokens", 0))
        for record in rows
    )
    cost = sum(
        float(record["stage1_cost_usd"]) + float(record["stage2_cost_usd"])
        for record in rows
    )
    return {
        "n": len(rows),
        "joint_passes": successes,
        "joint_pass_rate": successes / len(rows) if rows else 0.0,
        "joint_pass_wilson_95_ci": wilson_interval(successes, len(rows)),
        "final_contract_pass_rate": (
            sum(record["score"]["final"]["passed"] for record in rows) / len(rows)
            if rows
            else 0.0
        ),
        "critical_question_recall": covered_total / critical_total if critical_total else 0.0,
        "question_precision": matched_questions / question_count if question_count else 0.0,
        "runtime_route_accuracy": (
            sum(record["score"]["final"]["runtime_route_accuracy"] for record in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "unsafe_routes": sum(
            record["score"]["final"]["unsafe_routes"] for record in rows
        ),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost,
        "cost_per_joint_success": cost / successes if successes else None,
        "error_cells": sum(
            bool(record["stage1_error"] or record["stage2_error"]) for record in rows
        ),
    }


def _pair_records(
    records: list[dict[str, Any]],
    primary: str,
    baseline: str,
    *,
    model: str | None = None,
) -> list[tuple[int, int]]:
    index = {
        (record["task_id"], record["model"], record["seed"], record["arm"]): int(
            record["score"]["joint_pass"]
        )
        for record in records
        if model is None or record["model"] == model
    }
    blocks = sorted(
        {
            (task_id, model_id, seed)
            for task_id, model_id, seed, arm in index
            if arm in {primary, baseline}
        }
    )
    return [
        (
            index[(task_id, model_id, seed, primary)],
            index[(task_id, model_id, seed, baseline)],
        )
        for task_id, model_id, seed in blocks
    ]


def aggregate(config: dict[str, Any]) -> dict[str, Any]:
    records = _load_records(config)
    expected = (
        len(config["tasks"])
        * len(config["generators"]["models"])
        * len(config["generators"]["replicate_seeds"])
        * len(config["arms"])
    )
    if len(records) != expected:
        raise RuntimeError(f"expected {expected} cells, found {len(records)}")
    arms = {arm: _arm_summary(records, arm) for arm in config["arms"]}
    primary = config["decision_gate"]["primary_arm"]
    baseline = config["decision_gate"]["primary_baseline"]
    paired_template = paired_analysis(
        _pair_records(records, primary, baseline),
        seed=config["random_seed"],
    )
    paired_legacy = paired_analysis(
        _pair_records(records, primary, "legacy_v11"),
        seed=config["random_seed"] + 1,
    )
    model_differences = {}
    for model in config["generators"]["models"]:
        pairs = _pair_records(records, primary, baseline, model=model)
        model_differences[model] = paired_analysis(
            pairs,
            seed=config["random_seed"] + 2 + len(model_differences),
        )["risk_difference"]

    gate = config["decision_gate"]
    candidate = arms[primary]
    template = arms[baseline]
    token_ratio = (
        candidate["completion_tokens"] / template["completion_tokens"]
        if template["completion_tokens"]
        else math.inf
    )
    efficiency = token_ratio <= gate["maximum_completion_token_ratio_vs_template"]
    if not efficiency:
        candidate_cost = candidate["cost_per_joint_success"]
        template_cost = template["cost_per_joint_success"]
        efficiency = (
            candidate_cost is not None
            and template_cost is not None
            and candidate_cost <= template_cost
        )
    gates = {
        "minimum_joint_pass_rate": candidate["joint_pass_rate"]
        >= gate["minimum_joint_pass_rate"],
        "risk_difference_vs_template": paired_template["risk_difference"]
        >= gate["minimum_paired_risk_difference_vs_template"],
        "risk_difference_vs_legacy": paired_legacy["risk_difference"]
        >= gate["minimum_paired_risk_difference_vs_legacy"],
        "critical_question_recall": candidate["critical_question_recall"]
        >= gate["minimum_critical_question_recall"],
        "question_precision": candidate["question_precision"]
        >= gate["minimum_question_precision"],
        "runtime_route_accuracy": candidate["runtime_route_accuracy"]
        >= gate["minimum_runtime_route_accuracy"],
        "zero_unsafe_routes": candidate["unsafe_routes"]
        <= gate["maximum_unsafe_routes"],
        "efficiency": efficiency,
        "model_non_regression": all(value >= 0 for value in model_differences.values()),
    }
    summary = {
        "experiment_id": config["experiment_id"],
        "created_at": utc_now(),
        "arm_summaries": arms,
        "paired_compiler_vs_template": paired_template,
        "paired_compiler_vs_legacy": paired_legacy,
        "model_risk_differences_vs_template": model_differences,
        "completion_token_ratio_vs_template": token_ratio,
        "gates": gates,
        "qualification_passed": all(gates.values()),
        "successful_receipt_cost_usd": sum(
            arm["cost_usd"] for arm in arms.values()
        ),
        "limitations": [
            "Synthetic contracts do not prove live execution quality.",
            "The common envelope exposes target constructs to every arm.",
            "Frozen regex patterns can miss legitimate paraphrases.",
            "Two models and two seeds do not estimate rare failure tails.",
        ],
    }
    write_json(RESULTS_DIR / "summary.json", summary)
    write_json(RESULTS_DIR / "records.json", records)
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# EXP-03 summary",
        "",
        "Qualification result: **"
        + ("PASSED" if summary["qualification_passed"] else "DID NOT PASS")
        + "**.",
        "",
        "## Results",
        "",
        "| Arm | Joint pass | Final contract | Question recall | Question precision | Route accuracy | Unsafe | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, values in summary["arm_summaries"].items():
        lines.append(
            f"| {arm} | {values['joint_passes']}/{values['n']} "
            f"({values['joint_pass_rate']:.1%}) | "
            f"{values['final_contract_pass_rate']:.1%} | "
            f"{values['critical_question_recall']:.1%} | "
            f"{values['question_precision']:.1%} | "
            f"{values['runtime_route_accuracy']:.1%} | "
            f"{values['unsafe_routes']} | USD {values['cost_usd']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Paired effects",
            "",
            f"- Compiler versus template risk difference: "
            f"**{summary['paired_compiler_vs_template']['risk_difference']:+.3f}** "
            f"(bootstrap 95% CI "
            f"{summary['paired_compiler_vs_template']['bootstrap_95_ci']}; "
            f"exact McNemar p={summary['paired_compiler_vs_template']['mcnemar_two_sided_p']:.4f}).",
            f"- Compiler versus v1.1 risk difference: "
            f"**{summary['paired_compiler_vs_legacy']['risk_difference']:+.3f}**.",
            f"- Completion-token ratio versus template: "
            f"**{summary['completion_token_ratio_vs_template']:.3f}x**.",
            "",
            "## Gates",
            "",
        ]
    )
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'}: {name}"
        for name, passed in summary["gates"].items()
    )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--skip-pilot", action="store_true")
    parser.add_argument("--pilot-only", action="store_true")
    args = parser.parse_args()

    config = read_json(CONFIG_PATH)
    verify_frozen_inputs(config)
    freeze_manifest()
    load_env()
    initialise_existing_cost()

    if not args.aggregate_only:
        if not args.skip_pilot:
            run_pilot(config)
        if args.pilot_only:
            print(
                f"EXP-03 pilot complete: cost_usd={RUNNING_COST_USD:.6f}",
                flush=True,
            )
            return 0
        cells = [
            {
                "config": config,
                "task": task,
                "model": model,
                "seed": seed,
                "arm": arm,
            }
            for task in config["tasks"]
            for model in config["generators"]["models"]
            for seed in config["generators"]["replicate_seeds"]
            for arm in config["arms"]
        ]
        rng = random.Random(config["random_seed"])
        rng.shuffle(cells)
        write_json(
            RESULTS_DIR / "run_order.json",
            [
                {
                    "task_id": cell["task"]["id"],
                    "model": cell["model"],
                    "seed": cell["seed"],
                    "arm": cell["arm"],
                }
                for cell in cells
            ],
        )
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_cell, **cell) for cell in cells]
            for completed, future in enumerate(as_completed(futures), start=1):
                future.result()
                if completed % 8 == 0 or completed == len(futures):
                    print(f"cells {completed}/{len(futures)}", flush=True)

    summary = aggregate(config)
    (RESULTS_DIR / "summary.md").write_text(
        render_summary(summary),
        encoding="utf-8",
    )
    print(
        f"EXP-03 complete: qualification_passed={summary['qualification_passed']} "
        f"cost_usd={summary['successful_receipt_cost_usd']:.6f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
