# EXP-09 Protocol Deviations

## 2026-07-29: catalogue-shape gate representation fix

The first frozen receipt,
`results/qualification_20260729T021625Z.json`, incorrectly reported
`five_families_are_three_by_four: false` even though its own `family_shapes`
field recorded `[3, 4]` for all five families.

Cause: the in-memory values were tuples but the gate compared them with nested
lists. The comparison was changed from `shapes == [[3, 4]]` to
`shapes == [(3, 4)]`.

No world mechanic, seed, policy, threshold, probe context, or substantive gate
changed. A corrected analysis receipt is preserved alongside the original.
The variant-model R-squared failure remains a genuine failed gate and will not
be repaired inside EXP-09 or v2.2.
