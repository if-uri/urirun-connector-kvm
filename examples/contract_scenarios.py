#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Wiele scenariuszy, wiele URI — jedna brama (nowy pakiet ``urirun-contract``).

Odkrywa siostrzane pakiety scenariuszy ``urirun-contract-*`` (capture-click, windowpair, filepair,
kvstore), ładuje każdy WSPÓLNY ``contracts.json`` i — używając standalone gate'u ``urirun_contract`` —
sprawdza dla KAŻDEGO scenariusza:

  1. konformans KAŻDEJ trasy (URI): złoty payload pasuje do ``inp``, złota koperta do ``out``,
  2. KAŻDĄ krawędź WIRES: koperta producenta → wire_payload → consumer_input_check (FULL/PARTIAL),
  3. teeth: uszkodzona koperta (brak wymaganego klucza ``out``) jest ODRZUCona.

To jest „przetestuj wiele scenariuszy z wieloma URI" zrealizowane przez nową bramę kontraktu —
żaden scenariusz nie współdzieli kodu poza ``urirun_contract`` i swoim ``contracts.json``.

Uruchom:  python examples/contract_scenarios.py        (lub przez examples/contract_scenarios.sh)
"""
from __future__ import annotations

import glob
import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IFURI = os.path.dirname(REPO)
# nowy standalone pakiet bramy kontraktu
sys.path.insert(0, os.path.join(IFURI, "urirun-contract"))

from urirun_contract import (  # noqa: E402
    check,
    consumer_input_check,
    envelope_violation,
    find_wire,
    wire_payload,
)


def _load(path: str):
    doc = json.load(open(path))
    contracts = {r: SimpleNamespace(**{**c, "inverse_route": c.get("inverseRoute") or ""})
                 for r, c in doc["contracts"].items()}
    wires = [SimpleNamespace(**w) for w in doc.get("wires", [])]
    return contracts, wires


def _ok_example(c) -> dict | None:
    for ex in c.examples:
        if ex["result"].get("ok"):
            return ex["result"]
    return None


def _required_out_key(out) -> str | None:
    """Pierwszy wymagany, konkretnie-typowany klucz w schemacie out (do testu teeth)."""
    if isinstance(out, dict) and set(out) != {"oneOf"}:
        for k, v in out.items():
            if isinstance(v, str) and not v.startswith("?"):
                return k
    return None


def run_scenario(name: str, contracts_path: str) -> dict:
    contracts, wires = _load(contracts_path)
    report = {"name": name, "routes": [], "wires": [], "teeth": None, "problems": []}

    # 1. konformans każdej trasy (URI)
    for route, c in contracts.items():
        ok = True
        for i, ex in enumerate(c.examples):
            try:
                check(c.inp, ex["payload"], f"{route}#ex{i}.inp")
            except AssertionError as exc:
                ok = False
                report["problems"].append(f"{route}#ex{i} inp: {exc}")
            if ex["result"].get("ok"):
                v = envelope_violation(c, ex["result"])
                if v:
                    ok = False
                    report["problems"].append(f"{route}#ex{i} out: {v}")
        report["routes"].append((route, ok))

    # 2. każda krawędź WIRES (handoff producent → konsument)
    for w in wires:
        prod, cons = contracts[w.producer], contracts[w.consumer]
        env = _ok_example(prod)
        if env is None:
            report["problems"].append(f"{w.producer}: brak złotej koperty ok")
            report["wires"].append((w.producer, w.consumer, "?", False))
            continue
        payload = wire_payload(w, env)
        mode, problems = consumer_input_check(cons, payload, w)
        if problems:
            report["problems"].append(f"{w.producer}→{w.consumer}: {problems}")
        report["wires"].append((w.producer, w.consumer, mode, not problems))

    # 3. teeth: uszkodzona koperta odrzucona
    for route, c in contracts.items():
        env = _ok_example(c)
        key = _required_out_key(c.out)
        if env is not None and key is not None and key in env:
            broken = {k: v for k, v in env.items() if k != key}
            report["teeth"] = envelope_violation(c, broken) is not None
            break

    return report


def discover() -> list[tuple[str, str]]:
    found = []
    for d in sorted(glob.glob(os.path.join(IFURI, "urirun-contract-*"))):
        cj = os.path.join(d, "contracts.json")
        if os.path.isfile(cj):
            found.append((os.path.basename(d).replace("urirun-contract-", ""), cj))
    return found


def main() -> int:
    scenarios = discover()
    if not scenarios:
        print("SKIP: brak siostrzanych pakietów urirun-contract-* z contracts.json")
        return 0
    print(f"== {len(scenarios)} scenariuszy kontraktów (urirun-contract-*), brama: urirun_contract ==")
    total_uris = total_wires = 0
    failed = 0
    for name, path in scenarios:
        r = run_scenario(name, path)
        routes_ok = sum(1 for _, ok in r["routes"] if ok)
        wires_ok = sum(1 for *_, ok in r["wires"] if ok)
        total_uris += len(r["routes"])
        total_wires += len(r["wires"])
        wire_desc = ", ".join(f"{p.split('/')[0]}→{c.split('/')[0]}:{m}{'✓' if ok else '✗'}"
                              for p, c, m, ok in r["wires"])
        teeth = {True: "ZŁAPANE", False: "!! PRZESZŁO", None: "n/a"}[r["teeth"]]
        ok = (routes_ok == len(r["routes"]) and wires_ok == len(r["wires"])
              and r["teeth"] in (True, None))
        badge = "OK " if ok else "BŁĄD"
        print(f"  [{badge}] {name:<14} URI {routes_ok}/{len(r['routes'])} zgodne · "
              f"wire [{wire_desc}] · teeth {teeth}")
        for p in r["problems"]:
            print(f"          ! {p}")
        if not ok:
            failed += 1

    print()
    if failed == 0:
        print(f"OK: {len(scenarios)} scenariuszy, {total_uris} URI, {total_wires} krawędzi — "
              f"wszystkie zgodne przez jedną bramę; korupcja odrzucana.")
        return 0
    print(f"BŁĄD: {failed}/{len(scenarios)} scenariuszy ma problemy (patrz wyżej).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
