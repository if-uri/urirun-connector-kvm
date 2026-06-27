#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Generator szkieletów handlerów Z kontraktu — CIENKIE CLI nad JEDNYM źródłem.

Logika stubów (py/js/go) żyje w ``urirun_contract.codegen`` — jedno źródło dla wszystkich
connectorów. Ten plik tylko spina CONTRACTS kvm z generycznymi stubami; NIE przepisuje ich
(re-definicja byłaby dryfem — pilnuje tego urirun-contract/check_single_source.py).

  py  <route>   — szkielet handlera Pythona (@conn.handler + sygnatura z inp + koperta z out)
  js  <route>   — odpowiednik JS
  go  <route>   — odpowiednik Go
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")
from urirun_connector_kvm.contracts import CONTRACTS  # noqa: E402
from urirun_contract.codegen import go_stub, js_stub, py_stub  # noqa: E402

_STUB = {"py": py_stub, "js": js_stub, "go": go_stub}


def stub(lang: str, route: str) -> str:
    return _STUB[lang](route, CONTRACTS[route])


if __name__ == "__main__":
    lang, route = sys.argv[1], sys.argv[2]
    print(stub(lang, route))
