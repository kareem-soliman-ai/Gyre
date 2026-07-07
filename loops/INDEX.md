# Loop Catalogue

Each loop is one pattern. The format is fixed so you can scan any entry the same way:

> **Source** → **Mechanism** → **Agent translation** → **Signal** → **Exit condition** → **Shape** → **Effort/maturity**

- **Source** is the psychology or cybernetics. Cited, not reproduced.
- **Mechanism** is what the loop does in a mind.
- **Agent translation** is what it does in an agent, and where the analogy breaks.
- **Signal** is how you would measure loop quality from behaviour. This is the hard part.
- **Exit condition** is when the loop should stop, escalate, or switch.
- **Shape** is where it fits: hook, monitor, wrapper, memory layer, controller.
- **Maturity** flags whether the pattern is framing, buildable now, or an instrument that needs validation before it can claim anything.

## Maturity legend

- **Framing** — an idea and a naming, no code expected. Read it, argue with it.
- **Buildable** — a working version is a small job. The shape is prescriptive enough to implement from the doc.
- **Instrument** — this measures a latent property and cannot make claims until it has been validated on real traces. Method open, scoring closed. See [docs/measurement-stance.md](../docs/measurement-stance.md).

## The catalogue

| # | Loop | Maturity | One line |
|---|------|----------|----------|
| [L0](L0-tote.md) | TOTE | Framing | The loop as the unit of behaviour. The historical claim that frames everything else. |
| [L1](L1-rumination-vs-reflection.md) | Rumination vs Reflection | Buildable → Instrument | Same iteration, opposite outcome. Does each pass generate information or recycle it? |
| [L2](L2-metacognitive-calibration.md) | Metacognitive Calibration | Buildable | State confidence, check it against outcomes, let the running calibration steer behaviour. |
| [L3](L3-rupture-and-repair.md) | Rupture and Repair | Instrument | Detect when the human-agent alliance has ruptured, then repair instead of ploughing on. |
| [L4](L4-zeigarnik-intentions-register.md) | Zeigarnik Intentions Register | Buildable | Unfinished intentions stay active and resurface at relevant moments, then genuinely release. |
| [L5](L5-incubation-einstellung-breaker.md) | Incubation / Einstellung Breaker | Buildable | On fixation, disengage deliberately instead of trying harder, then return with attention reset. |
| [L6](L6-habituation-orienting.md) | Habituation / Orienting | Buildable | Attend to change, habituate to repetition, fire only on deviation from a learned baseline. |
| [L7](L7-meta-loop.md) | The Meta-Loop | Framing → Controller | Which loop runs now, and when to switch modes. The layer that makes this a library. |

Plus the [backlog](backlog.md): loops sketched in one line each, not yet built, open for anyone to develop.

## How to read maturity honestly

A pattern marked **Instrument** is making a measurement claim, and measurement claims are where good intentions go to die quietly. A rumination detector that fires on healthy iteration, or stays silent through genuine rumination, is not a neutral failure. It trains you to trust a number that is lying. So the instruments here describe their method in full and hold their scoring internals and thresholds back until they have been validated against real agent behaviour, not because the method is secret but because an unvalidated detector should not be handed a confident voice. If you want the reasoning in full, [docs/measurement-stance.md](../docs/measurement-stance.md) lays it out.
