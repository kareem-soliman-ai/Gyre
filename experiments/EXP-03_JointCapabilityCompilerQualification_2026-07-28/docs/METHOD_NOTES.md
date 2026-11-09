# EXP-03 method notes

- No task, pattern, model, seed, price, gate, or scorer was changed after the
  first evaluation call.
- The preregistered primary result remains 0/16 joint passes in every arm.
- The post-run `diagnostics.json` is explicitly secondary and does not replace
  the frozen score.
- Manual inspection identified an incomplete critical-question criterion and
  regex false negatives. These are measurement failures, not protocol
  deviations.
- Candidate C was updated only after EXP-03 completed. The frozen manifest
  prevents the updated skill from being substituted into EXP-03.
- EXP-03 is retained as a diagnostic pilot and must not be reused as a fresh
  promotion set.
