# Architecture: loops are controllers, measurements are sensors

Gyre has one load-bearing design decision, and everything else follows from it: a
**loop** and a **measurement** are separate things, joined by a thin interface, and
neither knows the other's internals.

## The decision, and why it is the right one

A loop is a controller. It decides when to act and how to route. A measurement is
a sensor. It turns behaviour into a signal the controller acts on. This is the
[TOTE](../loops/L0-tote.md) lineage taken literally: the loop is the control
structure psychology inherited from cybernetics, and cybernetics is emphatic on one
point that agent builders keep rediscovering the hard way. **A controller is only
as good as its sensor.** You can design a flawless control policy, and if the signal
feeding it is noisy, biased, or measuring the wrong thing, the system thrashes, and
the fault is in the sensor, not the policy.

So Gyre refuses to fuse them. The loop depends only on the `MeasurementProvider`
protocol. It never imports a concrete measurement. That single rule buys three
things:

1. **Measurement is pluggable.** Swap the sensor without touching the loop.
2. **The value gap is runnable, not asserted.** Run the same loop with a throwaway
   sensor and with a validated one, on the same trace, and watch it behave
   differently. You do not have to believe measurement matters; you can measure it.
3. **The fence has a natural seam.** The loops and the naive sensors are open; the
   validated sensors live behind an interface, not woven through the control code.

## The pieces

```
        observation                         Measurement
   (a diff, a log line,      ┌───────────┐  (value + calibration
    a prediction+outcome) ──▶│ Provider  │──▶ ladder + confounds)
                             │ (sensor)  │        │
                             └───────────┘        ▼
                                            ┌───────────┐   LoopVerdict
                                            │   Loop    │──▶ (CONTINUE / PLATEAU /
                                            │(controller)│    DEVIATION / RUPTURE ...)
                                            └───────────┘
```

- **`gyre.measurement`** — the seam. `MeasurementProvider` (the protocol you
  implement), `Measurement` (what it returns), `Meaning` (which direction is
  healthy). This module has no dependency on any loop or any concrete provider, and
  must never gain one.
- **`gyre.interfaces`** — the loop side. `LoopMonitor`, `LoopVerdict`, `ExitReason`,
  `Maturity`. Depends on the seam, never on a provider.
- **`gyre.loops`** — the controllers. `RuminationMonitor` (L1),
  `CalibrationGovernor` (L2), `EinstellungBreaker` (L5), `HabituationFilter` (L6).
  Each is constructed with a provider and owns only its control policy.
- **`gyre.providers`** — the sensors. Public naive baselines
  (`gyre.providers.naive`) and a registry. A gitignored `proprietary/` layer can
  register validated sensors without any public code referencing them.
- **`gyre.bench`** — the proving ground. Score any provider against labelled traces;
  put two in a head-to-head and read the gap.

## The dependency rule, stated once

```
gyre.measurement   (no dependencies on loops or providers)
      ▲   ▲
      │   └──────────── gyre.loops         (import the seam, never a provider)
      │
      └──────────────── gyre.providers.*   (import the seam + loop observation types)
```

Loops import the seam. Providers import the seam. Loops never import providers.
Providers never get imported by loops. If you ever find a loop module importing a
concrete provider, that is a bug in the architecture, not a shortcut.

## Where the control policy lives, and where measurement lives

This split is subtle and worth being explicit about, because it is where people
first want to put things in the wrong place.

- The **loop** owns the control policy: the patience counter (how long a signal has
  to stay bad before acting), the routing (plateau to reframe, escalate, or
  abandon), the standing-governor behaviour. This is identical across sensors.
- The **provider** owns the measurement: the scalar, and how much of the calibration
  ladder it can honestly fill. This is where sensors differ.
- The **threshold** is the interesting boundary case. A raw proxy cannot supply its
  own decision boundary, so the loop is forced to take a threshold from you (and you
  will guess). A calibrated sensor supplies its own boundary (a probability, a
  z-score against a baseline, an outright decision), so the loop never touches a
  hand-tuned threshold. The shared policy in `gyre.loops._policy.trigger_state`
  walks that ladder once, so every loop inherits the same fallback and the same
  teaching moment: the better your sensor, the less the loop has to guess.

## What this buys the reader

If you are here to use the loops, you can ignore all of this and pass in a provider.
If you are here to build a measurement, this is the map: implement the seam, and the
loops, the registry, and the benchmark all accept your sensor without knowing or
caring what is inside it. And if you are here for the argument, the architecture is
the argument: measurement is not a detail of the loop, it is a separable component
whose quality dominates the system's behaviour, and Gyre is built so you can see
that for yourself rather than take it on faith.

See [building-measurements.md](building-measurements.md) to build a sensor and
[measurement-stance.md](measurement-stance.md) for why the validated ones are held
back until they are validated.
