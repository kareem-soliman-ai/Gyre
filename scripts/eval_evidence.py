"""E1 — the information-arrival experiment.

Tests the central measurement claim from the L7/value-controller proposal: that
L1's missing signal is *evidence arrival* (a changed error, a moved test), not
output novelty. Runs the sensor ladder over BOTH synthetic corpora:

- the original artifact-only corpus (easy / hard / edge), so nothing regresses;
- the evidence-channel corpus (evid-easy / evid-hard / evid-retry / evid-pivot /
  evid-progress), whose cells trap each sensor family in a known way.

Falsifiable predictions, stated before running:

  P1. naive:evidence-novelty beats naive:diff-novelty on evid-retry (identical
      retry after the error changed) and matches it elsewhere.
  P2. psy:evi-semantic beats psy:semantic-novelty on every evid-* cell and
      matches it on the artifact-only cells.
  P3. psy:evi-semantic is the first self-deciding sensor to beat the naive
      baseline's ORACLE-thresholded overall F1. If it does not, the proposal's
      measurement claim fails on this corpus.

Also prints step-level TPR/FPR per sensor (per-trace reset), which E2 uses as
its sensor-quality parameters, so the controller experiment runs on measured
sensor numbers rather than invented ones.

Usage:
    python scripts/eval_evidence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import compare_providers
from gyre.loops._policy import ThresholdRequired, trigger_state
from gyre.providers import (
    DiffNoveltyProvider,
    EvidenceNoveltyProvider,
    available,
    get_provider,
)
from gyre.synthetic import by_difficulty, gen_l1_corpus, gen_l1_evidence_corpus


def build_providers():
    providers = [DiffNoveltyProvider(), EvidenceNoveltyProvider()]
    registered = set(available("L1"))
    protected = [
        name
        for name in ("psy:semantic-novelty", "psy:evi-semantic")
        if name in registered
    ]
    providers.extend(get_provider(name) for name in protected)
    if not protected:
        print("[info] protected providers not present; public sensors only", file=sys.stderr)
    return providers


def _table(title, scores):
    # On all-negative cells (edge, evid-pivot, evid-progress) F1 is degenerate
    # (no true positives exist), so accuracy is the column that shows false-fires.
    print(f"\n{title}")
    print(f"  {'provider':28} {'F1':>5} {'prec':>5} {'rec':>5} {'acc':>5}  {'decision boundary':<24}")
    print("  " + "-" * 80)
    for s in scores:
        where = "self-deciding" if s.calibrated else f"swept theta={s.best_threshold}"
        print(f"  {s.provider:28} {s.f1:5.2f} {s.precision:5.2f} {s.recall:5.2f} "
              f"{s.accuracy:5.2f}  {where:<24}")


def step_rates(provider, traces, threshold: float | None):
    """Step-level TPR/FPR with per-trace reset (the sensor-quality numbers E2 consumes)."""
    tp = fp = fn = tn = 0
    for tr in traces:
        provider.reset()
        for obs, truth in zip(tr.observations, tr.labels):
            m = provider.measure(obs)
            try:
                pred = trigger_state(m, threshold=threshold)
            except ThresholdRequired:
                pred = False
            tp += pred and truth
            fp += pred and not truth
            fn += (not pred) and truth
            tn += (not pred) and (not truth)
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return tpr, fpr


def main() -> int:
    artifact_corpus = gen_l1_corpus()
    evidence_corpus = gen_l1_evidence_corpus()
    providers = build_providers()

    groups = by_difficulty(artifact_corpus)
    groups.update(by_difficulty(evidence_corpus))
    all_traces = [st.trace for st in artifact_corpus + evidence_corpus]

    print(f"Corpora: artifact-only {len(artifact_corpus)} traces, "
          f"evidence-channel {len(evidence_corpus)} traces")
    print(f"Providers: {[p.name for p in providers]}")

    for difficulty in ("easy", "hard", "edge",
                       "evid-easy", "evid-hard", "evid-retry", "evid-pivot", "evid-progress"):
        if difficulty in groups:
            _table(f"[{difficulty}]  ({len(groups[difficulty])} traces)",
                   compare_providers(providers, groups[difficulty]))

    overall = compare_providers(providers, all_traces)
    _table("[overall: both corpora pooled]", overall)

    # Sensor-quality numbers for E2, at each provider's operating point
    # (the swept-best threshold for naive sensors, self-decision otherwise).
    print("\nStep-level operating points (per-trace reset), for the E2 simulator:")
    print(f"  {'provider':28} {'TPR':>6} {'FPR':>6}")
    print("  " + "-" * 44)
    by_name = {s.provider: s for s in overall}
    for p in providers:
        s = by_name[p.name]
        tpr, fpr = step_rates(p, all_traces, threshold=s.best_threshold)
        print(f"  {p.name:28} {tpr:6.2f} {fpr:6.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
