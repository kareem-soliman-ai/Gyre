# Contenders

Put public scoreboard implementations in this package. A contender exposes a
zero-argument factory returning a `MeasurementProvider`:

```python
def build():
    return MyProvider()
```

Then run:

```bash
python scripts/challenge.py \
  --contender contenders.my_sensor:build \
  --write-receipt benchmarks/submissions/YOUR_HANDLE-my-sensor.json \
  --submitter YOUR_HANDLE \
  --update-scoreboard
```

For a private implementation, either install it from a separate private
checkout or place it under `contenders/private/`, which Git ignores. Add
`--visibility private`. The receipt will publish the score but omit the module
path and mark the result self-reported and ineligible for the verified ranking.

See [the complete score guide](../docs/contributing-a-score.md).
