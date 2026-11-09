"""Claims-integrity gate adapted from an earlier science-bundle checker.

The rule it enforces: a public claim cannot outlive the evidence behind it.
Every headline number in a public doc carries a claim tag bound to a ledger
entry; the gate fails on dangling tags, on tags whose ledger status forbids
public use, and on forbidden phrases appearing untagged (the safety net for
numbers pasted without a tag). Provisional claims must sit next to a caveat.
"""

from gyre.claims_gate import check_claims


def _ledger():
    return {
        "claims": {
            "GYR-01": {
                "status": "confirmed",
                "public_allowed": True,
                "statement": "sensor ladder reaches F1 0.94 on synthetic ground truth",
                "evidence": "scripts/eval_synthetic.py",
            },
            "GYR-04": {
                "status": "cannot-claim",
                "public_allowed": False,
                "statement": "real-trace validity",
                "evidence": "pinned until Phase 3 expert anchor",
            },
            "GYR-05": {
                "status": "provisional",
                "public_allowed": True,
                "statement": "~47% thinking tokens saved",
                "evidence": "scripts/demo_reasoning_loop.py",
                "caveat_markers": ["synthetic", "demo"],
            },
        },
        "forbidden_phrases": ["real-trace validated", "production-proven"],
    }


def test_confirmed_tagged_claim_passes():
    docs = {"README.md": "The ladder hits F1 0.94 <!-- claim:GYR-01 --> on synthetic corpora."}
    result = check_claims(docs, _ledger())
    assert result.ok
    assert result.failures == []


def test_dangling_tag_fails():
    docs = {"README.md": "Amazing result <!-- claim:GYR-99 -->."}
    result = check_claims(docs, _ledger())
    assert not result.ok
    assert any("GYR-99" in f for f in result.failures)


def test_cannot_claim_status_fails_in_public_doc():
    docs = {"README.md": "Validated on real traces <!-- claim:GYR-04 -->."}
    result = check_claims(docs, _ledger())
    assert not result.ok
    assert any("GYR-04" in f for f in result.failures)


def test_forbidden_phrase_without_tag_fails():
    docs = {"docs/pitch.md": "Gyre is production-proven measurement."}
    result = check_claims(docs, _ledger())
    assert not result.ok
    assert any("production-proven" in f for f in result.failures)


def test_forbidden_phrase_on_a_tagged_line_is_allowed():
    docs = {"README.md": "production-proven <!-- claim:GYR-01 --> (synthetic tier)"}
    result = check_claims(docs, _ledger())
    assert result.ok


def test_provisional_claim_without_caveat_warns():
    docs = {"README.md": "Saves ~47% of thinking tokens <!-- claim:GYR-05 -->."}
    result = check_claims(docs, _ledger())
    assert result.ok  # warning, not failure
    assert any("GYR-05" in w for w in result.warnings)


def test_provisional_claim_with_caveat_is_clean():
    docs = {"README.md": "The synthetic demo saves ~47% of tokens <!-- claim:GYR-05 -->."}
    result = check_claims(docs, _ledger())
    assert result.ok
    assert result.warnings == []
