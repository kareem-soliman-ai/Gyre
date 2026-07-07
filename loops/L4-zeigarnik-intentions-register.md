# L4 — Zeigarnik Intentions Register

*Unfinished intentions stay active and resurface when relevant, then genuinely release on closure.*

**Maturity:** Buildable

---

## Source

- Zeigarnik, B. (1927). Über das Behalten von erledigten und unerledigten Handlungen [On the retention of completed and uncompleted actions]. *Psychologische Forschung*, 9, 1-85.
- Lewin, K. (1926). Tension systems and the dynamics of intention.
- Masicampo, E. J., & Baumeister, R. F. (2011). Consider it done! Plan making can eliminate the cognitive effects of unfulfilled goals. *Journal of Personality and Social Psychology*, 101(4), 667-683.

## Mechanism

Zeigarnik's finding, from watching waiters remember unpaid orders and forget paid ones: uncompleted tasks are remembered better than completed ones. An unfinished intention sets up what Lewin called a tension system, a state of activation that persists and intrudes on cognition until the task is done. The intention stays live. It pushes.

The crucial modern refinement is Masicampo and Baumeister's. It is not completion that releases the tension. It is completion **or a concrete plan**. Writing down a specific plan for when and how you will finish the task discharges the intrusion almost as well as actually finishing it. The mind will let go of an open loop if it trusts the loop is captured somewhere it will be picked up. Closure or a credible plan, either one releases.

## Agent translation

Agents have amnesia about abandoned threads. Mid-task, an agent notices a second problem ("this function has a bug too, but let me finish the current thing first"), and then the current thing consumes the context, the session moves on, and the noticed bug is gone. It never set up a tension system because the agent has no tension system. Open intentions do not persist and do not intrude. They evaporate.

The pattern is an **open-intentions register** with the Zeigarnik property built in. Not a task queue, and the distinction is the whole point. A queue is passive: items sit until something pulls them. Zeigarnik activation is intrusive by design: an open intention resurfaces itself when the current context becomes relevant to it. The agent is editing a nearby file, and the register surfaces "you flagged a bug in this module three steps ago, you are now in a position to fix it." Context-triggered, not you-asked-for-the-list.

And it releases properly. When the intention is genuinely closed, or when a concrete plan is formed and recorded (a follow-up task with enough specificity that a future session could execute it), the item stops intruding. Masicampo and Baumeister's finding is the design spec for the release condition: do not require completion to quiet the loop, accept a credible plan. This stops the register from becoming a nagging pile of everything the agent ever noticed, which would be its own failure mode.

Where the analogy holds: unusually well. The mechanism is almost mechanical already, activation that persists and intrudes until closure-or-plan, and agents lack exactly this, so the transfer is clean.

Where it breaks: human Zeigarnik tension is affectively costly, which is why the mind works to discharge it. An agent has no discomfort driving it to close loops, so the "release" is not relief, it is just correct bookkeeping. That is fine, it means you get the useful behaviour (intrusion when relevant, release on closure) without needing the agent to feel anything. But it also means you have to engineer the intrusion deliberately, because nothing pushes for it from inside.

## Signal

**Intrusion relevance.** The quality metric for this loop is not how many items it holds, it is whether a resurfaced item actually connects to the current context. A register that surfaces everything all the time is noise; a register that never surfaces is a queue. The signal is the hit rate: when the register intrudes, does the intrusion land on something the agent is now positioned to act on. That is measurable by whether surfaced items get acted on versus dismissed.

## Exit condition

Per item: the intention is closed (done) or planned (a concrete, recorded follow-up exists). On either, the item releases and stops intruding. The register itself is standing.

## Shape

A memory-layer pattern. It sits on top of whatever persistent memory substrate the agent already has, adding the two behaviours a plain store lacks: context-triggered resurfacing and closure-or-plan release. It pairs naturally with L1's "abandon with a structured note" exit: when a loop is abandoned, the note goes into the register, and the register decides when it becomes relevant again.

## Further reading

- Masicampo & Baumeister (2011) — the plan-making result, which is the part that makes this implementable without a nagging register.
- Zeigarnik (1927) — the original, for the mechanism.
