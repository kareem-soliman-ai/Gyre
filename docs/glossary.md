# Glossary

Terms used across the catalogue, defined once. Where a term comes from a specific literature, the source is noted so you can chase it.

**Agentic loop.** The unit of agent work: do something, check the result, decide whether to continue or stop. Structurally a TOTE unit (see below) with a large Operate step.

**Calibration.** The correspondence between stated confidence and actual accuracy. A well-calibrated agent that says "70% confident" is right about 70% of the time. Measured with proper scoring rules such as the Brier score. See [L2](../loops/L2-metacognitive-calibration.md).

**Calibration-as-property vs calibration-as-loop.** The static question (is this model's confidence well-correlated with its accuracy on a fixed benchmark) versus the dynamic one (does the agent update a running calibration model from outcomes and let it steer behaviour). Gyre is interested in the loop version. See [L2](../loops/L2-metacognitive-calibration.md).

**Control (Nelson & Narens).** Information flowing down from the meta level to the object level: the meta level changing what the object level does. Half of metacognition; the other half is monitoring.

**Dishabituation.** The return of a habituated response when the stimulus changes, even to a weaker stimulus. The tell that habituation is prediction-mismatch, not fatigue. See [L6](../loops/L6-habituation-orienting.md).

**Einstellung.** A mental set: continuing to apply a method that previously worked, past the point where it works or where a simpler method is available. From Luchins' water-jar experiments. See [L5](../loops/L5-incubation-einstellung-breaker.md).

**Habituation.** The decline of a response to a repeated stimulus, driven by a learned model of the expected stimulus rather than by exhaustion. Defined parametrically by Thompson & Spencer's nine criteria. See [L6](../loops/L6-habituation-orienting.md).

**Incubation.** The improvement in problem-solving that follows disengaging from a stuck problem, rather than pushing harder on it. Effect and its conditions established by Sio & Ormerod's meta-analysis. See [L5](../loops/L5-incubation-einstellung-breaker.md).

**Information gain.** The amount of new information a loop iteration produces relative to prior iterations. The discriminator between reflection (gain present) and rumination (gain absent). The construct is clean; the operationalisation is confounded and needs validation. See [L1](../loops/L1-rumination-vs-reflection.md).

**Human acceptance.** An explicit observation that a person accepts, prefers, or
consents to an output. It is the right criterion for preference and consent. It
is not interchangeable with objective task outcome.

**Human controller.** A person acting on a declared menu of control transitions,
such as requesting evidence, revising the criterion, changing authority,
delegating bounded work, pausing an action, or terminating a goal. A human
choice changes the route; it does not automatically label the route correct.

**Human measurement.** A scoped human observation treated as a signal with a
target construct, cues, criterion, error, confounds, confidence, and maturity.
It may earn greater decision authority through prospective comparison with
outcomes in a bounded task family.

**Instrument.** A pattern that makes a measurement claim about a latent property and therefore cannot state numbers until validated against ground truth. Method open, scoring closed. See [measurement-stance.md](measurement-stance.md).

**Latent construct.** A property you cannot observe directly and must infer from behaviour (rumination, rupture, deviation from normal). Measuring one well requires demonstrating validity and reliability, not just proposing a reasonable proxy.

**Meta-loop.** The controller that decides which loop runs now and when to switch. Roughly the explore-exploit question applied to an agent's own loops. See [L7](../loops/L7-meta-loop.md).

**Monitoring (Nelson & Narens).** Information flowing up from the object level to the meta level: the meta level building a model of how the object level is doing. Half of metacognition; the other half is control.

**Objective outcome.** A result assessed against a criterion independent of the
human or system recommendation being evaluated, such as a frozen test,
authoritative source, blinded adjudication, or delayed real-world result.
Objective does not mean infallible: the criterion still has coverage, construct,
and validity limits.

**Observer effect / observer tax.** A change caused by obtaining information,
not merely a cost charged for obtaining it. In Gyre's reactive world, an active
probe may alter the measurand, a later control mechanism, or later measurement
bias. The broader observer tax also includes spent time, probes, and future
optionality.

**Renewable negative control.** A reference measurement that targets the same
state while omitting the active probe's intervention. “Renewable” means repeated
use does not consume or progressively contaminate the reference mechanism.
Its validity is a world assumption that must be declared and tested.

**Working name / participant alias.** A revisable label attached to an
immutable phenomenon ID. It records a human-system interpretation but is not
the phenomenon's hidden true name and is never scored by vocabulary match.

**Reciprocal measured control.** Gyre's design hypothesis that human and AI
observations should both pass through scoped measurement, policy, action, and
outcome learning, while their different rights, responsibilities, and authority
remain explicit. See
[first-principles-loop-control.md](first-principles-loop-control.md).

**Reflection.** Repetitive thought that moves: each pass generates new information, reframes, or narrows. The productive twin of rumination. See [L1](../loops/L1-rumination-vs-reflection.md).

**Rumination.** Repetitive thought that circles: each pass recycles the same content and produces the affect of progress without the substance. The unproductive twin of reflection. Distinguished by information gain, not iteration count. See [L1](../loops/L1-rumination-vs-reflection.md).

**Rupture (and repair).** A breakdown in a working alliance, and the move to detect and address it. Process research found repair predicts outcomes better than rupture avoidance. Withdrawal ruptures (disengagement) are the dangerous, easily-missed kind. See [L3](../loops/L3-rupture-and-repair.md).

**TOTE.** Test, Operate, Test, Exit. Miller, Galanter & Pribram's 1960 proposal that the feedback loop, not the reflex arc, is the fundamental unit of behaviour. The ancestor of the agentic loop. See [L0](../loops/L0-tote.md).

**Zeigarnik effect.** Uncompleted tasks are remembered better than completed ones, because an unfinished intention sets up a persisting tension system that intrudes on cognition. Released by completion or, per Masicampo & Baumeister, by a concrete plan. See [L4](../loops/L4-zeigarnik-intentions-register.md).
