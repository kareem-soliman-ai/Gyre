# EXP-07 Analysis

## Objective

Qualify the first coupled Living Instrument Expedition against the known idle
exploit and a ceiling/floor gate.

## Methodology

Five frozen policies ran on public development seeds `0..199`. See the
[preregistration](../docs/PREREGISTRATION.md) and immutable
[`qualification_20260729T010520Z.json`](qualification_20260729T010520Z.json).

## Results

| Policy | Missions | Mean score | Score SD | Food pass | Cargo pass |
|---|---:|---:|---:|---:|---:|
| idle | 0/200 | 0.00 | 0.00 | 0.0% | 0.0% |
| production rush | 133/200 | 96.00 | 2.70 | 100.0% | 100.0% |
| balanced fixed | 200/200 | 100.00 | 0.00 | 100.0% | 100.0% |
| balanced quiet | 0/200 | 88.21 | 3.07 | 0.0% | 18.0% |
| balanced active | 0/200 | 86.79 | 3.05 | 0.0% | 17.5% |

Four of six aggregate gates passed. The 25-95% balanced-policy gate and
2-point score-variation gate failed.

## Discussion

The fixed production quotas removed the idle/cancel exploit, but v2.0 was too
easy for a fixed balanced allocation and too expensive for the low-production
survey baselines. The result qualifies the coupled mechanics, not challenge
difficulty.

## Next Steps

Preserve this receipt and test a versioned quota recovery. Do not retune EXP-07
in place.

