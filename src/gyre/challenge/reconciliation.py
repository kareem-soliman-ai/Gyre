"""Executable reference model for the event-reconciliation rescue task."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any


class ReconciliationError(ValueError):
    """The batch or checkpoint violates the public task contract."""


def _canonical_event(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ReconciliationError("each event must be a mapping")
    required = {"id", "sequence", "op", "key"}
    if not required <= set(raw):
        raise ReconciliationError(f"event is missing {sorted(required - set(raw))}")
    event_id = raw["id"]
    key = raw["key"]
    sequence = raw["sequence"]
    op = raw["op"]
    if not isinstance(event_id, str) or not event_id.strip():
        raise ReconciliationError("event id must be a non-empty string")
    if not isinstance(key, str) or not key.strip():
        raise ReconciliationError("event key must be a non-empty string")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ReconciliationError("sequence must be a non-negative integer")
    if op not in {"set", "increment", "delete"}:
        raise ReconciliationError("op must be set, increment, or delete")
    if op in {"set", "increment"} and "value" not in raw:
        raise ReconciliationError(f"{op} requires value")
    if op == "increment":
        value = raw["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ReconciliationError("increment value must be a finite number")
    canonical = {
        "id": event_id,
        "sequence": sequence,
        "op": op,
        "key": key,
    }
    if op in {"set", "increment"}:
        canonical["value"] = copy.deepcopy(raw["value"])
    return canonical


def _canonical_checkpoint(checkpoint: Mapping[str, Any] | None) -> dict[str, Any]:
    if checkpoint is None:
        return {"values": {}, "applied_ids": [], "seen": {}, "last_sequence": -1}
    if not isinstance(checkpoint, Mapping):
        raise ReconciliationError("checkpoint must be a mapping")
    try:
        values = copy.deepcopy(dict(checkpoint["values"]))
        applied_ids = list(checkpoint["applied_ids"])
        raw_seen = dict(checkpoint["seen"])
        last_sequence = checkpoint["last_sequence"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ReconciliationError("checkpoint has an invalid shape") from exc
    if (
        isinstance(last_sequence, bool)
        or not isinstance(last_sequence, int)
        or last_sequence < -1
    ):
        raise ReconciliationError("checkpoint last_sequence is invalid")
    seen = {event_id: _canonical_event(event) for event_id, event in raw_seen.items()}
    if list(seen) != applied_ids or set(applied_ids) != set(seen):
        raise ReconciliationError("checkpoint applied_ids and seen disagree")
    if seen and max(event["sequence"] for event in seen.values()) != last_sequence:
        raise ReconciliationError("checkpoint last_sequence disagrees with seen events")
    if not seen and last_sequence != -1:
        raise ReconciliationError("empty checkpoint must have last_sequence -1")
    return {
        "values": values,
        "applied_ids": applied_ids,
        "seen": seen,
        "last_sequence": last_sequence,
    }


def _summary(state: Mapping[str, Any]) -> dict[str, Any]:
    numeric_total = sum(
        float(value)
        for value in state["values"].values()
        if not isinstance(value, bool) and isinstance(value, (int, float))
    )
    return {
        "applied_count": len(state["applied_ids"]),
        "key_count": len(state["values"]),
        "last_sequence": state["last_sequence"],
        "numeric_total": numeric_total,
    }


def reconcile_reference(
    events: Sequence[Mapping[str, Any]],
    checkpoint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and reconcile a batch without mutating either input.

    Events are applied in ``(sequence, id)`` order. Identical duplicate ids are
    ignored; conflicting duplicate ids fail the whole call. An unseen event at
    or before a checkpoint's last sequence is rejected because replay cannot
    safely insert history that has already been materialised.
    """

    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise ReconciliationError("events must be a sequence")
    state = _canonical_checkpoint(checkpoint)
    incoming: dict[str, dict[str, Any]] = {}
    for raw in events:
        event = _canonical_event(raw)
        event_id = event["id"]
        prior = incoming.get(event_id) or state["seen"].get(event_id)
        if prior is not None:
            if prior != event:
                raise ReconciliationError(f"conflicting duplicate id: {event_id}")
            continue
        if event["sequence"] <= state["last_sequence"]:
            raise ReconciliationError(f"unseen stale event: {event_id}")
        incoming[event_id] = event

    for event in sorted(incoming.values(), key=lambda item: (item["sequence"], item["id"])):
        op = event["op"]
        key = event["key"]
        if op == "set":
            state["values"][key] = copy.deepcopy(event["value"])
        elif op == "increment":
            current = state["values"].get(key, 0)
            if (
                isinstance(current, bool)
                or not isinstance(current, (int, float))
                or not math.isfinite(float(current))
            ):
                raise ReconciliationError(f"cannot increment non-numeric key: {key}")
            state["values"][key] = current + event["value"]
        else:
            state["values"].pop(key, None)
        state["applied_ids"].append(event["id"])
        state["seen"][event["id"]] = copy.deepcopy(event)
        state["last_sequence"] = event["sequence"]

    state["summary"] = _summary(state)
    return state


__all__ = ["ReconciliationError", "reconcile_reference"]

