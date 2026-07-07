# `proprietary/` — the measurement fence

This directory is where validated, latent-variable measurement providers live.
Its contents are **gitignored**. Only two files ship publicly: this README and the
`__init__.py` stub. Everything else you drop here stays local.

## Why this fence exists

The rest of Gyre is open, on purpose. The loop patterns, the measurement seam,
the naive baseline providers, and the benchmark harness are all public and will
stay that way. What is *not* open is the thing that takes a background in
psychometrics, latent-variable modelling, and validation to build and to defend:
measurements that actually estimate a latent construct (rumination, calibration,
rupture) with known reliability, rather than a raw proxy that correlates with it
until it doesn't.

That is the open-core line. Free razor, and the loops are a genuinely good razor.
The validated psychometric blade is the part with a price on it.

If that reads as mercenary, look at what is actually free: every loop, the whole
interface, working naive measurements, and a benchmark that will honestly tell you
how good *your* measurement is. The only thing behind the fence is the validated
instrument, and an unvalidated instrument should not be trusted anyway (see
[docs/measurement-stance.md](../../../../docs/measurement-stance.md)).

## How to use this directory

Implement `gyre.measurement.MeasurementProvider`, drop the module here, and wire
it up in `__init__.py`'s `register_all`:

```python
# gyre/providers/proprietary/rumination_mvt.py  (gitignored)
from gyre.measurement import Meaning, Measurement

class MvtRuminationProvider:
    loop_id = "L1"
    name = "psy:mvt-rumination"
    def measure(self, obs): ...   # returns a calibrated Measurement
    def reset(self): ...
```

```python
# gyre/providers/proprietary/__init__.py  (your private copy)
def register_all(register):
    from .rumination_mvt import MvtRuminationProvider
    register("psy:mvt-rumination", MvtRuminationProvider)
```

The public `gyre.providers` package calls `register_all` best-effort on import, so
a provider dropped here is available by name without any public code referencing
it. A clean public checkout has none of this and runs on the naive baselines.

## The difference a real provider makes

A proprietary L1 provider does not return a lexical diff ratio. It returns a
`Measurement` with the calibration fields *filled in*: a `probability` that the
loop is ruminating, a `standardized` score against a modelled baseline, a
`decision` it has earned the right to make, and a `measurement_error` that reports
its own reliability. The loop code does not change. It just starts firing earlier,
more precisely, and with a number you can defend. That gap, made runnable, is the
point of the whole architecture.
