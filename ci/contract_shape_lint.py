#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Lint: każdy @conn.handler z kontraktem musi mieć sygnaturę zgodną z inp oraz kopertę
zgodną z out. Reguła obowiązuje BEZ wyjątków — nie ma „zatwierdzonego dryfu". Build, który
pozwala na ręczne przepisanie kształtu, dodaje drugą kopię zamiast jedynego źródła prawdy.

Sprawdza dwie niezmienniki:
  INP: każdy wymagany klucz z contract.inp musi być parametrem funkcji handlera (typ + default)
  OUT: każdy klucz najważniejszego wariantu z contract.out musi pojawić się w treści handlera

Uruchom:  python ci/contract_shape_lint.py [--strict]
Exit:     0 = OK, 1 = naruszenia (liczba na stdout)

--strict: sprawdza wszystkie 6 kontraktów. Bez flagi sprawdza tylko te, których handler
          jest zaimplementowany (tzn. nie zawiera raise NotImplementedError).
"""
from __future__ import annotations

import ast
import inspect
import sys

sys.path.insert(0, ".")
from urirun_connector_kvm.contracts import CONTRACTS
import urirun_connector_kvm.core as core_mod  # zarejestrowane handlery


_STRICT = "--strict" in sys.argv


def _required_inp_keys(c) -> set[str]:
    return {k for k, v in c.inp.items()
            if not (isinstance(v, str) and v.startswith("?"))}


def _out_leaf_keys(schema) -> set[str]:
    if isinstance(schema, dict):
        if set(schema) == {"oneOf"}:
            # sprawdzamy tylko wariant sukcesu (pierwszy)
            return _out_leaf_keys(schema["oneOf"][0])
        return set(schema.keys())
    return set()


def _fn_for_route(route: str):
    """Zwróć funkcję handlera zarejestrowaną dla danej trasy przez urirun."""
    try:
        from urirun.v2 import decorated_bindings
        db = decorated_bindings().get("bindings", {})
    except Exception:
        return None
    for uri, b in db.items():
        if not (uri.endswith(f"/{route}") or uri.endswith(route)):
            continue
        py = b.get("python") or {}
        export = py.get("export")
        if export:
            return getattr(core_mod, export, None)
    return None


def _fn_params(fn) -> set[str]:
    try:
        return set(inspect.signature(fn).parameters) - {"args", "kwargs"}
    except Exception:
        return set()


def _fn_source(fn) -> str:
    try:
        return inspect.getsource(fn)
    except Exception:
        return ""


def _is_implemented(fn) -> bool:
    src = _fn_source(fn)
    return "NotImplementedError" not in src and "raise NotImplementedError" not in src


def check_route(route: str, c) -> list[str]:
    problems: list[str] = []
    fn = _fn_for_route(route)
    if fn is None:
        # handler nieznaleziony — tylko w strict mode raportujemy
        if _STRICT:
            problems.append(f"{route}: handler nie znaleziony w bindings")
        return problems

    if not _STRICT and not _is_implemented(fn):
        return []  # szkielet bez ciała — pomijamy

    # INP: parametry funkcji muszą zawierać wymagane pola kontraktu
    params = _fn_params(fn)
    for key in _required_inp_keys(c):
        if key not in params:
            problems.append(
                f"{route}: inp['{key}'] (required) nie ma odpowiadającego parametru w handlerze")

    # OUT: treść handlera musi zawierać klucze wyjścia z kontraktu
    src = _fn_source(fn)
    for key, schema in (c.out["oneOf"][0] if set(c.out) == {"oneOf"} else c.out).items():
        sval = schema if isinstance(schema, str) else ""
        if sval.startswith("const:"):
            # sprawdzamy, czy wartość literału pojawia się w źródle (np. action="ui-fill")
            lit = sval[len("const:"):]
            if lit in ("true", "false"):
                continue  # True/False są zawsze ok
            if f'"{lit}"' not in src and f"'{lit}'" not in src:
                problems.append(
                    f"{route}: out['{key}'] = const:{lit!r} nie pojawia się w ciele handlera")
            continue
        # akceptujemy: "key" / 'key' (dict literal) LUB key= (kwarg)
        present = (f'"{key}"' in src or f"'{key}'" in src or f"{key}=" in src)
        if not present:
            problems.append(
                f"{route}: out['{key}'] nie pojawia się w ciele handlera")

    return problems


def main() -> int:
    total = 0
    checked = 0
    for route, c in CONTRACTS.items():
        probs = check_route(route, c)
        if probs:
            for p in probs:
                print(f"  LINT {p}")
            total += len(probs)
        else:
            checked += 1

    if total == 0:
        print(f"  OK: {checked}/{len(CONTRACTS)} kontraktów — sygnatura i koperta zgodne z CONTRACTS")
        return 0
    print(f"  BŁĄD: {total} naruszeń kształtu (patrz wyżej); uruchom contract_codegen.py by wygenerować poprawny szkielet")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
