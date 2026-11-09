# EXP-02 Reviewer 2 Audit

## Major concerns addressed before the run

1. **EXP-01 rewarded mentions, not valid contracts.** EXP-02 makes public and
   task-specific executable checks the primary outcome.
2. **The skill arm could not use its validator.** All arms now receive identical
   failure-only feedback and one repair opportunity.
3. **The old control used a different output shape.** All arms must return the
   canonical root manifest. Template versus skill isolates instructional value.
4. **One generator cannot establish transfer.** Two generator families and two
   seeds are crossed with every task and arm.
5. **Post-hoc tasks can overfit prior failures.** Two targeted and two transfer
   tasks are preregistered and reported separately.
6. **Model judges have order and verbosity biases.** Deterministic checks are
   primary; secondary judgements are order-swapped and count only consistent
   underlying preferences.

## Remaining objections

- Sixteen matched blocks are adequate for a qualification signal, not a narrow
  effect estimate. The exact paired test will have low power.
- Hidden checks operationalise authored requirements and may miss semantically
  unsafe designs that satisfy their surface predicates.
- No developer implements the graph, so task success, defect burden, review
  burden, and runtime loop behaviour remain untested.
- The `template` baseline is unusually strong. That is deliberate for isolating
  the marginal value of skill instructions, but it may understate value versus
  ordinary prompting.
- The experiment is designed by the skill's maintainers. Raw receipts, frozen
  checks, explicit deviations, and a future external replication remain
  necessary.

## Verdict before data

Proceed as a qualification experiment. Do not call a pass product validation,
developer evidence, or proof of proprietary instruments.
