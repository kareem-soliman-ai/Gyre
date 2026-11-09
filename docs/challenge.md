# The Gyre gauntlet: try to beat the instrument

> **Sensor-contribution track:** this gauntlet compares measurement providers.
> For the clone-and-play causal-control challenge, start with the
> [Alien Factory expedition](observer-effects-challenge.md).

You are a sceptical engineer. Good — this page is for you. The claim under test
is narrow and falsifiable: **does a sensor that models information gain per
step beat strong public proxies, and under which cells does that ordering
fail?** Everything needed to attack the public baselines ships in this repo.
Protected candidates do not; their synthetic development scores are published
against registry names with an explicit verification boundary.

## The game

1. **Implement a sensor.** Any object satisfying `MeasurementProvider`
   (`src/gyre/measurement.py`): a `measure(observation) -> Measurement` and a
   `reset()`. Start from [building-measurements.md](building-measurements.md)
   or copy a naive baseline (`src/gyre/providers/naive.py`).
2. **Run the gauntlet:**

   ```bash
   python scripts/challenge.py --contender yourpackage.yoursensor:build
   ```

   Your sensor is scored on two labelled synthetic corpora (labels hold by
   construction — the generators are in `src/gyre/synthetic.py`, so you can
   audit exactly what each cell contains) and ranked against the published
   scoreboard ([scoreboard.json](scoreboard.json)).
3. **Read the per-cell breakdown before celebrating.** The corpora contain
   all-negative trap cells (`edge`, `evid-pivot`, `evid-progress`: genuine
   progress that superficially looks like circling). Firing there is a false
   positive. A pooled win that loses the trap cells is measuring surface form,
   not the construct — the exact failure mode this repo exists to expose.

## The rules (read them; they favour you)

- The bench is **generous to your sensor**: if it returns raw values, the
  harness sweeps every threshold in hindsight and reports your best case.
  Self-deciding providers get no such favour — they are scored on their own
  decisions (`self-deciding: yes`).
- The corpora are public and deterministic. You can overfit them if you want;
  that is why the scoreboard is labelled synthetic-tier <!-- claim:GYR-01 -->,
  and why real-trace scores only ship after expert-anchored validation
  (that pipeline is `src/gyre/labeling.py` — also public, also attackable).
- The onset economics are runnable too: `scripts/demo_reasoning_loop.py` and
  `scripts/replay_routing.py` show the measurement gap propagating to loop
  cost, which is the number that actually matters.

## What beating the board would mean

If your sensor tops the current leader on the stated two-corpus ranking and
holds the trap cells, open an issue with your `--json` output. That is a genuine
benchmark result. It becomes evidence about the construct only if the ordering
survives new mechanism families, a sealed holdout, or appropriate real traces.
The repository's own record includes a mechanism that scored 1.00 on its home
cell and 0.00 pooled; the evaluation, not the story, decided its scope.

## What the scoreboard gate can and cannot verify

Two gates run over this repo's claims, and they catch different failures:

```bash
python scripts/check_claims.py            # every public claim is tagged to the ledger
python scripts/verify_claims_evidence.py  # every tagged FIGURE still reproduces
```

The first catches an untagged number. The second re-reads
[scoreboard.json](scoreboard.json) and asserts the figures the ledger claims are
still the figures the bench produces — so if a re-run moves the ladder, the
claim turns red rather than the copy quietly staying wrong. The scoreboard
itself is generated (`--rebuild-scoreboard`), never hand-edited.

CI recomputes every provider present in a clean public checkout and every
contributed provider included in a pull request. It cannot recompute a protected
provider whose implementation is absent. Such entries are maintainer-reported,
excluded from the verified ranking, and must carry a note stating whether the
score is development, holdout, or transfer evidence. This is a real trust
boundary, not something the registry seam removes. The exact verification
classes and private submission path are documented in
[score-verification.md](score-verification.md) and
[contributing-a-score.md](contributing-a-score.md).

## Why the instruments are not in the repo

Open method, protected instrument. Every mechanism is documented (the pattern
docs, the rubric, the build guide, the calibration *procedure*); what stays
private is fitted operating points, corrected mechanisms, and protected
corpora. Protection does not imply validity: validation still requires an
appropriate holdout, outcome criterion, and evidence receipt. A hosted provider
can later make repeatable evaluation possible without distributing its
internals; see [hosted-measurements.md](hosted-measurements.md).
