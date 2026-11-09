"""E2 + E4 — the controller gap, and the standard-practice ladder.

Holds the sensor constant and compares meta-controllers, the mirror image of
gyre.bench (which holds the controller constant and compares sensors). Three
tiers, so the ladder engineers actually climb is visible end to end:

- **Blind tier (standard practice, E4).** What agent scaffolds ship today:
  retry k times then give up (`for attempt in range(k)`), retry k times then
  page a human ("three strikes"), restart with fresh context every k steps
  (the timer reset), and run-to-budget. No sensing at all. Every blind policy
  gets its k swept and reports its BEST configuration in hindsight — the same
  generosity gyre.bench extends to naive sensors.
- **Sensed tier (Gyre loops, E2).** The same routes, but triggered by an L1
  low-gain flag at a sensor operating point MEASURED on the synthetic corpus
  (scripts/eval_evidence.py), for a weak public proxy and a protected
  development candidate. Fixed routes and the L5 divergent/convergent rule.
- **Adaptive tier (Tier 3).** A belief + expected-value controller, loaded
  through the protected controller registry. On a
  clean public checkout this tier reports itself unavailable and everything
  else still runs; the oracle (true phase, true parameters — the regret floor)
  is public, so the size of the gap the adaptive tier closes is verifiable
  even where the controller is not present.

World: episodes with a hidden phase (PROGRESSING / STUCK). Continuing while
stuck pays only if external evidence arrives; reframing recovers stuck loops
(better on divergent problems, per Sio & Ormerod) but risks context loss on a
healthy loop; escalating resolves reliably at a human-attention cost;
abandoning salvages the remaining budget. Sweeps: two cost regimes (cheap and
dear escalation) and a homogeneous sanity-check world where context-conditioned
policies should lose their edge.

Falsifiable predictions, stated before running:
  P8.  Every sensed policy family beats the best blind policy in heterogeneous
       worlds (the value of sensing is positive at equal budget).
  P9.  The strong sensor beats the weak sensor within the sensed tier.
  P10. The adaptive tier beats the best sensed fixed policy (E2's P4, restated
       on the full ladder), and the ladder ordering blind < sensed < adaptive
       holds in both cost regimes.

Pure stdlib + the gyre package. ~2 minutes. Usage:
    python scripts/exp_controller_gap.py [episodes_per_cell]
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, replace
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.control import ControlContext, get_controller
from gyre.interfaces import ExitReason, LoopVerdict
from gyre.loops.incubation import EinstellungBreaker
from gyre.measurement import Meaning, Measurement

# --- true world parameters ------------------------------------------------------

BUDGET = 12          # decision steps per episode
C_STEP = 0.05        # cost of one iteration (tokens/time)
C_REFRAME = 0.10     # cost of a context reset
C_HUMAN = 0.60       # cost of escalating to a human (cheap-help regime)
C_HUMAN_DEAR = 2.50  # expensive-help regime: tests brittleness of fixed routes
P_SUCCESS = 0.18     # per-step success while progressing
Q_STICK = 0.25       # per-step risk of getting stuck while progressing
E_EVIDENCE = 0.10    # per-step chance external evidence unsticks a stuck loop
P_REFRAME_DIV = 0.55     # reframe recovery, divergent problem (Sio & Ormerod)
P_REFRAME_CONV = 0.15    # reframe recovery, convergent problem
P_HUMAN = 0.75       # escalation resolves
CTX_LOSS = 0.30      # reframing a HEALTHY loop knocks it stuck (context loss)
P_DIVERGENT_HAT = 0.80   # controllers' divergent flag is right this often

# Sensor operating points MEASURED in E1 (step-level, per-trace reset).
SENSORS = {
    "weak (naive:diff-novelty)": (0.85, 0.13),
    "strong (psy:evi-semantic)": (0.96, 0.11),
}

PROG, STUCK = 0, 1
CONT, REFRAME, ESCALATE, ABANDON = 0, 1, 2, 3


def oracle_q(V: float, divergent: bool, c_human: float):
    """Value iteration on the TRUE parameters — the public regret floor.

    This is deliberately public: the oracle is what makes the size of the gap
    verifiable. Textbook finite-horizon planning; the protected tier's value is
    not this arithmetic, it is the fitted belief filter and calibration
    that let a controller act near this floor WITHOUT seeing the true phase.
    """
    p_rf = P_REFRAME_DIV if divergent else P_REFRAME_CONV
    Q = [[[0.0] * 4 for _ in range(2)] for _ in range(BUDGET + 1)]
    vp = [0.0] * (BUDGET + 1)
    vs = [0.0] * (BUDGET + 1)
    for k in range(1, BUDGET + 1):
        q = Q[k]
        q[PROG][CONT] = -C_STEP + P_SUCCESS * V + (1 - P_SUCCESS) * (
            (1 - Q_STICK) * vp[k - 1] + Q_STICK * vs[k - 1])
        q[STUCK][CONT] = -C_STEP + E_EVIDENCE * vp[k - 1] + (1 - E_EVIDENCE) * vs[k - 1]
        q[PROG][REFRAME] = -C_REFRAME + (1 - CTX_LOSS) * vp[k - 1] + CTX_LOSS * vs[k - 1]
        q[STUCK][REFRAME] = -C_REFRAME + p_rf * vp[k - 1] + (1 - p_rf) * vs[k - 1]
        q[PROG][ESCALATE] = q[STUCK][ESCALATE] = -c_human + P_HUMAN * V
        q[PROG][ABANDON] = q[STUCK][ABANDON] = 0.0
        vp[k] = max(q[PROG])
        vs[k] = max(q[STUCK])
    return Q


# --- blind tier: standard engineering practice (no sensing) ----------------------


class AlwaysContinue:
    name = "blind:run-to-budget"

    def start(self, V, divergent_hat, c_human):
        pass

    def act(self, k, flags):
        return CONT


class BlindAfterK:
    """`for attempt in range(k): ...` — after k blind iterations, take the exit.
    action=ABANDON is the plain retry loop; action=ESCALATE is 'three strikes
    then page a human'; both are ubiquitous and neither looks at a signal."""

    def __init__(self, k: int, action: int):
        self.k = k
        self.action = action
        self.name = f"blind:{'retry-give-up' if action == ABANDON else 'retry-escalate'} k={k}"

    def start(self, V, divergent_hat, c_human):
        self._steps = 0

    def act(self, k, flags):
        if self._steps >= self.k:
            return self.action
        self._steps += 1
        return CONT


class CycleReframe:
    """Restart with fresh context every k steps — the timer reset. No signal,
    just a clock. Real pattern: 'if it's been 5 iterations, wipe and retry'."""

    def __init__(self, k: int):
        self.k = k
        self.name = f"blind:cycle-reframe k={k}"

    def start(self, V, divergent_hat, c_human):
        self._steps = 0

    def act(self, k, flags):
        self._steps += 1
        if self._steps % self.k == 0:
            return REFRAME
        return CONT


# --- sensed tier: Gyre loops (flag-stream analogues of the reference controllers) —


class FixedPolicy:
    """RuminationMonitor patience + a fixed route (gyre.control's
    FixedRouteController, in flag-stream form for the simulator)."""

    def __init__(self, route: int, patience: int):
        self.route = route
        self.patience = patience
        self.name = f"sensed:{['cont', 'reframe', 'escalate', 'abandon'][route]} p={patience}"

    def start(self, V, divergent_hat, c_human):
        self._streak = 0
        self._seen = 0

    def act(self, k, flags):
        if len(flags) > self._seen:  # consume each flag exactly once
            self._seen = len(flags)
            self._streak = self._streak + 1 if flags[-1] else 0
        if self._streak >= self.patience:
            self._streak = 0
            return self.route
        return CONT


class L5Policy:
    """Patience, then EinstellungBreaker's divergent/convergent call — the one
    context bit Gyre ships openly (gyre.control's L5RouteController)."""

    def __init__(self, patience: int):
        self.patience = patience
        self.name = f"sensed:l5 p={patience}"
        self._breaker = EinstellungBreaker()

    def start(self, V, divergent_hat, c_human):
        self._streak = 0
        self._seen = 0
        self._divergent_hat = divergent_hat

    def act(self, k, flags):
        if len(flags) > self._seen:
            self._seen = len(flags)
            self._streak = self._streak + 1 if flags[-1] else 0
        if self._streak >= self.patience:
            self._streak = 0
            reason = self._breaker.decide(True, divergent=self._divergent_hat)
            return REFRAME if reason.value == "reframe" else ESCALATE
        return CONT


# --- adaptive tier: loaded through the protected controller registry -----------

_ROUTE_TO_ACTION = {
    ExitReason.CONTINUE: CONT,
    ExitReason.REFRAME: REFRAME,
    ExitReason.ESCALATE: ESCALATE,
    ExitReason.ABANDON: ABANDON,
}


def _flag_measurement(flag: bool) -> Measurement:
    return Measurement(
        value=0.0 if flag else 1.0, meaning=Meaning.HIGHER_IS_HEALTHIER,
        probability=0.95 if flag else 0.05, decision=flag, provider="sim:flag",
    )


class AdaptiveAdapter:
    """Runs the registered protected controller against the simulator by wrapping
    each flag as a calibrated L1 verdict — the same code path a production
    scaffold uses, not a reimplementation."""

    def __init__(self, controller, delta_label: str):
        self._c = controller
        self.name = f"adaptive d={delta_label}"

    def start(self, V, divergent_hat, c_human):
        self._c.reset()
        self._V = V
        self._divergent_hat = divergent_hat
        self._c_human = c_human
        self._seen = 0

    def act(self, k, flags):
        measurements = ()
        if len(flags) > self._seen:
            self._seen = len(flags)
            measurements = (_flag_measurement(flags[-1]),)
        verdict = LoopVerdict(
            exit_reason=ExitReason.CONTINUE, loop_id="L1", measurements=measurements
        )
        ctx = ControlContext(
            stakes=self._V, divergent=self._divergent_hat, steps_remaining=k,
            step_cost=C_STEP, reframe_cost=C_REFRAME, escalation_cost=self._c_human,
        )
        return _ROUTE_TO_ACTION[self._c.route([verdict], ctx)]


def make_adaptive(delta: float, rng: random.Random, tpr: float, fpr: float):
    """Construct the protected controller at (possibly warped) parameters.
    Returns None on a public checkout, and the ladder runs without the tier."""
    try:
        controller = get_controller("psy:adaptive-ev")
        world = replace(
            controller.world,
            p_success=P_SUCCESS,
            q_stick=Q_STICK,
            e_evidence=E_EVIDENCE,
            p_reframe_div=P_REFRAME_DIV,
            p_reframe_conv=P_REFRAME_CONV,
            p_human=P_HUMAN,
            ctx_loss=CTX_LOSS,
        )
    except (KeyError, AttributeError):
        return None

    def warp(p: float) -> float:
        return min(0.95, max(0.01, p * math.exp(delta * rng.gauss(0, 1))))

    if delta > 0.0:
        world = replace(world, **{
            f: warp(getattr(world, f))
            for f in ("p_success", "q_stick", "e_evidence", "p_reframe_div",
                      "p_reframe_conv", "p_human", "ctx_loss")
        })
        tpr, fpr = warp(tpr), warp(fpr)
    controller.sensor_tpr = min(tpr, 1.0)
    controller.sensor_fpr = min(fpr, 0.9)
    controller.world = world
    return AdaptiveAdapter(controller, f"{delta:.1f}")


# --- oracle -----------------------------------------------------------------------


class Oracle:
    name = "oracle"

    def start(self, V, divergent, c_human):
        self._Q = oracle_q(V, divergent, c_human)

    def act_with_phase(self, k, phase):
        return max(range(4), key=lambda a: self._Q[k][phase][a])


# --- simulation -------------------------------------------------------------------


def run_episode(policy, rng, tpr, fpr, heterogeneous, c_human):
    divergent = rng.random() < 0.5 if heterogeneous else True
    V = (5.0 if rng.random() < 0.5 else 1.0) if heterogeneous else 1.0
    divergent_hat = divergent if rng.random() < P_DIVERGENT_HAT else not divergent

    is_oracle = isinstance(policy, Oracle)
    policy.start(V, divergent if is_oracle else divergent_hat, c_human)

    phase = PROG
    value, escalations, flags = 0.0, 0, []
    steps_used = 0
    for k in range(BUDGET, 0, -1):
        a = policy.act_with_phase(k, phase) if is_oracle else policy.act(k, flags)
        steps_used += 1
        if a == CONT:
            value -= C_STEP
            if phase == PROG:
                if rng.random() < P_SUCCESS:
                    return value + V, True, escalations, steps_used
                if rng.random() < Q_STICK:
                    phase = STUCK
            else:
                if rng.random() < E_EVIDENCE:
                    phase = PROG
            flags.append(rng.random() < (tpr if phase == STUCK else fpr))
        elif a == REFRAME:
            value -= C_REFRAME
            if phase == STUCK:
                p_rf = P_REFRAME_DIV if divergent else P_REFRAME_CONV
                if rng.random() < p_rf:
                    phase = PROG
            else:
                if rng.random() < CTX_LOSS:
                    phase = STUCK
        elif a == ESCALATE:
            value -= c_human
            escalations += 1
            if rng.random() < P_HUMAN:
                return value + V, True, escalations, steps_used
            return value, False, escalations, steps_used
        else:
            return value, False, escalations, steps_used
    return value, False, escalations, steps_used


def evaluate(policy, seed, tpr, fpr, n, heterogeneous, c_human):
    rng = random.Random(seed)
    total, total_sq, wins, escs, steps = 0.0, 0.0, 0, 0, 0
    for _ in range(n):
        v, ok, e, s = run_episode(policy, rng, tpr, fpr, heterogeneous, c_human)
        total += v
        total_sq += v * v
        wins += ok
        escs += e
        steps += s
    mean = total / n
    se = math.sqrt(max(total_sq / n - mean * mean, 0.0) / n)
    return mean, se, wins / n, escs / n, steps / n


def evaluate_adaptive(delta, seed, tpr, fpr, n, heterogeneous, c_human, draws=8):
    """Average over independent misspecification draws so a delta-level's number
    is not hostage to one lucky/unlucky warp. Returns None on a public checkout."""
    per = max(1, n // draws)
    means, succs, escs, stepss = [], [], [], []
    for r in range(draws):
        rng = random.Random(seed + 1000 * r + int(delta * 100))
        pol = make_adaptive(delta, rng, tpr, fpr)
        if pol is None:
            return None
        mean, _, succ, esc, steps = evaluate(pol, seed + 7 * r, tpr, fpr, per,
                                             heterogeneous, c_human)
        means.append(mean)
        succs.append(succ)
        escs.append(esc)
        stepss.append(steps)
    m = sum(means) / draws
    spread = math.sqrt(sum((x - m) ** 2 for x in means) / draws)
    return m, spread, sum(succs) / draws, sum(escs) / draws, sum(stepss) / draws


BLIND = [
    AlwaysContinue(),
    *(BlindAfterK(k, ABANDON) for k in (2, 4, 6, 8)),
    *(BlindAfterK(k, ESCALATE) for k in (2, 4, 6, 8)),
    *(CycleReframe(k) for k in (2, 4, 6)),
]

SENSED = [
    FixedPolicy(REFRAME, 1), FixedPolicy(REFRAME, 3), FixedPolicy(REFRAME, 6),
    FixedPolicy(ESCALATE, 3), FixedPolicy(ABANDON, 3),
    L5Policy(1), L5Policy(3), L5Policy(6),
]

WORLDS = (
    ("heterogeneous | cheap help", True, C_HUMAN),
    ("heterogeneous | dear help", True, C_HUMAN_DEAR),
    ("homogeneous sanity check | cheap help", False, C_HUMAN),
)


@dataclass
class Row:
    name: str
    mean: float
    se: float
    succ: float
    esc: float
    steps: float


def _print_rows(rows, oracle_value, mark=()):
    for r in rows:
        marker = "".join(m for cond, m in mark if cond(r))
        print(f"  {r.name:26} {r.mean:7.3f} {r.se:6.3f} {r.succ:6.1%} {r.esc:7.2f} "
              f"{r.steps:6.1f} {oracle_value - r.mean:7.3f}{marker}")


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    print(f"E2+E4 controller gap & standard-practice ladder: {n} episodes/cell, "
          f"budget={BUDGET}\nSensor operating points measured in E1; adaptive tier "
          f"averaged over 8 misspecification draws\n")

    # Regret per policy per heterogeneous cost regime, for the robustness table:
    # a recipe tuned for one regime can be terrible in the other, and THAT is the
    # failure mode a deployed scaffold actually faces (nobody re-tunes k when
    # their on-call rotation gets more expensive).
    regret_by_regime: dict[str, dict[str, float]] = {}

    for world, heterogeneous, c_human in WORLDS:
        # Blind tier is sensor-independent: evaluate once per world.
        blind_rows = [Row(p.name, *evaluate(p, 12345, 0, 0, n, heterogeneous, c_human))
                      for p in BLIND]
        best_blind = max(blind_rows, key=lambda r: r.mean)
        oracle_row = Row("oracle", *evaluate(Oracle(), 12345, 0, 0, n, heterogeneous, c_human))

        print(f"=== world: {world} ===")
        print(f"  {'policy':26} {'value':>7} {'+/-':>6} {'succ%':>6} {'esc/ep':>7} {'steps':>6} {'regret':>7}")
        print("  " + "-" * 70)
        _print_rows(blind_rows, oracle_row.mean,
                    mark=[(lambda r, b=best_blind: r is b, "  <- best blind")])
        if heterogeneous:
            for r in blind_rows:
                regret_by_regime.setdefault(r.name, {})[world] = oracle_row.mean - r.mean

        for sensor, (tpr, fpr) in SENSORS.items():
            print(f"\n  --- sensed with {sensor} (TPR={tpr}, FPR={fpr}) ---")
            sensed_rows = [Row(p.name, *evaluate(p, 12345, tpr, fpr, n, heterogeneous, c_human))
                           for p in SENSED]
            best_sensed = max(sensed_rows, key=lambda r: r.mean)
            _print_rows(sensed_rows, oracle_row.mean,
                        mark=[(lambda r, b=best_sensed: r is b, "  <- best sensed")])

            adaptive_rows = []
            for delta in (0.0, 0.3, 0.6):
                res = evaluate_adaptive(delta, 20260717, tpr, fpr, n, heterogeneous, c_human)
                if res is None:
                    print("  adaptive tier unavailable (protected controller not "
                          "registered)")
                    break
                adaptive_rows.append(Row(f"adaptive d={delta:.1f}", *res))
            _print_rows(adaptive_rows, oracle_row.mean)
            if heterogeneous and "strong" in sensor:
                for r in sensed_rows + adaptive_rows:
                    regret_by_regime.setdefault(r.name, {})[world] = oracle_row.mean - r.mean

            # The ladder, in one block: what each rung buys.
            print(f"\n  ladder [{sensor}]:")
            print(f"    value of sensing        : {best_sensed.mean - best_blind.mean:+.3f}"
                  f"  (best sensed {best_sensed.mean:.3f} vs best blind {best_blind.mean:.3f})")
            if adaptive_rows:
                a0 = adaptive_rows[0]
                print(f"    value of adaptive control: {a0.mean - best_sensed.mean:+.3f}"
                      f"  (adaptive d=0 {a0.mean:.3f} vs best sensed {best_sensed.mean:.3f})")
                print(f"    remaining regret         : {oracle_row.mean - a0.mean:+.3f}"
                      f"  (oracle {oracle_row.mean:.3f})")

        _print_rows([oracle_row], oracle_row.mean)
        print()

    # --- the robustness table: worst-case regret across the two cost regimes ---
    both = {name: regs for name, regs in regret_by_regime.items() if len(regs) == 2}
    if both:
        print("=== robustness across cost regimes (heterogeneous worlds, strong sensor) ===")
        print("Worst-case regret vs the oracle, taken across cheap-help and dear-help.")
        print("A recipe tuned in hindsight for one regime still has to live in the other.\n")
        print(f"  {'policy':26} {'cheap':>7} {'dear':>7} {'worst':>7}")
        print("  " + "-" * 52)
        ranked = sorted(both.items(), key=lambda kv: max(kv[1].values()))
        for name, regs in ranked:
            cheap = regs.get("heterogeneous | cheap help", float("nan"))
            dear = regs.get("heterogeneous | dear help", float("nan"))
            print(f"  {name:26} {cheap:7.3f} {dear:7.3f} {max(regs.values()):7.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
