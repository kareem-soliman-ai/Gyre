# EXP-10 Hierarchical Variation Recovery

## Objective

Could stronger separation between variant tendencies make the group model
explain most effects without erasing persistent unit-level residuals?

## Methodology

Version 2.2.1 changed one quantity:

```text
base multiplier = 1 + 1.5 * (v2.2 base multiplier - 1)
```

Unit offsets, context slopes, one-in-four exceptions, ecological individuals,
seeds, policies, probe contexts, and all 11 EXP-09 gates were unchanged. The
recovery reused public development seeds after EXP-09, so it is not independent
confirmation.

The variance decomposition uses terminal revealed coefficients. Unit identity
therefore reaches an oracle R-squared of 1.0 by construction. This qualifies
the hierarchy expressed by the world, not a participant's ability to infer it
from budgeted observations.

## Results

All 11 frozen gates passed.

| Metric | EXP-09 v2.2 | EXP-10 v2.2.1 |
|---|---:|---:|
| Minimum within-variant SD | 0.0736 | 0.0736 |
| Median within-variant SD | 0.1140 | 0.1140 |
| Variant-and-context R-squared | 0.4317 | 0.6211 |
| Unit-identity incremental R-squared | 0.5683 | 0.3789 |
| Variant-model MAE improvement | 20.34% | 35.36% |
| Exception fraction | 25.00% | 25.00% |
| Ecological matched differences | 200/200 | 200/200 |
| Fixed/rotating terminal differences | 200/200 | 200/200 |

Mission outcomes also remained non-trivial:

| Policy | Accomplished | Mean score | Score SD |
|---|---:|---:|---:|
| idle | 0/200 | 0.00 | 0.00 |
| fixed-first | 79/200 | 97.24 | 3.70 |
| rotating units | 147/200 | 99.67 | 0.82 |

The rotating baseline is evidence of sensitivity to unit choice, not evidence
of optimal control. Its lower score variance may itself indicate a ceiling
among the missions it nearly completes.

## Discussion

The recovery reached the intended middle. Variant and context explain 62.11% of
pooled effect variance. Stable identity explains a further 37.89 percentage
points. A developer can therefore infer a useful majority rule, act on it, and
still benefit from tracking which particular lot, person, source, motor, or
organism is present.

The residual is structured. It persists across shifts and is exposed in the
terminal receipt. Fresh random noise would create difficulty without creating
anything learnable.

The result qualifies synthetic mechanics on reused public development seeds.
It does not establish ecological validity, real-world transfer, or improved
human-AI joint capability.

## Next Steps

Freeze unseen hierarchy profiles after controller submission, then compare
fixed, category-level adaptive, identity-level adaptive, human-only, AI-only,
and human-AI controllers under matched budgets.
