# EXP-02 Analysis

## Objective

Interpret the preregistered version 1.1 qualification without promoting a
failed gate or confusing synthetic contract quality with developer outcomes.

## Methodology

This analysis uses the final rescored outputs described in
`../docs/PROTOCOL_DEVIATIONS.md`. It separates observed results from
interpretation. The deterministic joint pass remains primary; order-swapped
model judgements are secondary.

## Results

| Task | Bare | Template | Skill |
|---|---:|---:|---:|
| Adaptive multi-tenant batch | 0/4 | 4/4 | 4/4 |
| Database migration | 0/4 | 0/4 | 1/4 |
| Evaluation adjudication | 0/4 | 4/4 | 4/4 |
| Privacy-sensitive onboarding | 0/4 | 1/4 | 2/4 |
| **Total** | **0/16** | **9/16** | **11/16** |

Observed:

- The skill improved final joint pass by 2/16 (+12.5 percentage points) over
  template alone. The preregistered threshold was +20 points.
- Exact McNemar p was 0.50: 3 blocks passed only with the skill and 1 passed
  only with the template.
- First-attempt joint pass was 5/16 for skill and 2/16 for template. After
  matched failure feedback, the difference narrowed from 3 to 2 successes.
- The bare arm never jointly passed, even after repair. The canonical template
  therefore supplied a large share of the package's usable structure.
- Skill completion was slightly shorter than template completion (0.993x).
  Generation cost was higher (USD 0.0820 versus USD 0.0691) because the skill
  text increased prompt tokens.
- The repaired checker found zero final skill safety failures, versus two for
  template and 26 for bare.
- Qwen produced 7/8 skill passes; DeepSeek produced 4/8. Four DeepSeek skill
  outputs hit the 3,200-token ceiling and failed the public validator.
- Database migration remained the hardest task. Final failures concentrated in
  the exact two-attempt enforcement and idempotent-ledger contract.

Secondary panel:

- Of 48 order-swapped judge blocks, only four were decisive and consistent:
  three preferred skill and one template.
- Fourteen were consistent ties and 30 changed underlying preference when
  display order was reversed.
- The literal 60% gate passed (75% of four decisive blocks), but the tiny
  decisive denominator and high order instability make this weak corroboration.

## Discussion

Evidence-supported interpretation:

1. **The template is the main public instrument.** A schema plus deterministic
   feedback moved pass rate from 0% to 56.25%. Adding the prose skill moved it
   to 68.75%.
2. **The prose is most useful before feedback.** It more than doubled
   first-attempt passes (5 versus 2), but the template arm recovered much of
   the gap after seeing the same failures.
3. **Version 1.1 improved the failure profile, not enough for promotion.**
   Relative to EXP-01, it no longer paid a completion-token penalty and its
   final outputs had no detected safety failure. It still missed the absolute
   reliability and marginal-effect gates.
4. **Compactness is model-dependent.** Qwen mostly completed the canonical
   contract; DeepSeek often exhausted the ceiling. Increasing the ceiling
   post hoc would invalidate this comparison. A future experiment should test
   a compact two-stage authoring procedure on new tasks.
5. **Bidirectional judging did its job by refusing false confidence.** The high
   inconsistency rate is evidence that an ordinary one-order judge panel would
   have been unstable, not a reason to average the directions.

Inference, not established:

- Developers may obtain most immediate value from installing the template and
  validator, with the skill acting as guidance for difficult authority,
  persistence, and measurement cases.
- A two-stage loop—first emit the minimal valid skeleton, then fill
  task-specific semantics under a field budget—may reduce truncation. This must
  be tested on a new held-out set.

Not established:

- better implemented software;
- lower review burden or fewer runtime defects;
- live loop reliability;
- validity of Gyre's private instruments;
- benefit for models, domains, or developers outside this synthetic study.

## Next Steps

1. Do not promote version 1.1 as qualified.
2. Freeze EXP-02 as a diagnostic set; do not tune on it and reuse it for
   promotion.
3. Treat the public template plus validator as the current strongest
   demonstrated developer surface.
4. Before version 1.2, prototype compact skeleton-first generation and explicit
   hard-constraint indexing on non-promotion fixtures.
5. Run the next promotion study on implementation-bearing repository tasks with
   executable tests, review burden, defects, cost, and latency.
