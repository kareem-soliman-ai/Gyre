# L1 — Rumination vs Reflection

*The flagship. Build this first.*

**Maturity:** Buildable (naive detector) → Instrument (validated scoring)

---

## Source

- Nolen-Hoeksema, S. (1991). Responses to depression and their effects on the duration of depressive episodes. *Journal of Abnormal Psychology.* The response styles theory that made rumination a measurable construct.
- Watkins, E. R. (2008). Constructive and unconstructive repetitive thought. *Psychological Bulletin*, 134(2), 163-206. The paper that split repetitive thought into a productive kind and an unproductive kind.
- Trapnell, P. D., & Campbell, J. D. (1999). Private self-consciousness and the five-factor model: distinguishing rumination from reflection. *Journal of Personality and Social Psychology.*

## Mechanism

Rumination and reflection look identical from outside. Both are a mind going over a problem again and again. The person cannot tell you which one they are doing just by describing the behaviour, because the behaviour is the same: iterating on a difficulty.

The difference is in what each pass does. Reflection is repetitive thought that moves. Each pass takes in something new, reframes the problem, or narrows the space. Rumination is repetitive thought that circles. Each pass recycles the same content with slightly different words, generates the same conclusions, and produces the affect of working on it without the substance of progress. Watkins' contribution was to show that repetitive thought is not good or bad in itself. The same machinery, pointed slightly differently, is either problem-solving or a trap.

The discriminator psychology settled on is not how many times you loop. A reflective person might make ten passes and a ruminative person three. It is whether each pass generates new information.

## Agent translation

Coding agents ruminate constantly, and it is one of the most expensive things they do. The classic case: a test fails, the agent proposes a fix, the fix fails the same way, the agent proposes a near-identical fix with a variable renamed or a line reordered, and repeats. Diff similarity between consecutive attempts approaches 1.0. Token spend climbs. Information gained is close to zero. From the outside it looks like the agent is working the problem. It is circling it.

This is the loop-engineering community's "why does my agent get stuck" problem, named. The usual fix is a hard cap: stop after N retries, fingerprint the tool calls and bail on the third identical one. That works, and it is a blunt version of the right idea. It stops on *repetition*. The psychology says the thing to stop on is not repetition, it is *absence of information gain*, which is subtly different and strictly better. An agent can rephrase enough to dodge a fingerprint match while making zero real progress. It can also legitimately retry a very similar action after new information arrived (a dependency finished installing, say) and that retry is reflective, not ruminative. Repetition detection misses both cases. Information gain catches both.

Where the analogy holds: the productive/unproductive distinction is exactly the one you want, and it is behavioural, which means it is measurable from traces.

Where it breaks: in humans, rumination is entangled with mood and rides on affective machinery that agents do not have. The construct transfers, the aetiology does not. An agent does not ruminate because it is anxious. It ruminates because its search has collapsed into a basin and nothing in the loop is measuring the collapse. That is arguably easier to fix than the human version, and it means you should resist importing the clinical framing wholesale. Borrow the discriminator, leave the diagnosis.

## Signal

**Information gain per iteration.** The construct is clean; the operationalisation is where the work is, and where an honest instrument has to be careful. Candidate measures, none of them settled:

- **Diff novelty ratio.** How much of attempt *n* is new relative to attempts 1..*n*-1. A dependency-free version can be built today from `difflib` on the artefacts. Cheap, transparent, and a reasonable first proxy.
- **Embedding distance between consecutive attempts.** Semantic rather than lexical novelty, so it is harder to fool by renaming. Costs an embedding call per iteration.
- **Error-message entropy across retries.** If the failures themselves stop changing, the loop has stopped learning even if the attempts look different. Sometimes the cleanest signal, because the environment's response is harder to game than the agent's output.

Each of these can be confounded. Diff novelty rewards thrashing: an agent that rewrites everything each pass looks maximally novel and maximally productive while getting nowhere. Embedding distance can flag a genuine reframe as noise, or miss a substantive change that is lexically small. Error entropy assumes informative error messages, which plenty of environments do not provide. Combining them helps and does not fully solve it. This is exactly why L1 is marked as crossing into **Instrument** territory: a number that claims "your agent is ruminating" has to be validated against traces a human has labelled, or it is just a vibe with a decimal point. See [docs/measurement-stance.md](../docs/measurement-stance.md).

## Exit condition

When information gain falls below threshold for N consecutive iterations, do not just stop. Force one of:

1. **Reframe** — hand control to [L5, Incubation / Einstellung Breaker](L5-incubation-einstellung-breaker.md): switch to an unrelated subtask, then return with a fresh context and reordered constraints.
2. **Escalate** — surface to the human with a structured summary of what was tried and why it plateaued, not a raw failure.
3. **Abandon with a note** — record the impasse in a form a later loop (or a later session) can pick up, so the dead end is not silently re-entered. This is where L1 hands to [L4, the Zeigarnik register](L4-zeigarnik-intentions-register.md).

The exit is not "give up." It is "this loop has stopped paying, route the energy somewhere it will."

## Shape

A monitor wrapped around any iterating agent. In Claude Code specifically, a hook that watches the transcript for the retry pattern and computes the novelty signal across recent attempts. It observes; it does not need to be in the agent's own reasoning path, which means you can add it to an existing agent without rewriting the agent.

## Why build this first

It is the loop every agent already suffers from, the signal is the clearest in the catalogue, and the demo writes its own explanation. Point the naive diff-novelty detector at one real trace of an agent going in circles, and the output is the pitch: here is your agent ruminating, here is the pass where it stopped learning, here is what continuing cost. The buildable version (diff novelty on the transcript) is a small job. The validated instrument (a scoring model you would let make claims) is the harder, staged piece.

## Further reading

- Watkins (2008), *Psychological Bulletin* — the definitive treatment of constructive versus unconstructive repetitive thought.
- Nolen-Hoeksema, Wisco & Lyubomirsky (2008), "Rethinking Rumination," *Perspectives on Psychological Science* — a readable overview of the construct and its measurement.
