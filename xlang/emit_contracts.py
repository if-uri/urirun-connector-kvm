# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Cienki wrapper: neutralny contracts.json z dataclass-owego ŹRÓDŁA PRAWDY (contracts.py).

Cała logika tłumaczenia żyje w toolkit (``contract_export.neutral_document``) — jedno źródło dla
wszystkich ~37 connectorów. Ten plik tylko spina CONTRACTS/WIRES kvm z generyczną funkcją.
"""
from __future__ import annotations

import json
import os

from urirun_connector_kvm.contracts import CONTRACTS, WIRES
from urirun_connectors_toolkit.contract_export import neutral_document

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    path = os.path.join(HERE, "contracts.json")
    with open(path, "w") as fh:
        json.dump(neutral_document(CONTRACTS, WIRES), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {path}: {len(CONTRACTS)} kontraktów, {len(WIRES)} krawędzi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
