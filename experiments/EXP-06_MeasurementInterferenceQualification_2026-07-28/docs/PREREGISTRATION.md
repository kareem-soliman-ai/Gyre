# EXP-06 Measurement-Interference Qualification

## Objective

Determine whether Gyre's public reactive-measurement world makes observer
effects difficult but discoverable, and whether recovering them improves
terminal control relative to pretending measurement is passive.

This is a mechanics and identifiability qualification. It is not evidence that
a preferred human-AI controller improves real-world outcomes.

## Methodology

Freeze the simulator, calibration procedure, profiles, seeds, policies,
metrics, and gates before inspecting the result.

### World

An active probe first reads the current latent state and may then:

1. shift the measurand;
2. change the gain through which later controls act; and
3. bias later active measurements.

Probe intensity lies in `[0, 1]`. Interference follows one of three public
candidate families: linear, saturating, or thresholded. A renewable reference
probe measures the latent state without those interventions or accumulated
active-instrument bias.

### Frozen development profiles

Ten public qualification profiles cover a null, three severities, three
dominant paths, nonlinear response curves, and signed mixed interference.
They are mechanics fixtures, not future leaderboard secrets.

### Policies

- `passive_naive`: treats every active reading as an undisturbed current state
  and assumes control gain one.
- `exact_prior`: receives the exact profile and response family.
- `discovered`: uses only active/reference calibration interactions at
  intensities 0.25, 0.5, and 1.0, fits each candidate family, and then controls
  with the estimated profile.

Calibration uses 60 independent episodes per intensity with observation noise
standard deviation 0.03. Final evaluation uses 400 new episodes per profile.
Each final episode takes two active measurements at intensities 0.35 and 0.85,
then applies one control intended to bring the latent state to zero.

### Metrics

- response-family recovery accuracy on non-null profiles;
- mean absolute error of the three full-intensity interference coefficients;
- terminal mean squared error (MSE) for each policy and profile;
- calibration probe count, reported separately from outcome.

### Qualification gates

All must pass:

1. recover at least 8 of 9 non-null response families;
2. mean coefficient absolute error at most 0.02;
3. discovered-policy aggregate terminal MSE at most 1.25 times exact-prior MSE;
4. discovered-policy aggregate terminal MSE below passive-naive MSE;
5. discovered-policy MSE below passive-naive MSE in every medium, high, or
   dominant-path profile.

The null profile is excluded from family accuracy because all response families
are observationally equivalent when every coefficient is zero.

## Results

Pending the frozen run.

## Discussion

Pending the frozen run.

## Next Steps

If the mechanics gate passes, keep the existence of possible interference
public in the standard challenge while withholding the realised path,
coefficients, and family. Use exact-prior mode for teaching and blind mode only
as a labelled research control.
