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

## v0.2 — The Modular Measurement Architecture (this release)

The seam that makes measurement pluggable, and the loops that run against it.

- [x] The measurement seam: `MeasurementProvider`, `Measurement` (with a calibration ladder), `Meaning`. Loops depend on the interface, never on a concrete sensor.
- [x] Loop controllers against the seam: [L1](loops/L1-rumination-vs-reflection.md) RuminationMonitor, [L2](loops/L2-metacognitive-calibration.md) CalibrationGovernor, [L5](loops/L5-incubation-einstellung-breaker.md) EinstellungBreaker, [L6](loops/L6-habituation-orienting.md) HabituationFilter.
- [x] Naive baseline sensors (diff-novelty, rolling Brier, z-score deviation), honest about being crude, so everything runs out of the box.
- [x] `gyre.bench`: score any sensor against labelled traces, head-to-head, so the value gap is runnable.
- [x] The [build-your-own-measurement guide](docs/building-measurements.md) and the gitignored proprietary provider fence.

## v0.3 — The Instrument, on real traces

Turn the flagship into a validated sensor and run it on reality.

- [ ] A real [L1](loops/L1-rumination-vs-reflection.md) rumination sensor that models the construct (not just lexical novelty), plugged in behind the interface.
- [ ] Run it on a real agent trace of a loop going in circles; score it against the naive baseline with `gyre.bench`.
- [ ] Report the measured result honestly: what it caught that the baseline missed, what it missed, what continuing cost. No claim beyond what the traces support.
- [ ] Package the L1 monitor as a reusable Claude Code hook.

## v0.4 — The Library

The full collection, with the architecture that makes it cohere.

- [ ] Remaining patterns implemented against the interface.
- [ ] The meta-loop controller ([L7](loops/L7-meta-loop.md)) as a described and validated interface, deciding which loop runs when.
- [ ] Instrument validation: the L1 and L3 scoring layers validated against labelled traces, so they can finally state a number they have earned.

## How to read this roadmap

The instruments (L1 scoring, L3) are gated behind validation on purpose. A detector does not get to make a claim until it has been checked against ground truth, so "validated instrument" sits at v0.4, not v0.2, even though a buildable version of L1 lands much earlier. The difference between the two is the difference between "here is how you would measure this" and "here is a number you should trust." See [docs/measurement-stance.md](docs/measurement-stance.md).

If nothing happens for a month, v0.1 is still a complete and useful thing. That is the design.
