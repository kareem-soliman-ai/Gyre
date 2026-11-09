# EXP-04 method notes

- No task, route dimension, probe, model, seed, price, gate, or scorer changed
  after the first evaluation call.
- EXP-04 used the post-EXP-03 recovery repair and fresh tasks.
- The preregistered joint result remains 0/16 in every arm.
- The semantic-equivalence route analysis is explicitly post hoc and does not
  replace exact-route scores.
- The post-EXP-04 autonomous-preflight update was made only after the frozen run
  completed. EXP-04's manifest prevents substituting that update.
- The inherited runner prints `EXP-03 complete` in its console footer and uses
  the EXP-03 HTTP title. Paths, configuration, frozen manifest, results, and
  summary correctly identify EXP-04; the footer is a cosmetic reuse artifact.
