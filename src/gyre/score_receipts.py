"""Portable score receipts for public and private Gyre contenders.

A receipt is evidence about *what was run*, not proof that the reported number
is true. Public implementations can be rerun from the recorded factory
specification. Private implementations deliberately omit that specification,
so their receipts remain self-reported until a sealed evaluator attests them.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
VERIFICATION_CLASSES = {
    "public-reproducible",
    "sealed-evaluator-attested",
    "self-reported",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scorer_manifest(repo: Path) -> dict[str, str]:
    """Hash the public files that define the score and generated cases."""
    paths = (
        "scripts/challenge.py",
        "src/gyre/bench.py",
        "src/gyre/synthetic.py",
    )
    return {relative: sha256_file(repo / relative) for relative in paths}


def git_state(repo: Path) -> dict[str, Any]:
    """Return useful provenance without failing outside a Git checkout."""

    def run(*args: str) -> str | None:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    revision = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {
        "commit": revision,
        "dirty": bool(status) if status is not None else None,
    }


def build_receipt(
    *,
    repo: Path,
    score: dict[str, Any],
    visibility: str,
    factory_spec: str | None,
    submitter: str,
    evidence_scope: str = "public-synthetic-development",
) -> dict[str, Any]:
    """Build a JSON-safe receipt with an explicit verification boundary."""
    if visibility not in {"public", "private"}:
        raise ValueError("visibility must be 'public' or 'private'")
    if visibility == "public" and not factory_spec:
        raise ValueError("a public receipt requires a factory specification")
    verification_class = (
        "public-reproducible" if visibility == "public" else "self-reported"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "receipt_type": "gyre-sensor-score",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "submitter": submitter,
        "provider": score["provider"],
        "implementation": {
            "visibility": visibility,
            # Never put a private module path into a public receipt: even path
            # names can disclose project or instrument identities.
            "factory": factory_spec if visibility == "public" else None,
        },
        "verification": {
            "class": verification_class,
            "ranking_eligible": visibility == "public",
            "evidence_scope": evidence_scope,
            "statement": (
                "CI can import and recompute this public implementation."
                if visibility == "public"
                else "The implementation was not supplied; this number is a "
                "public claim, not an independently verified result."
            ),
        },
        "score": score,
        "scorer": {
            "command": "python scripts/challenge.py",
            "files_sha256": scorer_manifest(repo),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "git": git_state(repo),
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def load_receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    """Return human-readable structural errors without claiming score truth."""
    errors: list[str] = []
    if receipt.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if receipt.get("receipt_type") != "gyre-sensor-score":
        errors.append("receipt_type must be 'gyre-sensor-score'")
    if not receipt.get("provider"):
        errors.append("provider is required")
    verification = receipt.get("verification", {})
    vclass = verification.get("class")
    if vclass not in VERIFICATION_CLASSES:
        errors.append(f"unknown verification class: {vclass!r}")
    implementation = receipt.get("implementation", {})
    visibility = implementation.get("visibility")
    factory = implementation.get("factory")
    if visibility not in {"public", "private"}:
        errors.append("implementation.visibility must be 'public' or 'private'")
    if visibility == "public" and not factory:
        errors.append("public implementations require implementation.factory")
    if visibility == "private" and factory is not None:
        errors.append("private receipts must not disclose implementation.factory")
    if vclass == "self-reported" and verification.get("ranking_eligible"):
        errors.append("self-reported receipts cannot be ranking eligible")
    score = receipt.get("score", {})
    if score.get("provider") != receipt.get("provider"):
        errors.append("receipt provider and score provider disagree")
    for corpus in ("difficulty", "evidence"):
        if corpus not in score.get("corpora", {}):
            errors.append(f"score is missing the {corpus!r} corpus")
    return errors


def manifest_matches(repo: Path, receipt: dict[str, Any]) -> list[str]:
    """Report scorer files that differ from the receipt's recorded version."""
    claimed = receipt.get("scorer", {}).get("files_sha256", {})
    current = scorer_manifest(repo)
    return [
        relative
        for relative, digest in current.items()
        if claimed.get(relative) != digest
    ]

