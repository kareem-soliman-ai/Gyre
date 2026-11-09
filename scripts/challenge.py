#!/usr/bin/env python3
"""The Gyre gauntlet: bring your own sensor and try to beat the scoreboard.

Everything needed to verify the measurement claims is in this repo: the loop
controllers, the labelled synthetic corpora (labels by construction), the bench
(generous to uncalibrated sensors — it hindsight-sweeps your threshold), and
the published scoreboard. Protected instrument implementations are not in the
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
from copy import deepcopy
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import evaluate_provider  # noqa: E402
from gyre.providers import available, get_provider  # noqa: E402
from gyre.score_receipts import build_receipt, write_receipt  # noqa: E402
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
    "psy:joint-sensor-v1": (
        "protected provider; operating point selected on these same public "
        "synthetic corpora. Maintainer-reported development score, not a sealed "
        "holdout, transfer result, or independently reproducible public entry"
    ),
    "selfcal:": (
        "self-baseline decision layer for LONG real traces; inert here because "
        "its burn-in exceeds these 4-5 step synthetic traces"
    ),
    "mvt:": "measures relative depletion, structurally blind to rumination-from-start",
    "pcr:gain-slope": (
        "measures the TREND in information gain, so it is structurally blind to a "
        "loop that was unproductive from step one - there is no decline to detect. "
        "Owns the depletion cell (1.00) where level sensors false-fire"
    ),
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


def _verification_for(entry: dict, *, factory_spec: str | None = None) -> dict:
    """Return explicit trust metadata, including for legacy scoreboard rows."""
    if isinstance(entry.get("verification"), dict):
        return deepcopy(entry["verification"])
    protected = entry.get("provider", "").startswith("psy:")
    if protected:
        return {
            "class": "self-reported",
            "ranking_eligible": False,
            "evidence_scope": "public-synthetic-development",
            "statement": (
                "Implementation absent from the public checkout; score is a "
                "maintainer report, not an independently verified result."
            ),
        }
    return {
        "class": "public-reproducible",
        "ranking_eligible": True,
        "evidence_scope": "public-synthetic-development",
        "statement": (
            "Implementation and scorer are public; CI can recompute this result."
        ),
    }


def _board_document(entries: list[dict]) -> dict:
    return {
        "tier": "synthetic (labels by construction); real-trace scores ship only "
        "after expert-anchored validation",
        "bench": "gyre.bench.evaluate_provider (per-trace reset; hindsight "
        "threshold sweep for uncalibrated sensors)",
        "ranking": "unweighted sum of pooled F1 across difficulty and evidence",
        "ranking_scope": (
            "The verified ranking includes public-reproducible and, once "
            "supported, sealed-evaluator-attested entries only. Self-reported "
            "scores remain visible but are not ranking eligible."
        ),
        "verification": (
            "A number alone is not proof. Public factories are recomputed by CI; "
            "private implementations require a sealed evaluator receipt for "
            "independent verification."
        ),
        "entries": entries,
    }


def _load_board() -> dict:
    if not SCOREBOARD.is_file():
        return _board_document([])
    return json.loads(SCOREBOARD.read_text(encoding="utf-8"))


def _write_board(entries: list[dict]) -> None:
    SCOREBOARD.write_text(
        json.dumps(_board_document(entries), indent=2) + "\n",
        encoding="utf-8",
    )


def _upsert_receipt(receipt: dict, receipt_path: Path) -> None:
    board = _load_board()
    row = deepcopy(receipt["score"])
    row["verification"] = deepcopy(receipt["verification"])
    try:
        row["receipt"] = receipt_path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        row["receipt"] = None
    if receipt["implementation"]["visibility"] == "public":
        row["factory"] = receipt["implementation"]["factory"]
    entries = [
        entry
        for entry in board.get("entries", [])
        if entry.get("provider") != row["provider"]
    ]
    entries.append(row)
    entries.sort(key=lambda entry: entry["provider"])
    _write_board(entries)


def print_table(rows: list[dict], published: list[dict]) -> None:
    def key(r):
        return -(
            r["corpora"].get("evidence", {}).get("f1", 0.0)
            + r["corpora"].get("difficulty", {}).get("f1", 0.0)
        )

    merged = [dict(r, _source="you") for r in rows] + []
    for row in published:
        verification = _verification_for(row)
        source = verification["class"]
        if not verification["ranking_eligible"]:
            source += " (not ranked)"
        merged.append(dict(row, _source=source))
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
    ap.add_argument(
        "--write-receipt",
        type=Path,
        help="write a public score receipt for --contender",
    )
    ap.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="public",
        help="whether the contender implementation will be supplied (default: public)",
    )
    ap.add_argument(
        "--submitter",
        default="anonymous",
        help="public handle or team name stored in the receipt",
    )
    ap.add_argument(
        "--update-scoreboard",
        action="store_true",
        help="upsert the receipt's row into docs/scoreboard.json",
    )
    args = ap.parse_args()
    if args.write_receipt and not args.contender:
        ap.error("--write-receipt requires --contender")
    if args.update_scoreboard and not args.write_receipt:
        ap.error("--update-scoreboard requires --write-receipt")

    if args.rebuild_scoreboard:
        previous = {
            row["provider"]: row for row in _load_board().get("entries", [])
        }
        rows: list[dict] = []
        registered = set(available("L1"))
        for name in sorted(registered):
            row = score_provider(lambda n=name: get_provider(n))
            old = previous.get(name, {})
            row["verification"] = _verification_for(old or row)
            if old.get("receipt"):
                row["receipt"] = old["receipt"]
            rows.append(row)
        # Preserve or recompute contenders that are not part of the registry.
        for name, old in sorted(previous.items()):
            if name in registered:
                continue
            verification = _verification_for(old)
            factory_spec = old.get("factory")
            if verification["class"] == "public-reproducible" and factory_spec:
                row = score_provider(load_contender(factory_spec), name_hint=factory_spec)
                row["factory"] = factory_spec
                row["verification"] = verification
                if old.get("receipt"):
                    row["receipt"] = old["receipt"]
                rows.append(row)
            else:
                kept = deepcopy(old)
                kept["verification"] = verification
                rows.append(kept)
        rows.sort(key=lambda entry: entry["provider"])
        _write_board(rows)
        print(f"scoreboard rebuilt from local run -> {SCOREBOARD} ({len(rows)} entries)")
        return 0

    names = args.providers or [n for n in available("L1") if not n.startswith("psy:")]
    rows = [score_provider(lambda n=n: get_provider(n)) for n in names]
    if args.contender:
        factory = load_contender(args.contender)
        contender_row = score_provider(factory, name_hint=args.contender)
        rows.append(contender_row)
        if args.write_receipt:
            receipt_path = (
                args.write_receipt
                if args.write_receipt.is_absolute()
                else REPO / args.write_receipt
            )
            receipt = build_receipt(
                repo=REPO,
                score=contender_row,
                visibility=args.visibility,
                factory_spec=args.contender,
                submitter=args.submitter,
            )
            write_receipt(receipt_path, receipt)
            print(f"receipt written -> {receipt_path}")
            if args.update_scoreboard:
                _upsert_receipt(receipt, receipt_path)
                print(f"scoreboard updated -> {SCOREBOARD}")

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
