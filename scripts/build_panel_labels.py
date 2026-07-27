#!/usr/bin/env python3
"""Wave A4 — build a provenance-tagged label set with a judge panel (no marathon).

Runs a panel of LLM judges over a trace set, auto-labels the steps the panel
agrees on, and surfaces only the top ``--human-budget`` genuinely disputed steps
(ranked by value-of-information) for an expert to adjudicate. Writes an enriched
JSON with per-step credal intervals and provenance, so the downstream
`qualify_judges.py` / `replay_routing.py` / `calibrate_ceilings.py` can run.

The judge panel defaults to cheap open-weight OpenRouter models (initial testing;
swap freely, verify the ids against the live model list). Needs OPENROUTER_API_KEY
for a live run; `--dry-run` prints the plan without calling any model.

Usage:
    python scripts/build_panel_labels.py --input traces/private/scoring_set.json --human-budget 10
    python scripts/build_panel_labels.py --input ... --models qwen/qwen-2.5-7b-instruct --models google/gemma-2-9b-it
    python scripts/build_panel_labels.py --input ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def load_env(path: Path) -> None:
    """Minimal .env loader (no dependency): set os.environ from KEY=VALUE lines.
    Existing environment variables win (setdefault), so a real shell export is not
    overridden by the file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from gyre.labeling import (  # noqa: E402
    DEFAULT_JUDGE_MODELS,
    build_openrouter_panel,
    build_panel_labels,
)
from gyre.traces import RawTrace, TraceStep  # noqa: E402


def load_raw_traces(path: Path) -> list[RawTrace]:
    """Load a scoring-set / trace JSON (list of {trace_id, source, steps:[{text,...}]})
    as RawTraces. Any existing labels are ignored — the panel produces them."""
    data = json.loads(path.read_text(encoding="utf-8"))
    traces: list[RawTrace] = []
    for entry in data:
        steps = [
            TraceStep(text=s["text"], index=s.get("index", i))
            for i, s in enumerate(entry.get("steps", []))
        ]
        traces.append(
            RawTrace(steps=steps, source=entry.get("source", ""), trace_id=entry.get("trace_id", "trace"))
        )
    return traces


def main() -> int:
    ap = argparse.ArgumentParser(description="Panel-label a trace set with a VoI human anchor.")
    ap.add_argument("--input", default="traces/private/scoring_set.json")
    ap.add_argument("--output", default="traces/private/panel_labels.json")
    ap.add_argument("--human-budget", type=int, default=10, help="max steps to route to an expert")
    ap.add_argument("--models", action="append", default=None, help="judge model id (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; do not call models or write")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[ERROR] input not found: {in_path}", file=sys.stderr)
        return 1
    traces = load_raw_traces(in_path)
    total_steps = sum(len(t.steps) for t in traces)
    models = tuple(args.models) if args.models else DEFAULT_JUDGE_MODELS
    print(f"[INFO] {len(traces)} traces, {total_steps} steps; panel = {list(models)}", file=sys.stderr)

    if args.dry_run:
        print(f"[DRY-RUN] would run a {len(models)}-judge panel and route <= "
              f"{args.human_budget} disputed steps to an expert. No model calls made.", file=sys.stderr)
        return 0

    load_env(_root / ".env")
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("[ERROR] no OPENROUTER_API_KEY (set it in .env or the environment)", file=sys.stderr)
        return 1
    judges = build_openrouter_panel(models)
    records, summary = build_panel_labels(traces, judges, human_budget=args.human_budget)

    Path(args.output).write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"[OK] wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
