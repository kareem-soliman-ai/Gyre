# Predictive Signals and Joint Value in Human-AI Loops

> Compact version: [Gyre's Major Lessons](LESSONS.md). This document is the
> deeper prospective-signal, measurement-error, and value-function note.

## Objective

This note specifies how a human-AI loop can use information available **before**
the final outcome to improve a joint decision. It connects four ideas:

1. a human observation and a system observation are both fallible measurements;
2. a useful early signal must predict a later, independently declared outcome;
3. prediction quality is not the same as decision value;
4. a value-aware controller should select from a bounded action menu while
   preserving hard authority and safety constraints.

The result is a design proposal, not a qualified performance claim:

> [PLAUSIBLE] A human-AI dyad should record independent prospective forecasts,
> learn which pre-outcome signals add out-of-sample predictive value, and use
> those signals to estimate the value of allowed actions. It should then update
> both controllers from the later outcome.

## Methodology

This proposal was rebuilt with the quick first-principles procedure.

### Stage 1: challenge the attractive assumptions

Several statements that sound right are not sufficient:

- A signal can predict an outcome without being useful for choosing an action.
- A signal can carry much information while having no practical consequence.
- A confident forecast can be badly calibrated.
- Two accurate forecasters can add little joint value when their errors are
  strongly correlated.
- Human acceptance can be predictable while objective task quality remains
  poor.
- A feature discovered with final-outcome information can look predictive while
  being unusable in a live loop.

The target is therefore not "more early signals." It is **incremental,
prospective, decision-relevant signal under a declared outcome and cost model**.

### Stage 2: retain the irreducible facts

A decision requires:

- a state that is at least partly observable;
- a set of actions the current authority policy permits;
- a predictive distribution over relevant outcomes for each action;
- declared consequences, costs, and hard constraints;
- a later outcome that can test the forecast;
- an update rule that preserves misses as well as successes.

If the latent state cannot be inferred from the available observations, the
loop has an observability problem. It needs a probe, a new sensor, a more modest
claim, or a human decision. More controller sophistication cannot recover a
state that no available signal identifies.

### Stage 3: rebuild the decision

Let:

- \(s_t\) be the pre-outcome task state and context;
- \(z_t^H\) and \(z_t^A\) be human and AI signals recorded at time \(t\);
- \(a\) be one permitted action;
- \(Y\) be the independently declared outcome;
- \(U_o(Y)\) be outcome utility;
- \(C(a)\), \(R(a)\), and \(L(a)\) be action cost, risk, and learning value.

For every allowed action, the controller needs an estimate such as:

\[
Q(a \mid s_t,z_t^H,z_t^A)
=
\mathbb{E}[U_o(Y)\mid s_t,z_t^H,z_t^A,\operatorname{do}(a)]
- C(a) - R(a) + L(a)
\]

The `do(a)` notation marks an important boundary: a model that only predicts
what usually happens after an action has not necessarily estimated what the
action causes. Without randomisation, a defensible causal model, or another
identification strategy, label the result **predicted value**, not causal action
value.

Hard constraints are applied before optimisation:

\[
a^*=\arg\max_{a\in\mathcal{A}_{allowed}(s_t)} Q(a\mid s_t,z_t^H,z_t^A)
\]

Rights, consent, publication authority, and unacceptable safety risks should
not disappear into a scalar penalty that a sufficiently attractive reward can
outweigh.

The value of one more measurement is decision-theoretic:

\[
\operatorname{EVSI}(e)
=
\mathbb{E}_{e}\left[\max_a Q(a\mid s_t,e)\right]
- \max_a Q(a\mid s_t)
- C(e)-C_{delay}(e)
\]

This differs from entropy reduction. An observation is worth buying when it can
change the best decision enough to repay its measurement and delay costs.
Howard's information-value argument makes the same distinction: probabilities
without consequences do not determine the importance of information
([Howard, 1966](https://doi.org/10.1109/TSSC.1966.300074)).

### Stage 4: stress the reconstruction

The proposal should fail safely in at least these cases:

| Stress case | Required response |
|---|---|
| Human and system forecasts agree because one saw the other's answer | Treat independence as compromised; do not count two signals |
| Early feature was computed with the final outcome or future trace | Mark leakage; prohibit it from prospective control |
| Signal predicts acceptance but the decision concerns correctness | Reject the construct substitution |
| Signal is accurate overall but fails in this task family | Route by local scope; reset or demote after drift |
| Human and system rankings disagree | Surface the disagreement and expected-value range; seek information only if it can change the decision |
| Estimated value is high but action violates an authority boundary | Remove the action from the allowed set |
| All actions have poor predicted outcomes | Surface the low ceiling; do not turn relative confidence into an absolute quality claim |
| Outcome is not independently observable | Use preference, process, or consequence proxies and state the remaining uncertainty |

### Stage 5: least-wrong current answer

The least-wrong implementation is a **shadow-mode prospective signal ledger**
plus a **constrained action-value receipt**. It should learn before it acts.
Fitted fusion weights and autonomous routing should remain disabled until the
signals demonstrate out-of-sample value in a bounded task family.

## Results

### 1. The pre-outcome signal ledger

Record each candidate signal before the outcome:

| Field | Purpose |
|---|---|
| `signal_id` | Stable identifier |
| `source` | Human, system, deterministic verifier, or external source |
| `construct` | What the observation is intended to measure |
| `observed_at` | When the signal became available |
| `forecast_locked_at` | Proof it preceded the outcome and other forecasters' disclosure |
| `target_outcome` | The later criterion it predicts |
| `horizon` | Time or control distance to that outcome |
| `forecast` | Probability or distribution, not just a label |
| `measurement_error` | Known or assumed uncertainty in the signal itself |
| `scope` | Task family, user, model, verifier, and environment |
| `dependence_group` | Signals likely to share data, context, model family, or failure mode |
| `leakage_status` | Prospective-safe, retrospective-only, or unknown |
| `calibration_receipt` | Sample count, proper score, intervals, and validity period |
| `drift_state` | In-scope, suspect, or reset |

The ledger is symmetrical. A human can forecast that a code change will fail a
test; a system can forecast that the human will accept a design. Each forecast
is scored against its own target. Neither receives authority merely for being
human- or machine-generated.

### 2. Candidate signals available before an outcome

The useful candidates are task-dependent. These should begin as hypotheses:

| Source | Candidate pre-outcome signal | Likely target | Important confound |
|---|---|---|---|
| System | Independent verifier coverage and health | Objective defect escape | A stale verifier can be confidently wrong |
| System | New evidence per iteration | Recovery or completion | Lexical novelty can mimic information gain |
| System | Test trajectory and invariant coverage | Final task pass | Tests can omit the real requirement |
| System | Prediction residual or model disagreement | Hidden state or failure risk | Shared model families create common-mode error |
| System | Cost spent per verified progress unit | Futility or budget overrun | Hard tasks can look like rumination |
| System | Plan volatility and repeated reversals | Rework or unresolved ambiguity | Healthy exploration also changes plans |
| System | Distribution or source drift | Calibration failure | Drift detector may share the production feature space |
| System | Reversibility and recovery evidence | Cost of an error | Nominal reversibility can hide external consequences |
| Human | Prospective outcome probability | Objective or preference outcome | Confidence can exceed sensitivity |
| Human | Named cue and error diagnosis | Corrective value of intervention | Vague discomfort and precise diagnosis are different signals |
| Human | Task-local familiarity plus feedback history | Forecast reliability | Seniority is not task-local calibration |
| Human | Stability of the success criterion | Rework and acceptance | Preference may legitimately evolve |
| Joint | Forecast disagreement | Possible complementarity or ambiguity | Disagreement can also be random noise |
| Joint | Residual error correlation | Value of fusion | Aggregate accuracy hides shared failures |
| Joint | Improvement after one party's revision | Conditional capability | Revision and outcome are confounded without a comparator |

Response time, fluency, verbosity, and confidence may also predict outcomes, but
they are unusually easy to confound. They should not receive control authority
without task-local evidence.

### 3. What signal theory contributes

The most useful signal-theory lessons are operational:

- **Observability:** if available outputs do not identify a decision-relevant
  state, add a probe or lower the claim.
- **Innovation:** the difference between a forecast and the next observation is
  itself a signal. Persistent structured residuals suggest model
  misspecification, not merely bad luck. Kalman's original filtering framework
  explicitly propagates estimation-error covariance
  ([Kalman, 1960](https://doi.org/10.1115/1.3662552)).
- **Sequential accumulation:** weak evidence can be accumulated until a commit,
  continue, or abandon boundary is crossed. This is better than re-deciding
  from scratch at every step.
- **Change detection:** a CUSUM-like monitor can detect a sustained change in
  residuals or signal quality before a pooled calibration average notices it
  ([Page, 1954](https://doi.org/10.1093/biomet/41.1-2.100)).
- **Hysteresis and deadbands:** use separate enter and exit thresholds so noisy
  estimates do not cause route chatter.
- **Sampling and aliasing:** signals observed at the wrong cadence can make
  distinct dynamics look identical. Evaluate the observation schedule, not only
  the detector.
- **Common-mode error:** additional sensors help only when they contribute
  sufficiently independent information.
- **Matched detection:** define the expected signature of a failure before
  searching for it, while retaining open-world checks for failures outside the
  template.

Signal-to-noise ratio alone is not enough. A clean signal can be irrelevant to
the decision, while a noisy signal can be valuable if it changes the preferred
action in consequential cases.

### 4. What probability-cloud and measurement-error thinking contributes

The public [PCR replication package](https://github.com/kareem-soliman-ai/PCR-methodology)
demonstrates the relevant method boundary: when predictors are measured with
error, naive regression can attenuate or otherwise distort the estimated
relationship between a signal and an outcome. The STRATOS guidance likewise
shows that the direction and size of measurement-error bias depend on the error
model and study design
([Keogh et al., 2020](https://doi.org/10.1002/sim.8532)).

For loop engineering, this implies:

1. treat human and system signal values as noisy observations, not exact
   predictors;
2. retain per-observation uncertainty when it is defensible;
3. test conclusions across plausible measurement-error assumptions;
4. fit and evaluate by task family or regime when calibration changes;
5. separate retrospective discovery features from prospective-safe features;
6. compare error-aware estimates with the naive model and a no-signal baseline.

PCR is not automatically the right estimator. It is most relevant when a
continuous pre-outcome signal and the outcome are both measured with meaningful
error and the error model is supportable. Binary, sparse, non-comparable loop
decisions may require calibration models, hierarchical models, survival models,
or no fitted model at all.

No private estimator, fitted threshold, or dataset is required in Gyre. A
private or hosted provider can later implement an error-aware estimator behind
the public measurement seam.

### 5. How humans and systems should learn from the same loop

For a decision where both parties have relevant information:

1. Name the outcome and action menu.
2. Record the human and system forecasts independently, before either sees the
   other's probability.
3. Record the evidence and cues behind each forecast.
4. Show both forecasts, their calibration scope, and their disagreement.
5. Estimate action values only inside the permitted authority set.
6. Act, verify, and record the objective and acceptance outcomes separately.
7. Score each forecast with a proper scoring rule. Proper scores incentivise
   honest probabilistic forecasts rather than strategic confidence
   ([Gneiting and Raftery, 2007](https://doi.org/10.1198/016214506000001437)).
8. Show which cues were diagnostic, where the errors were correlated, and what
   the evidence changes for the next comparable decision.

Independent forecast locking matters because displayed AI confidence can shift
human self-confidence; outcome feedback reduces some of that alignment
([Li et al., 2025](https://arxiv.org/abs/2501.12868)). Confidence-weighted
human-machine combinations can outperform either party when confidence is
calibrated and error patterns are diverse, but adding a person or a model does
not guarantee complementarity
([Yáñez et al., 2024](https://arxiv.org/abs/2408.08083)).

The teaching receipt should answer:

- Which signal was observed?
- What later outcome did it predict?
- How much incremental predictive value did it add on held-out cases?
- Did it change the selected action?
- Was the action's expected value borne out?
- Which cues should the human or system notice next time?

### 6. Do not collapse joint value into one hidden scalar

[PLAUSIBLE] A useful default is a constrained trade-off surface with at least:

- objective outcome value;
- human acceptance when acceptance is a real goal;
- error and safety consequence;
- action, verification, delay, and interruption cost;
- reversibility and recovery value;
- capability-learning value.

Weights must be explicit. Where preferences are unresolved, show a Pareto
surface or value interval rather than manufacturing one precise score. The
system may still recommend one action, but should state whether it is:

- dominant across plausible weights;
- preferred only under declared weights;
- sensitive to one uncertain signal;
- blocked by a hard authority constraint.

### 7. Gyre's current machinery and the necessary correction

Gyre already contains:

- a marginal-value stopping rule for depleted loops;
- a UCB1 meta-controller over routing policies;
- a `ValueOfInformationProvider`.

The current VoI provider subtracts observation cost from expected entropy
reduction. That is a useful uncertainty-reduction heuristic, but it is not the
decision-theoretic EVSI defined above. Entropy and cost are expressed in
different units, and the calculation does not ask whether the observation can
change the best action or improve the declared outcome.

[PLAUSIBLE] The next public baseline should therefore:

1. preserve the existing provider as an explicitly named
   `entropy_reduction_stop` baseline;
2. add an experimental action-value provider whose utilities, costs, allowed
   actions, and forecast provenance are explicit;
3. refuse confidence-weighted fusion when calibration or dependence evidence is
   missing;
4. emit a range and disagreement receipt before it emits a fused estimate.

### 8. Add the observer tax and future-observation value

The observer-effect evidence adds one essential correction:
**measurement is sometimes an intervention**.

In a human-AI loop, asking a question consumes attention and may anchor the
human. Showing AI confidence can alter later human confidence. Repeatedly
evaluating against one judge can change the artefact being produced. A probe
may reveal information now while degrading the source, evaluator, relationship,
or evidence available later.

[PLAUSIBLE] Extend the state transition accordingly:

\[
s_{t+1}\sim P(s_{t+1}\mid s_t,a_t,e_t)
\]

where \(e_t\) is the measurement or evidence-seeking action. The dynamic action
value becomes:

\[
Q(s_t,a_t,e_t)
=
\mathbb{E}\left[
U_t-C_t-R_t-D_t+\gamma V(s_{t+1})
\right]
\]

Here \(D_t\) is measurement disturbance and \(V(s_{t+1})\) includes the value
of future observations still available after the intervention. This prevents a
controller from repeatedly choosing a locally efficient probe that damages
later evidence.

A persistent-feedback simulator pilot supplies unusually useful evidence
because its attractive ratio policy failed:

- a conservative uncertainty bound repaired an initial disturbance-cap
  violation;
- the adaptive information/disturbance ratio did not beat information-only or
  random allocation;
- fixed weak probing achieved both lower error and lower disturbance;
- even an oracle-disturbance version did not rescue the policy.

The result is simulator-tier and does not validate a Gyre controller. It does
localise a design failure: better disturbance measurement cannot rescue a
myopic policy that ignores downstream observation value.

The resulting lessons for Gyre are:

1. **Estimate observer disturbance separately from information gain.** Record
   attention burden, anchoring, source change, evaluator change, delay, and loss
   of future evidence.
2. **Use conservative budget accounting.** A point estimate near a hard cap is
   unsafe; route on an upper uncertainty bound or another declared safety
   margin.
3. **Keep information and disturbance as a frontier.** A ratio can prefer tiny,
   useless probes. Apply minimum information, coverage, horizon, and risk
   constraints before ranking feasible options.
4. **Make fixed weak the primary baseline.** Adaptive sophistication must beat a
   cheap, low-disturbance policy, not merely a no-action floor.
5. **Use an oracle-policy diagnostic.** If the policy still fails with the true
   signal, stop improving the sensor and repair the policy.
6. **Use renewable negative controls.** Where a probe cannot disturb the source,
   a disturbance-aware policy should not gain a built-in advantage.
7. **Identify the counterfactual before claiming disturbance.** Simulator twins
   with common random numbers are powerful mechanics tests. Real loops need
   randomisation, a defensible digital twin, instrumental variables, interrupted
   time series, or explicit partial-identification bounds.
8. **Freeze before the holdout.** Keep pilot data, power analysis, settings,
   source families, and holdout seeds disjoint; preserve failed runs rather than
   silently replacing them.
9. **Treat sensor federation as incremental evidence.** Correlation is only a
   rough redundancy screen. The real test is whether a new human or system
   signal adds held-out value after existing signals and shared failure modes
   are considered.
10. **Verify absence adversarially.** "No evidence was found" needs an active
    second search for contradicting evidence. A lexical search is only a
    baseline, not a qualified absence verifier.

This correction changes the proposed value-of-information rule:

\[
\operatorname{dynamic\ EVSI}(e)
=
\text{immediate decision improvement}
+ \text{future epistemic optionality}
- \text{measurement cost}
- \text{delay}
- \text{observer disturbance}
\]

Do not estimate this as one precise scalar until its components and trade-offs
are supportable. A constrained frontier and interval are the safer public
baseline.

## Discussion

The proposal changes the unit of loop engineering. The controller no longer
asks only, "Does this signal cross a threshold?" It asks:

> Given what the human and system could know before the outcome, which permitted
> action has the best expected joint consequence, and is another measurement
> worth enough to change that choice?

This also changes graph engineering. A conditional edge should carry:

```text
prospective signals
    -> scoped predictive model
    -> allowed action set
    -> measurement-disturbance and future-observation model
    -> constrained dynamic action values
    -> route
    -> independent outcome
    -> calibration and capability update
```

The graph needs separate stores for forecasts, action selection, outcome
verification, and calibration. It does not need a new agent for each store.
Add nodes only where operation, context, authority, or parallelism differs.

The evidence boundary remains strict. Predictive association qualifies a signal.
It does not qualify a controller. A controller needs evidence that its actions
improve outcomes relative to a matched baseline. Joint capability needs an
additional comparison showing that the dyad outperforms the better constituent
under a matched budget, or delivers equivalent outcomes with lower burden or
risk.

## Next Steps

1. Use the
   [Gyre Joint Capability Challenge](joint-capability-challenge.md) as the
   external outcome task and qualify its scoring instrument before evaluating a
   controller.
2. Keep all forecasts in shadow mode until a preregistered experiment qualifies
   their incremental predictive value.
3. Run a factorial experiment that independently varies:
   - no signal, raw signal, calibrated signal, and corrupted oracle signal;
   - fixed routing and value-aware routing;
   - renewable and observer-disturbing measurement environments;
   - individual human, individual system, and joint forecasts.
4. Lock forecasts before disclosure and outcome. Split evaluation by task or
   project family, not by individual decision.
5. Measure Brier or log score, calibration, discrimination, incremental
   held-out prediction, decision regret, objective outcome, acceptance,
   interruption burden, cost, unsafe autonomy, and later transfer of the
   capability lesson.
6. Include an oracle-policy cell, an unsolvable-task stratum, a verifier-drift
   stratum, a fixed-weak baseline, a renewable negative control, a
   current-versus-future observation trade-off, and an error-correlation stress
   test.
7. Promote no fitted fusion or autonomous policy unless it beats the matched
   no-value baseline on objective outcomes without increasing unsafe autonomy.

## Public and protected boundary

Ship publicly:

- the signal ledger and action-value schemas;
- the formulas and transparent baseline;
- synthetic and user-authored cases;
- leakage, dependence, and calibration checks;
- the factorial evaluation harness and failed receipts.

Keep protected:

- fitted signal weights and operating thresholds;
- private user capability profiles and interaction traces;
- proprietary outcome instruments and corpora;
- private error-aware estimator code;
- production policy parameters learned from protected data.

Open method and closed instrument still applies. The public playground should
make the reasoning inspectable; it should not publish the calibration that makes
a production controller valuable or personally revealing.
