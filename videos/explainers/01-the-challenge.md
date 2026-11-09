# Explainer 01: The Alien Factory challenge

**Target:** 2 minutes. **Audience:** first-time visitor. **Outcome:** the viewer
can run the demo and explain what is scored.

## Cold open

Visual: a modular factory lands on a dark alien plain. A storm wall fills the
horizon. Three unknown phenomena move near the site.

Narration:

> You have arrived on a new continent with a factory to stabilise and a
> hurricane already on the way. The organisms around you may ignore your
> instruments, adapt to them, or react to being observed. You do not know which.

## Story

Visual: terminal command `python scripts/alien_factory.py`.

> Gyre turns loop engineering into a causal-discovery game. You observe,
> compare active scans with a quiet reference station, form hypotheses, and
> choose interventions. The simulator keeps four things separate: the
> phenomenon's immutable identity, the name you give it, your causal model, and
> what actually happens.

Visual: `xeno-17 -> "scan-reactive flock" -> hypothesis -> next outcome`.

> Your names are never answer keys. Your score comes from terminal factory
> stability, time, probe cost, and interference. Measurement can help, but
> measuring too aggressively can also change what you are trying to learn.

## Close

> Run the demo in five minutes. Then change the sensors, controller, action
> menu, or human-AI authority rules. The challenge is not to produce the most
> convincing explanation. It is to build a loop that survives contact with the
> world.

On screen:

```text
git clone https://github.com/kareem-soliman-ai/Gyre.git
python -m pip install -e .
python scripts/alien_factory.py --demo
```

Evidence boundary: do not describe the adaptive-budget challenge as validated;
EXP-06 qualified local observer-effect mechanics and generous-budget
discoverability only.

