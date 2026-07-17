"""Calibrate psy:evi-semantic's ceilings by leave-one-concept-out CV.

The sensor's two decision boundaries (artifact staleness ceiling, evidence
arrival ceiling) were hand-set from an embedding-model probe. The measurement
stance says a production sensor earns its boundary by fitting it on labelled
data. This script demonstrates that path on the synthetic corpus:

- folds = the four fix concepts. For each fold, grid-search both ceilings to
  maximise F1 on the traces of the OTHER three concepts (plus the shared
  concept-free cells), then score the held-out concept's traces at the chosen
  ceilings.
- reports per-fold chosen ceilings, held-out F1, and the comparison against the
  hand-set defaults on the same held-out traces.

Honesty: this is synthetic-tier calibration. It shows the fitting machinery and
whether the hand-set defaults were near-optimal; it does NOT transfer to real
traces, whose ceilings must be fitted on a scored real corpus (the E3 rung).

Usage: python scripts/calibrate_ceilings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import evaluate_provider
from gyre.synthetic import (
    _CONCEPTS,
    gen_easy,
    gen_edge,
    gen_evid_easy,
    gen_evid_hard,
    gen_evid_pivot,
    gen_evid_progress,
    gen_evid_retry,
    gen_hard,
)

# Generic search ranges; the instrument's current (hand-set) ceilings are read
# off the provider at runtime rather than written here — parameter values are
# instrument internals, the procedure is the open part.
ARTIFACT_GRID = [round(0.20 + 0.04 * i, 2) for i in range(6)]
EVIDENCE_GRID = [round(0.05 + 0.05 * i, 2) for i in range(5)]


def concept_traces(concept: str):
    return [
        st.trace
        for st in (
            gen_easy(concept), gen_hard(concept),
            gen_evid_easy(concept), gen_evid_hard(concept), gen_evid_retry(concept),
        )
    ]


def shared_traces():
    return [st.trace for st in (gen_edge(5), gen_edge(4), gen_evid_pivot(4), gen_evid_progress(4))]


def score(embed, traces, artifact_ceiling, evidence_ceiling) -> float:
    from gyre.providers.proprietary.evi_semantic import EviSemanticProvider

    p = EviSemanticProvider(
        embed=embed, artifact_ceiling=artifact_ceiling, evidence_ceiling=evidence_ceiling
    )
    return evaluate_provider(p, traces).f1


def main() -> int:
    try:
        from gyre.embedding import make_embedder
        from gyre.providers.proprietary.evi_semantic import EviSemanticProvider

        embed = make_embedder("local")
        current = EviSemanticProvider(embed=embed)
        defaults = (current._artifact_ceiling, current._evidence_ceiling)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] needs the proprietary layer + fastembed ({exc})", file=sys.stderr)
        return 1

    concepts = list(_CONCEPTS)
    print(f"Leave-one-concept-out over {concepts}; grid "
          f"{len(ARTIFACT_GRID)}x{len(EVIDENCE_GRID)}, current ceilings {defaults}\n")
    print(f"  {'held-out':16} {'fit ceilings':>14} {'F1 fit':>7} {'F1 default':>11}")
    print("  " + "-" * 52)

    fitted, default_scores = [], []
    for held_out in concepts:
        train = shared_traces()
        for c in concepts:
            if c != held_out:
                train += concept_traces(c)
        best = max(
            ((a, e) for a in ARTIFACT_GRID for e in EVIDENCE_GRID),
            key=lambda ae: score(embed, train, *ae),
        )
        test = concept_traces(held_out) + shared_traces()
        f1_fit = score(embed, test, *best)
        f1_def = score(embed, test, *defaults)
        fitted.append(f1_fit)
        default_scores.append(f1_def)
        print(f"  {held_out:16} {best[0]:>7.2f}/{best[1]:.2f} {f1_fit:>7.2f} {f1_def:>11.2f}")

    print(f"\n  mean held-out F1: fitted {sum(fitted)/len(fitted):.3f} "
          f"vs hand-set defaults {sum(default_scores)/len(default_scores):.3f}")
    print("  (synthetic-tier calibration: demonstrates the fitting path; real-trace"
          "\n   ceilings must be fitted on a scored real corpus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
