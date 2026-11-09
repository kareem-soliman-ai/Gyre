# EXP-02 Preregistration: Loop Engineer v1.1 Qualification

Status: frozen before evaluation-task generation calls on 2026-07-28.

## Objective

Determine whether the public `loop-engineer` skill version 1.1.0 improves
machine-checkable loop/graph contracts beyond the canonical JSON template
alone, under matched model, task, seed, output budget, validator feedback, and
one repair opportunity. A third bare-contract arm estimates the template's
contribution.

This is a controlled qualification study, not evidence that the skill improves
live software delivery or that Gyre's private instruments are validated.

## Hypotheses

- Primary null: the full skill has no higher final joint pass probability than
  the template-only arm.
- Primary alternative: the skill adds usable control-design instructions beyond
  the schema and raises final joint pass probability without adding safety
  failures.
- Secondary: the template-only arm outperforms the bare output contract.
- Falsifier: any apparent gain is confined to the two tasks deliberately
  targeting EXP-01 failure classes, requires more than 1.5 times the completion
  tokens without reducing cost per success, or increases safety-critical
  failures.

## Methodology

### Design

The independent variables are arm (`bare`, `template`, `skill`), task (four),
generator family (two), and replicate seed (two). This produces 48 initial
designs. The task/model/seed tuple is the matched block.

- `bare`: task plus a concise list of required top-level manifest fields.
- `template`: the same common prompt plus the v1.1 canonical JSON asset.
- `skill`: the same common prompt, canonical asset, and v1.1 skill text.

Every arm receives the same deterministic public validator and task-specific
held-out checker after its first attempt. Failures only are returned for one
repair pass. Checks that passed are not disclosed. The final output is the last
attempt, whether or not it passes.

Two tasks target defects observed in EXP-01 (constraint enforcement,
consequential authority, and adaptive-topology controls); two transfer tasks
test correlated adjudication and privacy-state invalidation. Results are
reported separately by stratum.

### Outcomes

Primary outcome:

1. final joint pass: parseable canonical manifest, public validator pass, and
   every task-specific held-out contract check passes.

Secondary outcomes:

- first-attempt joint pass and repair conversion;
- public-validator pass and held-out-check pass separately;
- safety-critical held-out failures;
- task-constraint coverage;
- completion tokens, prompt tokens, cost, latency, nodes, and edges;
- order-swapped blind preference for full skill versus template only.

The semantic panel uses three model families not used as generators. Each judge
sees both A/B and B/A. A preference counts only when both orientations identify
the same underlying arm; disagreement is `inconsistent`, not a win. The
deterministic outcome remains primary because model judges can exhibit position
and verbosity biases.

### Analysis

For skill versus template and skill versus bare, report:

- paired joint-pass counts and risk differences;
- exact two-sided McNemar tests over discordant matched blocks;
- pass rate by task, model, seed, and targeted/transfer stratum;
- first-pass to final-pass change;
- pass@1 and two-run pass-all (`pass^2`) summaries within task/model cells;
- cost per final joint success and completion-token ratios.

No failed or truncated call is silently replaced. Retries for transient
transport errors retain failure receipts. Any model, parameter, task, checker,
or judge replacement is a protocol deviation.

### Promotion gate

Version 1.1 passes this qualification only if all are true:

1. final joint pass rate is at least 75% (12/16);
2. paired risk difference versus template is at least +0.20;
3. safety-critical final failures equal zero;
4. completion-token ratio versus template is no more than 1.5, or cost per
   joint success is no higher;
5. paired difference is non-negative on the two transfer tasks;
6. at least 60% of consistent, non-tie secondary panel preferences favour the
   skill.

The p-value is descriptive at this pilot size and is not itself a gate.

## Controls and Confounds

- Common prompts, token ceilings, feedback format, and repair count are matched.
- Task order, arm order, and blind labels are deterministically shuffled.
- Skill, asset, validator, configuration, and base commit hashes are frozen.
- Exact task requirements are visible; checker implementations are withheld
  until after generation, then published for reproducibility.
- Targeted tasks can reward repairs prompted by EXP-01. Promotion therefore
  requires no transfer-task regression and reports strata separately.
- The schema and hidden checks share public constructs. Semantic judging checks
  for coherent use, but cannot establish implementation quality.
- Two seeds per task/model cell estimate stochastic sensitivity but do not
  precisely estimate tail reliability.
- API providers may ignore seeds or route different backends.

## Procedure

1. Freeze hashes, tasks, models, prices, prompts, checks, and gates.
2. Run a non-evaluation smoke call to verify JSON transport and parsing.
3. Generate attempt 0 for all 48 cells, checkpointing every receipt.
4. Run public and held-out checks.
5. Return only failed check messages and generate at most one repair.
6. Freeze final deterministic scores.
7. Judge skill versus template in both display orders.
8. Aggregate with the preregistered rules and retain raw receipts.

## Cost and Time

The hard API stopping ceiling is USD 2.00. Expected runtime is 20–35 minutes
with bounded parallelism; every completed call is resumable. Raw receipts are
small and remain in the public experiment folder because they contain
synthetic prompts and public skill material only.

## Results

Not observed at preregistration.

## Discussion

Not interpreted at preregistration.

## Next Steps

If the gate passes, evaluate developer implementation outcomes with executable
software tasks. If it fails, diagnose task-level failures before changing the
skill; do not tune on this set and then reuse it as a promotion set.
