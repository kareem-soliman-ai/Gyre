"""Turn agent transcripts into unlabelled traces ready for scoring.

Usage:
    python scripts/ingest_transcript.py <transcript.jsonl> [more.jsonl ...] -o traces.json

Format-tolerant: extracts ordered assistant text from each .jsonl (Claude Code
transcripts, mem0 exports, custom logs) and writes a list of RawTraces. Point a
judge at the output next (see scripts/qualify_judges.py and gyre.labeling).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gyre.traces import from_jsonl, save_traces


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest .jsonl transcripts into RawTraces.")
    ap.add_argument("inputs", nargs="+", help="one or more .jsonl transcript files")
    ap.add_argument("-o", "--out", default="traces.json", help="output JSON path")
    ap.add_argument("--min-steps", type=int, default=2, help="drop traces with fewer steps")
    args = ap.parse_args()

    traces = []
    for path in args.inputs:
        tr = from_jsonl(path)
        if len(tr.steps) >= args.min_steps:
            traces.append(tr)
        print(f"  {Path(path).name}: {len(tr.steps)} steps")

    save_traces(traces, args.out)
    total = sum(len(t.steps) for t in traces)
    print(f"\nWrote {len(traces)} traces ({total} steps) to {args.out}")


if __name__ == "__main__":
    main()
