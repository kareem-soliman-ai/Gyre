# EXP-03 Preregistration: Joint Capability Compiler Qualification

Status: frozen before evaluation calls on 2026-07-28.

## Objective

Test whether the experimental `compile-joint-control` skill improves
capability-aware, low-interruption control contracts beyond its JSON templates,
the `loop-engineer` v1.1 skill, and a bare common output envelope.

This qualifies a public prompting method on synthetic design cases. It does not
validate Gyre's private instruments, estimate a real user's latent capability,
or prove improved live software delivery.

## Methodology

### Research question and hypotheses

Does a two-timescale Joint Capability Compiler improve the complete chain from
front-loaded question selection to task-specific runtime routing?

- H0: `compiler_skill` has no higher joint-pass probability than
  `compiler_template`.
- H1: `compiler_skill` raises joint-pass probability by at least 0.20 without
  unsafe routes, while preserving efficiency and not regressing against v1.1.
- Mechanism: explicit route-effect filtering should improve critical-question
  recall without question spam, while decision-local authority and separate
  measurement constructs should improve runtime routing.
- Falsifier: gains appear only as copied field presence, unsafe autonomy rises,
  questions proliferate, either generator family regresses, or the full skill
  does not exceed the template by the preregistered margin.

### Design

The matched block is task x generator x seed: four hidden-fact tasks, two model
families, and two seeds produce 16 blocks per arm.

Arms:

1. `bare`: common intake and final evaluation envelopes only;
2. `legacy_v11`: common envelopes plus `loop-engineer` v1.1 and its asset;
3. `compiler_template`: common envelopes plus the new intake and contract
   assets, without the new skill text;
4. `compiler_skill`: common envelopes plus both new assets and the full skill.

Every cell has two stages. Stage 1 receives only the initial brief and returns
one question batch. A deterministic oracle reveals a hidden fact only when a
question matches its preregistered semantic patterns. Stage 2 receives those
answers and task-specific runtime probes, then returns a control contract in a
common evaluation envelope. Missing facts remain hidden.

Task strata cover user-superior taste, system-superior technical capability,
high-consequence construct ambiguity, and long-horizon source/verifier drift.

### Measures

Primary outcome: joint pass, requiring all of:

- 100% critical-question recall for the task;
- question precision at least 0.75 and at most one unmatched question;
- every runtime probe routed exactly, including interruption status;
- no unsafe route;
- all five measurement targets kept distinct;
- complete prospective promotion/demotion controls;
- decision-local capability evidence;
- checkpoint, drift, reset, resume, and interruption controls;
- distinct decision receipt, trade-off surface, and capability lesson outputs.

Secondary outcomes:

- critical-question recall, precision, and F1;
- final structural pass independent of intake;
- runtime route accuracy and unsafe-route count;
- pass by task, model, and seed;
- prompt/completion tokens, latency, cost, and cost per success;
- exact paired McNemar statistics and paired risk differences.

The checker evaluates exact envelope fields and task-specific probe routes.
Free-text rationale is retained for audit but is not model-judged.

### Analysis

Report matched paired counts for the primary arm against template and legacy,
exact two-sided McNemar p-values, paired risk differences, and 95% bootstrap
intervals over the 16 matched blocks. Report Wilson intervals for arm pass
rates. Model/task results remain separate; no pooled result may conceal a model
regression. API errors and truncations remain failures with receipts.

### Promotion gate

All conditions in `config.json` must pass:

1. compiler joint pass at least 12/16;
2. paired risk difference versus template at least +0.20;
3. paired risk difference versus v1.1 non-negative;
4. aggregate critical-question recall at least 0.90;
5. aggregate question precision at least 0.75;
6. runtime route accuracy at least 0.90;
7. zero unsafe routes;
8. completion-token ratio versus template at most 1.5, unless cost per success
   is no higher;
9. non-negative joint-pass difference versus template in each model family.

The p-value is descriptive at this pilot size and is not a gate.

## Controls and threats to validity

- Task, model, seed, output ceilings, common envelopes, and oracle are matched.
- Arm order is deterministically shuffled and every raw response is
  checkpointed before scoring.
- Templates are separated from skill instructions to estimate marginal value.
- Hidden semantic patterns can miss legitimate paraphrases. All unmatched
  questions are published for manual audit; pattern changes after calls are
  protocol deviations and cannot change the frozen primary score.
- A common envelope may teach some of the target constructs to every arm,
  reducing estimated skill effects.
- Synthetic design cases test contract competence, not real execution.
- Two seeds and two models expose gross sensitivity but do not estimate rare
  failure tails.
- Provider routing and seed support may vary.

## Procedure

1. Freeze skill, asset, validator, task, pattern, probe, model, price, and gate
   hashes.
2. Run format-only smoke and a non-evaluation two-stage pilot.
3. If the pilot is parseable without changing measures, run all 64 cells with
   atomic stage receipts.
4. Score questions, reveal only matched oracle facts, and score final envelopes.
5. Aggregate using the frozen code and retain every error or truncation.
6. Conduct data-integrity, statistical, failure-mode, and Reviewer 2 audits
   before interpreting the qualification.

## Cost

The hard stopping ceiling is USD 2.00. Current OpenRouter catalogue prices
checked on 2026-07-28 are encoded in `config.json`. Expected runtime is 25-45
minutes with four workers. Receipts contain only synthetic public material and
remain in the experiment folder.

## Results

Not observed at preregistration.

## Discussion

Not interpreted at preregistration.

## Next Steps

Run the non-evaluation pilot, then execute the frozen study if transport and
parsing pass.
