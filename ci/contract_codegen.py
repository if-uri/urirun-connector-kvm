#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Generator szkieletów handlerów Z kontraktu — domyka pętlę deklaracja→kod tam, gdzie
LLM jest najmocniejszy. Model edytuje DEKLARACJĘ (contracts.py); build GENERUJE sygnaturę
i kształt koperty; jedyne, co pisze człowiek/LLM ręcznie, to CIAŁO logiki. Kontrakt nie
może zdryfować, bo jego kształt jest generowany, nie przepisywany.

Wpina się w istniejący ``connector_scaffold.py`` (_python_files / _js_files / _go_files),
więc to nie nowy mechanizm — to zasilenie scaffoldu kontraktem zamiast pustym szablonem.

  py  <route>   — szkielet handlera Pythona (@conn.handler + sygnatura z inp + koperta z out)
  js  <route>   — odpowiednik JS
  go  <route>   — odpowiednik Go
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")
from urirun_connector_kvm.contracts import CONTRACTS  # noqa: E402

# token schematu → (typ Pythona, domyślna wartość)
_PY = {"str": ("str", '""'), "int": ("int", "0"), "num": ("float", "0.0"),
       "bool": ("bool", "False"), "obj": ("dict | None", "None"),
       "list": ("list | None", "None"), "any": ("object", "None")}
_JS = {"str": '""', "int": "0", "num": "0", "bool": "false",
       "obj": "null", "list": "null", "any": "null"}
_GO = {"str": '""', "int": "0", "num": "0", "bool": "false",
       "obj": "nil", "list": "nil", "any": "nil"}


def _base(tok: str) -> str:
    return tok[1:] if tok.startswith("?") else tok


def _snake(route: str) -> str:
    return route.split("/")[-1].replace("-", "_")


def _camel(route: str) -> str:
    last = route.split("/")[-1]
    parts = last.replace("-", "_").split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _const(tok: str):
    lit = tok[len("const:"):]
    return True if lit == "true" else False if lit == "false" else lit


# ── kształt koperty z out-schematu (rekurencyjnie) ──────────────────────────
def _py_value(schema):
    if isinstance(schema, dict):
        if set(schema) == {"oneOf"}:
            return "{}  # oneOf: " + " | ".join(
                "{" + ",".join(sorted(b)) + "}" for b in schema["oneOf"])
        inner = ", ".join(f'"{k}": {_py_value(v)}' for k, v in schema.items())
        return "{" + inner + "}"
    if isinstance(schema, list):
        return "[]"
    s = _base(schema)
    if s.startswith("const:"):
        v = _const(s)
        return repr(v) if isinstance(v, str) else str(v)
    return {"str": '""', "int": "0", "num": "0.0", "bool": "False",
            "obj": "{}", "list": "[]", "any": "None"}.get(s, "None")


def py_stub(route: str) -> str:
    c = CONTRACTS[route]
    params = []
    for key, tok in c.inp.items():
        pytype, default = _PY[_base(tok)]
        params.append(f"{key}: {pytype} = {default}")
    sig = ", ".join(params) if params else ""
    label = f"TODO: {route}"
    if set(c.out) == {"oneOf"}:
        succ = c.out["oneOf"][0]
        body_kv = ", ".join(f'{k}={_py_value(v)}' for k, v in succ.items())
        ret = f"return _ok({body_kv})  # oneOf — wariant Degraded zwróć osobną gałęzią"
    else:
        body_kv = ", ".join(f'{k}={_py_value(v)}' for k, v in c.out.items())
        ret = f"return _ok({body_kv})"
    return f'''@conn.handler("{route}", isolated=True, meta={{"label": "{label}"}})
def {_snake(route)}({sig}) -> dict[str, Any]:
    """WYGENEROWANE Z KONTRAKTU {c.version}. Sygnatura i kształt koperty pochodzą z
    contracts.py — NIE edytuj ich ręcznie (build odrzuci dryf). Uzupełnij tylko ciało."""
    raise NotImplementedError("ciało {route}")  # noqa: F841 — uzupełnij logikę, potem:
    {ret}'''


def js_stub(route: str) -> str:
    c = CONTRACTS[route]
    dargs = ", ".join(f"{k} = {_JS[_base(t)]}" for k, t in c.inp.items())
    out = c.out["oneOf"][0] if set(c.out) == {"oneOf"} else c.out

    def jsval(v):
        if isinstance(v, dict):
            return "{" + ", ".join(f"{k}: {jsval(x)}" for k, x in v.items()) + "}"
        if isinstance(v, list):
            return "[]"
        s = _base(v)
        if s.startswith("const:"):
            cv = _const(s)
            return f'"{cv}"' if isinstance(cv, str) else str(cv).lower()
        return {"str": '""', "int": "0", "bool": "false", "obj": "{}", "list": "[]"}.get(s, "null")

    body = ", ".join(f"{k}: {jsval(v)}" for k, v in out.items())
    return f'''// WYGENEROWANE Z KONTRAKTU {c.version} — kształt z contracts.json, nie edytuj ręcznie
export function {_camel(route)}({{ {dargs} }} = {{}}) {{
  throw new Error("ciało {route}");          // uzupełnij logikę, potem:
  return ok({{ {body} }});
}}'''


def go_stub(route: str) -> str:
    c = CONTRACTS[route]

    def _go_type(tok):
        b = _base(tok)
        return {"str": "string", "int": "int", "num": "float64", "bool": "bool",
                "obj": "map[string]any", "list": "[]any", "any": "any"}.get(b, "any")

    fields = "\n".join(f"\t{k.title()} {_go_type(t)} `json:\"{k}\"`"
                       for k, t in c.inp.items())
    return f'''// WYGENEROWANE Z KONTRAKTU {c.version} — kształt z contracts.json, nie edytuj ręcznie
type {_camel(route).title()}In struct {{
{fields}
}}

func {_camel(route).title()}(in {_camel(route).title()}In) (map[string]any, error) {{
\treturn nil, fmt.Errorf("ciało {route} niezaimplementowane")
\t// po implementacji zwróć kopertę zgodną z out-schematem kontraktu
}}'''


if __name__ == "__main__":
    lang, route = sys.argv[1], sys.argv[2]
    print({"py": py_stub, "js": js_stub, "go": go_stub}[lang](route))
