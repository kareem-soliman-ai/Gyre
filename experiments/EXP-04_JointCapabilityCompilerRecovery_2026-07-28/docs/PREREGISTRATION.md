# EXP-04 preregistration: Joint Capability Compiler recovery qualification

Status: frozen before evaluation calls on 2026-07-28.

## Objective

Re-test Candidate C after repairing its tendency to conflate a control-flow
pause with a human interruption, while replacing EXP-03's invalid intake
criterion.

## Methodology

### Hypotheses

- H0: the full compiler does not improve joint-pass probability over its
  templates.
- H1: the compiler raises paired joint pass by at least 0.20, reaches at least
  12/16, and preserves zero unsafe routes and low interruption burden.
- Falsifier: it still escalates bounded recovery to the human, asks about facts
  already specified, regresses in either model family, or needs more than the
  efficiency allowance.

### Design

The four arms, two generator families, two seeds, two-stage procedure, common
final envelope, checkpointing, and gates match EXP-03. All four tasks are fresh.
Every operational fact other than the manipulated hidden facts is explicit.

Stage 1 questions must include one `route_dimension` from the frozen list.
Critical coverage is exact equality between that field and the task's hidden
dimension. A dimension can earn credit once; duplicate questions count as
unmatched. The oracle reveals only covered dimensions. This is a deterministic
classification contract, not a semantic regex.

The final envelope adds:

- `recover_without_interrupt_when`;
- `interrupt_when_recovery_fails`.

Joint pass requires 100% task-level critical-dimension recall, at least 0.75
precision, no more than one unmatched question, all exact probe routes, both
recovery fields, and all prior structural checks.

### Outcomes and analysis

Primary and secondary outcomes, paired McNemar tests, bootstrap intervals,
Wilson intervals, efficiency calculations, model-level non-regression, and the
nine-part promotion gate are unchanged from EXP-03.

### Validity controls

- Initial briefs were audited against topology, authority, verification,
  criterion, stopping, delivery, continuity, and learning dimensions before
  freezing.
- Exact dimension labels remove regex paraphrase error but test whether models
  can self-classify route effects; a model could attach a plausible label to a
  poor question.
- Duplicate labels are penalized to prevent question spam.
- Runtime probes independently test whether the hidden answer actually changes
  control.
- The common envelope biases arm effects toward zero.
- Synthetic contracts remain non-implementation evidence.

### Cost

The hard OpenRouter ceiling is USD 2.00. Model catalogue prices were rechecked
on 2026-07-28 and are frozen in `config.json`.

## Results

Not observed at preregistration.

## Discussion

Not interpreted at preregistration.

## Next Steps

Run a non-evaluation pilot. If parseable and under the ceilings, run all 64
fresh cells without changing the task, labels, probes, or gates.
