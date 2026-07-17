"""E3 harness — replay the sensor → monitor → controller pipeline over labelled traces.

Runs every (sensor, controller) pair over a labelled L1 corpus and scores the
pipeline's FIRING behaviour with the outcome model from the measurement×loop
eval spec (internal/measurement-x-loop-eval-spec.md):

- lead time  — steps between ground-truth onset and the first fire
- false fire — the pipeline fired on a step whose ground-truth label is False
- miss       — ground truth had an onset, the pipeline never fired
- cost       — 1 unit per measurement call, +5 per false-positive action,
               +1 per iteration spent past a missed/late onset

Corpus selection, in order:
1. traces/private/scoring_set.json, if it exists AND carries at least one
   positive label (a freshly generated scoring set is an unscored template —
   all-False labels — and is skipped with a warning until a human scores it).
2. Otherwise the synthetic corpora (artifact-only + evidence-channel), labels
   known by construction.

Controllers differ in WHEN they fire (the adaptive one routes on its belief,
not on a patience counter) and in WHICH route they choose. Replay can score the
timing; it cannot score route outcomes, because a recorded trace does not say
what would have happened after a reframe or an escalation. Route choices are
reported descriptively. Scoring them needs either the E2 simulator
(scripts/exp_controller_gap.py) or, eventually, outcome-annotated real traces.

The adaptive controller is constructed at each sensor's operating point (TPR /
FPR measured on this corpus, per-trace reset) — the controller consumes the
sensor's measured quality, never an assumed one.

Usage:
    python scripts/replay_routing.py            # patience=3 for counter-based controllers
    python scripts/replay_routing.py --patience 2
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import LabelledTrace, evaluate_provider
from gyre.control import ControlContext, FixedRouteController, L5RouteController
from gyre.interfaces import ExitReason
from gyre.loops.rumination import RuminationMonitor
from gyre.providers import DiffNoveltyProvider, EvidenceNoveltyProvider

# Cost model, from the eval spec.
COST_MEASURE = 1
COST_FALSE_ACTION = 5
COST_MISSED_ITER = 1


@dataclass
class ReplaySummary:
    sensor: str
    controller: str
    n_traces: int
    fired: int
    false_fires: int
    misses: int
    lead_times: list[int]
    routes: dict[str, int]
    cost: float

    @property
    def mean_lead(self) -> float | None:
        return sum(self.lead_times) / len(self.lead_times) if self.lead_times else None


def load_corpus() -> tuple[str, list[LabelledTrace]]:
    scored = Path(__file__).resolve().parents[1] / "traces" / "private" / "scoring_set.json"
    if scored.exists():
        from gyre.traces import ScoredTrace

        data = json.loads(scored.read_text(encoding="utf-8"))
        traces = [ScoredTrace.from_dict(d) for d in data]
        if any(s.is_ruminating for t in traces for s in t.steps):
            return "real (traces/private/scoring_set.json)", [t.to_bench() for t in traces]
        print(
            "[warn] scoring_set.json present but has zero positive labels — it is an "
            "unscored template. Score it (see scoring_worksheet.md), then re-run to "
            "replay on real traces. Falling back to synthetic.",
            file=sys.stderr,
        )
    from gyre.synthetic import gen_l1_corpus, gen_l1_evidence_corpus

    return "synthetic (both corpora)", [
        st.trace for st in gen_l1_corpus() + gen_l1_evidence_corpus()
    ]


def build_sensors():
    sensors = [DiffNoveltyProvider(), EvidenceNoveltyProvider()]
    try:
        from gyre.embedding import make_embedder
        from gyre.providers.proprietary.evi_semantic import EviSemanticProvider

        p = EviSemanticProvider(embed=make_embedder("local"))
        p.name = "psy:evi-semantic(local)"
        sensors.append(p)
    except Exception as exc:  # noqa: BLE001 - public checkout
        print(f"[info] proprietary sensor layer not present ({exc})", file=sys.stderr)
    return sensors


def step_rates(provider, traces, threshold):
    from gyre.loops._policy import ThresholdRequired, trigger_state

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


def build_controllers(tpr: float, fpr: float, threshold: float | None):
    controllers = [FixedRouteController(ExitReason.REFRAME), L5RouteController()]
    try:
        from gyre.control.proprietary.adaptive_ev import AdaptiveEVController

        controllers.append(
            AdaptiveEVController(
                sensor_tpr=max(tpr, 0.05),  # a zero-TPR sensor breaks the filter; floor it
                sensor_fpr=min(max(fpr, 0.0), 0.9),
                flag_threshold=threshold,
            )
        )
    except Exception as exc:  # noqa: BLE001 - public checkout
        print(f"[info] proprietary controller layer not present ({exc})", file=sys.stderr)
    return controllers


def replay(sensor_factory, controller, traces, patience, threshold) -> ReplaySummary:
    fired = false_fires = misses = 0
    lead_times: list[int] = []
    routes: dict[str, int] = {}
    cost = 0.0
    for tr in traces:
        sensor = sensor_factory()
        monitor = RuminationMonitor(sensor, patience=patience, threshold=threshold)
        controller.reset()
        n = len(tr.observations)
        onset = tr.labels.index(True) if any(tr.labels) else None

        fire_step, route = None, None
        for i, obs in enumerate(tr.observations):
            cost += COST_MEASURE
            monitor.observe(obs)
            ctx = ControlContext(steps_remaining=n - i)
            r = controller.route([monitor.verdict()], ctx)
            if r is not ExitReason.CONTINUE:
                fire_step, route = i, r
                break

        if fire_step is not None:
            fired += 1
            routes[route.value] = routes.get(route.value, 0) + 1
            if not tr.labels[fire_step]:
                false_fires += 1
                cost += COST_FALSE_ACTION
            if onset is not None:
                lead_times.append(fire_step - onset)
                cost += COST_MISSED_ITER * max(0, fire_step - onset)
        elif onset is not None:
            misses += 1
            cost += COST_MISSED_ITER * (n - onset)

    return ReplaySummary(
        sensor="", controller=controller.name, n_traces=len(traces),
        fired=fired, false_fires=false_fires, misses=misses,
        lead_times=lead_times, routes=routes, cost=cost,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay sensor->monitor->controller over labelled traces.")
    ap.add_argument("--patience", type=int, default=3)
    args = ap.parse_args()

    source, traces = load_corpus()
    print(f"Corpus: {source} — {len(traces)} traces, "
          f"{sum(1 for t in traces if any(t.labels))} with a rumination onset")

    for sensor_proto in build_sensors():
        # Operating point + (for naive sensors) the swept threshold, on this corpus.
        score = evaluate_provider(sensor_proto, traces)
        threshold = score.best_threshold
        tpr, fpr = step_rates(sensor_proto, traces, threshold)
        boundary = "self-deciding" if score.calibrated else f"theta={threshold}"
        print(f"\n=== sensor: {sensor_proto.name}  ({boundary}, step TPR={tpr:.2f} FPR={fpr:.2f}) ===")
        print(f"  {'controller':18} {'fired':>5} {'false':>5} {'miss':>4} {'lead':>6} {'cost':>7}  routes")
        print("  " + "-" * 72)
        for controller in build_controllers(tpr, fpr, threshold):
            s = replay(lambda sp=sensor_proto: (sp.reset() or sp), controller,
                       traces, args.patience, threshold)
            lead = f"{s.mean_lead:+.1f}" if s.mean_lead is not None else "  n/a"
            routes = ", ".join(f"{k}:{v}" for k, v in sorted(s.routes.items())) or "-"
            print(f"  {s.controller:18} {s.fired:>5} {s.false_fires:>5} {s.misses:>4} "
                  f"{lead:>6} {s.cost:>7.0f}  {routes}")

    print("\nRead it like this: 'lead' is fire-step minus onset (negative = early,"
          "\npositive = late); 'false' is fires on a step whose label is False;"
          "\ncost = measurements + 5x false actions + 1x per iteration past onset."
          "\nRoute choices are descriptive — scoring their outcomes needs the E2"
          "\nsimulator or outcome-annotated traces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
