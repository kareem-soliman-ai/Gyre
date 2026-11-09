# Scripts

All public scripts run against Gyre's public interfaces and degrade gracefully
when no private provider is installed.

## Start here

| Script | Purpose |
|---|---|
| `hierarchical_factory.py` | Play v2.2.1 with three variants and four persistent units per operational or ecological family. |
| `living_factory.py` | Play the coupled farm, factory, survival, ecology, and instrument challenge. |
| `alien_factory.py` | Play the minimal v1 observer-effects tutorial and reproduce its design boundary. |
| `loop_playground.py` | Explore human/AI authority and verification choices. |
| `challenge.py` | Score public sensors or a provider supplied through the public interface. |
| `verify_scoreboard.py` | Re-derive the published public scoreboard. |
| `verify_score_receipts.py` | Re-run public receipts and visibly label private self-reports. |
| `check_claims.py` | Check that public claims remain tied to evidence. |
| `verify_claims_evidence.py` | Reproduce figures referenced by the claims ledger. |

The remaining scripts support calibration, panel design, replay, and the
documented experiments. Run a script with `--help` before use.

## Private boundary

Private drivers belong in `scripts/private/`, private experiments in
`experiments/private/`, and private tests in `tests/private/` or a
`tests/test_proprietary_*.py` file. Those paths are gitignored. Public scripts
may discover private implementations through the provider/controller
registries, but must never import or reproduce their internals.
