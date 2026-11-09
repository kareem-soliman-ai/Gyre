# EXP-09 Hierarchical Variation Qualification

## Objective

Test whether Living Instrument Expedition v2.2 adds useful hierarchical
heterogeneity without making public variant labels either deterministic answer
keys or meaningless decoration.

The target structure is:

```text
family tendency
  + variant tendency
  + persistent unit deviation
  + context interaction
  + measurement error
```

A variant-level causal model should explain most cases and outperform a global
mean. It should leave non-zero, repeatable within-variant residuals that can be
reduced by learning the identity of a particular lot, crew member, power unit,
drive unit, or organism.

## Methodology

### Version and preservation boundary

Implement a distinct `LivingInstrumentExpeditionV22`. Do not modify the v2.0
or v2.1 dynamics, tests, or experiment receipts. Version 2.2 may compose v2.1
but must return receipts that report its actual post-composition effects.

### Hierarchy

The public world contains five operational families:

1. food stock;
2. cargo stock;
3. crew;
4. power source; and
5. motor or drive unit.

Each family contains three public variants and each variant contains four
stable units. Public IDs and narrative cues expose the hierarchy without
publishing the latent numerical profile.

Each of the three ecological trace families contains four stable individual
organisms. Three follow the trace family's majority orientation and adaptation.
One is a persistent exception. Active and quiet observation can target an
individual, while family-level status remains available.

### Frozen synthetic construction

- Seeds: `0..199`.
- Operational families: 5.
- Variants per operational family: 3.
- Units per operational variant: 4.
- Ecological trace families: 3.
- Individuals per ecological family: 4.
- Intended exception fraction: 0.25 within every operational variant and every
  ecological family.
- Standardised probe contexts: weather `0.2, 0.5, 0.8` crossed with load
  `0.25, 0.75`.
- Mission policies: `idle`, `fixed_first`, `rotating_units`.

The unit profile is drawn once during world construction and then persists.
No unit effect is redrawn between shifts.

### Outcomes

For standardised operational probes:

- variance of realised unit effects within each public variant;
- coefficient of determination for a global-mean model;
- coefficient of determination for the known variant-and-context model;
- coefficient of determination for the unit-identity model;
- mean absolute error for global and variant models; and
- fraction of units whose weather response contradicts their variant's
  majority response.

For ecological individuals:

- family and individual counts;
- exception fraction;
- difference between matched active observations of a majority member and its
  family exception; and
- deterministic replay under the same seed and action sequence.

For mission behaviour:

- accomplishment rate and mission-score distribution for each frozen policy;
- idle-policy gate failures; and
- paired terminal differences between fixed-first and rotating-unit policies.

### Qualification gates

All must pass:

1. all five operational families contain exactly three variants with four
   units per variant;
2. every operational variant has within-variant standard deviation of at least
   `0.04` across standardised realised effects;
3. the variant-and-context model explains at least `50%` but less than `95%`
   of pooled operational effect variance;
4. adding stable unit identity improves pooled R-squared by at least `0.08`;
5. variant-and-context mean absolute error is at least `15%` lower than the
   global-mean error;
6. operational exception prevalence is between `20%` and `30%`;
7. every ecological family contains four individuals with exactly one
   persistent exception;
8. matched active observation of a majority member and exception produces a
   different signed ecological response on at least `95%` of seeds;
9. the idle policy accomplishes zero missions;
10. fixed-first and rotating-unit policies differ in at least one terminal
    production or survival measure on at least `80%` of paired seeds; and
11. v2.0, v2.1, and v2.2 contract tests all pass.

### Falsifiers

The hierarchical claim fails if a variant label explains less than half of
effect variance, if it explains nearly all variance, if unit residuals are too
small to matter, if exceptions are freshly sampled rather than persistent, or
if the added hierarchy does not change attainable mission trajectories.

### Threats to validity

- These are synthetic mechanics, not evidence about biological, industrial,
  or human populations.
- The frozen construction encodes the intended hierarchy. Qualification tests
  whether the implementation expresses that construction, not whether the
  structure emerged naturally.
- The same 200 public development seeds are visible and must not support an
  independent generalisation claim.
- R-squared depends on the frozen probe-context distribution.
- A passing mission-difference gate establishes sensitivity, not improved joint
  human-AI capability.

## Results

Pending the first frozen run.

## Discussion

Pending.

## Next Steps

Run the frozen qualification once, preserve the receipt, and document both
passing and failed gates without retuning this experiment.
