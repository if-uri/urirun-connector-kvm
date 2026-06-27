# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Emiter neutralnego ``contracts.json`` z dataclass-owego ŹRÓDŁA PRAWDY (contracts.py).

To jest warunek konieczny polyglota: contracts.json NIE jest ręczną kopią (to byłby
pierwotny dryf ×N języków), tylko ARTEFAKTEM GENEROWANYM z jedynej deklaracji w Pythonie.
Każdy język (py/js/go) czyta TEN SAM wygenerowany plik — emiter jest jedynym mostem
między dataclassą a neutralnym formatem.

Uruchom:  PYTHONPATH=<toolkit> python xlang/emit_contracts.py
Wynik:    xlang/contracts.json  (schemaVersion 1; klucz inverse_route → inverseRoute)
"""
from __future__ import annotations

import json
import os

from urirun_connector_kvm.contracts import CONTRACTS, WIRES

HERE = os.path.dirname(os.path.abspath(__file__))


def _contract_to_json(c) -> dict:
    # inp/out to już czysty mini-język schematu (str/dict/list) → serializuje się wprost.
    # tuples (errors, examples) → listy JSON. inverse_route → camelCase inverseRoute (null gdy brak).
    return {
        "version": c.version,
        "effect": c.effect,
        "reversible": c.reversible,
        "inverseRoute": c.inverse_route or None,
        "inp": c.inp,
        "out": c.out,
        "errors": list(c.errors),
        "examples": [dict(ex) for ex in c.examples],
    }


def build_doc() -> dict:
    return {
        "schemaVersion": 1,
        "source": "urirun_connector_kvm/contracts.py (dataclass) — GENERATED, do not hand-edit",
        "contracts": {route: _contract_to_json(c) for route, c in CONTRACTS.items()},
        "wires": [
            {"producer": w.producer, "consumer": w.consumer,
             "mapping": w.mapping, "note": w.note}
            for w in WIRES
        ],
    }


def main() -> int:
    doc = build_doc()
    out_path = os.path.join(HERE, "contracts.json")
    with open(out_path, "w") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {out_path}: {len(doc['contracts'])} kontraktów, {len(doc['wires'])} krawędzi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
