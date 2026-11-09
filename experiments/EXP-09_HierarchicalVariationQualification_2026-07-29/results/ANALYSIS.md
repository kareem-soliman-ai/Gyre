# EXP-09 Hierarchical Variation Qualification

## Objective

Could a public variant label remain causally useful while stable units inside
that variant behaved differently?

## Methodology

Version 2.2 added five operational families, three variants per family, and
four persistent units per variant. Three units followed each variant's majority
weather response and one was a fixed exception. Each ecological trace also
contained four individuals with the same three-to-one structure.

The frozen harness evaluated 72,000 standardised unit-context rows across seeds
`0..199`, matched ecological interventions, three mission policies, and the
v2.0 through v2.2 contract tests.

The R-squared values are a terminal latent-profile decomposition. The unit
model receives the revealed unit coefficients and is therefore an oracle
ceiling, not a learned predictor. EXP-09 tests whether the synthetic world
contains the intended hierarchy. It does not test whether a participant can
recover that hierarchy within fourteen shifts.

The first receipt contained an analysis bug: a tuple/list mismatch falsely
failed the catalogue-shape gate. The corrected receipt changed no mechanic,
seed, threshold, or substantive result. Both receipts remain in this folder and
the correction is recorded in `docs/PROTOCOL_DEVIATIONS.md`.

## Results

| Metric | Result | Frozen gate |
|---|---:|---:|
| Minimum within-variant SD | 0.0736 | at least 0.04 |
| Variant-and-context R-squared | 0.4317 | 0.50 to less than 0.95 |
| Unit-identity incremental R-squared | 0.5683 | at least 0.08 |
| Variant-model MAE improvement | 20.34% | at least 15% |
| Operational exception fraction | 25.00% | 20% to 30% |
| Ecological signed-response difference | 200/200 | at least 190/200 |
| Fixed/rotating terminal difference | 200/200 | at least 160/200 |
| Contract tests | 22 passed | pass |

The corrected omnibus result was 10 of 11 gates. Qualification did not pass.

The idle policy completed 0/200 missions. Fixed-first completed 81/200 and
rotating units completed 131/200. These policy figures show that unit choice
affected the terminal task, but they do not establish that rotation is optimal.

## Discussion

The first design created meaningful and persistent within-variant variance. It
made the public label too weak under the preregistered variance criterion.
Variant membership reduced MAE by 20.34% relative to a global mean and correctly
described three of four units, yet explained only 43.17% of pooled effect
variance.

This is a useful failed boundary. Maximising heterogeneity without preserving
enough between-variant separation turns a category into a weak hint. The player
then has little reason to learn the causal logic before memorising individuals.

These are synthetic development-seed mechanics. They support no biological
claim and no claim that a human-AI dyad performs better.

## Next Steps

Test one versioned recovery that increases between-variant separation without
reducing unit offsets, exception prevalence, or ecological heterogeneity.
