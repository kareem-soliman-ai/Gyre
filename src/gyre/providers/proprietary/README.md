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

That is the open-core line: the methods, interfaces, baselines, and falsification
harness are public; fitted instruments and protected validation assets are not.
Protection is not evidence of validity. A provider still has to earn its claims
against an appropriate holdout and outcome criterion (see
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

## What a qualified provider must add

A protected L1 provider can return a `Measurement` with calibration fields
filled in: a probability, a standardised score against a modelled baseline, a
decision, and measurement error. Those fields are only trustworthy to the
extent supported by validation. The loop code does not change, which allows a
public baseline and a protected candidate to be compared through the same seam
without distributing the protected implementation.
