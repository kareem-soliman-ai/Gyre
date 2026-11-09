"""Trust-boundary tests for public and private score receipts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from gyre.score_receipts import build_receipt, validate_receipt_shape


ROOT = Path(__file__).resolve().parents[1]


def _score(provider: str = "example:sensor") -> dict:
    corpus = {
        "f1": 0.5,
        "precision": 0.5,
        "recall": 0.5,
        "calibrated": True,
        "cells": {"easy": 0.5},
    }
    return {
        "provider": provider,
        "corpora": {"difficulty": corpus, "evidence": corpus},
    }


def test_private_receipt_omits_factory_and_cannot_be_ranked():
    receipt = build_receipt(
        repo=ROOT,
        score=_score(),
        visibility="private",
        factory_spec=r"C:\private\secret_sensor:build",
        submitter="private-team",
    )
    assert receipt["implementation"]["factory"] is None
    assert receipt["verification"]["class"] == "self-reported"
    assert receipt["verification"]["ranking_eligible"] is False
    assert validate_receipt_shape(receipt) == []
    assert "secret_sensor" not in json.dumps(receipt)


def test_public_receipt_requires_and_records_rerunnable_factory():
    receipt = build_receipt(
        repo=ROOT,
        score=_score(),
        visibility="public",
        factory_spec="contenders.example:build",
        submitter="public-team",
    )
    assert receipt["implementation"]["factory"] == "contenders.example:build"
    assert receipt["verification"]["class"] == "public-reproducible"
    assert receipt["verification"]["ranking_eligible"] is True
    assert validate_receipt_shape(receipt) == []


def test_private_receipt_verifier_says_unverified_without_failing(tmp_path):
    receipt = build_receipt(
        repo=ROOT,
        score=_score(),
        visibility="private",
        factory_spec=None,
        submitter="private-team",
    )
    path = tmp_path / "private-score.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/verify_score_receipts.py", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "UNVERIFIED" in completed.stdout
    assert "0 public reproduced, 1 private explicitly unverified" in completed.stdout

