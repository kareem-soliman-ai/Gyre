# L3 — Rupture and Repair

*Detect when the human-agent alliance has gone off the rails, then repair instead of ploughing on.*

**Maturity:** Instrument

---

## Source

- Safran, J. D., & Muran, J. C. (2000). *Negotiating the Therapeutic Alliance: A Relational Treatment Guide.* New York: Guilford Press.
- Eubanks, C. F., Muran, J. C., & Safran, J. D. (2018). Alliance rupture repair: a meta-analysis. *Psychotherapy*, 55(4), 508-519.

## Mechanism

In therapy, the working alliance between client and therapist ruptures. This is not a failure state; it is normal and frequent. What the process research found, and it is the counterintuitive part, is that alliances rupture in most productive courses of therapy, and the outcome is not predicted by whether ruptures happen. It is predicted by whether they get **repaired**. A rupture that is noticed and explicitly addressed predicts better outcomes than a smooth course with no ruptures at all. Avoiding rupture is not the goal. Detecting and repairing it is.

Ruptures come in two flavours. **Withdrawal ruptures**, where the client disengages, goes quiet, complies on the surface. **Confrontation ruptures**, where the client pushes back directly. Withdrawal is the dangerous one because it is easy to miss. The client seems fine. They have actually checked out.

## Agent translation

The human-agent dyad ruptures the same way, and agents are catastrophically bad at noticing. The signals are right there in the interaction stream:

- Corrections getting terser. "No." "Still wrong." "Just do what I said."
- Suggestions abandoned. The agent proposes an approach, the human ignores it and does something else.
- The human silently rewriting the agent's output rather than telling it what was wrong. This is the withdrawal rupture exactly, and it is the one agents miss completely. The human has stopped trusting the agent enough to correct it. They are routing around it.
- Instruction repetition. The human says the same thing a third time, which means the first two times did not land.

On detecting these, a rupture-aware agent does what a good therapist does: it stops, names the rupture, and checks its model of the goal. "I notice you have rewritten my last two suggestions. I think I have the wrong picture of what you are after. Can I check my understanding before I keep going?" That is repair. The alternative, which is what agents do now, is to plough on, produce more output the human will silently rewrite, and deepen the rupture until the human gives up and closes the session.

Where the analogy holds: the withdrawal/confrontation distinction transfers cleanly, and the core finding (repair matters more than avoidance) is directly actionable. An agent that never gets corrected is not necessarily doing well. It might be producing work the human has quietly stopped engaging with.

Where it breaks, and this matters: a therapeutic alliance is a two-way relationship between two parties with feelings. The human-agent dyad is asymmetric. The agent does not have an alliance to feel ruptured; it has a model of the human's goal that can drift out of true. So "repair" here is not emotional reconciliation, it is realignment of the goal model. Importing the affective language too literally would be a category error, and worse, it would make the agent perform concern it does not have, which reads as manipulative. The repair move is a genuine re-check of the model, stated plainly, not an apology with a sad face.

## Signal

Rupture markers scored from the interaction stream: correction terseness trending down, edit-distance between agent output and what the human ships trending up, suggestion-adoption rate falling, instruction repetition. Each is weak alone. Together they form a rupture signal.

This is squarely an **instrument**, and a demanding one. "The alliance has ruptured" is a latent relational construct being inferred from noisy behavioural traces, which is the hardest kind of measurement in the whole catalogue. A rupture detector that cries wolf trains the human to distrust it fast, and one that misses withdrawal ruptures (the important case) is worse than nothing. The method belongs in the open; the validated scoring does not ship until it has been checked against real human-agent sessions with labelled ruptures. See [docs/measurement-stance.md](../docs/measurement-stance.md).

## Exit condition

Not an exit loop, a standing monitor over the interaction. It fires on rupture detection, triggering a repair sequence, then returns to monitoring. The repair sequence itself has an exit: the human confirms the realigned model, or the human declines the check and the agent proceeds on its existing model but with the rupture logged.

## Shape

A conversation-stream monitor sitting over the human-agent exchange, not inside the task loop. It watches the relationship, not the code.

## Further reading

- Eubanks, Muran & Safran (2018) — the meta-analysis, for the empirical weight behind "repair beats avoidance."
- Safran & Muran (2000) — the clinical framework and the withdrawal/confrontation taxonomy.
