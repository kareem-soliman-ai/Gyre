# Contributing to Gyre

Gyre is a catalogue and a measurement playground. Both get better when people
test their seams. There are four kinds of contribution.

## 1. Argue with a translation

Every pattern doc has a "where the analogy holds / where it breaks" section, because every human-to-agent translation fails somewhere. If you think an entry has the seam in the wrong place, or claims a transfer that does not hold, open an issue. This is the most valuable thing you can do, because a translation that hides its seams is worse than no translation, and I would rather be corrected than be confidently wrong in public.

## 2. Add a loop

The catalogue is eight entries against sixty-five years of literature. It is missing more than it holds.

To propose one:

1. Copy [docs/pattern-template.md](docs/pattern-template.md) to `loops/LN-your-loop.md`.
2. **Cite the primary source.** Author, year, title, venue. The original, not a secondary summary. If you are not certain the source says what you claim, check before writing it down. Accurate attribution is the whole value of this catalogue, and one made-up citation poisons it.
3. **Write the "where it breaks" section honestly.** If you cannot find where your translation fails, you have not pushed on it hard enough. Human loops ride on affective machinery agents lack; that is usually where the seam is.
4. **Mark maturity accurately.** `Framing`, `Buildable`, or `Instrument`. Do not mark something `Buildable` to make it sound readier than it is. If it makes a measurement claim about a latent property, it is an `Instrument`, and see the next section.
5. Open a PR. If you want to discuss the framing before writing the whole thing, open an issue first.

There is a [backlog](loops/backlog.md) of loops already sketched in one line each. If one of those is your field, take it.

## 3. Build a detector

The `Buildable` and `Instrument` patterns can be implemented against the [`LoopMonitor` interface](src/gyre/interfaces.py). Contributions of working monitors are welcome, with one firm rule that is not negotiable:

**No performance claims without validation.** You may contribute a detector and describe its method. You may not claim it "saves X" or "catches Y%" unless you have validated it against real agent traces with labelled ground truth, and you attach the sample, the method, and the caveats. A detector that reports a confident number it has not earned is a liability, and this repository will not ship one. [docs/measurement-stance.md](docs/measurement-stance.md) explains why in full. This is not bureaucracy; it is the difference between a measurement and a guess with a decimal point.

## 4. Add a control case

The [Loop Control Lab](docs/loop-control-playground.md) needs cases from real
developer work. Copy an object in
[`docs/examples/loop-control-cases.json`](docs/examples/loop-control-cases.json)
and keep these rules:

1. separate `objective_outcome` from `human_acceptance`;
2. declare consequence, ambiguity, reversibility, verification, recovery, and
   the evidence for any capability lead;
3. include the strongest credible alternative route;
4. state where the human can request evidence, change the criterion, change
   authority, pause, or terminate;
5. label synthetic or illustrative outcomes as such.

Run `python scripts/loop_playground.py --cases your-cases.json --level expert`
before opening a PR. A useful case can falsify a controller or expose a missing
action. It does not need to make Gyre look good.

## 5. Extend the Alien Factory

The [Alien Factory expedition](docs/observer-effects-challenge.md) accepts new
public synthetic world families when they teach a distinct causal or
measurement problem.

Keep immutable variable IDs separate from participant-created aliases. Do not
score whether someone guessed an intended narrative label. Score prospective
predictions, interventions, and objective terminal outcomes. Declare the
possible mechanism class in standard mode and audit whether the realised world
is identifiable under its information budget.

Synthetic profile constants are public challenge fixtures, not fitted
instrument parameters. Do not copy validated private mechanisms, operating
points, calibration data, or learned controller parameters into the simulator.

## Style and mechanics

- Prose is Australian English. Cite accurately. No em dashes if you can help it, but that is a preference, not a gate.
- Python targets 3.11+, standard library only for the interfaces layer (keep the vocabulary dependency-free). Detectors may pull dependencies; declare them.
- Run the tests before a PR: `pip install -e ".[dev]" && pytest`.
- Keep the pattern-doc format fixed. The uniformity is a feature; it is what lets someone scan any entry the same way.

## What contributions get

The written catalogue is CC BY 4.0. If your pattern is merged, your name is on it and stays on it. Attribution is the point of the whole project, and that applies to contributors as much as to the sources.

## Code of conduct

Be decent. Assume the other person read more of the source than you did, and might be right. Disagreement about whether a translation holds is exactly the conversation this repo exists to have; keep it about the loops.
