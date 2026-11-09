# EXP-08 Living Instrument Expedition Recovery

## Objective

Test a versioned repair for the two failed EXP-07 difficulty gates without
changing the coupled world dynamics or erasing the first result.

EXP-07 showed that the idle/cancel exploit failed and that active measurement
had ecological and instrumental consequences. It also showed a ceiling:
`balanced_fixed` completed 200/200 missions with a score of 100 on every seed.

## Methodology

### Frozen repair

Use `LivingInstrumentExpeditionV21`, which differs from v2.0 only in the fixed
production gates:

- food quota: `18 -> 22`;
- cargo quota: `15 -> 22`.

The quota values were selected from the already observed EXP-07 public
development distributions. This makes EXP-08 a recovery qualification, not an
independent confirmation. The 200 seeds remain development seeds and may not
support a generalisation claim.

Mission score remains the geometric mean of capped food, cargo, crew, and
shelter attainment. A new control-efficiency receipt reports charge reserve,
parts reserve, evidence tax, and reversibility separately. Efficiency cannot
compensate for a failed mission gate.

### Frozen policies and seeds

Use the same seeds `0..199` and the same five policies as EXP-07:

1. `idle`;
2. `production_rush` at `4:4:0`;
3. `balanced_fixed` at `3:3:2`;
4. `balanced_quiet` at `2:2:1` with rotating quiet surveys; and
5. `balanced_active` at `2:2:1` with rotating intensity-0.5 active surveys.

### Outcomes

- mission-accomplishment and individual gate-pass rates;
- mission score mean and standard deviation;
- food and cargo production;
- minimum crew and shelter state;
- active/quiet disturbance difference;
- paired active/quiet terminal difference rate; and
- control-efficiency score and its four components.

### Qualification gates

All must pass:

1. `idle` accomplishes zero missions;
2. `balanced_fixed` accomplishes 25% to 95% of missions;
3. `balanced_fixed` accomplishes more missions than `production_rush`;
4. `balanced_fixed` mission-score standard deviation is at least 2 points;
5. `balanced_active` is more disturbing than `balanced_quiet`;
6. active and quiet policies differ in terminal outcomes on at least 20% of
   paired seeds; and
7. the v2.1 contract tests pass.

## Results

Pending the first frozen run.

## Discussion

Even a passing recovery run will establish only that v2.1 escapes the observed
development ceiling. A post-freeze hidden profile set and stronger adaptive
baselines are required before competitive claims.

## Next Steps

If the gates pass, expose v2.1 through the CLI and documentation while retaining
v1 and v2.0 as runnable failure receipts.

