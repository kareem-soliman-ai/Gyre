#!/usr/bin/env python3
"""Re-derive every locally available scoreboard entry and fail on disagreement.

A public or contributed entry is not accepted because someone reported a
number; this script recomputes it from the corpora and requires the same answer.
A contributor cannot inflate a score, and the maintainer cannot quietly leave a
recomputable entry stale.

Every row must declare a verification class. A ``public-reproducible`` row must
name code that this checkout can import, and disagreement or absence is a
failure. A ``self-reported`` row is skipped and must be ineligible for the
verified ranking. Private code becomes independently verifiable only through a
future signed ``sealed-evaluator-attested`` receipt.

Usage:
    python scripts/verify_scoreboard.py
    python scripts/verify_scoreboard.py --tolerance 0.01
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from gyre.providers import available, get_provider  # noqa: E402

SCOREBOARD = _root / "docs" / "scoreboard.json"


def load_factory(spec: str):
    module_name, _, attribute = spec.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, attribute or "build")


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
    checked = self_reported = 0

    for entry in board.get("entries", []):
        name = entry["provider"]
        verification = entry.get("verification")
        if not isinstance(verification, dict):
            failures.append(f"{name}: missing verification metadata")
            continue
        vclass = verification.get("class")
        ranking_eligible = verification.get("ranking_eligible")
        if vclass == "self-reported":
            self_reported += 1
            if ranking_eligible:
                failures.append(
                    f"{name}: self-reported entries cannot be ranking eligible"
                )
            continue
        if vclass == "sealed-evaluator-attested":
            failures.append(
                f"{name}: sealed attestation verification is not implemented yet"
            )
            continue
        if vclass != "public-reproducible":
            failures.append(f"{name}: unknown verification class {vclass!r}")
            continue
        if not ranking_eligible:
            failures.append(
                f"{name}: public-reproducible entries must be ranking eligible"
            )
            continue

        if name in registered:
            factory = lambda n=name: get_provider(n)
        elif entry.get("factory"):
            try:
                factory = load_factory(entry["factory"])
            except Exception as exc:  # noqa: BLE001 - contributor import is the gate
                failures.append(
                    f"{name}: public factory {entry['factory']!r} is unavailable: {exc}"
                )
                continue
        else:
            failures.append(
                f"{name}: public-reproducible entry has no registered provider "
                "or factory specification"
            )
            continue
        checked += 1
        fresh = score_provider(factory, name_hint=entry.get("factory", name))
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
        f"{self_reported} self-reported entries visibly excluded from ranking)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
