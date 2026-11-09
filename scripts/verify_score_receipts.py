#!/usr/bin/env python3
"""Validate score receipts and rerun every public contender.

Private receipts are accepted as well-formed *claims* but reported UNVERIFIED.
The command exits non-zero only for malformed receipts, stale public scorer
manifests, or public scores that do not reproduce.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from challenge import load_contender, score_provider  # noqa: E402
from gyre.score_receipts import (  # noqa: E402
    load_receipt,
    manifest_matches,
    validate_receipt_shape,
)

SUBMISSIONS = ROOT / "benchmarks" / "submissions"


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _score_differences(claimed: dict, fresh: dict, tolerance: float) -> list[str]:
    differences: list[str] = []
    for corpus, claimed_metrics in claimed.get("corpora", {}).items():
        fresh_metrics = fresh.get("corpora", {}).get(corpus, {})
        for metric in ("f1", "precision", "recall"):
            if metric not in claimed_metrics:
                continue
            got = fresh_metrics.get(metric)
            if got is None or abs(got - claimed_metrics[metric]) > tolerance:
                differences.append(
                    f"{corpus}/{metric}: claimed {claimed_metrics[metric]}, got {got}"
                )
        if claimed_metrics.get("cells") != fresh_metrics.get("cells"):
            differences.append(f"{corpus}/cells differ")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="*", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.005)
    args = parser.parse_args()

    paths = args.receipts or sorted(SUBMISSIONS.glob("*.json"))
    failures: list[str] = []
    reproduced = unverified = 0
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        try:
            receipt = load_receipt(path)
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{path}: cannot read receipt: {exc}")
            continue
        errors = validate_receipt_shape(receipt)
        if errors:
            failures.extend(f"{path}: {error}" for error in errors)
            continue
        vclass = receipt["verification"]["class"]
        if vclass == "self-reported":
            unverified += 1
            print(
                f"UNVERIFIED  {receipt['provider']} ({_display_path(path)}): "
                "private implementation not supplied"
            )
            continue
        if vclass == "sealed-evaluator-attested":
            failures.append(
                f"{path}: sealed evaluator signatures are not yet supported by "
                "the public verifier"
            )
            continue
        changed = manifest_matches(ROOT, receipt)
        if changed:
            failures.append(
                f"{path}: scorer changed since receipt ({', '.join(changed)}); rerun it"
            )
            continue
        spec = receipt["implementation"]["factory"]
        try:
            fresh = score_provider(load_contender(spec), name_hint=spec)
        except Exception as exc:  # noqa: BLE001 - contributor import failures are evidence
            failures.append(f"{path}: could not rerun {spec!r}: {exc}")
            continue
        differences = _score_differences(
            receipt["score"], fresh, tolerance=args.tolerance
        )
        if differences:
            failures.extend(
                f"{path}: {receipt['provider']} {difference}"
                for difference in differences
            )
            continue
        reproduced += 1
        print(f"REPRODUCED  {receipt['provider']} ({_display_path(path)})")

    for failure in failures:
        print(f"FAIL  {failure}", file=sys.stderr)
    print(
        f"receipts: {reproduced} public reproduced, "
        f"{unverified} private explicitly unverified, {len(failures)} failures"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
