# Roadmap

Gyre ships in vertical slices. Each slice is independently useful, so the project has value even if the next slice never happens. That is deliberate: nothing here depends on momentum.

## v0.1 — The Claim (this release)

The framing and the taxonomy, shipped open.

- [x] The catalogue: eight loop patterns (L0 through L7) plus a backlog, each with source, mechanism, agent translation, signal, exit condition, and shape.
- [x] The framing essay: [loop engineering is cybernetic psychology rediscovered](docs/cybernetic-psychology.md).
- [x] The measurement stance: why the instrument layer describes its method openly and holds its validated scoring.
- [x] Interfaces: a dependency-free `LoopMonitor` protocol and vocabulary so detectors built later share one shape.
- [x] Dual license (Apache-2.0 for code, CC BY 4.0 for the catalogue).

v0.1 is complete on its own. Everything below is optional and can resume cold from this repository.

## v0.2 — The Instrument

Turn the flagship pattern into a working detector and run it on reality.

- [ ] A naive [L1](loops/L1-rumination-vs-reflection.md) rumination detector: diff-novelty on an agent transcript, built against the `LoopMonitor` interface.
- [ ] Run it on a real agent trace of a loop going in circles.
- [ ] Report the measured result honestly: what it caught, what it missed, what continuing cost. No claim beyond what the trace supports.

## v0.3 — The Packaging

Make the detector reusable and add the loop that public feedback pulls for.

- [ ] The L1 detector as a reusable hook (Claude Code hook shape, watching the transcript).
- [ ] One more loop implemented, chosen by which one the community asks for most (likely [L4](loops/L4-zeigarnik-intentions-register.md) or [L6](loops/L6-habituation-orienting.md)).

## v0.4 — The Library

The full collection, with the architecture that makes it cohere.

- [ ] Remaining patterns implemented against the interface.
- [ ] The meta-loop controller ([L7](loops/L7-meta-loop.md)) as a described and validated interface, deciding which loop runs when.
- [ ] Instrument validation: the L1 and L3 scoring layers validated against labelled traces, so they can finally state a number they have earned.

## How to read this roadmap

The instruments (L1 scoring, L3) are gated behind validation on purpose. A detector does not get to make a claim until it has been checked against ground truth, so "validated instrument" sits at v0.4, not v0.2, even though a buildable version of L1 lands much earlier. The difference between the two is the difference between "here is how you would measure this" and "here is a number you should trust." See [docs/measurement-stance.md](docs/measurement-stance.md).

If nothing happens for a month, v0.1 is still a complete and useful thing. That is the design.
