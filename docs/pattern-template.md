# Pattern Template

Copy this to `loops/LN-your-loop.md` and fill it in. The fixed format is the point: it lets anyone scan any entry the same way, and it forces the parts that are easy to skip (the signal, and where the analogy breaks).

---

```markdown
# LN — Loop Name

*One-line description of what the loop does.*

**Maturity:** Framing | Buildable | Instrument

---

## Source

The psychology or cybernetics, cited to primary literature. Author, year, title,
venue. Cite the original where you can, not a secondary summary of it. If the
mechanism has a modern refinement that changes the design (the way Masicampo &
Baumeister change L4), cite that too.

## Mechanism

What the loop does in a mind. Two or three paragraphs. Explain the mechanism well
enough that someone who has never read the source understands what is being
claimed, and why it is a loop rather than a one-shot behaviour.

## Agent translation

What the loop does in an agent. This is the load-bearing section. It must include:

- The concrete agent behaviour the loop addresses or produces.
- **Where the analogy holds.** Say it plainly.
- **Where it breaks.** This is not optional. Every human-to-agent translation
  breaks somewhere, usually because agents lack the affective machinery the human
  mechanism rides on. Name the seam. A translation that hides its seams is worse
  than no translation, because it invites people to import the parts that do not
  transfer.

## Signal

How you would measure loop quality from behaviour. Candidate operationalisations,
stated as candidates, with their confounds named. If the signal is a measurement
claim about a latent property, say so, and mark the maturity as Instrument. See
[measurement-stance.md](measurement-stance.md).

## Exit condition

When the loop should stop, escalate, or switch. If it is a standing governor
rather than a terminating loop, say that. If it is a policy invoked by another
loop's exit, name the loop.

## Shape

Where it fits in a scaffold: hook, monitor, wrapper, memory layer, filter,
controller. Note which other loops it composes with.

## Further reading

Two or three pointers, with a one-line note on what each is good for.
```

---

## Rules for a good entry

**Cite honestly.** The value of this catalogue is that the psychology is real and accurately attributed. A pattern with a made-up or misremembered citation poisons the well. If you are not sure the source says what you claim, check it before you write it down.

**Mark maturity accurately.** Three levels:

- **Framing** — an idea and a naming. No code expected.
- **Buildable** — a working version is a small job, and the shape is prescriptive enough to build from the doc.
- **Instrument** — it measures a latent property and cannot make claims until validated. Method open, scoring held back. Do not mark something Buildable to make it sound more ready than it is.

**Show the seam.** The "where it breaks" requirement is the thing that keeps this catalogue from being pop-psychology-for-engineers. Every entry names where the human-to-agent analogy fails. If you cannot find where yours breaks, you have not pushed on it hard enough.

**No performance claims without validation.** An entry may describe a signal and a method. It may not state that a detector saves X or catches Y% until that has been measured on real traces, with the caveats attached. See [measurement-stance.md](measurement-stance.md) for why this rule is strict.
