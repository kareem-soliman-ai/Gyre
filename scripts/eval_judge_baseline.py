"""E7 — the strongest engineering baseline: an LLM judge as a per-step sensor.

The sensors in eval_evidence.py beat naive baselines WE wrote. The strongest
baseline a good engineer would actually reach for today is different: ask a
frontier-ish LLM, per step, "is this rumination?" — the rubric-as-prompt
pattern. If a validated local instrument cannot at least approach that on
accuracy while beating it wildly on cost and latency, the instrument story is
weak. If it can, the economics write the pitch: an LLM call per loop iteration
is exactly the token burn the sensor exists to prevent.

This script wraps ``gyre.labeling.OpenRouterJudge`` (public module, public
rubric) as a MeasurementProvider and scores it on the same synthetic corpora,
same rules, as every other sensor. The judge sees BOTH channels (artifact and
error) — the same information the evidence-aware sensors get. Per-call latency
is measured; cost is reported as calls (one chat completion per step).

Needs OPENROUTER_API_KEY. Model falls back down a list of cheap defaults.

Usage:
    python scripts/eval_judge_baseline.py
    python scripts/eval_judge_baseline.py --model openai/gpt-4o-mini
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import compare_providers, evaluate_provider
from gyre.labeling import OpenRouterJudge
from gyre.measurement import Meaning, Measurement
from gyre.providers import DiffNoveltyProvider, EvidenceNoveltyProvider
from gyre.synthetic import by_difficulty, gen_l1_corpus, gen_l1_evidence_corpus

FALLBACK_MODELS = [
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "anthropic/claude-haiku-4.5",
]


class JudgeSensor:
    """An LLM judge, dressed as a MeasurementProvider so the harness treats it
    exactly like any other sensor. Stateful: prior steps are the judge's
    context, reset per trace like every provider."""

    loop_id = "L1"

    def __init__(self, judge: OpenRouterJudge):
        self._judge = judge
        self.name = judge.name
        self._priors: list[str] = []
        self.calls = 0
        self.total_ms = 0.0

    @staticmethod
    def _step_text(observation) -> str:
        text = observation.artifact
        if observation.error is not None:
            text += f"\n[environment response]\n{observation.error}"
        return text

    def measure(self, observation) -> Measurement:
        text = self._step_text(observation)
        t0 = time.perf_counter()
        v = self._judge.score_step(text, self._priors)
        self.total_ms += (time.perf_counter() - t0) * 1000
        self.calls += 1
        self._priors.append(text)
        prob = v.confidence if v.is_ruminating else 1.0 - v.confidence
        return Measurement(
            value=1.0 - prob,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            probability=prob,
            decision=v.is_ruminating,
            confounds=(
                "one chat completion per loop iteration: cost and latency scale with the loop",
                "prompt-sensitive; rubric drift changes the boundary",
            ),
            provider=self.name,
            detail={"rationale": v.rationale},
        )

    def reset(self) -> None:
        self._priors = []


def build_local_sensors():
    sensors = [DiffNoveltyProvider(), EvidenceNoveltyProvider()]
    try:
        from gyre.embedding import make_embedder
        from gyre.providers.proprietary.evi_semantic import EviSemanticProvider

        p = EviSemanticProvider(embed=make_embedder("local"))
        p.name = "psy:evi-semantic(local)"
        sensors.append(p)
    except Exception as exc:  # noqa: BLE001
        print(f"[info] proprietary layer not present ({exc})", file=sys.stderr)
    return sensors


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM-judge-as-sensor baseline (E7).")
    ap.add_argument("--model", default=None, help="OpenRouter model id for the judge")
    args = ap.parse_args()

    corpus = gen_l1_corpus() + gen_l1_evidence_corpus()
    traces = [st.trace for st in corpus]
    n_steps = sum(len(t.observations) for t in traces)
    print(f"Corpus: {len(traces)} traces, {n_steps} steps "
          f"(judge cost = {n_steps} chat completions)")

    models = [args.model] if args.model else FALLBACK_MODELS
    judge_sensor = None
    for model in models:
        candidate = JudgeSensor(OpenRouterJudge(model))
        try:
            probe = traces[0].observations[0]
            candidate.measure(probe)
            candidate.reset()
            judge_sensor = candidate
            break
        except Exception as exc:  # noqa: BLE001 - model unavailable, try next
            print(f"[info] {model} failed ({exc}); trying next", file=sys.stderr)
    if judge_sensor is None:
        print("[error] no judge model reachable", file=sys.stderr)
        return 1
    print(f"Judge: {judge_sensor.name}\n")

    providers = build_local_sensors() + [judge_sensor]
    groups = by_difficulty(corpus)

    t0 = time.perf_counter()
    overall = compare_providers(providers, traces)
    wall = time.perf_counter() - t0

    print(f"[overall: both corpora pooled]  ({wall:.0f}s wall)")
    print(f"  {'provider':30} {'F1':>5} {'prec':>5} {'rec':>5} {'acc':>5}  {'decision boundary':<22}")
    print("  " + "-" * 80)
    for s in overall:
        where = "self-deciding" if s.calibrated else f"swept theta={s.best_threshold}"
        print(f"  {s.provider:30} {s.f1:5.2f} {s.precision:5.2f} {s.recall:5.2f} "
              f"{s.accuracy:5.2f}  {where:<22}")

    print("\n[per difficulty: judge only]")
    for difficulty in sorted(groups):
        s = evaluate_provider(judge_sensor, groups[difficulty])
        print(f"  {difficulty:14} F1 {s.f1:5.2f}  prec {s.precision:5.2f}  "
              f"rec {s.recall:5.2f}  acc {s.accuracy:5.2f}")

    per_call = judge_sensor.total_ms / max(judge_sensor.calls, 1)
    print(f"\nJudge economics: {judge_sensor.calls} calls, {per_call:.0f} ms/call mean, "
          f"{judge_sensor.total_ms / 1000:.0f}s total scoring time.")
    print("Local sensors score the same corpus in milliseconds per step with zero API")
    print("calls; a judge in the loop pays one completion per iteration, forever.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
