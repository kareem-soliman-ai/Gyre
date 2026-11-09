# EXP-05B Measured-Control Rescue Mechanics Pilot

## Objective

Run one complete prospective-measurement, control, and final-submit cycle and
observe the resulting Verified Outcome Score.

## Methodology

The submission and system forecast were frozen before final evaluation. The
forecast expected 97/100 and assigned probability 0.85 to the 95-100 score
band. The controller declined a validation probe because its estimated value
was only 0.5 score points, then submitted once local contract tests passed.

The final evaluator ran seeds 2909, 3251, and 4001. Outcome-calibrated source
reliability was updated only after each score resolved. The promotion gate
received one explicitly synthetic, self-evaluated receipt.

## Results

| Metric | Result |
|---|---:|
| Mean Verified Outcome Score | 100.00 |
| Minimum / maximum seed score | 100.00 / 100.00 |
| Behavioural conformance | 55 / 55 |
| Regression preservation | 15 / 15 |
| Robustness and metamorphic | 15 / 15 |
| Recovery, replay, idempotency | 10 / 10 |
| Performance | 5 / 5 |
| Final scorer calls | 3 |
| Validation probes | 0 |
| Scoring wall time | 0.328 seconds |
| Forecast multiclass Brier score | 0.0378 |

Active human minutes and API cost were not instrumented and remain missing.
They are not recorded as zero.

After three same-family successful outcomes, the source registry's posterior
mean was 0.8 under a Beta(1,1) prior. This is descriptive only.

The controller-promotion report was **not eligible**:

- no independent matched counterfactual receipts;
- insufficient independent domains.

Joint-capability gain was not calculated because no matched human-only,
system-only, or ordinary-chat baselines exist.

## Discussion

The result proves the local mechanics can produce and score a complete
submission. It does not prove that measured control caused the score. The
candidate and scorer were built in the same session, the final seeds were
development seeds rather than externally held secrets, and the task hit the
ceiling.

The 100/100 score therefore reveals a design problem as well as successful
execution: this version is too easy to discriminate strong systems or
human-system combinations. The next version needs structural generator
variation and matched baseline attempts before the result can support a
joint-capability claim.

## Next Steps

1. Generate task instances after candidate/controller freeze under independent
   evaluator custody.
2. Add structurally interacting fault families, not merely new random values.
3. Run human-only, system-only, ordinary-chat, and measured-control conditions
   under matched budgets.
4. Report outcome and efficiency separately, then calculate paired
   joint-capability gain.

