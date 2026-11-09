# EXP-06 Measurement-Interference Qualification

## Objective

Test whether Gyre's reactive-measurement mechanics are empirically identifiable
and whether an interaction-derived model improves later control over a policy
that assumes measurement is passive.

## Methodology

The simulator, ten profiles, three calibration intensities, policies, seeds,
sample counts, metrics, and five qualification gates were frozen in
[the preregistration](../docs/PREREGISTRATION.md) before the run.

The profiles varied:

- interference severity from null through high;
- dominant measurement-to-measurand, measurement-to-mechanism, and
  measurement-to-future-measurement paths;
- linear, saturating, and threshold response families; and
- positive and signed mixed coefficients.

The `discovered` policy received no latent state or oracle differences. It used
observable active/reference interactions to estimate each path at three
intensities, selected a response family by least squares, and applied the fitted
profile to 400 fresh control episodes per profile. `exact_prior` received the
true profile. `passive_naive` assumed probing changed nothing.

Calibration used 60 episodes at each of three intensities. Each episode used
four readings, for 720 calibration readings per profile. Final episodes used
two active readings at intensities 0.35 and 0.85, followed by one control.
Observation-noise standard deviation was 0.03.

## Results

All five preregistered gates passed.

| Metric | Result | Gate |
|---|---:|---:|
| Non-null response families recovered | 9 / 9 | at least 8 / 9 |
| Mean coefficient absolute error | 0.003319 | at most 0.02 |
| Passive-naive aggregate terminal MSE | 0.044444 | comparator |
| Exact-prior aggregate terminal MSE | 0.000903 | lower reference |
| Discovered aggregate terminal MSE | 0.000947 | at most 1.25x exact |
| Discovered / exact MSE ratio | 1.048 | at most 1.25 |
| Discovered reduction from naive MSE | 97.87% | must improve |
| Hard cells where discovered beat naive | 8 / 8 | 8 / 8 |

The response family fitted to the null profile was saturating, but that cell
was excluded from family accuracy as preregistered: with all three
coefficients zero, the response families are observationally equivalent.

The immutable machine-readable receipt is
[`qualification_20260728T112346Z.json`](qualification_20260728T112346Z.json).

## Discussion

The result establishes a narrow but useful property: in this synthetic world,
the three kinds of measurement interference are recoverable from interactions
without disclosing their realised coefficients, and accounting for them
materially improves terminal control.

It does not establish that the challenge is already hard enough. The successful
baseline spent 720 calibration readings per profile and knew the complete
candidate family set. This is a generous identifiability qualification, not a
competitive information budget. The result therefore supports hiding the
realised mechanism while guaranteeing an empirical route to it; it does not
support hiding the very possibility of observer effects.

The exact-prior and discovered policies differ by only 4.8% in aggregate MSE.
That small gap is evidence about these frozen profiles, sample counts, and
noise level only. It is not evidence that exact priors are generally
unnecessary.

The baseline, profiles, and seeds were locally authored. There was no
independent custody, no adaptive adversary, no human participant, and no
matched human-AI comparison. No claim about real-world transfer or joint
capability follows.

## Next Steps

1. Add an information-budget track that prices active and reference probes and
   reports an efficiency frontier rather than rewarding unlimited calibration.
2. Generate profiles after controller freeze, including path-specific response
   families, delayed effects, hysteresis, partial renewability, and mechanism
   interactions.
3. Preserve exact-prior mode as a tutorial and debugging surface.
4. Make existence-only disclosure the standard fair challenge: possible paths,
   family set, and discoverability contract public; coefficients, active paths,
   curve, and severity hidden.
5. Use blind disclosure only as a labelled research-control condition.
6. Add corrupted-reference and weak-identification cells so systems must
   quantify residual ambiguity rather than always committing to one fitted
   profile.
