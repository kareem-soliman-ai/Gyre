# EXP-02 Results: Loop Engineer v1.1 Qualification

## Objective

Test whether the full v1.1 skill improves executable loop/graph contracts beyond its canonical JSON template under matched generation and repair conditions.

The preregistered qualification gate **DID NOT PASS**.

## Methodology

Four new tasks crossed two generator families, two seeds, and three arms. Every arm received identical failure-only public-validator and held-out-check feedback plus at most one repair. Deterministic joint pass was primary; three blind judge families evaluated skill versus template in both display orders.

## Results

| Measure | Bare | Template | Skill |
|---|---:|---:|---:|
| Final joint pass | 0/16 | 9/16 | 11/16 |
| First-attempt joint pass | 0/16 | 2/16 | 5/16 |
| Public-validator pass rate | 0.250 | 0.750 | 0.750 |
| Held-out-check pass rate | 0.000 | 0.688 | 0.812 |
| Safety-critical failures | 26 | 2 | 0 |
| Mean completion tokens | 2763.9 | 2501.8 | 2484.8 |
| Total generation cost, USD | 0.0743 | 0.0691 | 0.0820 |

Skill versus template paired risk difference: **+0.125**; exact McNemar p = **0.5000**.
Targeted-task difference: **+0.125**; transfer-task difference: **+0.125**.
Completion-token ratio: **0.993x**.

Order-swapped consistent preferences: skill 3, template 1, tie 14, inconsistent 30, invalid 0. Skill share of decisive preferences: **0.750**.

Preregistered gates:

- [ ] `skill_joint_pass_rate`
- [ ] `paired_risk_difference`
- [x] `zero_skill_safety_failures`
- [x] `efficiency`
- [x] `nonnegative_transfer_difference`
- [x] `secondary_judge_preference`

Successful-receipt API cost: **USD 1.155875**.

## Discussion

This is controlled qualification evidence about public design contracts. It does not establish improved developer implementation outcomes, live loop behaviour, or validity of Gyre's private instruments.

Limitations:

- Synthetic design contracts were not implemented by developers.
- Two seeds per task/model cell do not precisely estimate tail reliability.
- Held-out checks operationalise authored requirements and can miss semantic defects.
- Model judges were not independently calibrated for this rubric.

## Next Steps

If the gate passed, proceed to implementation-bearing developer tasks. If it failed, diagnose task-level receipts without tuning on and reusing this promotion set.
