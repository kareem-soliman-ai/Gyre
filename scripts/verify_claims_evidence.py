#!/usr/bin/env python3
"""Do the numbers in the claims ledger still match the artefacts they cite?

`scripts/check_claims.py` verifies that public claims are TAGGED to ledger
entries. That catches an untagged claim; it cannot catch a claim whose number
has quietly stopped being true. This closes that gap: every ledger entry with a
`verify` block names a generated artefact and the figures it must still produce,
and this script re-reads the artefact and asserts them.

The pairing matters. Tags without value checks let stale numbers live forever;
value checks without tags let untagged copy slip through. Run both in CI.

Usage:
    python scripts/verify_claims_evidence.py
    python scripts/verify_claims_evidence.py --ledger docs/claims-ledger.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _lookup(artefact: dict, check: dict) -> float | None:
    """Pull one figure out of a scoreboard-shaped artefact."""
    for entry in artefact.get("entries", []):
        if entry.get("provider") != check["provider"]:
            continue
        corpus = entry.get("corpora", {}).get(check["corpus"], {})
        return corpus.get(check["metric"])
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(REPO / "docs" / "claims-ledger.json"))
    args = ap.parse_args()

    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    failures: list[str] = []
    checked = 0
    verified_claims = 0

    for claim_id, claim in ledger.get("claims", {}).items():
        spec = claim.get("verify")
        if not spec:
            continue
        verified_claims += 1
        source = REPO / spec["source"]
        if not source.is_file():
            failures.append(f"{claim_id}: cited artefact {spec['source']} is missing")
            continue
        artefact = json.loads(source.read_text(encoding="utf-8"))
        for check in spec.get("checks", []):
            checked += 1
            actual = _lookup(artefact, check)
            label = f"{claim_id} {check['provider']}/{check['corpus']}/{check['metric']}"
            if actual is None:
                failures.append(f"{label}: not found in {spec['source']}")
            elif abs(actual - check["expect"]) > check.get("tolerance", 0.0):
                failures.append(
                    f"{label}: artefact says {actual}, ledger claims "
                    f"{check['expect']} (tolerance {check.get('tolerance', 0.0)}) "
                    "— re-derive the claim or fix the copy"
                )

    for f in failures:
        print(f"FAIL  {f}")
    if failures:
        print(f"claims evidence: {len(failures)} figure(s) no longer reproduce")
        return 1
    print(
        f"claims evidence: OK ({verified_claims} claims with verify blocks, "
        f"{checked} figures re-checked against their artefacts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
