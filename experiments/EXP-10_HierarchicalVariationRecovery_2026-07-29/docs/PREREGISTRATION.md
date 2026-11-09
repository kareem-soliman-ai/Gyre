# EXP-10 Hierarchical Variation Recovery

## Objective

Test one versioned repair for the sole substantive EXP-09 failure while
preserving its strong within-variant heterogeneity.

EXP-09 v2.2 passed 10 of 11 corrected gates. The variant-and-context model
explained `0.4317` of pooled effect variance, below the frozen `0.50` floor,
while stable unit identity added `0.5683` R-squared. The hierarchy therefore
made identity useful but made the public variant label less informative than
intended.

## Methodology

### Frozen repair

Create `LivingInstrumentExpeditionV221`. Relative to v2.2, change only the
between-variant base multiplier:

```text
recovered base = 1 + 1.5 * (v2.2 base - 1)
```

Do not change:

- persistent unit offsets;
- weather or load slopes;
- the one-in-four exception structure;
- ecological individuals;
- seeds, probe contexts, policies, quotas, or qualification thresholds; or
- v2.0, v2.1, or v2.2.

This increases separation between variant tendencies without reducing
within-variant spread.

### Frozen evaluation

Repeat the EXP-09 seeds `0..199`, standardised contexts, policies, metrics, and
all 11 qualification gates. The first v2.2.1 run is final for this recovery
experiment.

## Results

Pending the first frozen run.

## Discussion

This is a development-seed recovery test selected after observing EXP-09. Even
a pass is not independent confirmation and does not establish ecological
validity or improved human-AI joint capability.

## Next Steps

If the recovery passes, expose v2.2.1 as the playable hierarchical version
while keeping v2.2 and EXP-09 as runnable failure evidence.
