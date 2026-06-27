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

    # A read whose output the contract FORCES you to name as Success | Degraded — the messy
    # 4-shape return of capture() collapses to two declared shapes a planner can branch on.
    "screen/query/capture": Contract(
        version="v1", effect="query",
        inp={"monitor": "?int", "base64": "?bool", "max_width": "?int", "cx": "?int", "cy": "?int"},
        out={"oneOf": [
            # Success: a real frame (urirun.tag adds live=false; note there is NO `action` field).
            {"ok": "const:true", "kind": "const:screenshot", "path": "str", "bytes": "int", "live": "bool"},
            # Degraded: portal-denied / placeholder — the chain stays alive on a flagged non-capture.
            {"ok": "const:true", "action": "const:capture", "degraded": "const:true", "degradedReason": "str"},
        ]},
        examples=(
            {"payload": {"base64": False},
             "result": {"ok": True, "connector": "kvm", "kind": "screenshot", "path": "/x.png",
                        "monitor": 0, "via": "grim", "backend": "grim", "fullSize": [2560, 1440],
                        "crop": None, "bytes": 204931, "live": False}},
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "action": "capture", "degraded": True,
                        "degradedReason": "portal denied by user", "platform": "linux/wayland"}},
        )),

    # The ONE high-level command an LLM planner targets. The HITL safe-gate (refusing an
    # irreversible label unless safe=false) is part of the contract — a declared Blocked shape.
    "ui/command/act": Contract(
        version="v1", effect="command", reversible=False,
        inp={"do": "enum:click|fill|find|wait", "text": "?str", "value": "?str", "safe": "?bool"},
        out={"oneOf": [
            {"ok": "const:true", "action": "const:act", "do": "str", "tries": "list"},
            {"ok": "const:false", "action": "const:act", "do": "str", "blocked": "const:irreversible"},
            {"ok": "const:false", "action": "const:act", "do": "str", "error": "str"},
        ]},
        examples=(
            {"payload": {"do": "find", "text": "Submit"},
             "result": {"ok": True, "connector": "kvm", "action": "act", "do": "find", "app": "",
                        "surface": "cdp", "ready": True, "found": True, "center": [840, 612],
                        "tries": [{"attempt": 1, "strategy": "cdp", "ok": True}]}},
            {"payload": {"do": "click", "text": "Publish", "safe": True},
             "result": {"ok": False, "connector": "kvm", "action": "act", "do": "click",
                        "blocked": "irreversible",
                        "error": "refusing to click 'publish' with safe=true (pass safe=false to allow)"}},
        )),
}
