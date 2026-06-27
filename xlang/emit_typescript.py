# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Eksporter mini-języka kontraktu → TYPY TypeScript (.d.ts) z tego samego źródła prawdy.

Dotąd egzekwowaliśmy kontrakt w RUNTIME (py/js/go/rust + JSON Schema). Ten krok przenosi
egzekucję do CZASU KOMPILACJI: z `contracts.py` generujemy typy TS, więc konsument w TS dostaje
sprawdzanie kontraktu ZANIM program się uruchomi. To samo kłamstwo na drucie (screen jako stringi)
staje się BŁĘDEM KOMPILACJI, a nie dopiero błędem walidacji w locie.

Mapowanie (mini-język → TypeScript):
  str→string  int/num→number  bool→boolean  obj→Record<string,unknown>  list→unknown[]  any→unknown
  "?T"            → własność opcjonalna  "key"?: T
  "const:X"      → literał  "X"  (true/false → boolean literal)
  "enum:a|b"     → "a" | "b"
  {...}          → typ obiektowy z indeksem `[k: string]: unknown` (koperta niesie też ok/connector/action)
  ["T"]          → T[]
  {"oneOf":[...]}→ unia A | B

Uruchom:  PYTHONPATH=<repo>:<toolkit> python xlang/emit_typescript.py
Wynik:    xlang/ts/contracts.d.ts
"""
from __future__ import annotations

import json
import os

from urirun_connector_kvm.contracts import CONTRACTS

HERE = os.path.dirname(os.path.abspath(__file__))

_LEAF = {
    "str": "string", "int": "number", "num": "number", "bool": "boolean",
    "obj": "Record<string, unknown>", "list": "unknown[]", "any": "unknown",
}


def _const(token: str) -> str:
    lit = token[len("const:"):]
    if lit in ("true", "false"):
        return lit
    return json.dumps(lit)  # literał stringowy w cudzysłowie


def ts_type(node, indent: int = 0) -> str:
    if isinstance(node, dict) and set(node) == {"oneOf"}:
        return " | ".join(ts_type(b, indent) for b in node["oneOf"])
    if isinstance(node, dict):
        pad = "  " * (indent + 1)
        lines = []
        for key, sub in node.items():
            optional = isinstance(sub, str) and sub.startswith("?")
            sub_t = sub[1:] if optional else sub
            q = "?" if optional else ""
            lines.append(f'{pad}{json.dumps(key)}{q}: {ts_type(sub_t, indent + 1)};')
        # indeks: klucze nadmiarowe dozwolone (koperta zawsze niesie ok/connector/action)
        lines.append(f'{pad}[k: string]: unknown;')
        return "{\n" + "\n".join(lines) + "\n" + ("  " * indent) + "}"
    if isinstance(node, list):
        return (ts_type(node[0], indent) + "[]") if node else "unknown[]"
    s = node[1:] if isinstance(node, str) and node.startswith("?") else node
    if s.startswith("const:"):
        return _const(s)
    if s.startswith("enum:"):
        return " | ".join(json.dumps(v) for v in s[len("enum:"):].split("|"))
    leaf = _LEAF.get(s)
    if leaf is None:
        raise ValueError(f"nieznany token schematu: {s!r}")
    return leaf


def _sanitize(route: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in route)


def build() -> str:
    out = [
        "// GENERATED z urirun_connector_kvm/contracts.py (dataclass) — nie edytuj ręcznie.",
        "// Te same kontrakty co contracts.json/contracts.schema.json, ale jako typy czasu kompilacji.",
        "",
    ]
    entries = []
    for route, c in CONTRACTS.items():
        s = _sanitize(route)
        out.append(f"export type In_{s} = {ts_type(c.inp)};")
        out.append(f"export type Out_{s} = {ts_type(c.out)};")
        out.append("")
        entries.append(f'  {json.dumps(route)}: {{ input: In_{s}; output: Out_{s} }};')
    out.append("export interface Contracts {")
    out.extend(entries)
    out.append("}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    path = os.path.join(HERE, "ts", "contracts.d.ts")
    with open(path, "w") as fh:
        fh.write(build())
    print(f"wrote {path}: {len(CONTRACTS)} tras → typy TypeScript (czas kompilacji)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
