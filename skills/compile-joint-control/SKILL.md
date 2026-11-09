---
name: compile-joint-control
description: Compile or audit capability-aware human-agent loops for long-horizon work. Use when an agent should ask route-changing questions once upfront, act autonomously on reversible and verifiable work, reserve consequential or unresolved decisions for a human, explain expert work while performing it, learn which pre-outcome human and system signals predict later outcomes, compare allowed actions with explicit value and information costs, or resume across checkpoints without repeatedly disturbing the user. Also use to separate task quality, human acceptance, human capability, system capability, and joint capability before building an agent graph or controller.
---

# Joint Capability Compiler

Compile a two-timescale control system: a fast task loop follows a bounded
delegation contract, while a slower evidence loop updates capability claims,
calibration, and drift. Optimize joint human-system capability, not a universal
human-versus-system score.

## 1. Map before asking

Extract the goal, evidence of completion, consequences, reversibility,
verification, known human strengths, known system evidence, ambiguity policy,
interruption policy, learning preference, and anticipated decisions.

For each missing fact, first classify who can supply it:

- `human`: private intent, taste, authority, consequence tolerance, or judgement
  only the user can provide;
- `system_observable`: repository state, available tests, source versions,
  verifier health, or another fact the system can inspect;
- `external_unknown`: evidence neither party currently has.

Resolve `system_observable` facts through bounded preflight checks before asking
the user. Do not turn the user into a lookup tool for facts the system can
inspect. Use a conservative default or evidence-seeking action for an
`external_unknown`.

Then ask whether an unresolved human-held answer changes at least one of:

- topology or sequence;
- authority or external side effects;
- verification or stopping;
- delivery or escalation.

If it changes none, do not ask. Use a conservative, explicit default.

Copy `assets/intake-state.json` and produce one `joint-control-intake` object.
If system-observable facts remain, set `status` to `needs_preflight`, put their
checks in `preflight_checks`, execute them, and remap before asking anything.
Then ask every currently anticipatable, human-answerable, route-changing
question in the single `questions` list. State `answer_source: human`, the
affected decision, route effect, safe default, and risk of that default.

If `status` is `needs_input`, return the question batch and stop. Do not compile
the graph in the same turn. If the user already supplied the needed information,
set `status` to `ready` with empty question and preflight lists.

## 2. Compile decision-local authority

After the intake is ready, copy `assets/joint-control-contract.json`. Preserve
one record per decision family; do not infer one global capability score.

Assign the default lead from evidence:

- Keep high-consequence actions human-owned.
- Keep consequential unresolved ambiguity human- or jointly owned.
- Prefer the human when their demonstrated task-local capability is stronger.
- Let the system execute when the action is reversible, independently
  verifiable, within authority, and supported by task-local evidence.
- Permit low-consequence option generation without approval; reserve the final
  taste boundary for the human when their taste is the stronger criterion.

Human revisions are evidence about human capability only when later outcome
evidence supports the direction of the revision. System confidence is never
capability evidence by itself.

Treat a human observation the same way. Name its construct, observable report,
criterion, scope, likely error, and confounds. A human saying "this looks
right" is a raw acceptance or judgement signal. It is not objective quality
evidence unless an independent outcome criterion supports that interpretation.
Human expertise is decision-local: prefer it only inside task families where
the environment offers learnable regularities and the person has had enough
feedback to learn them.

## 3. Keep five constructs separate

Create separate signals for:

1. `task_outcome`;
2. `human_acceptance`;
3. `system_capability`;
4. `human_capability`;
5. `joint_capability`.

Predicting acceptance correctly calibrates an acceptance sensor. It does not
prove objective quality. Record measurement error, confounds, scope, and
independence for every signal.

Default maturity to `raw`. Use `calibrated` or `self-deciding` only with
prospective predictions made before outcomes, a declared criterion, observed
error, a bounded scope, sample count, and expiry. Add demotion and reset rules
for drift. A self-deciding signal may control only the boundary it was calibrated
to control.

## 4. Compile prospective signal and value

Add one `prospective_value` contract. This layer asks which information
available before the outcome predicts a declared target and whether it changes
the preferred allowed action.

Lock human and system forecasts independently before either controller sees the
other forecast or the final outcome. Record the target, horizon, probability or
distribution, observed cues, measurement error, task-family scope, likely
dependence, and leakage status. Score each source against its own target:
acceptance prediction remains separate from objective task outcome.

For every allowed action, declare the value components:

`expected objective outcome - action cost - risk + learning value`

Keep human acceptance as a separate component when it is genuinely part of the
goal. Apply safety, consent, rights, and authority boundaries before comparing
values; do not turn them into penalties that a large reward can outweigh.

Prediction does not establish an action's causal effect. Unless the action
effect is identified by randomisation, a defensible causal model, or another
declared design, label the result `predicted_value`.

Seek another observation only when its expected ability to change the best
allowed action is worth more than its measurement and delay cost. Entropy
reduction alone is not value of information.

Treat measurement as a possible intervention. Record whether asking, testing,
explaining, or verifying changes human attention or confidence, the source,
evaluator, task state, or the quality of future evidence. Price future
observation value rather than selecting on a myopic information-to-disturbance
ratio. Apply disturbance and authority caps to a declared upper uncertainty
bound, not only a point estimate.

Call an action or measurement effect causal only when a paired counterfactual,
randomisation, defensible causal model, or explicit partial-identification
argument supports it. Otherwise call it predicted disturbance or value.

Do not fuse human and system forecasts without task-local calibration and
dependence evidence. Shared context, model family, source material, or forecast
disclosure creates correlated evidence. When fusion is not earned, surface the
forecast range, disagreement, and what outcome would calibrate each party.

If every route has a poor predicted outcome, state the low absolute ceiling.
Do not make the relative winner sound good. Keep uncalibrated forecasts in
shadow mode and promote a value-aware policy only when it improves objective
outcomes against a matched baseline without increasing unsafe autonomy. Make a
fixed low-disturbance policy the primary baseline and include a negative-control
setting where measurement cannot disturb the source.

See
[`docs/predictive-signals-and-joint-value.md`](../../docs/predictive-signals-and-joint-value.md)
for the signal ledger, mathematics, leakage boundary, and evaluation design.

## 5. Compile the task loop

Use the simplest topology that can express the distinct operations and
authorities. Add a graph node only for a different operation, authority,
context, or parallel workstream.

Keep the chain explicit:

`object work -> independent signals -> policy rule -> declared action`

Reference signal, action, decision, and verification identifiers rather than
restating prose. Give the loop terminal states and positive budgets. Persist the
last verified checkpoint, prospective predictions, observed outcomes, open
decisions, and authority state.

At runtime, interrupt only for:

- a declared human decision boundary;
- unexpected consequential ambiguity;
- verifier failure or drift;
- authority, scope, or criterion change.

Routine implementation details remain autonomous when the contract allows them.
Keep control-flow pauses separate from human interruptions. On a failed check,
source drift, or stale checkpoint, first stop the affected action and let the
system diagnose, refresh state, or re-verify within a bounded recovery budget.
Notify asynchronously if useful. Interrupt the human only when recovery is
exhausted, authority must change, consequences become high, or unresolved
judgement needs the human's stronger capability. Encode both
`recover_without_interrupt_when` and `interrupt_when_recovery_fails`.

## 6. Teach without transferring every decision

Emit three separate channels when making a consequential recommendation:

- `decision_receipt`: one recommendation, its confidence, rationale,
  alternatives, and lower alternative confidences;
- `tradeoff_surface`: expected outcome of the best route, credible alternatives,
  and unresolved uncertainty;
- `capability_lesson`: the unfamiliar function demonstrated, evidence produced,
  and what the user should notice next time.

Use probabilities only when calibrated to the stated criterion. Otherwise label
confidence as an uncalibrated estimate and name what would change it.

## 7. Compile the human controller

Do not reduce the human to an accept-or-reject terminal. When a human boundary
is reached, present a bounded control menu that can change the route:

- follow the recommendation;
- choose a surfaced alternative;
- request named evidence;
- revise the success criterion;
- change the authority boundary;
- delegate a bounded action with a verifier and budget;
- pause the affected action while preserving the goal;
- terminate the whole goal with a reason.

For every option state its effect, next state, reversibility, and evidence
effect. A human choice is a control action, not proof of objective quality.
Record it separately from task outcome and acceptance. Guard against choice
architecture: do not hide an option, preselect consent, or present materially
unequal routes as though they were equivalent.

Use the same maturity ladder for human measurement:

1. `raw`: an observation or confidence report with named confounds;
2. `standardized`: compared with an explicit reference set or rubric;
3. `calibrated`: prospective confidence compared with repeated outcomes under a
   declared criterion and scope;
4. `self-deciding`: permitted to control that bounded decision family, with
   expiry and demotion rules.

Help the user climb only when it is useful: elicit predictions before outcomes,
prefer objective criteria where available, show misses as well as hits, estimate
error across repeated comparable cases, distinguish sensitivity from a cautious
or permissive response threshold, and reset capability claims after drift.
Calibration training itself is a hypothesis; verify that feedback improves
calibration rather than merely confidence.

When no decision is required, keep non-interrupting controls available:
inspect the receipt, request evidence, change the next authority boundary, take
control, pause, or terminate. Availability is not an interruption.

## 8. Validate and report

Run:

```bash
python scripts/validate.py path/to/intake-or-contract.json
```

Fix every `FAIL`. Review each `WARN`. Then report:

- the compiled authority boundary;
- questions resolved or defaults applied;
- largest unresolved measurement risk;
- next prospective prediction needed to improve calibration.

A passing contract proves structural completeness, not that the controller
outperforms its matched baseline. Use `references/evaluation-cases.md` for
forward tests and compare task outcome, unsafe autonomy, interruption burden,
calibration, cost, and joint capability under matched budgets.

## Public boundary

Ship the method, contracts, validator, and evaluation harness. Do not ship
private corpora, fitted instruments, operating thresholds, user capability
profiles, or proprietary controller parameters.
