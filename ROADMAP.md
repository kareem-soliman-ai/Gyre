# Roadmap

Gyre ships in vertical slices. Each slice is independently useful, so the project has value even if the next slice never happens. That is deliberate: nothing here depends on momentum.

## v0.1 — The Claim (this release)

The framing and the taxonomy, shipped open.

- [x] The catalogue: eight loop patterns (L0 through L7) plus a backlog, each with source, mechanism, agent translation, signal, exit condition, and shape.
- [x] The framing essay: [loop engineering is cybernetic psychology rediscovered](docs/cybernetic-psychology.md).
- [x] The measurement stance: why the instrument layer describes its method openly and holds its validated scoring.
- [x] Interfaces: a dependency-free `LoopMonitor` protocol and vocabulary so detectors built later share one shape.
- [x] Dual license (Apache-2.0 for code, CC BY 4.0 for the catalogue).

v0.1 is complete on its own. Everything below is optional and can resume cold from this repository.

## v0.2 — The Modular Measurement Architecture (this release)

The seam that makes measurement pluggable, and the loops that run against it.

- [x] The measurement seam: `MeasurementProvider`, `Measurement` (with a calibration ladder), `Meaning`. Loops depend on the interface, never on a concrete sensor.
- [x] Loop controllers against the seam: [L1](loops/L1-rumination-vs-reflection.md) RuminationMonitor, [L2](loops/L2-metacognitive-calibration.md) CalibrationGovernor, [L5](loops/L5-incubation-einstellung-breaker.md) EinstellungBreaker, [L6](loops/L6-habituation-orienting.md) HabituationFilter.
- [x] Naive baseline sensors (diff-novelty, rolling Brier, z-score deviation), honest about being crude, so everything runs out of the box.
- [x] `gyre.bench`: score any sensor against labelled traces, head-to-head, so the value gap is runnable.
- [x] The [build-your-own-measurement guide](docs/building-measurements.md) and the gitignored proprietary provider fence.
- [x] A public [loop-and-graph engineering guide](docs/loop-and-graph-engineering.md) that treats conditional edges as sensor-plus-policy decisions and maps coordination, authority, budgets, persistence, and adaptation.
- [x] A portable [`loop-engineer` skill](skills/loop-engineer/SKILL.md), JSON design contract, and deterministic validator for developer use.
- [x] An experimental [`compile-joint-control` skill](skills/compile-joint-control/SKILL.md) for autonomous preflight, one human question batch, decision-local authority, reciprocal human control menus, calibration receipts, resumability, and low-interruption recovery.
- [x] A dependency-free [Loop Control Lab](docs/loop-control-playground.md) with beginner, builder, and expert views, editable cases, separate objective and acceptance outcomes, and transparent binary-stop versus control-menu baselines.
- [x] A [first-principles control note](docs/first-principles-loop-control.md) applying the measurement ladder to both human and system observations while preserving objective outcome tests.
- [x] A public [predictive-signal and joint-value design](docs/predictive-signals-and-joint-value.md) that distinguishes pre-outcome prediction from action value, imports measurement-error and signal-theory discipline without private instruments, and extends the experimental joint-control contract with forecast-lock, leakage, dependence, value, and hard-constraint rules.
- [x] A [Joint Capability Challenge specification](docs/joint-capability-challenge.md) for one sealed repository-rescue task family, with an independently qualified 0-100 outcome score, paired human/system/joint comparisons, limited validation probes, and separate outcome, joint-gain, and efficiency leaderboards.
- [x] A five-minute [Start Here](docs/START_HERE.md), compact [major-lessons map](docs/LESSONS.md), and task-oriented [documentation index](docs/INDEX.md) so research essays are references rather than onboarding requirements.
- [x] The narrative [Alien Factory expedition](docs/observer-effects-challenge.md): anonymous stable variable IDs, participant-owned aliases and hypotheses, reactive active scans, a renewable reference station, countermeasures, a pre-hurricane action budget, and evaluator-owned terminal scoring.
- [x] The [Living Instrument Expedition](docs/living-instrument-expedition.md):
  a coupled farm/factory world with food, cargo, crew, shelter, power,
  weather, finite repairs, irreversible salvage, degrading instruments, and
  varied reactive organisms. V2.2.1 adds three variants and four persistent
  units per operational or ecological family. Earlier versions remain runnable
  failure receipts.
- [x] A public/private [score receipt workflow](docs/contributing-a-score.md): CI-reproduced public contenders, visibly unverified private self-reports, ranking-eligibility enforcement, local private-path protection, and a specified sealed-evaluator trust class.
- [x] A repository-local [video studio](videos/README.md) with five explainer scripts, bounded NotebookLM source manifests, Alien Factory prompt/continuity assets, D-drive media custody, and generation receipts.

## v0.3 — The Instrument, on real traces

Turn the flagship into a validated sensor and run it on reality.

- [ ] A real [L1](loops/L1-rumination-vs-reflection.md) rumination sensor that models the construct (not just lexical novelty), plugged in behind the interface.
- [ ] Run it on a real agent trace of a loop going in circles; score it against the naive baseline with `gyre.bench`.
- [ ] Report the measured result honestly: what it caught that the baseline missed, what it missed, what continuing cost. No claim beyond what the traces support.
- [ ] Package the L1 monitor as a reusable Claude Code hook.
- [x] `EXP-01` Run a controlled held-out qualification of the `loop-engineer` skill (completed 2026-07-28). The gate did not pass: 11/18 blind votes favoured the skill, composite difference +0.746, unsafe-authority flags 2 versus 1, completion-token ratio 2.18.
- [ ] Evaluate the `loop-engineer` skill on real developer tasks against a no-skill baseline: contract completeness, graph complexity, unsafe authority, implementation defects, task outcome, cost, and latency.
- [x] `EXP-02` Requalify version 1.1.0 on four independent executable-contract tasks (completed 2026-07-28). The gate did not pass: skill 11/16, template 9/16, bare 0/16; +12.5 points missed the +20-point marginal gate.
- [ ] Qualify `loop-engineer` version 1.2.0 on fresh implementation-bearing tasks. Version 1.2 adds observer-effect accounting, negative-control requirements, and immutable latent IDs separated from participant aliases; EXP-02 evidence applies only to v1.1.0.
- [x] `EXP-03` Test the first Joint Capability Compiler on hidden-fact tasks (completed 2026-07-28). Retained as a failed measurement receipt: every arm hit the joint-pass floor because the critical-question criterion omitted genuine route-changing unknowns.
- [x] `EXP-04` Re-test bounded autonomous recovery with exact route dimensions (completed 2026-07-28). The gate did not pass; conditional final contracts improved to 10/16 versus 5/16 for the template with zero unsafe routes, but the intake construct still confused human-held facts with system-observable preflight.
- [ ] Evaluate the compiler on new implementation-bearing repository tasks after autonomous preflight. Measure actual task outcome, independent verification, autonomous recoveries, human interruptions, human control-menu choices, human and system prediction calibration, cost, and capability lessons. Test whether calibration teaching improves later judgement rather than merely confidence. Freeze EXP-01 through EXP-04 as diagnostic sets; do not reuse them for promotion.
- [ ] `EXP-05A` Build and qualify the Sealed Repository Rescue scoring instrument before testing a preferred controller: complete behavioural contract, independent reference model, requirement-to-test traceability, alternate-correct and adversarial-invalid implementations, mutation audit, three-reviewer fairness screen, clean container, and sealed post-freeze seeds.
- [ ] `EXP-05B` Qualify the prospective-signal and action-value layer on the sealed rescue task in shadow mode. Run human-only, system-only, ordinary-chat joint, and measured-control joint conditions; lock forecasts before disclosure and outcome; include raw, calibrated, corrupted-oracle, verifier-drift, fixed-weak, renewable negative-control, future-observation, unsolvable, and correlated-error cells; measure outcome score, paired joint-capability gain, held-out prediction, calibration, decision regret, acceptance, interruption burden, unsafe autonomy, cost, and later capability transfer. Do not fit or promote fusion on EXP-01 through EXP-04.
- [x] `EXP-05A` engineering sub-gate (2026-07-28): reference and alternate-correct implementations scored 100 on three development seeds; declared invalids scored 21.48-92.5. Public qualification remains open for independent fairness review, clean-container parity, sealed custody, and anti-tamper review.
- [x] `EXP-05B` mechanics pilot (2026-07-28): preliminary score 100/100 across three development seeds, zero validation probes, forecast Brier 0.0378. No joint-capability claim: same-session scorer/submission, ceiling saturation, and no matched constituent or ordinary-chat baselines.
- [x] `EXP-06` Qualify reactive measurement mechanics (2026-07-28): active probes can alter the measurand, later control gain, and later measurement bias. Across ten frozen profiles, interaction-only discovery recovered 9/9 identifiable response families with coefficient MAE 0.003319 and terminal MSE 0.000947 versus passive-naive 0.044444. This is synthetic mechanics evidence under a generous 720-reading calibration allowance, not a joint-capability claim.
- [x] `EXP-07` Test the first coupled Living Instrument Expedition (2026-07-29).
  Idle completed 0/200, but fixed balanced control completed 200/200 with zero
  score variation, so the difficulty gate failed.
- [x] `EXP-08` Test the versioned v2.1 production-gate recovery (2026-07-29).
  Fixed balanced control completed 99/200 versus production rush 74/200 and
  idle 0/200. Five of six gates passed; mission-score SD 1.45 missed the frozen
  2.00 threshold, so the omnibus gate did not pass.
- [x] `EXP-09` Test persistent within-variant heterogeneity (completed
  2026-07-29). Ten of eleven corrected gates passed. Variant and context
  explained 43.17% of effect variance, below the frozen 50% floor, while stable
  unit identity added 56.83 percentage points.
- [x] `EXP-10` Test the versioned v2.2.1 hierarchy recovery (completed
  2026-07-29). All 11 reused-development gates passed. Variant and context
  explained 62.11% of effect variance, stable identity added 37.89 percentage
  points, and minimum within-variant SD remained 0.0736.
- [ ] Finish the post-freeze Alien Factory challenge: freeze controllers before
  generating profiles; compare category-level and identity-level adaptive
  controllers; qualify the fourteen-shift causal-recovery task; add
  delayed effects, corrupted references, and weak-identification cells only
  when each changes a measurable decision; keep tutorial, standard, and blind
  research divisions separate.
- [ ] Build and operate the sealed score evaluator: hidden benchmark seasons, evaluator-controlled execution, committed predictions, signed receipts, public signature verification, and retrospective release of retired suites where licensing permits.
- [ ] Render AF-01, AF-02, and AF-04 after the Higgsfield connector credential is configured; review 1080p source continuity, then produce separately receipted 3840x2160 masters. Do not describe source clips as native 4K.
- [ ] Add one thin framework adapter only after the framework-neutral manifest has survived those tasks; the adapter must not move sensor or policy logic into framework-specific prompts.

## v0.4 — The Library

The full collection, with the architecture that makes it cohere.

- [ ] Remaining patterns implemented against the interface.
- [ ] The meta-loop controller ([L7](loops/L7-meta-loop.md)) as a described and validated interface, deciding which loop runs when.
- [ ] Instrument validation: the L1 and L3 scoring layers validated against labelled traces, so they can finally state a number they have earned.

## How to read this roadmap

The instruments (L1 scoring, L3) are gated behind validation on purpose. A detector does not get to make a claim until it has been checked against ground truth, so "validated instrument" sits at v0.4, not v0.2, even though a buildable version of L1 lands much earlier. The difference between the two is the difference between "here is how you would measure this" and "here is a number you should trust." See [docs/measurement-stance.md](docs/measurement-stance.md).

If nothing happens for a month, v0.1 is still a complete and useful thing. That is the design.
