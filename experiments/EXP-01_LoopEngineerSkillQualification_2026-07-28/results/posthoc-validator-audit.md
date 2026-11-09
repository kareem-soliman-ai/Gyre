# EXP-01 Post-hoc Validator Audit

## Objective

Could the generated manifests pass the validator that the skill tells a coding
agent to run?

## Methodology

The inner `manifest` from each of the 12 frozen generation receipts was passed
unchanged to `skills/loop-engineer/scripts/validate_spec.py`. This audit was
specified after the primary results were known, so it is diagnostic rather than
a preregistered outcome.

## Results

All 12 inner manifests failed. The common experiment response contract required
`prompts` outside `manifest`, while the validator requires
`prompt_contracts` inside the manifest. That evaluation-wrapper mismatch
invalidates the all-condition pass rate as a measure of skill benefit.

One failure contained additional substantive defects. The skill-condition
incident-response design at seed 202:

- set `human_approval: false` on two nodes it labelled high consequence;
- explicitly admitted that high-consequence actions lacked oversight;
- emitted the noncanonical maturity value `standardised`, copied from the skill
  prose, while the validator accepted only `standardized`.

The skill-condition evidence-synthesis design at seed 202 also labelled its
coverage sensor `calibrated` without supplying calibration evidence and omitted
the brief's 90,000-token and four-worker limits from enforceable budget fields.

## Discussion

The validator caught the incident-response authority contradiction. The
behavioural harness did not make validator execution available to the generator,
so EXP-01 tested the skill as prompt context rather than the complete
skill-plus-tool workflow. The prompt-location and spelling mismatches are skill
package defects. The missing approval and unearned calibration label are
behavioural failures that require stronger structural gates.

## Next Steps

Version the skill and validator together. Put prompt contracts inside the
machine-checkable spec, add a task-constraint ledger, require evidence for a
`calibrated` maturity label, and keep the next behavioural run independent of
these three tasks.
