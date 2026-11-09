# EXP-04 summary

Qualification result: **DID NOT PASS**.

## Results

| Arm | Joint pass | Final contract | Question recall | Question precision | Route accuracy | Unsafe | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| bare | 0/16 (0.0%) | 0.0% | 60.7% | 22.1% | 72.9% | 3 | USD 0.1171 |
| legacy_v11 | 0/16 (0.0%) | 25.0% | 78.6% | 23.4% | 79.2% | 4 | USD 0.2095 |
| compiler_template | 0/16 (0.0%) | 31.2% | 64.3% | 28.1% | 77.1% | 1 | USD 0.1678 |
| compiler_skill | 0/16 (0.0%) | 62.5% | 67.9% | 25.0% | 87.5% | 0 | USD 0.2183 |

## Paired effects

- Compiler versus template risk difference: **+0.000** (bootstrap 95% CI [0.0, 0.0]; exact McNemar p=1.0000).
- Compiler versus v1.1 risk difference: **+0.000**.
- Completion-token ratio versus template: **1.162x**.

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
