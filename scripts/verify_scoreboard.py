#!/usr/bin/env python3
"""Re-derive the scoreboard and fail if the committed file disagrees.

The point of a published scoreboard is that nobody has to trust it. So a
submitted entry is not accepted because someone reported a number; it is
accepted because this script recomputes the number from the corpora in the repo
and gets the same answer. A contributor cannot inflate their score, and the
maintainer cannot quietly leave a stale one in place.

Entries for providers that are not registered in this checkout (the private
instrument tier) are skipped rather than failed - a public checkout cannot
recompute them, and pretending otherwise would either break every fork or
require shipping the instruments.

Usage:
    python scripts/verify_scoreboard.py
    python scripts/verify_scoreboard.py --tolerance 0.01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from gyre.providers import available, get_provider  # noqa: E402

SCOREBOARD = _root / "docs" / "scoreboard.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tolerance", type=float, default=0.005)
    args = ap.parse_args()

    if not SCOREBOARD.is_file():
        print(f"[ERROR] no scoreboard at {SCOREBOARD}", file=sys.stderr)
        return 1

    from challenge import score_provider  # noqa: E402  (sibling script)

    board = json.loads(SCOREBOARD.read_text(encoding="utf-8"))
    registered = set(available())
    failures: list[str] = []
    checked = skipped = 0

    for entry in board.get("entries", []):
        name = entry["provider"]
        if name not in registered:
            skipped += 1
            continue
        checked += 1
        fresh = score_provider(lambda n=name: get_provider(n))
        for corpus, claimed in entry.get("corpora", {}).items():
            got = fresh["corpora"].get(corpus, {})
            for metric in ("f1", "precision", "recall"):
                if metric not in claimed:
                    continue
                delta = abs(got.get(metric, -1) - claimed[metric])
                if delta > args.tolerance:
                    failures.append(
                        f"{name} {corpus}/{metric}: committed {claimed[metric]}, "
                        f"recomputed {got.get(metric)} (delta {delta:.4f})"
                    )

    for f in failures:
        print(f"FAIL  {f}")
    if failures:
        print(
            f"\nscoreboard: {len(failures)} entr(ies) do not reproduce. "
            "Regenerate with: python scripts/challenge.py --rebuild-scoreboard"
        )
        return 1
    print(
        f"scoreboard: OK ({checked} entries recomputed and matched, "
        f"{skipped} skipped as not registered in this checkout)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
