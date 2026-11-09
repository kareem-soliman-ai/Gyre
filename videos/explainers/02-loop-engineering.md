# Explainer 02: When repetition becomes a loop

**Target:** 3 minutes. **Outcome:** the viewer can draw a minimum viable loop.

Narration:

> Repeating an agent prompt is not yet loop engineering. An engineered loop has
> a world state, an observation, a sensor that interprets it, a controller that
> chooses from declared actions, terminal conditions, and a budget.

Visual:

```text
world -> observation -> sensor -> controller -> action -> world
                         |             |
                    uncertainty    authority
```

> The separation matters because each link can fail differently. A good
> controller acting on a bad sensor confidently makes the wrong correction. A
> good sensor feeding a weak action menu can diagnose a problem it cannot fix.
> A persuasive trace can satisfy a person while failing the objective outcome.

> Graph engineering is the same problem at a larger scale. Nodes do not become
> useful because they have specialist names. Each decision edge needs state,
> evidence, authority, cost, and a recovery path. Adaptive topology should earn
> promotion by beating a fixed graph on matched outcomes, not by looking more
> intelligent.

Close:

> In Gyre, hold the controller constant and swap the sensor. Then hold the
> sensor constant and swap the controller. If the result changes, you have
> learned which link carried the value.

Demo: `python scripts/loop_playground.py --list`.

