# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Cienki wrapper: standardowy JSON Schema (draft 2020-12) z dataclass-owego źródła prawdy.

Logika tłumaczenia mini-języka → JSON Schema żyje w toolkit (``contract_export.schema_document``
/ ``contract_jsonschema``) — jedno źródło dla wszystkich connectorów.
"""
from __future__ import annotations

import json
import os

from urirun_connector_kvm.contracts import CONTRACTS
from urirun_connectors_toolkit.contract_export import schema_document

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    path = os.path.join(HERE, "contracts.schema.json")
    with open(path, "w") as fh:
        json.dump(schema_document(CONTRACTS), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {path}: {len(CONTRACTS)} tras → standardowy JSON Schema (draft 2020-12)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
