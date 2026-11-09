# EXP-07 Living Instrument Expedition Qualification

## Objective

Determine whether a versioned Alien Factory world can require coupled
survival, food, and industrial control while making measurement interference,
instrument degradation, ecological response diversity, and repair trade-offs
discoverable rather than arbitrary.

This is a synthetic mechanics qualification. It does not estimate wildlife
behaviour, prove ecological validity, or establish that a human-AI dyad
outperforms either party alone.

## Methodology

### Design

The public development world will contain:

- a finite shift horizon and a per-shift power ceiling;
- separate food, cargo, crew, and shelter gates;
- finite charge, rations, and spare parts;
- coupled cultivation, fabrication, shelter, instrument, weather, and
  organism states;
- active and quiet surveys with different information and disturbance costs;
- instrument drift from use, weather, and biofouling;
- repair actions that consume spares;
- one-way component salvage that creates spares while permanently reducing
  capacity; and
- three stable organism IDs whose semantic roles and response profiles are
  hidden until the terminal receipt.

Organism profiles will separate response orientation from adaptation:
avoidance, attraction, or contextual orientation may combine with habituation,
sensitisation, or threshold response. These are synthetic mechanism classes
inspired by field observations, not fitted animal parameters.

Participant aliases and prose hypotheses will never alter or enter the
objective score. A separate optional causal-recovery score will compare a
pre-finish profile estimate with the revealed synthetic profile.

### Frozen policies

Run each policy on seeds `0..199`:

1. `idle`: allocate no power, make no surveys, and take no repairs;
2. `production_rush`: split all available shift power equally between
   cultivation and fabrication;
3. `balanced_fixed`: allocate cultivation, fabrication, and shelter power in a
   fixed `3:3:2` ratio;
4. `balanced_quiet`: use a `2:2:1` allocation and rotate a quiet survey across
   organism IDs; and
5. `balanced_active`: use the same `2:2:1` allocation and rotate a
   medium-intensity
   active survey across organism IDs.

Policies may reduce allocations only when remaining charge cannot fund the
frozen plan. They may not inspect terminal or hidden state.

### Outcomes

Primary engineering outcomes:

- mission-accomplishment rate;
- mean mission score;
- food- and cargo-quota pass rates;
- crew- and shelter-gate pass rates; and
- score standard deviation across seeds.

Secondary outcomes:

- final charge and spares;
- active and quiet survey counts;
- cumulative disturbance;
- minimum crew and shelter state;
- instrument fidelity; and
- salvage and repair counts.

Mission score uses a geometric mean of capped food, cargo, crew, and shelter
attainment so one dimension cannot compensate for a zero on another.
Mission accomplishment remains a separate all-gates boolean.

### Qualification gates

All mechanics gates must pass:

1. `idle` accomplishes zero missions;
2. `balanced_fixed` accomplishes at least 25% but no more than 95% of missions;
3. `balanced_fixed` accomplishes more missions than `production_rush`;
4. `balanced_active` records more disturbance than `balanced_quiet`;
5. paired active and quiet policies differ in terminal outcomes on at least
   20% of seeds;
6. `balanced_fixed` score standard deviation is at least 2 points, showing
   that initial conditions matter; and
7. the simulator contract tests demonstrate all three orientation classes,
   all three adaptation classes, active-survey reactivity, instrument drift,
   repair conservation, irreversible salvage, and score/name separation.

These gates qualify mechanics and resistance to the known idle/cancel exploit.
They do not establish that the challenge is optimally difficult.

## Results

Pending the first frozen run.

## Discussion

The first run is immutable evidence. If a gate fails, any repair will be made
in a new versioned run or documented as a protocol deviation rather than
silently overwriting the result.

## Next Steps

If mechanics pass, add a post-freeze policy submission interface and a sealed
profile set before making comparative human, AI, or dyad capability claims.
