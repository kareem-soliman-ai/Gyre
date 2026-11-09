# Living Instrument Expedition

## Play first

```bash
python scripts/hierarchical_factory.py
```

Use `--demo` for a non-interactive baseline.
The simpler v2.1 world remains available through `scripts/living_factory.py`.

## Objective

Establish a farm and factory on an alien continent before stormfall. Over
fourteen shifts, produce at least 22 food units and 22 cargo units while
keeping the crew and storm frame above their survival floors.

This is Alien Factory v2.2.1. The original
[three-variable teaching world](observer-effects-challenge.md) remains
runnable because its dominant idle/cancel exploit is useful evidence about
benchmark design.

## What the player controls

Each shift is a menu of bounded controller choices:

- allocate power to cultivation, fabrication, or shelter;
- choose a food lot, cargo unit, crew member, power source, and motor;
- make no survey, a quiet field survey, or an active instrument survey;
- repair one subsystem with finite spare parts; or
- salvage a component for three spares while permanently reducing its
  capacity.

Known inventories and quotas are printed exactly. Latent condition is
communicated through stable sigils and narrative cues such as leaf posture,
frame resonance, press rhythm, and calibration marks. The player can give
living traces revisable names, but those names never become simulator truth.

## Why both a farm and a factory?

One output alone creates a dominant strategy. Coupling food, industrial
production, crew condition, shelter, charge, repairs, weather, instruments, and
organisms forces a controller to preserve several necessary conditions at
once.

The world is still intentionally small:

```text
weather ------> shelter ------> crew ------> fabrication ------> cargo
   |               |              |
   |               +--------------+
   v
cultivation ------> food --------> crew
   ^                  |
   |                  v
living traces ----> instrument <---- active survey
   ^                  |
   +---- active survey+

salvage -> spares -> repair -> shelter/cultivation/fabricator/instrument
```

This graph is schematic. Several signs, gains, response histories, and initial
states remain hidden.

## Why a category should be useful but incomplete

Every operational family contains three public variants. Each variant contains
four stable units:

```text
operational family
  -> public variant and narrative cue
      -> four selectable units
          -> three majority responses
          -> one persistent exception
```

The terminal receipt reveals the numerical profile. Before then, the player can
learn it through repeated outcomes. The same unit behaves consistently across
shifts, although its effect still depends on weather and load.

This structure avoids two weak benchmark designs:

- if a variant label determines every response, learning the label becomes an
  answer key; and
- if every response is fresh noise, exceptions create difficulty but no
  learnable causal structure.

EXP-10 measured the middle. Variant and context explained 62.11% of pooled
effect variance. Stable unit identity explained another 37.89 percentage
points. These figures qualify the synthetic construction on reused development
seeds, not a universal variance ratio. The decomposition uses terminal revealed
profiles, so it is an oracle structural audit rather than evidence that a
participant can infer every unit within fourteen shifts.

The `motor-*` family represents motors or drive units. It does not introduce
motorcycles into the cargo graph.

## Ecological families and individuals

Every seed contains one trace family from each public orientation class and
each adaptation class:

| Construct | Candidate values |
|---|---|
| orientation | avoidance, attraction, contextual |
| adaptation | habituation, sensitisation, threshold |

The pairing is shuffled across stable IDs. Every trace family contains four
stable individuals. Three follow the family orientation and adaptation; one is
a persistent exception. Active surveys can target an individual and may change
abundance, future reactivity, instrument bias, and instrument fidelity. Quiet
surveys return only a coarse field cue but cause no synthetic ecological shift.

These are synthetic mechanism classes, not animal estimates. See
[Ecological Observer Effects](references/ecological-observer-effects.md) for
the primary-study grounding and its limits.

## Human-AI complementarity

The task creates distinct useful roles without assigning them by identity:

- a human can use narrative and world knowledge to notice that feeding,
  shelter, cultivation, maintenance, and production are jointly necessary;
- a system can track inventories, fit response histories, compare policies,
  maintain uncertainty, and execute repeated allocations consistently; and
- either party can challenge the other's model using the objective receipt.

This is a design affordance, not evidence that a dyad is superior. That claim
requires a matched human-only, AI-only, and dyad experiment on post-freeze
worlds.

## Scoring

Four hard gates remain separate:

1. crew survived;
2. shelter held;
3. food quota met; and
4. cargo quota met.

Mission score is the geometric mean of capped attainment on those four
dimensions. A zero therefore cannot be hidden by surplus elsewhere.

Three additional receipts are intentionally secondary:

- control efficiency: charge, spares, observer tax, and reversibility;
- causal recovery: submitted orientation/adaptation estimates; and
- hierarchical recovery: submitted majority weather responses and exception
  prevalence estimates, scored separately; and
- raw traces: surveys, disturbance, repairs, salvages, and revealed terminal
  state.

Leaderboard ordering should compare mission accomplishment first, then report
mission score and the non-dominated efficiency surface. High "efficiency" while
producing nothing is not success.

## Qualification results

EXP-07 v2.0 killed the idle exploit but failed its difficulty gate:
`balanced_fixed` completed 200/200 public development seeds at a capped
100/100.

EXP-08 v2.1 raised both production gates using the observed development
distribution. The fixed balanced baseline then completed 99/200 missions,
versus 74/200 for production rush and 0/200 for idle. Active survey runs
degraded mean instrument fidelity from 70.87 to 52.69 and differed from their
quiet twins on 200/200 seeds.

The preregistered EXP-08 omnibus gate still did not pass because balanced score
standard deviation was 1.45, below the arbitrary 2-point threshold. The binary
mission outcome was discriminating, but this remains a recovery result on
reused development seeds, not independent confirmation.

EXP-09 v2.2 added the full hierarchy. Ten of eleven corrected gates passed, but
variant and context explained only 43.17% of effect variance. The frozen 50%
floor failed. The design had meaningful individual differences, but category
membership was less informative than intended.

EXP-10 v2.2.1 increased only the separation between variant tendencies. It
passed all 11 recovery gates without reducing within-variant spread or changing
the one-in-four exception rate. Fixed-first completed 79/200 missions, rotating
units completed 147/200, and idle completed 0/200. Rotation is a public
baseline, not an optimality claim.

## Next Steps

- freeze new hierarchy profiles after controller submission;
- add adaptive and oracle baselines;
- compare category-level and identity-level adaptive controllers;
- qualify causal-profile recovery under the fourteen-shift budget;
- test matched human-only, AI-only, and dyad conditions; and
- preserve private policies behind the existing controller seam while
  publishing receipts and replayable public baselines.
