#!/usr/bin/env python3
"""The Gyre gauntlet: bring your own sensor and try to beat the scoreboard.

Everything needed to verify the measurement claims is in this repo: the loop
controllers, the labelled synthetic corpora (labels by construction), the bench
(generous to uncalibrated sensors — it hindsight-sweeps your threshold), and
the published scoreboard. The validated instruments themselves are not in the
repo; their scores are published against their registry names, and the hosted
demo (docs/hosted-measurements.md) shows the wire contract they answer on.

Run the public baselines:
    python scripts/challenge.py

Run YOUR sensor (any module exposing a zero-arg factory returning a
MeasurementProvider):
    python scripts/challenge.py --contender mypkg.mysensor:build

Rebuild the scoreboard from a local run (maintainers):
    python scripts/challenge.py --rebuild-scoreboard

Rules of the game (see docs/challenge.md): score is pooled F1 on the two
synthetic corpora, per-cell breakdown shown so a win on easy cells cannot hide
a loss on the construct-subtle ones. Self-deciding sensors are scored on their
own decisions; raw-value sensors get their best hindsight threshold, which
flatters them — and they still lose to a sensor that models the construct.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import evaluate_provider  # noqa: E402
from gyre.providers import available, get_provider  # noqa: E402
from gyre.synthetic import by_difficulty, gen_l1_corpus, gen_l1_evidence_corpus  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCOREBOARD = REPO / "docs" / "scoreboard.json"

CORPORA = {
    "difficulty": gen_l1_corpus,
    "evidence": gen_l1_evidence_corpus,
}


def load_contender(spec: str):
    """'package.module:factory' -> a zero-arg provider factory."""
    mod_name, _, attr = spec.partition(":")
    mod = importlib.import_module(mod_name)
    factory = getattr(mod, attr or "build")
    return factory


# Standing notes shown on the scoreboard where a sensor's design makes a corpus
# structurally unreadable for it — a zero without the note would misinform.
PROVIDER_NOTES = {
    "selfcal:": (
        "self-baseline decision layer for LONG real traces; inert here because "
        "its burn-in exceeds these 4-5 step synthetic traces"
    ),
    "mvt:": "measures relative depletion, structurally blind to rumination-from-start",
    "psy:mvt-rumination": "measures relative depletion, structurally blind to rumination-from-start",
}


def _note_for(name: str) -> str:
    for prefix, note in PROVIDER_NOTES.items():
        if name.startswith(prefix):
            return note
    return ""


def score_provider(factory, name_hint: str = "") -> dict:
    row: dict = {"provider": name_hint, "corpora": {}}
    for corpus_name, gen in CORPORA.items():
        corpus = gen()
        pooled = [st.trace for st in corpus]
        score = evaluate_provider(factory(), pooled)
        row["provider"] = score.provider
        cells = {}
        for cell, traces in sorted(by_difficulty(corpus).items()):
            cells[cell] = round(evaluate_provider(factory(), traces).f1, 3)
        row["corpora"][corpus_name] = {
            "f1": round(score.f1, 3),
            "precision": round(score.precision, 3),
            "recall": round(score.recall, 3),
            "calibrated": score.calibrated,
            "cells": cells,
        }
    note = _note_for(row["provider"])
    if note:
        row["note"] = note
    return row


def print_table(rows: list[dict], published: list[dict]) -> None:
    def key(r):
        return -(
            r["corpora"].get("evidence", {}).get("f1", 0.0)
            + r["corpora"].get("difficulty", {}).get("f1", 0.0)
        )

    merged = [dict(r, _source="you") for r in rows] + [
        dict(r, _source="published") for r in published
    ]
    merged.sort(key=key)
    print(f"\n{'provider':30} {'difficulty':>10} {'evidence':>9} {'self-deciding':>14}  source")
    print("-" * 78)
    for r in merged:
        d = r["corpora"].get("difficulty", {})
        e = r["corpora"].get("evidence", {})
        cal = d.get("calibrated", e.get("calibrated", False))
        mark = " *" if r.get("note") else ""
        print(
            f"{r['provider']:30} {d.get('f1', float('nan')):>10.3f} "
            f"{e.get('f1', float('nan')):>9.3f} {'yes' if cal else 'no':>14}  {r['_source']}{mark}"
        )
    for r in merged:
        if r.get("note"):
            print(f"  * {r['provider']}: {r['note']}")
    print(
        "\nPer-cell F1 matters more than the pooled number: check the construct-"
        "subtle cells (edge, evid-pivot, evid-progress are all-negative traps -"
        " firing there is a false positive) before calling a win."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contender", help="module:factory for your own provider")
    ap.add_argument(
        "--providers",
        nargs="*",
        help="registered provider names to score (default: public L1 baselines)",
    )
    ap.add_argument("--rebuild-scoreboard", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit full rows as JSON")
    args = ap.parse_args()

    if args.rebuild_scoreboard:
        rows = [
            score_provider(lambda n=n: get_provider(n)) for n in available("L1")
        ]
        SCOREBOARD.write_text(
            json.dumps(
                {
                    "tier": "synthetic (labels by construction); real-trace scores "
                    "ship only after expert-anchored validation",
                    "bench": "gyre.bench.evaluate_provider (per-trace reset; hindsight "
                    "threshold sweep for uncalibrated sensors)",
                    "entries": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"scoreboard rebuilt from local run -> {SCOREBOARD} ({len(rows)} entries)")
        return 0

    names = args.providers or [n for n in available("L1") if not n.startswith("psy:")]
    rows = [score_provider(lambda n=n: get_provider(n)) for n in names]
    if args.contender:
        factory = load_contender(args.contender)
        rows.append(score_provider(factory, name_hint=args.contender))

    published = []
    if SCOREBOARD.is_file():
        published = json.loads(SCOREBOARD.read_text(encoding="utf-8")).get("entries", [])
        scored = {r["provider"] for r in rows}
        published = [r for r in published if r["provider"] not in scored]

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows, published)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
