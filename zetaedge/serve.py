"""Tiny stdlib HTTP service around the certificate engine.

Endpoints (all JSON, all reproducible, no auth because it is meant to run on
localhost or inside a VPC):

  GET  /health
  GET  /zero/{index}                 γ of the index-th zero   (precomputed table)
  GET  /zeros?t_max=1000             verified zeros below a height
  POST /certify   {"n": "12345"}     certificate block
  POST /nextprime {"n": "12345"}     next prime + certificate
  GET  /bounds?x_max=10000000        RH error-bar audit

Run:  python -m zetaedge.serve --port 8788
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .bounds import gap_audit, pi_error_audit
from .certify import certificate, next_prime
from .explicit import audit_psi_bound, audit_pi_bound
from .zeros import find_zeros

_ZEROS: list[float] = []
_ZERO_LOCK = threading.Lock()
_ZERO_HEIGHT = 0.0


def zeros_upto(t: float) -> list[float]:
    """Memoized zero table; grows monotonically with the requested height."""
    global _ZEROS, _ZERO_HEIGHT
    with _ZERO_LOCK:
        if t <= _ZERO_HEIGHT and _ZEROS:
            return [g for g in _ZEROS if g <= t]
        _ZEROS = [z.gamma for z in find_zeros(t_max=t, t_min=0.5, step=0.25)]
        _ZERO_HEIGHT = t
        return _ZEROS


class Handler(BaseHTTPRequestHandler):
    server_version = "zetaedge/0.2"

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quiet by default
        pass

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/health":
                from . import __version__

                return self._send(200, {"ok": True, "version": __version__,
                                        "zeros_cached": len(_ZEROS), "height": _ZERO_HEIGHT})
            if u.path.startswith("/zero/"):
                idx = int(u.path.rsplit("/", 1)[1])
                g = zeros_upto(max(100.0, float(q.get("t_max", 1000))))
                if not 1 <= idx <= len(g):
                    return self._send(404, {"error": "index out of range", "available": len(g)})
                return self._send(200, {"index": idx, "gamma": g[idx - 1]})
            if u.path == "/zeros":
                g = zeros_upto(float(q.get("t_max", 100)))
                return self._send(200, {"count": len(g), "gammas": g[: int(q.get("limit", 50))]})
            if u.path == "/bounds":
                x = int(q.get("x_max", 10_000_000))
                return self._send(200, {
                    "psi": audit_psi_bound(x),
                    "pi": audit_pi_bound(min(x, 2_000_000)),
                    "gaps": {k: v for k, v in gap_audit(x).items() if k != "records"},
                    "pi_vs_R": {k: v for k, v in pi_error_audit(min(x, 2_000_000)).items() if k != "rows"},
                })
            return self._send(404, {"error": "unknown path"})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"error": repr(exc)})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw or b"{}")
            num = int(str(data.get("n", "0")), 0)
            if u.path == "/certify":
                return self._send(200, certificate(num).as_dict())
            if u.path == "/nextprime":
                p, scanned = next_prime(num)
                out = certificate(p).as_dict()
                out.update({"start": str(num), "next_prime": str(p), "delta": str(p - num),
                            "candidates_scanned": scanned})
                return self._send(200, out)
            return self._send(404, {"error": "unknown path"})
        except Exception as exc:  # noqa: BLE001
            return self._send(400, {"error": repr(exc)})


def serve(port: int = 8788, host: str = "127.0.0.1"):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"zetaedge listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    import argparse

    from . import __version__

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    serve(a.port, a.host)