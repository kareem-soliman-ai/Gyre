# EXP-01 Loop Engineer Skill Qualification

## Objective

Test whether giving the same coding model Gyre's public `loop-engineer` skill
improves its design of bounded agent loops and graphs relative to a no-skill
prompt under matched model, task, sampling, token ceiling, and judging
conditions.

This is a small controlled qualification study. It can expose structural
failures and justify a larger developer evaluation. It cannot establish
population-level benefit, implementation correctness, or transfer to deployed
systems.

## Methodology

### Frozen intervention

- Skill SHA-256:
  `dd589770ce28d8a8579f07a7051467cf0a1d7e5007eed34f25de32d303d53b07`
- Manifest asset SHA-256:
  `87fd0299a1f8003e906e96d128c18d2a22c04577ae0c21e868f103d71f8ed9d5`
- Repository base commit:
  `dc0b8f0bbae108436a1b50887d4bfa36a9df5b1f`

The skill and asset must not change between generation and scoring. Any change
creates a new run rather than overwriting this one.

### Conditions

1. `no_skill`: common task and common output contract only.
2. `skill`: identical common material plus the frozen skill and manifest asset.

The common contract asks for one JSON design package but does not enumerate the
skill's preferred control fields. Both conditions use the same generator model,
temperature, maximum output, seeds, and task order randomisation.

### Held-out tasks

The three prompts in `skills/loop-engineer/references/evaluation-cases.md` are
excluded because the skill can refer to them. EXP-01 instead uses:

1. a Python CI repair loop containing flaky checks and an unavailable-service
   failure;
2. a SaaS incident-response graph with conflicting diagnoses and consequential
   deployment and communication actions;
3. an adaptive evidence-synthesis graph with redundant source families,
   fan-out cost, and a publication boundary.

These are realistic design briefs, not live deployments.

### Sampling and models

- Generator: `qwen/qwen3-coder`
- Replicates: 2 per task and condition, 12 generations total
- Generation temperature: 0.2
- Generation seeds: 101 and 202
- Maximum generation tokens: 3,500
- Blind judges:
  - `google/gemma-4-31b-it`
  - `deepseek/deepseek-v4-flash`
  - `stepfun/step-3.7-flash`
- Judge temperature: 0
- Maximum judge tokens: 1,000
- Maximum experiment spend: USD 0.50

The judges come from three model families, but they have not been qualified on
this new rubric. Panel agreement is therefore descriptive rather than ground
truth.

### Outcomes

Primary outcome: blind pairwise judge preference across six matched output
pairs. Each judge evaluates:

- task correctness;
- justified graph complexity;
- measurement and routing validity;
- safe authority and human approval;
- bounded stopping and recovery;
- implementability;
- cost awareness.

Secondary outcomes:

- axis-score difference on the same blind rubric;
- deterministic mention-level contract completeness;
- parseable JSON rate;
- generation tokens, latency, and estimated cost;
- unsafe-authority flags;
- needless-complexity flags.

The deterministic score is a surface audit, not semantic proof. It cannot be
the sole basis for promotion.

### Analysis and decision rules

Report task-level observations and aggregate descriptive statistics. With only
six matched pairs, do not report statistical significance.

The skill passes this qualification gate only if all are true:

1. at least 12 of 18 blind panel votes prefer the skill condition, with ties
   counted as non-wins;
2. the mean blind composite improves by at least 0.50 on the five-point scale;
3. no increase in judge-flagged unsafe authority;
4. parseable-output rate does not decrease;
5. the skill condition does not exceed 1.75 times the no-skill output-token cost
   unless its composite improvement is at least 0.75.

Passing qualifies a larger evaluation; it does not validate the skill.

### Ordering, blinding, and resumability

- Generation order is fixed by seed `20260728` and persisted before calls.
- Judges see `Design A` and `Design B`; condition labels are randomly swapped
  per task, replicate, and judge.
- Raw generation and judgement receipts are written immediately and never
  overwritten.
- A resumed run skips valid existing receipts.
- Skill hashes, prompts, model identifiers, usage, latency, and errors are
  retained.

## Results

Frozen before generation. Results will be written under `../results/`.

## Discussion

Frozen before generation.

## Next Steps

If the gate passes, run an implementation-bearing evaluation with independent
developers or clean-context coding agents and executable acceptance tests. If
it fails, inspect task-level failure modes before revising the skill.
