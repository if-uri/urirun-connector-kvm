#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Dowód, że NIEPISANY RĘCZNIE konsument egzekwuje ten sam kontrakt.

Bierzemy wygenerowany `contracts.schema.json` (standardowy JSON Schema z tego samego źródła)
i walidujemy nim złoty korpus OFF-THE-SHELF walidatorem (`jsonschema`, implementacja specyfikacji
IETF) — ZEROWYM własnym kodem walidacji. Plus teeth: standardowy walidator ODRZUCA to samo
kłamstwo na drucie (int→string), które łapie nasz ręczny walidator. To pokazuje, że neutralne
źródło feeduje też codegen/bramy API/tooling, nie tylko ręcznie pisane czytniki py/js/go/rust.

Uruchom przez ./jsonschema_proof.sh (regeneruje oba artefakty i ustawia PYTHONPATH).
"""
from __future__ import annotations

import json
import os

from jsonschema import Draft202012Validator

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS = json.load(open(os.path.join(HERE, "contracts.json")))["contracts"]
SCHEMA = json.load(open(os.path.join(HERE, "contracts.schema.json")))["routes"]


def _valid(schema: dict, value) -> str | None:
    errs = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: e.path)
    if not errs:
        return None
    e = errs[0]
    loc = "/".join(str(p) for p in e.path) or "<root>"
    return f"{loc}: {e.message}"


def main() -> int:
    print("== off-the-shelf JSON Schema validator (jsonschema) na wygenerowanym schemacie ==")
    print("   (zero własnego kodu walidacji — konsument czyta standard, nie nasz mini-język)")
    checks = bad = 0
    for route, c in CONTRACTS.items():
        rs = SCHEMA[route]
        for i, ex in enumerate(c["examples"]):
            checks += 1
            vin = _valid(rs["input"], ex["payload"])
            vout = _valid(rs["output"], ex["result"]) if ex["result"].get("ok") else None
            if vin or vout:
                bad += 1
                print(f"  FAIL {route}#ex{i}: in={vin} out={vout}")
    print(f"  [{'OK' if bad == 0 else 'FAIL'}] {checks - bad}/{checks} złotych przykładów "
          f"zwalidowanych standardowym walidatorem przeciw wygenerowanemu schematowi")

    print()
    print("== teeth: standardowy walidator odrzuca to samo kłamstwo na drucie (int→string) ==")
    lie = {"ok": True, "connector": "kvm", "action": "click-abs",
           "screen": ["2560", "1440"], "did": "click@(0,0)"}  # screen jako stringi
    verdict = _valid(SCHEMA["abs/command/click"]["output"], lie)
    teeth_ok = verdict is not None
    badge = "ZŁAPANE" if teeth_ok else "!! PRZESZŁO !!"
    print(f"  [{badge}] abs/command/click.output: {verdict}")

    print()
    if bad == 0 and teeth_ok:
        print("OK: standardowe tooling egzekwuje kontrakt z neutralnego źródła — bez ręcznego walidatora.")
        return 0
    print("BŁĄD: patrz wyżej.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
