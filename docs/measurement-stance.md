# The Measurement Stance

Why some loops are marked **Instrument**, why their scoring internals are not in this repository, and why that is a feature rather than a hedge.

---

## The problem with measuring a loop

Several patterns in this catalogue do not just describe a loop, they claim to **detect** something about it: that a loop is ruminating (L1), that an alliance has ruptured (L3), that a channel has deviated from normal (L6). These are measurement claims. And measurement claims about latent properties, things you cannot observe directly and have to infer from behaviour, are where good intentions quietly become liabilities.

Consider a rumination detector. "This loop has stopped generating information" is not a fact you can read off the trace. It is a latent construct you are inferring from a proxy: diff novelty, embedding distance, error entropy. Every one of those proxies is confounded. Diff novelty rewards an agent that thrashes (rewrites everything each pass looks maximally novel while getting nowhere). Embedding distance can score a genuine reframe as noise. Error entropy assumes the environment gives informative errors. So the detector can be wrong in two directions: it can fire on healthy iteration, or stay silent through genuine rumination.

Neither failure is neutral. A detector that fires on healthy iteration trains you to distrust it, and you turn it off. A detector that stays silent through real rumination lets the expensive thing keep happening while reassuring you it is fine. A confidently wrong measurement is worse than no measurement, because it displaces the judgment you would otherwise have applied.

## What validity means here

This is not a new problem. It is the oldest problem in psychometrics, and psychology has a well-developed apparatus for it: a measure has to demonstrate **validity** (does it measure what it claims) and **reliability** (does it measure consistently) before its numbers mean anything. You establish that by testing the measure against ground truth, not by asserting that the method is reasonable.

For a loop detector, that means: take real agent traces, have humans label them (this loop was ruminating, this one was making progress), and check whether the detector's scores actually track the labels. Until that has been done, the detector has a method but not a validated instrument, and the honest thing is to say so.

## The fence, and why it is drawn where it is

Gyre draws a specific line:

- **The method is open.** Every Instrument-grade pattern describes its signal, its candidate operationalisations, and their confounds, in full, in the public pattern doc. Nothing about the approach is secret. You could build your own detector from the doc.
- **The validated scoring is not open, yet.** The specific scoring internals, thresholds, and validation pipelines, the parts that would let a detector make a confident claim, stay closed until they have been validated on real traces. Not because the method is proprietary, but because an unvalidated detector should not be handed a confident voice with this project's name on it.

This is "open method, closed pipeline," and it is the same fence serious measurement work draws everywhere. It is not a marketing hold-back. It is the difference between "here is how you would measure this" (safe to publish) and "here is a number you should trust" (has to be earned first).

## How the fence is drawn in the code

This is not just a policy, it is the architecture. Loops are controllers and measurements are sensors, joined by a `MeasurementProvider` interface, and the loop never imports a concrete sensor (see [architecture.md](architecture.md)). That seam is what lets the fence be clean rather than grudging:

- The **loops**, the **measurement seam**, the **naive baseline sensors**, and the **benchmark harness** are all public. Everything runs out of the box on the baselines.
- **Validated instruments** plug into the same interface from a gitignored layer. A public checkout simply has none and falls back to the baselines. Nothing about the loop changes; only the quality of the signal does.

So "open method, closed instrument" is literally true: the method is the public interface plus the [build guide](building-measurements.md), and the closed part is a set of provider implementations behind the fence, not a secret woven through the control code.

## Prove it rather than claim it

Because measurement is pluggable, you do not have to trust anyone's assertion that a better sensor helps. `gyre.bench` scores any provider against labelled traces, and `compare_providers` runs a head-to-head. Put a naive baseline and a serious sensor on the same traces and read the gap. That is the honest version of the value argument: not "measurement matters, trust me," but "here is the number, run it yourself." The harness is generous to the naive provider (it sweeps a threshold and reports best-case), and the naive provider usually loses anyway, which is the result worth sitting with.

## What this means if you are building on Gyre

- The **naive baselines** (diff-novelty for L1, rolling Brier for L2, z-score deviation for L6) are real and usable. For low-stakes, high-signal cases they are genuinely enough, and you should not gold-plate a measurement whose errors cost you nothing.
- To go past them, **build a sensor** against the interface and hold your result to the bar: a detector you built is a hypothesis until you have checked it against labelled traces with `gyre.bench`. Report it as one.
- **No performance claims ship unvalidated.** You will not find "saves 40% of tokens" anywhere in this repository, because no sensor here has earned that number yet. When one has, the claim will appear with its sample, its method, and its caveats intact, and not before.

## The short version

Naming a loop is cheap and safe, so the taxonomy ships open and fast. Measuring a loop is hard and easy to get quietly wrong, so the measurement layer describes its method openly and holds its validated scoring until the validation exists. Give away the pattern. Earn the number.
