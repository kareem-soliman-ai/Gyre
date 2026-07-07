"""Qualify LLM judges against a small human-scored set (the EQA gate).

You hand-score a handful of steps; this checks whether a cheap judge agrees with
you well enough (Cohen's kappa + Gwet's AC1) to be trusted to label the rest. Only
qualified judges get to scale the corpus.

Usage:
    export OPENROUTER_API_KEY=...
    python scripts/qualify_judges.py human_scored.json \
        --judges deepseek/deepseek-chat qwen/qwen-2.5-72b-instruct anthropic/claude-3.5-sonnet

``human_scored.json`` is a list of ScoredTrace dicts (your gold labels). Each
candidate judge re-scores the same steps; the report ranks them by qualification.

Note: this makes real API calls (one per step per judge). Keep the gold set small.
"""

from __future__ import annotations

import argparse

from gyre.labeling import OpenRouterJudge, judge_trace, qualify_judge
from gyre.traces import RawTrace, TraceStep, load_scored_traces


def main() -> None:
    ap = argparse.ArgumentParser(description="Qualify LLM judges vs a human-scored set.")
    ap.add_argument("human", help="JSON file of human-scored traces (gold labels)")
    ap.add_argument("--judges", nargs="+", required=True, help="OpenRouter model ids")
    ap.add_argument("--kappa-floor", type=float, default=0.6)
    ap.add_argument("--ac1-floor", type=float, default=0.6)
    args = ap.parse_args()

    gold = load_scored_traces(args.human)
    human_labels = [s.is_ruminating for tr in gold for s in tr.steps]
    # Reconstruct the raw steps (text only) so each judge scores the same inputs.
    raw = [
        RawTrace(
            steps=[TraceStep(text=s.text, index=s.index) for s in tr.steps],
            trace_id=tr.trace_id,
        )
        for tr in gold
    ]

    print(f"Gold set: {len(human_labels)} steps, "
          f"{sum(human_labels)} ruminating ({sum(human_labels)/max(1,len(human_labels)):.0%})\n")
    print(f"  {'judge':40} {'kappa':>6} {'AC1':>6} {'agree':>6} {'qualified':>10}")
    print("  " + "-" * 74)

    results = []
    for model in args.judges:
        judge = OpenRouterJudge(model)
        judge_labels = [s.is_ruminating for tr in raw for s in judge_trace(judge, tr).steps]
        q = qualify_judge(
            judge_labels, human_labels,
            judge_name=model, kappa_floor=args.kappa_floor, ac1_floor=args.ac1_floor,
        )
        results.append(q)

    for q in sorted(results, key=lambda r: r.gwet_ac1, reverse=True):
        mark = "yes" if q.qualified else "no"
        print(f"  {q.judge:40} {q.cohen_kappa:6.2f} {q.gwet_ac1:6.2f} {q.raw_agreement:6.2f} {mark:>10}")

    winners = [q.judge for q in results if q.qualified]
    print(f"\nQualified judges: {winners or 'none — try a stronger judge or a panel'}")


if __name__ == "__main__":
    main()
