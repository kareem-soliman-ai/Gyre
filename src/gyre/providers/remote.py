"""Remote measurement: run the scoring somewhere else, keep the loop unchanged.

This is the piece that lets a proprietary measurement stay off your machine
entirely. ``RemoteMeasurementProvider`` implements the same
``MeasurementProvider`` protocol as any local sensor, but instead of computing a
reading it serialises the observation, hands it to a transport (an HTTP call to a
hosted scoring service, by default), and reconstructs the ``Measurement`` from the
response. The loop calling it cannot tell the difference between this and a local
provider. That is the whole point: the interface is transport-agnostic, so the
scoring logic can live behind an API and the client here carries none of it.

What ships publicly is exactly this file: an HTTP client and a serialisation
convention. No scoring, no thresholds, no model. Those live server-side. An
engineer gets the client and an API key; they never see the instrument.

Positioning, stated honestly so nobody is surprised: a network call per loop
iteration adds latency, and a hosted endpoint is a dependency. This is built for
evaluation, demonstration, and low-stakes use, plus a self-host path for anyone
who wants the scoring in-process. It is not a thing to put on an agent's critical
path in production on someone else's uptime. See docs/hosted-measurements.md.

Dependencies: standard library only (``urllib`` for the default transport).
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from gyre.measurement import Measurement

# A transport takes a JSON-safe request dict and returns a JSON-safe response dict.
Transport = Callable[[dict], dict]


def _encode_observation(observation: Any) -> Any:
    """Turn an observation into something JSON can carry.

    Handles the built-in observation dataclasses, any dataclass, plain objects
    with a ``__dict__``, and raw dicts. Anything else must be made JSON-safe by
    the caller.
    """
    if is_dataclass(observation) and not isinstance(observation, type):
        return asdict(observation)
    if isinstance(observation, dict):
        return observation
    if hasattr(observation, "__dict__"):
        return {k: v for k, v in vars(observation).items() if not k.startswith("_")}
    return observation


class RemoteMeasurementProvider:
    """A sensor whose scoring happens elsewhere, behind a transport.

    Args:
        loop_id: which loop's construct the remote scorer measures. Must match the
            loop it is wired into, same as any provider.
        name: identifier for provenance and the benchmark.
        transport: a callable that takes a request dict and returns a response
            dict. In production this is an HTTP client (see ``http_transport``); in
            tests it is an in-process fake, which is how the whole remote path is
            proven without a network or any cloud spend.
        session_id: opaque handle the server uses to key any per-run state (a
            remote provider is usually stateful: it models a baseline, a rolling
            window). ``reset`` tells the server to drop it.
    """

    def __init__(
        self,
        loop_id: str,
        name: str,
        transport: Transport,
        *,
        session_id: str = "default",
    ) -> None:
        self.loop_id = loop_id
        self.name = name
        self._transport = transport
        self._session = session_id

    def measure(self, observation: Any) -> Measurement:
        response = self._transport(
            {
                "op": "measure",
                "loop_id": self.loop_id,
                "session": self._session,
                "observation": _encode_observation(observation),
            }
        )
        return Measurement.from_dict(response)

    def reset(self) -> None:
        self._transport(
            {"op": "reset", "loop_id": self.loop_id, "session": self._session}
        )


def http_transport(
    endpoint: str,
    *,
    api_key: str | None = None,
    timeout: float = 10.0,
) -> Transport:
    """Build a transport that POSTs JSON to a hosted scoring endpoint.

    The wire contract is deliberately trivial: POST the request dict as JSON,
    expect a Measurement dict (``Measurement.to_dict`` form) back for a ``measure``
    op, or an empty object for ``reset``. Any server that honours that contract
    works, which keeps the client dumb and the interesting work server-side.
    """

    def transport(payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - caller supplies endpoint
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

    return transport
