#!/usr/bin/env python3
"""Run classical item analysis over a judged corpus and print the item bank.

Input JSON shape:
    {"reference": [true, false, ...],
     "judges": {"judge-name": [true, false, ...], ...}}

The reference is whatever gold you have (human labels, expert-anchored panel
labels). Output: per-item difficulty, discrimination, and flags — with
hard_review items explicitly routed to human eyes, never auto-culled.

Usage:
    python scripts/item_analysis.py labels.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.item_analysis import analyze_items  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("labels", help="JSON file with 'reference' and 'judges'")
    args = ap.parse_args()

    data = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    stats = analyze_items(
        {k: [bool(x) for x in v] for k, v in data["judges"].items()},
        [bool(x) for x in data["reference"]],
    )

    print(f"{'item':>5} {'difficulty':>10} {'discrim':>8}  flags")
    print("-" * 50)
    for s in stats:
        flags = ",".join(s.flags) or "-"
        cull = "  [cull candidate]" if s.cull_candidate else ""
        print(f"{s.index:>5} {s.difficulty:>10.2f} {s.discrimination:>8.2f}  {flags}{cull}")

    n_cull = sum(1 for s in stats if s.cull_candidate)
    n_review = sum(1 for s in stats if "hard_review" in s.flags)
    print(
        f"\n{len(stats)} items: {n_cull} cull candidates, "
        f"{n_review} flagged hard_review (human eyes, never auto-culled)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
