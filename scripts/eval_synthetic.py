"""Run the measurement discrimination eval on synthetic ground truth.

No human scoring anywhere: the traces are constructed with known labels (see
gyre.synthetic), so this runs immediately and tells you where each sensor's
boundary is across difficulty levels. It compares the naive baseline against the
proprietary sensors at several embedding qualities, because for L1 the embedding
is the thing that moves the ceiling.

Usage:
    python scripts/eval_synthetic.py
    python scripts/eval_synthetic.py --api-model openai/text-embedding-3-small

In a clean public checkout only the naive baseline is present (still informative:
watch it fail on the hard cases). With the private layer, the proprietary sensors
appear at hash / char / api embedding quality.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import compare_providers
from gyre.providers import DiffNoveltyProvider
from gyre.synthetic import by_difficulty, gen_l1_corpus


def build_providers(api_model: str | None):
    providers = [DiffNoveltyProvider()]
    try:
        from gyre.embedding import make_embedder
        from gyre.providers.proprietary.mvt_rumination import (
            DiffusionRuminationProvider,
            MvtRuminationProvider,
        )
    except Exception as e:  # noqa: BLE001 - public checkout has no proprietary layer
        print(f"[info] proprietary layer not present ({e}); naive baseline only", file=sys.stderr)
        return providers

    for kind in ("hash", "char"):
        try:
            p = MvtRuminationProvider(embed=make_embedder(kind))
            p.name = f"psy:mvt({kind})"
            providers.append(p)
        except Exception as e:  # noqa: BLE001 - e.g. sklearn missing for 'char'
            print(f"[info] skipping psy:mvt({kind}): {e}", file=sys.stderr)
    try:
        d = DiffusionRuminationProvider(embed=make_embedder("char"))
        d.name = "psy:diffusion(char)"
        providers.append(d)
    except Exception:  # noqa: BLE001
        pass
    # The corrected sensor: absolute semantic novelty on a real (fastembed) embedding.
    try:
        from gyre.providers.proprietary.semantic_novelty import SemanticNoveltyProvider

        p = SemanticNoveltyProvider(embed=make_embedder("local"))
        p.name = "psy:semantic-novelty(local)"
        providers.append(p)
    except Exception as e:  # noqa: BLE001 - fastembed missing, or model download blocked
        print(f"[info] skipping psy:semantic-novelty (local embedder): {e}", file=sys.stderr)
    if api_model:
        try:
            p = MvtRuminationProvider(embed=make_embedder(f"api:{api_model}"))
            p.name = f"psy:mvt(api:{api_model})"
            providers.append(p)
        except Exception as e:  # noqa: BLE001
            print(f"[info] skipping api embedder: {e}", file=sys.stderr)
    return providers


def _table(title, scores):
    print(f"\n{title}")
    print(f"  {'provider':26} {'F1':>5} {'prec':>5} {'rec':>5}  {'decision boundary':<24}")
    print("  " + "-" * 70)
    for s in scores:
        where = "self-deciding" if s.calibrated else f"swept theta={s.best_threshold}"
        print(f"  {s.provider:26} {s.f1:5.2f} {s.precision:5.2f} {s.recall:5.2f}  {where:<24}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Synthetic measurement-discrimination eval.")
    ap.add_argument("--api-model", default=None, help="OpenRouter embedding model id for a semantic run")
    args = ap.parse_args()

    corpus = gen_l1_corpus()
    groups = by_difficulty(corpus)
    providers = build_providers(args.api_model)

    print(f"Synthetic L1 corpus: {len(corpus)} traces "
          f"({', '.join(f'{k}={len(v)}' for k, v in groups.items())})")
    print(f"Providers: {[p.name for p in providers]}")

    for difficulty in ("easy", "hard", "edge"):
        if difficulty in groups:
            _table(f"[{difficulty}]  ({len(groups[difficulty])} traces)",
                   compare_providers(providers, groups[difficulty]))

    all_traces = [st.trace for st in corpus]
    _table("[overall]", compare_providers(providers, all_traces))

    print("\nRead it like this: 'easy' is lexical repeats (everyone should pass),")
    print("'hard' is reworded rumination (lexical sensors fail, semantic ones catch it),")
    print("'edge' is real progress that looks like thrashing (firing here is a false positive).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
