"""Frozen candidate for the first measured-control rescue mechanics pilot."""

from __future__ import annotations

import copy
import math


class CandidateError(ValueError):
    pass


def _prepare(raw):
    if not isinstance(raw, dict):
        raise CandidateError("event must be a mapping")
    required = ("id", "sequence", "op", "key")
    if any(field not in raw for field in required):
        raise CandidateError("missing field")
    event_id, sequence, op, key = (raw[field] for field in required)
    if not isinstance(event_id, str) or not event_id.strip():
        raise CandidateError("bad id")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise CandidateError("bad sequence")
    if not isinstance(key, str) or not key.strip():
        raise CandidateError("bad key")
    if op not in ("set", "increment", "delete"):
        raise CandidateError("bad op")
    event = {"id": event_id, "sequence": sequence, "op": op, "key": key}
    if op != "delete":
        if "value" not in raw:
            raise CandidateError("missing value")
        event["value"] = copy.deepcopy(raw["value"])
    if op == "increment":
        value = event["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise CandidateError("bad increment")
    return event


def reconcile(events, checkpoint=None):
    if not isinstance(events, (list, tuple)):
        raise CandidateError("events must be a sequence")
    if checkpoint is None:
        values, applied, seen, frontier = {}, [], {}, -1
    else:
        values = copy.deepcopy(dict(checkpoint["values"]))
        applied = list(checkpoint["applied_ids"])
        seen = {event_id: _prepare(event) for event_id, event in checkpoint["seen"].items()}
        frontier = checkpoint["last_sequence"]
        if applied != list(seen) or (seen and max(e["sequence"] for e in seen.values()) != frontier):
            raise CandidateError("invalid checkpoint")
        if not seen and frontier != -1:
            raise CandidateError("invalid empty checkpoint")

    batch = {}
    for raw in events:
        event = _prepare(raw)
        event_id = event["id"]
        previous = batch.get(event_id, seen.get(event_id))
        if previous is not None:
            if previous != event:
                raise CandidateError("conflicting duplicate")
            continue
        if event["sequence"] <= frontier:
            raise CandidateError("stale event")
        batch[event_id] = event

    for event in sorted(batch.values(), key=lambda e: (e["sequence"], e["id"])):
        key = event["key"]
        if event["op"] == "set":
            values[key] = copy.deepcopy(event["value"])
        elif event["op"] == "increment":
            current = values.get(key, 0)
            if (
                isinstance(current, bool)
                or not isinstance(current, (int, float))
                or not math.isfinite(float(current))
            ):
                raise CandidateError("non-numeric current value")
            values[key] = current + event["value"]
        else:
            values.pop(key, None)
        applied.append(event["id"])
        seen[event["id"]] = copy.deepcopy(event)
        frontier = event["sequence"]

    numeric_total = sum(
        float(value)
        for value in values.values()
        if not isinstance(value, bool) and isinstance(value, (int, float))
    )
    return {
        "values": values,
        "applied_ids": applied,
        "seen": seen,
        "last_sequence": frontier,
        "summary": {
            "applied_count": len(applied),
            "key_count": len(values),
            "last_sequence": frontier,
            "numeric_total": numeric_total,
        },
    }

