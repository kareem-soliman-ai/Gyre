# Gyre

**A runnable playground for engineering agent loops, measurements, controllers,
and human-AI coordination.**

Gyre begins with a simple separation:

> A loop is a controller. A measurement is a sensor. A graph is made of
> decisions whose edges contain both.

It then adds the complication that makes real systems difficult: observing, testing, asking, or verifying may change the object being measured.

## Try it in five minutes

Python 3.11 or later is required. No API key or external service is needed.

```bash
git clone https://github.com/kareem-soliman-ai/Gyre.git
cd Gyre
python -m pip install -e .
python scripts/hierarchical_factory.py --demo
```

You are establishing a farm and factory on an uncharted continent before
stormfall. Food, cargo, shelter, crew condition, energy, repairs, weather,
instruments, and living traces interact. Food beds, cargo types, crew, power
sources, motors, and organisms vary both between public variants and within
them. The rotating-unit baseline succeeds on 147/200 reused public development
seeds, so the demo is a starting point rather than an answer.

The simulator keeps identity, interpretation, and outcome separate:

```text
immutable ID -> trace-17
your alias   -> "possible night pollinator"
your model   -> "active scans reduce later visits" (confidence 0.65)
criterion    -> production, survival, and what happens after the next survey
```

Names are never scored. Mission gates, efficiency, causal recovery, observer
disturbance, and resource use remain separate.

For the interactive controller menu:

```bash
python scripts/hierarchical_factory.py
```

The simpler v2.1 expedition remains available at
`python scripts/living_factory.py`.
The original three-variable observer-effect tutorial remains available at
`python scripts/alien_factory.py`.

Full five-minute guide: [docs/START_HERE.md](docs/START_HERE.md).

## What Gyre is trying to teach

1. A useful loop needs a controlled variable, observation, sensor, policy, action menu, terminal states, and budget.
2. Measurement quality, policy quality, and final outcome are different links and can fail independently.
3. Pooled scores and plausible labels can hide the failure that matters.
4. Measurement does not always pay; compare strong blind and fixed baselines.
5. A measurement can disturb the measurand, later controls, or later evidence.
6. Human and AI judgements are scoped measurements, not automatic truth.
7. Human acceptance and objective outcome must remain separate.
8. Human-system capability is shown by matched outcomes, not by a persuasive collaboration trace.
9. Participant-created names are hypotheses, not benchmark answer keys.
10. Public methods and protected candidate instruments can coexist behind a clean interface.

Read the compact [major-lessons map](docs/LESSONS.md), then follow only the links relevant to you.

## Three ways to use the repository

| If you want to… | Start here |
|---|---|
| Play the hierarchical farm/factory expedition | `python scripts/hierarchical_factory.py` |
| Play the simpler v2.1 expedition | `python scripts/living_factory.py` |
| Learn the smallest observer-effect mechanic | `python scripts/alien_factory.py` |
| See evidence contradict an intuitive prediction | `python -m gyre.lessons` |
| Explore human/system control choices | `python scripts/loop_playground.py --list` |
| Browse psychology-derived loop patterns | [Loop catalogue](loops/INDEX.md) |
| Build and compare a measurement | [Build Your Own Measurement](docs/building-measurements.md) |
| Design an agent loop or graph | [`loop-engineer` skill](skills/loop-engineer/SKILL.md) |
| Make an explainer or Alien Factory promo | [Video studio](videos/README.md) |
| Inspect experiments, including failed gates | [Experiment index](experiments/INDEX.md) |
| Find deeper research notes | [Documentation map](docs/INDEX.md) |

## The architecture

Gyre keeps four concerns separable:

```text
world/state
    -> observation
    -> measurement provider
    -> controller or graph policy
    -> declared action
    -> independent outcome
```

When observation is reactive, the measurement node also has explicit causal edges back into world state, mechanism state, or instrument state.

Public loops depend on the `MeasurementProvider` interface, never a particular sensor. Hold the controller constant and compare sensors; hold the sensor
constant and compare controllers. See [architecture.md](docs/architecture.md).

## What ships openly

- eight psychology-grounded loop patterns;
- measurement and loop interfaces;
- naive sensors and strong public baselines;
- benchmark and claims-verification machinery;
- the Alien Factory v1 tutorial, hierarchical Living Instrument Expedition, and Loop Control Lab;
- framework-neutral loop/graph design contracts;
- experiment preregistrations, receipts, nulls, and failed gates.

What does not ship: private corpora, fitted operating points, user capability
profiles, protected instrument implementations, or learned controller
parameters. Protection is an IP boundary, not a validation claim.
The method remains replaceable and testable without exposing those assets.

## Evidence status

The repository does not treat “implemented” as “validated.”

- The public loop-design skills remain experimental; their qualification gates did not pass.
- The Sealed Repository Rescue scorer passed an engineering sub-gate, while independent public benchmark gates remain open.
- EXP-06 qualified the local observer-effect mechanics and generous-budget discoverability.
- EXP-07 killed the idle exploit but exposed a 200/200 balanced-policy ceiling.
- EXP-08 v2.1 reduced that baseline to 99/200, but its preregistered omnibus
  gate still did not pass because score variation missed the frozen threshold.
- EXP-09 added persistent within-variant heterogeneity but failed its
  variant-model gate: category and context explained 43.17% of effect variance.
- EXP-10 v2.2.1 passed all 11 recovery gates on reused development seeds:
  category and context explained 62.11%, while stable unit identity added
  37.89 percentage points. This is a mechanics result, not independent
  confirmation.
- The protected development candidate currently leads the stated synthetic
  sensor ranking, but its operating point was selected on those same public
  corpora. The scoreboard marks it as a maintainer-reported development result,
  not a holdout or transfer result.
- Post-freeze adaptive Alien Factory qualification and real-world
  joint-capability claims remain open.

Run `python scripts/challenge.py` to reproduce every public entry. Public
contenders can submit CI-reproducible receipts; private contenders can publish
scores without publishing machinery, but those rows remain visibly
self-reported and outside the verified ranking. See the
[score submission guide](docs/contributing-a-score.md) and
[verification model](docs/score-verification.md).

See [experiments/INDEX.md](experiments/INDEX.md) for exact results and
boundaries.

## Contributing

Contributions can add loop patterns, challenge the public sensors, improve teaching worlds, or supply stronger falsifiers. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

The question behind the project is practical: which measurements and control structures help agents produce better independently verified outcomes, and under what conditions do they fail?

## Credit and licence

Gyre translates work from psychology, psychometrics, cybernetics, control theory, and current agent engineering. The deeper lineage and translation
limits are documented in the [loop catalogue](loops/INDEX.md) and [Cybernetic Psychology](docs/cybernetic-psychology.md).

The project is built with AI collaboration; framing and interpretive decisions remain the maintainer's.

Code is Apache-2.0. Written catalogue material is CC BY 4.0. See
[LICENSE](LICENSE) and [LICENSE-docs](LICENSE-docs).
