# L7 — The Meta-Loop

*Which loop runs now, and when to switch. The layer that makes this a library rather than a grab-bag.*

**Maturity:** Framing → Controller (interface described here; the controller itself is not in this repository)

---

## Source

- The explore-exploit tradition: Sutton & Barto on the exploration-exploitation dilemma; Cohen, McClure & Yu (2007), "Should I stay or should I go? How the human brain manages the trade-off between exploitation and exploration," *Philosophical Transactions of the Royal Society B.*
- Control theory and the hierarchy of feedback loops (Carver & Scheier), inherited from [L0](L0-tote.md).

## Mechanism

Every loop below this one answers "how do I run this loop well." None of them answers "which loop should I be running right now." That is a different question, and in a mind it is roughly the explore-exploit question: do I keep working the current line (exploit) or switch to something else (explore), and at what rhythm do I oscillate between the two.

The framing claim of Gyre is that an agent's loops are not a flat list you trigger independently. They are contents that a controller schedules. Rumination detection (L1) tells you a loop has stopped paying. Incubation (L5) is one response. Escalation is another. Calibration (L2) is a standing governor that should be able to bias those choices. Something has to arbitrate: given the current state, which loop gets the agent's next move. That arbitrator is the meta-loop.

## Agent translation

L7 is the controller that decides which of L1 through L6 is in charge at a given moment, and when to switch modes. It is what turns a pile of independently useful patterns into a system: patterns at the bottom, measurement instruments in the middle reporting loop quality, and a rhythm controller on top deciding what runs when.

Concretely, the controller consumes the signals the other loops produce (information gain from L1, calibration state from L2, rupture signal from L3, deviation alerts from L6) and decides allocation. When L1 says the current loop has plateaued and L2 says confidence is low, the controller might hand to information-seeking. When L3 signals a rupture, that pre-empts almost everything, because there is no point optimising the object-level loop if the human has disengaged from it. The controller is where the loops stop being local hacks and start being a governed rhythm.

Where the analogy holds: the explore-exploit framing is a genuine and well-studied account of how minds allocate between staying and switching, and it maps onto the "which loop now" problem directly.

Where it breaks, and it is worth being honest about this: the meta-loop is a hard problem with its own research lineage, and a naive controller (fixed priorities, hand-tuned switching rules) will be brittle in exactly the situations where you needed it most. Getting the oscillation rhythm right, when to switch and how often, is not a solved problem in agents or, arguably, in humans. This entry describes the *interface* the meta-loop presents to the rest of the catalogue. It does not hand you a working controller, because a working controller that decides an agent's mode-switching is precisely the kind of thing that needs to be built carefully and validated rather than sketched in a README.

## Signal

The meta-loop's own quality signal is oscillation appropriateness: is it switching modes when switching pays, and holding when holding pays. That is measurable in principle, harder in practice, and depends on having the lower loops' signals be trustworthy first. You cannot build a good controller on top of instruments that lie, which is another reason the instruments (L1, L3) get validated before the controller gets built.

## Exit condition

The meta-loop is the outermost standing loop. It does not exit; it is the thing that decides when the loops inside it exit. In [L0](L0-tote.md)'s terms, it is the top of the TOTE hierarchy, the loop whose Operate step is "run whichever sub-loop the situation calls for."

## Shape

A system layer, and the last thing to build. It is deliberately first to talk about (it is the architectural claim that makes the collection cohere) and last to ship (it depends on everything below it working and being measurable). In Gyre's disclosure structure this is Tier 3: described as an interface here, implemented and validated separately, not given away as a sketch that would be brittle if anyone tried to run it.

## Why it is here as framing

Without L7, Gyre is a useful list of eight independently good patterns. With L7, it is a claim about architecture: that the loops of a mind are scheduled, not fired at random, and that the scheduler is itself a loop with its own psychology. The claim is worth stating now even though the controller ships later, because the claim is what tells you the other eight patterns belong together.

## Further reading

- Cohen, McClure & Yu (2007) — the explore-exploit trade-off in the brain, readable and directly on point.
- Sutton & Barto, *Reinforcement Learning* — the computational framing of exploration versus exploitation.
