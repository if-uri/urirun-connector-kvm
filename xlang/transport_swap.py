#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Dowód NIEZMIENNICZOŚCI TRANSPORTU, uogólniony na języki.

Teza: tożsamość operacji to URI, NIE transport. Ten sam węzeł, odpytany o tę samą trasę
z tym samym payloadem, MUSI zwrócić tę samą kopertę — niezależnie czy po stdio czy po HTTP.
Jeśli koperta zależy od transportu, „kontrakt" był naprawdę szczegółem transportu.

Dla każdego języka (py/js/go) uruchamiamy DWA serwery tego samego handlera za DWOMA
transportami i sprawdzamy trzy rzeczy na każdej trasie × złotym payloadzie:
  1. koperta ze stdio jest zgodna z `out`,
  2. koperta z HTTP jest zgodna z `out`,
  3. obie koperty są IDENTYCZNE (URI → koperta, transport nie wnosi nic do treści).

Uruchom przez ./transport_swap.sh (PYTHONPATH + regeneracja contracts.json + build go).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

from urirun_connectors_toolkit.contract_gate import envelope_violation

from conformance_driver import CONTRACTS, Node as StdioNode  # reuse: stdio JSON-lines + kontrakty

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = {
    "py": [sys.executable, os.path.join(HERE, "peer.py")],
    "js": ["node", os.path.join(HERE, "peer.mjs")],
    "go": [os.path.join(HERE, "peer_go")],
}
# Rust — OPCJONALNY czwarty węzeł: dołączany tylko gdy zbudowany peer_rs istnieje.
if os.path.exists(os.path.join(HERE, "peer_rs")):
    BASE["rs"] = [os.path.join(HERE, "peer_rs")]


class HttpNode:
    """Ten sam handler za HTTP. Czyta 'READY <port>' z stdout (port efemeryczny — zero kolizji)."""

    def __init__(self, cmd: list[str]):
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, cwd=HERE)
        line = self.proc.stdout.readline()
        if not line.startswith("READY"):
            raise RuntimeError(f"serwer http nie wystartował: {line!r}")
        self.port = int(line.split()[1])

    def call(self, route: str, payload: dict) -> dict:
        data = json.dumps({"id": 1, "route": route, "payload": payload}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())["envelope"]

    def close(self):
        self.proc.terminate()
        self.proc.wait()


def main() -> int:
    print("== niezmienniczość transportu: ten sam węzeł × stdio vs HTTP, ta sama koperta? ==")
    overall_ok = True
    for name, base in BASE.items():
        stdio = StdioNode(base + ["serve"])
        http = HttpNode(base + ["serve-http"])
        checks = mism = noncomp = 0
        detail = []
        try:
            for route, contract in CONTRACTS.items():
                for ex in contract.examples:
                    a = stdio.call(route, ex["payload"])
                    b = http.call(route, ex["payload"])
                    checks += 1
                    if envelope_violation(contract, a) or envelope_violation(contract, b):
                        noncomp += 1
                        detail.append(f"      NIEZGODNE {route}")
                    if a != b:
                        mism += 1
                        detail.append(f"      ROZBIEŻNE {route}: stdio≠http")
        finally:
            stdio.close()
            http.close()
        ok = (mism == 0 and noncomp == 0)
        overall_ok = overall_ok and ok
        badge = "TRANSPORT-INVARIANT" if ok else "!! ZALEŻNE OD TRANSPORTU"
        print(f"  [{badge}] {name}: {checks} tras × 2 transporty, "
              f"{checks - mism}/{checks} koperta identyczna, {checks - noncomp}/{checks} zgodna z out")
        for d in detail:
            print(d)

    print()
    if overall_ok:
        print("OK: dla każdego języka URI determinuje kopertę — transport jest wymienny.")
        return 0
    print("BŁĄD: koperta zależy od transportu (patrz wyżej).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
