# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Route contracts for the kvm connector — the LLM-editable declaration (single source of truth).

The contract *type* and the conformance *gate* live in the kernel
(``urirun_connectors_toolkit.contract_gate``); only these declarations live here, joined to the
handlers in ``core.py`` by route key. Keep this small enough to fit an LLM context: it is the thing
a model edits (a declaration, where its model is reliable) rather than re-deriving the output shape
from scattered handler ``return`` statements.

Wiring (add once, at the bottom of ``core.py``)::

    from urirun_connectors_toolkit.contract_gate import attach_contracts
    from urirun_connector_kvm.contracts import CONTRACTS
    attach_contracts(conn, CONTRACTS)   # bindings now carry effect/output/examples for the planner

The conformance gate runs in CI via ``tests/test_contract_conformance.py``
(``URIRUN_CONTRACT_CHECK=1`` additionally cross-checks the live handler signatures).
"""
from __future__ import annotations

from urirun_connectors_toolkit.contract_gate import Contract

# A serializable snapshot shape reused across the close/restore examples (matches window_close's
# CDP snapshot: url + scroll + forms + sessionStorage + the injected id).
_SNAP = {"url": "https://example.com", "scrollX": 0, "scrollY": 0, "forms": [], "session": {}, "id": "active"}

CONTRACTS: dict[str, Contract] = {

    "window/command/close": Contract(
        version="v1", effect="command", reversible=True,
        inverse_route="window/command/restore",      # reversibility DECLARED, not pasted ad-hoc
        inp={"id": "?str"},
        out={
            "ok": "const:true",
            "action": "const:window-close",
            "reversible": "const:true",
            "snapshot": "obj",
            "inverse": {"path": "const:window/command/restore", "args": {"snapshot": "obj"}},
        },
        examples=(
            {"payload": {"id": "active"},
             "result": {"ok": True, "connector": "kvm", "action": "window-close",
                        "did": "close(active)", "reversible": True, "snapshot": _SNAP,
                        "inverse": {"path": "window/command/restore", "args": {"snapshot": _SNAP}}}},
        )),

    "window/command/restore": Contract(
        version="v1", effect="command", reversible=True,
        inverse_route="window/command/close",
        inp={"snapshot": "obj"},
        out={
            "ok": "const:true",
            "action": "const:window-restore",
            "reversible": "const:true",
            "inverse": {"path": "const:window/command/close", "args": {"id": "?str"}},
        },
        examples=(
            {"payload": {"snapshot": _SNAP},
             "result": {"ok": True, "connector": "kvm", "action": "window-restore",
                        "did": "restore(active)", "reversible": True,
                        "inverse": {"path": "window/command/close", "args": {"id": "active"}}}},
        )),
}
