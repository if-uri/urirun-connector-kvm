#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Python-owy uczestnik wymiany — ładuje NEUTRALNY contracts.json (nie obiekty Pythona)
i reużywa funkcji kernela z contract_gate. Dowód, że kernel jest sterowany KSZTAŁTEM
danych (.inp/.out), więc działa identycznie niezależnie od tego, czy kontrakt przyszedł
z dataclassy, z JSON-a, czy z proto. CLI lustrzane do peer.mjs i peer.go → spinalne potokiem.

  produce <route>        — wypisz złotą kopertę ok jako JSON
  consume <prod> <cons>  — wczytaj JSON ze stdin, zbuduj wejście konsumenta, zwaliduj
  serve [--lie]          — serwer RPC (JSON-lines/stdio): {route,payload} → koperta. Cel
                           zewnętrznego drivera konformansu. --lie modeluje błąd
                           SERIALIZACJI po walidacji in-language (int→string na drucie).
  serve-http [--lie]     — TEN SAM handler za DRUGIM transportem (HTTP POST /). Port
                           efemeryczny; węzeł wypisuje "READY <port>". Cel dowodu
                           niezmienniczości transportu: ten sam URI → ta sama koperta.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

DOC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts.json")))
# neutralny JSON → lekkie obiekty z .inp/.out/... (kernel czyta tylko te atrybuty)
CONTRACTS = {route: SimpleNamespace(**{**c, "inverse_route": c.get("inverseRoute") or ""})
             for route, c in DOC["contracts"].items()}
WIRES = [SimpleNamespace(**w) for w in DOC["wires"]]

from urirun_connectors_toolkit.contract_gate import (  # noqa: E402
    consumer_input_check,
    wire_payload,
)


def _find_wire(producer: str, consumer: str):
    for w in WIRES:
        if w.producer == producer and w.consumer == consumer:
            return w
    raise KeyError(f"brak krawędzi {producer} -> {consumer}")


def _ok_example(route: str) -> dict:
    for ex in CONTRACTS[route].examples:
        if ex["result"].get("ok"):
            return ex["result"]
    raise SystemExit(f"{route}: brak złotej koperty ok")


def _clone_ok_example(route: str) -> dict:
    return json.loads(json.dumps(_ok_example(route)))


def handle(route: str, payload: dict, lie: bool = False) -> dict:
    """Prawdziwy handler trasy (stub) — LICZY kopertę z payloadu, nie zwraca złotego przykładu
    (inaczej dowód byłby cyrkularny). To jest „node" odpytywany przez zewnętrzny driver."""
    if route == "screen/query/capture":
        return {"ok": True, "connector": "kvm", "action": "capture", "kind": "screenshot",
                "path": "~/.urirun/artifacts/s.png", "bytes": 204931,
                "fullSize": [2560, 1440], "via": "py-serve"}
    if route == "abs/command/click":
        sw, sh = payload.get("sw", 1920), payload.get("sh", 1080)
        screen = [str(sw), str(sh)] if lie else [sw, sh]  # --lie: int→string na drucie
        return {"ok": True, "connector": "kvm", "action": "click-abs", "screen": screen,
                "did": f"click@({payload.get('x', 0)},{payload.get('y', 0)})"}
    if route == "window/command/close":
        snap = {"url": "https://example.test/x", "scrollX": 0, "scrollY": 240,
                "forms": [], "id": payload.get("id", "active")}
        return {"ok": True, "connector": "kvm", "action": "window-close",
                "did": f"close({snap['id']})", "reversible": True, "snapshot": snap,
                "inverse": {"path": "window/command/restore", "args": {"snapshot": snap}}}
    if route == "window/command/restore":
        snap = payload.get("snapshot") or {}
        wid = snap.get("id", "active")
        return {"ok": True, "connector": "kvm", "action": "window-restore",
                "did": f"restore({wid})", "reversible": True,
                "inverse": {"path": "window/command/close", "args": {"id": wid}}}
    if route == "cdp/page/command/navigate":
        url = payload.get("url", "https://example.test/a")
        return {"ok": True, "connector": "kvm", "action": "cdp-navigate",
                "url": url, "ready": {"ok": True, "readyState": "complete"},
                "inverse": {"path": "cdp/page/command/navigate",
                            "args": {"url": "https://example.test/prev"}}}
    if route == "ui/command/fill":
        value = payload.get("value", "")
        text = payload.get("text", "field")
        return {"ok": True, "connector": "kvm", "action": "ui-fill",
                "inverse": {"path": "ui/command/fill",
                            "args": {"text": text, "value": "prev-value"}}}
    if route in CONTRACTS:
        return _clone_ok_example(route)
    raise KeyError(route)


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "serve":
        lie = "--lie" in sys.argv[2:]
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            env = handle(req["route"], req.get("payload") or {}, lie)
            sys.stdout.write(json.dumps({"id": req.get("id"), "envelope": env}) + "\n")
            sys.stdout.flush()
        return 0
    if cmd == "serve-http":
        from http.server import BaseHTTPRequestHandler, HTTPServer
        lie = "--lie" in sys.argv[2:]

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # cisza
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n) or b"{}")
                env = handle(req["route"], req.get("payload") or {}, lie)
                body = json.dumps({"id": req.get("id"), "envelope": env}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = HTTPServer(("127.0.0.1", 0), H)
        print(f"READY {srv.server_address[1]}", flush=True)
        srv.serve_forever()
        return 0
    if cmd == "produce":
        json.dump(_ok_example(sys.argv[2]), sys.stdout)
        return 0
    if cmd == "consume":
        producer, consumer = sys.argv[2], sys.argv[3]
        envelope = json.load(sys.stdin)
        wire = _find_wire(producer, consumer)
        payload = wire_payload(wire, envelope)
        mode, problems = consumer_input_check(CONTRACTS[consumer], payload, wire)
        json.dump({"ok": not problems, "mode": mode, "builtInput": payload, "problems": problems},
                  sys.stdout)
        return 0 if not problems else 1
    raise SystemExit(f"nieznany tryb {cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())
