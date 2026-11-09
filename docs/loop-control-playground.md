# Loop Control Lab

The Loop Control Lab is a dependency-free playground for learning how evidence,
authority, and control actions interact. It compares two transparent teaching
policies:

- `binary-stop`: continue when the one signal passes; otherwise terminate;
- `control-menu`: recover, seek evidence, reframe, involve a human controller,
  or terminate according to the declared case.

Neither policy is a fitted instrument or a production controller.

## Quick start

```bash
python scripts/loop_playground.py --list
python scripts/loop_playground.py --case accepted-but-objectively-failing
python scripts/loop_playground.py --case verifier-drift --level builder
python scripts/loop_playground.py --case high-stakes-ambiguity --level expert
```

The default runs both policies so the value of a control menu is visible rather
than asserted.

## Choose your depth

### New to agent loops

Run the default beginner view. Read four lines:

1. what objective evidence exists;
2. what the human accepted or preferred;
3. what the loop recommends;
4. whether the human needs to be interrupted now.

Then change one field in
[`examples/loop-control-cases.json`](examples/loop-control-cases.json). Try
changing `recovery_available`, `consequence`, or `capability_lead` and rerun the
case.

### Building an agent

Use `--level builder`. It exposes:

```text
sensor -> policy inputs -> selected action -> authority -> outcome channels
```

It also shows the human controller's menu. A human can request evidence, revise
the criterion, delegate bounded authority, pause an action, or terminate the
goal. The interface is deliberately not accept-or-reject.

Use the lab to draft the case, then compile the complete graph contract with:

```bash
python skills/loop-engineer/scripts/validate_spec.py your-loop-graph-spec.json
python skills/compile-joint-control/scripts/validate.py your-joint-control-contract.json
```

Passing either validator proves structural completeness only.

### Experienced engineer or researcher

Use `--level expert` or `--json` for machine-readable case and receipt objects.
Import `gyre.control_playground.evaluate_scenario` to build a matched baseline,
or expose your policy as a callable that accepts one case and returns a complete
receipt:

```bash
python scripts/loop_playground.py \
  --case verifier-drift \
  --policy control-menu \
  --policy-plugin mypackage.my_policy:evaluate \
  --level expert
```

External receipts are checked for the separate outcome channels, human
measurement, and human control menu before they are displayed.

Do not compare policies only on their route labels. Execute them against tasks
and record:

- objective task outcome;
- human acceptance or preference;
- unsafe autonomy;
- recoveries and recovery success;
- human interruptions and time;
- prospective human and system confidence;
- calibration error by task family;
- cost, latency, and switching cost;
- joint capability change.

Freeze cases and analysis before using a result for promotion. Include healthy
repetition, unsolvable work, verifier corruption, source drift, high-consequence
ambiguity, and a case where acceptance disagrees with objective outcome.

## Included cases

| Case | Separation it demonstrates |
|---|---|
| `accepted-but-objectively-failing` | Acceptance is not task quality |
| `verifier-drift` | Stop an action without terminating the goal or interrupting the user |
| `taste-boundary` | System option generation with human final curation |
| `high-stakes-ambiguity` | Human authority floor under consequence and uncertainty |
| `verified-reversible-autonomy` | Bounded autonomy supported by verification and reversibility |

## Calibrate a human observation

Each receipt treats the current human observation as a `raw` measurement. To
make it more trustworthy in a bounded decision family:

1. **Name the target.** What is being judged: correctness, usefulness, risk,
   taste, or expected outcome?
2. **Predict before observing.** Record the decision and confidence before the
   result or AI recommendation can create hindsight.
3. **Choose the criterion.** Prefer an independent objective outcome where one
   exists. If the target is preference, use explicit preference.
4. **Retain all outcomes.** Hits, misses, false alarms, and correct rejections
   matter.
5. **Measure error.** Use calibration bands, Brier score, sensitivity, and
   response bias only when the cases are comparable.
6. **Scope the claim.** A calibrated code-review judgement is not calibrated
   medical or aesthetic judgement.
7. **Test the teaching loop.** Verify whether feedback improves later judgement;
   do not infer learning from confidence or engagement.

For a single decision, a useful card is:

```json
{
  "construct": "Will this change pass the frozen regression suite?",
  "prediction": "pass",
  "confidence": 0.7,
  "criterion": "the frozen suite result",
  "capability_scope": "small Python parser refactors",
  "confounds": ["unseen integration tests", "AI recommendation anchoring"],
  "outcome": "record after the test, not before"
}
```

A single card does not calibrate anyone. It starts a prospective record.

## Build a custom case

Copy one object from
[`examples/loop-control-cases.json`](examples/loop-control-cases.json). Keep
`objective_outcome` and `human_acceptance` as separate objects even when they
currently agree. Every case must declare consequence, ambiguity, reversibility,
independent verification, recovery availability, and the current task-local
capability lead.

Run it with:

```bash
python scripts/loop_playground.py --cases path/to/cases.json --level builder
```

## What the lab does not prove

- The included policy is not empirically optimal.
- Its confidence is explicitly uncalibrated.
- A declared `capability_lead` is an input, not a capability evaluation.
- The cases do not establish transfer to live software or human decisions.
- A human menu can still manipulate through framing, ordering, defaults, or
  missing options.
- Objective tests can still measure the wrong construct or cover too little.

The complete first-principles rationale and psychological evidence are in
[first-principles-loop-control.md](first-principles-loop-control.md).
