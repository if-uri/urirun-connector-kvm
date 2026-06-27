#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Zewnętrzny driver konformansu — odpytuje KAŻDY węzeł po jego prawdziwym transporcie
i waliduje ODPOWIEDŹ wobec wspólnego kontraktu. To łapie to, czego round-trip NIE łapie:
węzeł może przejść własną bramę in-language, a wciąż KŁAMAĆ na drucie (bug serializacji).

Round-trip (run.sh) sprawdzał KONSUMPCJĘ: czy konsument umie zbudować poprawne wejście.
Driver sprawdza PRODUKCJĘ przez transport: czy handler węzła, odpytany po jego adresie,
emituje kopertę zgodną z `out`. Walidację robi STRONA TRZECIA trzymająca kontrakt —
węzeł ufający sobie nigdy nie złapie własnego buga wyjścia.

Złote przykłady stają się językowo-neutralnym KORPUSEM TESTOWYM: „implementacja X w języku L
jest zgodna" = „dla każdego przykładowego payloadu handler L produkuje wyjście pasujące do out".

Transport: JSON-lines RPC po stdin/stdout podprocesu (prawdziwa granica procesu + serializacja).
Uruchom przez ./driver.sh (ustawia PYTHONPATH, regeneruje contracts.json, buduje peer_go).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from urirun_connectors_toolkit.contract_gate import Contract, envelope_violation

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = json.load(open(os.path.join(HERE, "contracts.json")))
CONTRACTS = {
    r: Contract(version=c["version"], effect=c["effect"], reversible=c["reversible"],
                inverse_route=c.get("inverseRoute") or "", inp=c["inp"], out=c["out"],
                errors=tuple(c["errors"]), examples=tuple(c["examples"]))
    for r, c in DOC["contracts"].items()
}

NODES = {
    "py": [sys.executable, os.path.join(HERE, "peer.py"), "serve"],
    "js": ["node", os.path.join(HERE, "peer.mjs"), "serve"],
    "go": [os.path.join(HERE, "peer_go"), "serve"],
}


class Node:
    """Węzeł osiągalny po transporcie — driver NIE współdzieli z nim obiektu, tylko bajty."""

    def __init__(self, cmd: list[str], lie: bool = False):
        self.proc = subprocess.Popen(
            list(cmd) + (["--lie"] if lie else []),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, cwd=HERE)

    def call(self, route: str, payload: dict) -> dict:
        self.proc.stdin.write(json.dumps({"id": 1, "route": route, "payload": payload}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"węzeł nie odpowiedział na {route}")
        return json.loads(line)["envelope"]

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def drive(lie: bool = False):
    """Dla każdego węzła × każdej trasy × każdego złotego payloadu: odpytaj i zwaliduj wyjście.
    Zwraca [(node, route, ex_idx, violation_or_None)]."""
    rows = []
    for name, cmd in NODES.items():
        node = Node(cmd, lie=lie)
        try:
            for route, contract in CONTRACTS.items():
                for i, ex in enumerate(contract.examples):
                    env = node.call(route, ex["payload"])
                    rows.append((name, route, i, envelope_violation(contract, env)))
        finally:
            node.close()
    return rows


def main() -> int:
    print("== driver konformansu: odpytaj każdy węzeł po transporcie, zwaliduj WYJŚCIE wobec out ==")
    rows = drive(lie=False)
    bad = [r for r in rows if r[3] is not None]
    by_node = {}
    for name, route, _, viol in rows:
        by_node.setdefault(name, []).append(viol)
    for name, viols in by_node.items():
        ok = sum(1 for v in viols if v is None)
        badge = "WIRE-HONEST" if ok == len(viols) else "!! KŁAMIE  "
        print(f"  [{badge}] {name}: {ok}/{len(viols)} odpowiedzi zgodnych z kontraktem przez transport")
    for name, route, i, viol in bad:
        print(f"      FAIL {name} {route}#ex{i}: {viol}")

    print()
    print("== ten sam driver z węzłami --lie (int→string na drucie PO walidacji in-language) ==")
    print("   (każdy węzeł przeszedłby własną bramę wejścia; tylko driver trzyma kontrakt wyjścia)")
    lie_rows = drive(lie=True)
    caught = {}
    for name, route, i, viol in lie_rows:
        if route == "abs/command/click":
            caught.setdefault(name, viol)
    teeth_ok = True
    for name, viol in caught.items():
        if viol is None:
            teeth_ok = False
            print(f"  [!! PRZESZŁO !!] {name}: driver NIE złapał kłamstwa na drucie")
        else:
            print(f"  [ZŁAPANE] {name} abs/command/click: {viol}")

    print()
    if not bad and teeth_ok:
        print("OK: uczciwe węzły zgodne przez transport; kłamiące złapane przez stronę trzecią.")
        return 0
    print("BŁĄD: patrz wyżej.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
