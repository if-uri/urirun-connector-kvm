#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Python-owy uczestnik wymiany — ładuje NEUTRALNY contracts.json (nie obiekty Pythona)
i reużywa funkcji kernela z contract_gate. Dowód, że kernel jest sterowany KSZTAŁTEM
danych (.inp/.out), więc działa identycznie niezależnie od tego, czy kontrakt przyszedł
z dataclassy, z JSON-a, czy z proto. CLI lustrzane do peer.mjs i peer.go → spinalne potokiem.

  produce <route>        — wypisz złotą kopertę ok jako JSON
  consume <prod> <cons>  — wczytaj JSON ze stdin, zbuduj wejście konsumenta, zwaliduj
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


def main() -> int:
    cmd = sys.argv[1]
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
