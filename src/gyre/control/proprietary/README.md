# `control/proprietary/` — the controller fence

This directory is where validated meta-controllers (Tier 3, the L7 layer) live.
Its contents are **gitignored**. Only two files ship publicly: this README and
the `__init__.py` stub. Everything else you drop here stays local.

## Why this fence exists

The control seam (`gyre.control`), the reference controllers (fixed-route,
L5-informed), and the controller-gap experiment
(`scripts/exp_controller_gap.py`) are all public and stay that way. The
experiment is also the honest sales pitch for what sits behind this fence: no
fixed route is safe across cost regimes — the best fixed policy under cheap
escalation is nearly the worst when human attention gets expensive — and a
context-conditioned controller closes most of the gap to oracle routing.

What is not open is the adaptive controller itself. The L7 pattern doc says why
in one line: a controller that decides an agent's mode-switching will be
brittle in exactly the situations where you needed it most unless it is built
against validated sensors and validated itself. Handing out a sketch with a
confident voice would be worse than handing out nothing. The interface is
public; the validated implementation has a price on it.

## The contract

A controller module dropped here only needs to expose:

```python
def register_controllers(register):
    register("psy:my-controller", MyControllerFactory)
```

and the public `gyre.control` registry discovers it on import, without any
tracked code naming it. A clean public checkout runs on the reference
controllers; a checkout with this layer gains the adaptive ones. Same seam,
same rules as `gyre.providers.proprietary`.
