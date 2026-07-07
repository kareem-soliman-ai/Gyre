# Hosted Measurements

The measurement seam does not care where the computation happens. A provider takes
an observation and returns a `Measurement`; whether it computes that locally or
asks a server is invisible to the loop. That fact makes a specific arrangement
possible: a measurement can run entirely off your machine, behind an API, so a
validated instrument can be *used* without being *seen*.

## How it works

```
your agent loop  ──observe──▶  RemoteMeasurementProvider  ──HTTP──▶  scoring service
     (public, yours)              (public client, ~120 lines)         (private, hosted)
                  ◀──Measurement──                        ◀──JSON──
```

`RemoteMeasurementProvider` (in [`gyre.providers.remote`](../src/gyre/providers/remote.py))
is a public HTTP client. It serialises the observation, posts it, and rebuilds the
`Measurement` from the response. It contains no scoring, no thresholds, no model.
The instrument lives server-side. An engineer gets the client and an API key and
plugs it into any loop exactly like a local sensor:

```python
from gyre import RuminationMonitor
from gyre.providers import RemoteMeasurementProvider, http_transport

sensor = RemoteMeasurementProvider(
    "L1", "hosted:rumination",
    http_transport("https://api.example.com/score", api_key="..."),
)
monitor = RuminationMonitor(sensor)   # identical to using a local provider
```

The wire contract is trivial on purpose: POST a request dict, get a
`Measurement.to_dict()` back. Any server honouring it works, which keeps the
client dumb and the value server-side. [`test_remote.py`](../tests/test_remote.py)
proves the whole path with an in-process fake server, so the architecture is
verified without a network or a cent of cloud spend. Run
[`scripts/demo_remote_vs_naive.py`](../scripts/demo_remote_vs_naive.py) to see a
hosted-style sensor beat a naive local one on the same loop.

## Why this is the right shape for the fence

The open-core line falls exactly where it should. Everything an engineer needs to
*build with* is open: the loops, the seam, the naive baselines, the benchmark, and
this client. The one thing that is not open is the validated instrument, and it is
not open because it takes real psychometric work to build and validate, not because
the interface is secret. Serving it over an API is just the cleanest way to let
people use it without shipping it, the same arrangement a hosted model API uses.

## Honest positioning (read this before depending on it)

A hosted sensor is a network call per loop iteration and a dependency on someone
else's uptime. That has consequences, and pretending otherwise would be the kind of
overselling this project exists to avoid.

- **It adds latency.** Fine for a monitor that runs once per agent iteration,
  wrong for a hot inner loop.
- **It is a dependency.** No serious team should put a solo-maintained endpoint on
  a production agent's critical path. Treat the hosted option as an evaluation,
  demonstration, and low-stakes tool first.
- **Self-hosting is the production answer.** The same interface accepts a local
  provider. If a measurement proves its worth to you, run it in-process. The hosted
  API is for trying before building, and for cases where you would rather not.
- **Reproducibility.** A hosted scorer you cannot inspect is not independently
  verifiable, which is a fair objection. The mitigation is that the *baseline* and
  the *method* are fully public: the naive providers, the benchmark, and (when
  published) the labelled traces let anyone reproduce the comparison. The claim on
  offer is "this hosted sensor beats this open baseline on these open traces," and
  that claim is checkable even when the sensor's internals are not.

## What has to be true before any of this earns trust

The architecture is proven. What is not yet proven, and matters far more, is that a
hosted measurement *demonstrably improves outcomes*. That is an evaluation question,
and it is harder than the plumbing. The honest ladder, cheapest rung first:

1. **Detection.** Does the sensor identify the latent state better than the naive
   baseline, on labelled traces? Offline, cheap, run with `gyre.bench`.
2. **Counterfactual.** How much earlier does it fire than a retry-cap or a naive
   threshold on the same real traces? Pure replay, near-free. This is the concrete,
   reproducible number worth leading with.
3. **Outcome.** Does a loop *using* the sensor actually improve end-task success or
   cost, against a controlled baseline? Online, expensive, high-variance, and the
   real test. This is where controlled experiments and real compute go, and no
   performance claim about the system ships until this rung has data behind it.

Rungs 1 and 2 are affordable and are most of the credibility for a technical
audience. Rung 3 is the expensive, decisive one. See
[measurement-stance.md](measurement-stance.md) for why the order is non-negotiable:
a hosted number you cannot defend is worse than no number at all.
