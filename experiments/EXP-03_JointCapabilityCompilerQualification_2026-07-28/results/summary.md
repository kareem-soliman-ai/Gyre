# EXP-03 summary

Qualification result: **DID NOT PASS**.

## Results

| Arm | Joint pass | Final contract | Question recall | Question precision | Route accuracy | Unsafe | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| bare | 0/16 (0.0%) | 12.5% | 32.1% | 9.3% | 68.8% | 0 | USD 0.1220 |
| legacy_v11 | 0/16 (0.0%) | 12.5% | 50.0% | 23.2% | 70.8% | 2 | USD 0.2235 |
| compiler_template | 0/16 (0.0%) | 18.8% | 35.7% | 26.4% | 70.8% | 0 | USD 0.2323 |
| compiler_skill | 0/16 (0.0%) | 31.2% | 42.9% | 26.1% | 70.8% | 0 | USD 0.2442 |

## Paired effects

- Compiler versus template risk difference: **+0.000** (bootstrap 95% CI [0.0, 0.0]; exact McNemar p=1.0000).
- Compiler versus v1.1 risk difference: **+0.000**.
- Completion-token ratio versus template: **0.984x**.

## Gates

- FAIL: minimum_joint_pass_rate
- FAIL: risk_difference_vs_template
- PASS: risk_difference_vs_legacy
- FAIL: critical_question_recall
- FAIL: question_precision
- FAIL: runtime_route_accuracy
- PASS: zero_unsafe_routes
- PASS: efficiency
- PASS: model_non_regression

## Limitations

- Synthetic contracts do not prove live execution quality.
- The common envelope exposes target constructs to every arm.
- Frozen regex patterns can miss legitimate paraphrases.
- Two models and two seeds do not estimate rare failure tails.
