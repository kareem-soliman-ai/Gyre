#!/usr/bin/env python3
"""Score all registered L1 providers against the human-labelled scoring set.

Produces a markdown table ordered by F1, showing which providers are calibrated
(self-deciding) vs naive (threshold-swept), and the gap between them.

Usage:
    python scripts/compare_all_providers.py
    python scripts/compare_all_providers.py --scoring-set traces/private/scoring_set.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure gyre is importable regardless of CWD
_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import LabelledTrace, compare_providers
from gyre.loops.rumination import IterationObservation
from gyre.providers import available, get_provider


def load_scored_traces(path: Path) -> list[LabelledTrace]:
    """Load the human-scored scoring set and convert to LabelledTraces."""
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    traces: list[LabelledTrace] = []
    for entry in raw:
        steps = entry.get("steps", [])
        observations = [
            IterationObservation(artifact=s["text"], index=s.get("index", i))
            for i, s in enumerate(steps)
        ]
        labels = [s.get("is_ruminating", False) for s in steps]
        trace_id = entry.get("trace_id", "unknown")
        traces.append(
            LabelledTrace(
                observations=observations,
                labels=labels,
                loop_id="L1",
                name=trace_id,
            )
        )
    return traces


def print_score_table(scores, out) -> None:
    """Print a markdown table."""
    print("\n## Provider comparison (L1 rumination detection)\n", file=out)
    print("| Provider | Type | F1 | Precision | Recall | Accuracy | Calibrated? |", file=out)
    print("| --- | --- | ---: | ---: | ---: | ---: | --- |", file=out)
    for s in scores:
        cal = "Self-deciding" if s.calibrated else f"Swept (θ={s.best_threshold:.2f})"
        prov_type = "proprietary" if s.provider.startswith("psy:") else "naive"
        print(
            f"| {s.provider} | {prov_type} | {s.f1:.3f} | {s.precision:.3f} | "
            f"{s.recall:.3f} | {s.accuracy:.3f} | {cal} |",
            file=out,
        )
    print("", file=out)

    # Summary
    cal_scores = [s for s in scores if s.calibrated]
    raw_scores = [s for s in scores if not s.calibrated]
    if cal_scores and raw_scores:
        best_cal = max(cal_scores, key=lambda s: s.f1)
        best_raw = max(raw_scores, key=lambda s: s.f1)
        gap = best_cal.f1 - best_raw.f1
        print(f"**Best calibrated:** {best_cal.provider} (F1={best_cal.f1:.3f})", file=out)
        print(f"**Best naive:** {best_raw.provider} (F1={best_raw.f1:.3f}, θ={best_raw.best_threshold:.2f})", file=out)
        print(f"**Gap:** ΔF1 = {gap:+.3f}", file=out)
        if gap > 0:
            print(f"The calibrated sensor beats the naive baseline by {gap:.1%}.", file=out)
        else:
            print("The naive baseline matches or beats calibrated providers on this set.", file=out)
    print("", file=out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Score all L1 providers against a labelled scoring set.")
    ap.add_argument(
        "--scoring-set",
        default="traces/private/scoring_set.json",
        help="Path to the human-scored scoring set JSON",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout)",
    )
    ap.add_argument(
        "--provider",
        action="append",
        default=None,
        help="Specific provider(s) to test (repeatable). Default: all L1 providers.",
    )
    args = ap.parse_args()

    scoring_path = Path(args.scoring_set)
    if not scoring_path.exists():
        print(f"[ERROR] Scoring set not found: {scoring_path}", file=sys.stderr)
        print("[HINT]  Run scripts/build_scoring_set.py first, or label the worksheet.", file=sys.stderr)
        return 1

    traces = load_scored_traces(scoring_path)
    total_steps = sum(len(t.labels) for t in traces)
    total_pos = sum(sum(t.labels) for t in traces)
    print(f"[INFO] Loaded {len(traces)} traces ({total_steps} steps, {total_pos} ruminating)", file=sys.stderr)

    if args.provider:
        provider_names = args.provider
    else:
        provider_names = available("L1")

    if not provider_names:
        print("[ERROR] No L1 providers registered.", file=sys.stderr)
        return 1

    providers = [get_provider(n) for n in provider_names]
    print(f"[INFO] Comparing {len(providers)} providers: {provider_names}", file=sys.stderr)

    scores = compare_providers(providers, traces)

    out = open(args.output, "w") if args.output else sys.stdout
    try:
        print_score_table(scores, out)
        print(f"[OK] Results written.", file=sys.stderr)
    finally:
        if args.output:
            out.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
