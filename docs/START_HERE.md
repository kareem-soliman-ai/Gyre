# Start Here: Five Minutes to Gyre

Gyre teaches one practical idea:

> An agent loop is a controller. Every decision it makes depends on a
> measurement, and obtaining that measurement may itself change the world.

You do not need an API key, model download, database, or web service.

## Minute 0-1: install

Gyre requires Python 3.11 or later.

```bash
git clone https://github.com/kareem-soliman-ai/Gyre.git
cd Gyre
python -m pip install -e .
```

## Minute 1-3: enter the expedition

```bash
python scripts/hierarchical_factory.py --demo
```

You are establishing a sheltered farm and factory before stormfall. Fourteen
shifts remain. You need 22 food units, 22 cargo units, a surviving crew, and a
standing storm frame.

The demo rotates through stable food lots, cargo units, crew members, power
sources, and motors while holding its allocation at `3:3:2`. Watch the exact
inventories, production totals, weather, and terminal hierarchy receipt.
Across 200 reused public development seeds this baseline completed 147
missions, so it is useful but not sufficient.

Run the interactive menu when you are ready:

```bash
python scripts/hierarchical_factory.py
```

Use `catalog` to see three public variants per operational family and four
stable units inside every variant. Three units follow their variant's majority
weather response; one is a persistent exception. The three living trace
families use the same four-individual structure.

Useful commands:

```text
status
catalog
use power source-42/b
quiet trace-17/a 2 2 1
active trace-17/a 0.5 2 2 1
estimate-variant source-42 increases 0.25 0.70
repair instrument 1
finish
```

The simpler v2.1 expedition, including participant-created trace names and
hypotheses, remains runnable:

```bash
python scripts/living_factory.py
```

The smaller v1 observer-effect tutorial is still runnable:

```bash
python scripts/alien_factory.py --demo
```

## Minute 3-4: notice what is being taught

The expedition separates:

- an immutable variable ID from your revisable name for it;
- an observation from the hidden state it imperfectly represents;
- an active scan from a causally quiet reference observation;
- information gained from disturbance caused;
- a useful group-level causal rule from the stable exceptions it does not
  explain;
- the controller's decision from the objective terminal outcome; and
- mission accomplishment from control efficiency and causal recovery.

Your names are never scored. They are working hypotheses. The evaluator scores what happened after your interventions.

## Minute 4-5: run one evidence lesson

```bash
python -m gyre.lessons
python -m gyre.lessons 1
```

The executable lessons ask you to predict before showing a repository result. For the complete compact synthesis, read [LESSONS.md](LESSONS.md).

## Choose your next path

| Goal | Next step |
|---|---|
| Understand the project | [Major lessons](LESSONS.md) |
| Explore loop-control cases | `python scripts/loop_playground.py --list` |
| Browse the psychology-derived patterns | [Loop catalogue](../loops/INDEX.md) |
| Build or compare a sensor | [Build Your Own Measurement](building-measurements.md) |
| Design an agent loop or graph | [`loop-engineer` skill](../skills/loop-engineer/SKILL.md) |
| Play the coupled challenge | [Living Instrument Expedition](living-instrument-expedition.md) |
| Study the smallest observer-effect mechanic | [Alien Factory v1](observer-effects-challenge.md) |
| Inspect evidence and failed gates | [Experiment index](../experiments/INDEX.md) |
| Find every deeper document | [Documentation index](INDEX.md) |

## Evidence boundary

The expedition is a synthetic teaching world. It demonstrates mechanics and supports objective scoring; it does not prove that a particular controller,
human-AI arrangement, or measurement transfers to real deployments.

Gyre publishes baseline code, experiment receipts, failed gates, and methods.
Protected instrument implementations, fitted operating points, private corpora,
and learned controller parameters remain outside the public repository.
Protection is an IP boundary, not evidence of validity.
