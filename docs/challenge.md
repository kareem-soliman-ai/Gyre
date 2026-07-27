# The Gyre gauntlet: try to beat the instrument

You are a sceptical engineer. Good — this page is for you. The claim under test
is narrow and falsifiable: **a sensor that models the construct (information
gain per step) beats any proxy an engineer writes in an afternoon, and the gap
shows up in loop outcomes.** Everything needed to attack that claim ships in
this repo. The validated instruments themselves do not — their scores are
published against their registry names, and you are invited to beat those
scores with anything you can build.

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
  harness sweeps every threshold in hindsight and reports your best case. The
  published instruments get no such favour — they are scored on their own
  decisions (`self-deciding: yes`).
- The corpora are public and deterministic. You can overfit them if you want;
  that is why the scoreboard is labelled synthetic-tier <!-- claim:GYR-01 -->,
  and why real-trace scores only ship after expert-anchored validation
  (that pipeline is `src/gyre/labeling.py` — also public, also attackable).
- The onset economics are runnable too: `scripts/demo_reasoning_loop.py` and
  `scripts/replay_routing.py` show the measurement gap propagating to loop
  cost, which is the number that actually matters.

## What "beating the instrument" would mean

If your sensor tops `psy:evi-semantic` pooled AND holds the trap cells, we want
to hear about it — that is a genuine finding about the construct, and this
repo's own history shows what happens next: the vendored MVT mechanism scored
a perfect 1.00 on its home cell and 0.00 pooled, and the eval, not the story,
decided its fate. Open an issue with your `--json` output.

## The scoreboard cannot go stale without going red

Two gates run over this repo's claims, and they catch different failures:

```bash
python scripts/check_claims.py            # every public claim is tagged to the ledger
python scripts/verify_claims_evidence.py  # every tagged FIGURE still reproduces
```

The first catches an untagged number. The second re-reads
[scoreboard.json](scoreboard.json) and asserts the figures the ledger claims are
still the figures the bench produces — so if a re-run moves the ladder, the
claim turns red rather than the copy quietly staying wrong. The scoreboard
itself is generated (`--rebuild-scoreboard`), never hand-edited, and the ordering
is the claim: instrument > evidence-naive > diff-naive on the evidence corpus.

If you beat that ordering, the gate is what makes it undeniable rather than
arguable.

## Why the instruments are not in the repo

Open method, closed instrument. Every mechanism is documented (the pattern
docs, the rubric, the build guide, the calibration *procedure*); what stays
private is what makes an instrument validated: fitted operating points,
corrected mechanisms, and the labelled corpora they were earned on. A
measurement that ships its fitted constants is a measurement you can game; one
that answers over a wire (see [hosted-measurements.md](hosted-measurements.md))
is one you can only try to beat. That is the standing invitation.
