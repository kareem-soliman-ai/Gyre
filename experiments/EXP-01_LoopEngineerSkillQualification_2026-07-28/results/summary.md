# EXP-01 Results: Loop Engineer Skill Qualification

## Objective

Compare matched agent-control designs produced with and without Gyre's public
`loop-engineer` skill. The preregistered qualification gate **DID NOT PASS**.

## Methodology

One generator model produced two replicates per condition on three held-out
design tasks. Three blind model families scored each matched pair. Deterministic
contract checks, usage, latency, and raw receipts were retained. See
`../docs/PREREGISTRATION.md` for the frozen design and decision rule.

## Results

| Measure | No skill | Skill |
|---|---:|---:|
| Parseable JSON rate | 1.000 | 1.000 |
| Mean structural mention score | 0.157 | 0.889 |
| Mean blind composite (1-5) | 3.444 | 4.190 |
| Mean completion tokens | 1010.7 | 2200.3 |
| Mean latency, seconds | 9.18 | 22.81 |
| Generation cost, USD | 0.009882 | 0.028595 |
| Unsafe-authority judge flags | 1 | 2 |
| Needless-complexity judge flags | 5 | 3 |

Blind preferences: **skill 11**, **no skill
4**, **tie 3**. Mean composite difference:
**+0.746**. Completion-token ratio:
**2.177×**. Successful
receipt cost: **USD 0.071825** (a lower
bound because failed-call usage was not retained).

| Task | Skill votes | No-skill votes | Ties | Composite difference |
|---|---:|---:|---:|---:|
| `ci_repair` | 4 | 0 | 2 | +1.024 |
| `incident_response` | 3 | 2 | 1 | +0.524 |
| `adaptive_synthesis` | 4 | 2 | 0 | +0.690 |

Preregistered gates:

- [ ] `at_least_12_of_18_skill_votes`
- [x] `composite_improvement_at_least_0_50`
- [ ] `no_increase_in_unsafe_authority`
- [x] `parseable_rate_not_lower`
- [ ] `token_tradeoff_acceptable`

## Discussion

This result is descriptive qualification evidence. A pass permits a larger
implementation-bearing evaluation; it does not validate the skill or establish
causal benefit for developers.

The blind panel changed after StepFun repeatedly returned empty content. See
`../docs/PROTOCOL_DEVIATIONS.md` before interpreting the aggregate.

Limitations:

- Three controlled design briefs are not live developer deployments.
- Only one generator model was evaluated.
- The blind judges were not independently qualified on this rubric.
- Deterministic completeness is a mention-level surface audit.
- Outputs were designed but not implemented against executable tasks.
- The skill condition necessarily used more prompt tokens.
- StepFun was replaced post hoc by GPT-5.4 Mini after repeated empty responses.
- GPT-5.4 Mini added JSON-mode enforcement after one truncated response.
- Failed-call usage was not retained, so successful-receipt cost is a lower bound.

## Next Steps

Inspect task-level judge reasons and raw designs. If the gate passed, run
clean-context agents or independent developers on executable tasks with tests,
review burden, defects, and end-to-end outcomes. If it failed, revise only after
identifying which preregistered criteria failed.
