# EXP-08 Analysis

## Objective

Test the preregistered v2.1 production-gate recovery on the same public
development seeds.

## Methodology

The only world change was food quota `18 -> 22` and cargo quota `15 -> 22`.
Five frozen policies ran on seeds `0..199`. See the
[preregistration](../docs/PREREGISTRATION.md) and immutable
[`recovery_20260729T010829Z.json`](recovery_20260729T010829Z.json).

## Results

| Policy | Missions | Mean mission score | Score SD | Mean efficiency |
|---|---:|---:|---:|---:|
| idle | 0/200 | 0.00 | 0.00 | 97.12 |
| production rush | 74/200 | 94.50 | 3.99 | 80.95 |
| balanced fixed | 99/200 | 99.03 | 1.45 | 80.95 |
| balanced quiet | 0/200 | 76.43 | 2.91 | 96.16 |
| balanced active | 0/200 | 75.19 | 2.89 | 79.73 |

Balanced fixed passed food on 126/200 and cargo on 146/200, with both and all
safety gates passing on 99/200. It beat production rush by 12.5 percentage
points. Active surveys produced more disturbance, reduced mean instrument
fidelity from 70.87 to 52.69, and differed from quiet twins on 200/200 seeds.

Five of six aggregate gates passed. The preregistered score-SD gate failed:
1.45 observed versus 2.00 required. The omnibus qualification therefore did
not pass.

## Discussion

The recovery removed the balanced-policy ceiling in the binary mission outcome.
The remaining failure is a property of the capped continuous score, not a lack
of outcome variation. It would be post-hoc to waive the gate.

Efficiency is correctly non-objective: idle preserved the most resources but
accomplished no missions. This demonstrates why efficiency must never be
allowed to compensate for objective failure.

The reused seeds and quota selection from EXP-07 make this development
evidence. No independent challenge-validity, ecological, or human-AI
capability claim follows.

## Next Steps

Freeze a new seed/profile set and define a lexicographic ranking contract before
any participant or private-controller evaluation.

