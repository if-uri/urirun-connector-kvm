# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Eksporter mini-języka kontraktu → STANDARDOWY JSON Schema (draft 2020-12).

Krok poza „N ręcznie pisanych czytników": neutralne źródło ma feedować też konsumentów
NIEPISANYCH RĘCZNIE — codegen, bramy API, tooling IDE — które czytają standardowy schemat,
nie nasz mini-język. Ten eksporter tłumaczy ten sam dataclass-owy ŹRÓDŁO PRAWDY na JSON Schema,
więc dowolny zgodny ze specyfikacją walidator (tu: biblioteka `jsonschema`) egzekwuje kontrakt
ZEROWYM własnym kodem walidacji.

Mapowanie (mini-język → JSON Schema):
  str/int/num/bool/obj/list → {"type": ...}          any → {} (zawsze prawda)
  "?T"            → klucz NIE w `required` (reszta tak samo)
  "const:X"       → {"const": X}  (true/false → bool)
  "enum:a|b"      → {"enum": [...]}
  {...}           → {"type":"object","properties":{...},"required":[...]} ; additionalProperties:true
                    (klucze nadmiarowe SĄ dozwolone — koperta niesie też ok/connector/action)
  ["T"]           → {"type":"array","items": <T>}
  {"oneOf":[...]} → {"anyOf":[...]}   ← UWAGA: nasze oneOf = „pasuje do CO NAJMNIEJ jednego"
                                         (walidator zwraca przy pierwszym trafieniu) = anyOf, NIE oneOf

Uruchom:  PYTHONPATH=<repo>:<toolkit> python xlang/emit_jsonschema.py
Wynik:    xlang/contracts.schema.json
"""
from __future__ import annotations

import json
import os

from urirun_connector_kvm.contracts import CONTRACTS

HERE = os.path.dirname(os.path.abspath(__file__))

_LEAF = {
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "num": {"type": "number"},
    "bool": {"type": "boolean"},
    "obj": {"type": "object"},
    "list": {"type": "array"},
    "any": True,  # JSON Schema: `true` akceptuje wszystko
}


def _const(token: str):
    lit = token[len("const:"):]
    if lit == "true":
        return True
    if lit == "false":
        return False
    return lit


def to_schema(node):
    """Przetłumacz węzeł mini-języka na JSON Schema (draft 2020-12)."""
    if isinstance(node, dict) and set(node) == {"oneOf"}:
        # nasze oneOf to UNIA „co najmniej jeden" → anyOf (NIE oneOf z draftu, które jest XOR)
        return {"anyOf": [to_schema(b) for b in node["oneOf"]]}
    if isinstance(node, dict):
        props, required = {}, []
        for key, sub in node.items():
            optional = isinstance(sub, str) and sub.startswith("?")
            sub_t = sub[1:] if optional else sub
            props[key] = to_schema(sub_t)
            if not optional:
                required.append(key)
        out = {"type": "object", "properties": props}
        if required:
            out["required"] = required
        out["additionalProperties"] = True  # koperta niesie też ok/connector/action — dozwolone
        return out
    if isinstance(node, list):
        return {"type": "array", "items": to_schema(node[0])} if node else {"type": "array"}
    # token string
    s = node[1:] if isinstance(node, str) and node.startswith("?") else node
    if s.startswith("const:"):
        return {"const": _const(s)}
    if s.startswith("enum:"):
        return {"enum": s[len("enum:"):].split("|")}
    leaf = _LEAF.get(s)
    if leaf is None:
        raise ValueError(f"nieznany token schematu: {s!r}")
    return leaf


def build_doc() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "kvm:// route contracts — generated JSON Schema",
        "source": "urirun_connector_kvm/contracts.py (dataclass) — GENERATED, do not hand-edit",
        "routes": {
            route: {"input": to_schema(c.inp), "output": to_schema(c.out)}
            for route, c in CONTRACTS.items()
        },
    }


def main() -> int:
    doc = build_doc()
    out_path = os.path.join(HERE, "contracts.schema.json")
    with open(out_path, "w") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {out_path}: {len(doc['routes'])} tras → standardowy JSON Schema (draft 2020-12)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
