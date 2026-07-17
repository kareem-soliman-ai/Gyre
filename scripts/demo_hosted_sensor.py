"""E5 — the hosted-instrument round trip, live.

The claim in docs/hosted-measurements.md, demonstrated end to end on one
machine: a validated sensor can run BEHIND AN API and the loop cannot tell.
This script

1. starts a local HTTP scoring service (stdlib http.server) that holds the
   best sensor available in this checkout server-side — the proprietary
   ``psy:evi-semantic`` when the private layer is present, the public
   ``naive:evidence-novelty`` otherwise (same demo, humbler instrument);
2. builds a ``RemoteMeasurementProvider`` pointed at it — the exact client an
   engineer would get with an API key: transport + serialisation, no scoring,
   no thresholds, no model;
3. scores the same synthetic corpus twice, once with the in-process sensor and
   once through the wire, and prints both score rows plus per-call latency.

The two rows must be identical: the wire is transparent to the loop. What the
client never receives is the instrument — embeddings, ceilings, and state all
stay server-side. That is the whole hosted-measurement seam: engineers keep
their own loops and point the provider seam at an endpoint.

Pure stdlib + gyre. Usage: python scripts/demo_hosted_sensor.py
"""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.bench import evaluate_provider
from gyre.loops.rumination import IterationObservation
from gyre.providers import EvidenceNoveltyProvider
from gyre.providers.remote import RemoteMeasurementProvider, http_transport
from gyre.synthetic import gen_l1_corpus, gen_l1_evidence_corpus


def make_server_side_sensor():
    """The instrument that stays on the server. Best available in this checkout."""
    try:
        from gyre.embedding import make_embedder
        from gyre.providers.proprietary.evi_semantic import EviSemanticProvider

        p = EviSemanticProvider(embed=make_embedder("local"))
        p.name = "psy:evi-semantic"
        return p
    except Exception:  # noqa: BLE001 - public checkout: host the naive sensor instead
        return EvidenceNoveltyProvider()


class ScoringHandler(BaseHTTPRequestHandler):
    """The wire contract from gyre.providers.remote, server side: POST a request
    dict, get a Measurement dict back. Sessions key server-side sensor state."""

    sensors: dict[str, object] = {}
    sensor_factory = staticmethod(make_server_side_sensor)

    def do_POST(self):  # noqa: N802 - http.server API
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        session = payload.get("session", "default")
        sensor = self.sensors.setdefault(session, self.sensor_factory())
        if payload["op"] == "measure":
            obs = IterationObservation(**payload["observation"])
            body = json.dumps(sensor.measure(obs).to_dict()).encode()
        else:  # reset
            sensor.reset()
            body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the demo output clean
        return


def main() -> int:
    local = make_server_side_sensor()
    print(f"Server-side instrument: {local.name}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), ScoringHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Scoring service listening on http://127.0.0.1:{port}\n")

    calls, total_ms = [0], [0.0]
    base_transport = http_transport(f"http://127.0.0.1:{port}/score")

    def timed_transport(payload):
        t0 = time.perf_counter()
        out = base_transport(payload)
        total_ms[0] += (time.perf_counter() - t0) * 1000
        calls[0] += 1
        return out

    remote = RemoteMeasurementProvider("L1", f"hosted:{local.name}", timed_transport)

    traces = [st.trace for st in gen_l1_corpus() + gen_l1_evidence_corpus()]
    print(f"Scoring {len(traces)} synthetic traces, locally and over the wire...")
    s_local = evaluate_provider(local, traces)
    s_remote = evaluate_provider(remote, traces)
    server.shutdown()

    print(f"\n  {'provider':28} {'F1':>5} {'prec':>5} {'rec':>5} {'acc':>5}")
    print("  " + "-" * 54)
    for s in (s_local, s_remote):
        print(f"  {s.provider:28} {s.f1:5.2f} {s.precision:5.2f} {s.recall:5.2f} {s.accuracy:5.2f}")

    identical = (s_local.f1, s_local.precision, s_local.recall, s_local.accuracy) == (
        s_remote.f1, s_remote.precision, s_remote.recall, s_remote.accuracy)
    print(f"\n  identical scores: {identical}")
    print(f"  wire overhead: {calls[0]} calls, {total_ms[0] / max(calls[0], 1):.1f} ms/call mean "
          f"(loopback; a real endpoint adds network latency — see docs/hosted-measurements.md)")
    print("\n  The loop code cannot tell the difference. The instrument never left the server.")
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
