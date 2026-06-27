# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Cienki wrapper: typy TypeScript (.d.ts) z dataclass-owego źródła prawdy.

Logika tłumaczenia mini-języka → TS żyje w toolkit (``contract_typescript.to_typescript``) —
jedno źródło dla wszystkich connectorów; egzekucja kontraktu w czasie kompilacji.
"""
from __future__ import annotations

import os

from urirun_connector_kvm.contracts import CONTRACTS
from urirun_connectors_toolkit.contract_typescript import to_typescript

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    path = os.path.join(HERE, "ts", "contracts.d.ts")
    with open(path, "w") as fh:
        fh.write(to_typescript(CONTRACTS))
    print(f"wrote {path}: {len(CONTRACTS)} tras → typy TypeScript (czas kompilacji)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
