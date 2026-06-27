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
        errors=("unreachable",),
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
            # Pre-flight input rejection (malformed `do`, missing fill `value`) returns a bare fail
            # BEFORE acting — no `action`/`do` — so the contract must not claim every fail carries them.
            {"ok": "const:false", "error": "str"},
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

    # The display geometry callers need without a screenshot — the coordinate space capture/click
    # live in. Pins the field names the planner reads back (fullSize/width/height).
    "display/query/info": Contract(
        version="v1", effect="query",
        inp={},
        out={"ok": "const:true", "action": "const:display-info", "fullSize": "list",
             "width": "int", "height": "int", "monitorCount": "int"},
        examples=(
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "action": "display-info",
                        "fullSize": [2560, 1440], "width": 2560, "height": 1440,
                        "monitors": [{"x": 0, "y": 0, "w": 2560, "h": 1440}], "monitorCount": 1,
                        "platform": "linux/wayland", "wayland": True, "multiMonitor": False,
                        "fractionalHiDPI": False, "osLevelReliable": False}},
        )),

    # Is a CDP debug endpoint reachable, and where — the precondition the act/find router checks.
    "cdp/session/query/status": Contract(
        version="v1", effect="query",
        inp={},
        out={"ok": "const:true", "action": "const:cdp-status", "reachable": "bool", "endpoint": "?str"},
        examples=(
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "action": "cdp-status",
                        "reachable": False, "endpoint": "http://127.0.0.1:9222"}},
        )),
}


def _input_cmd(action: str, inp: dict, *, example_payload: dict) -> Contract:
    """A uniform input/* command contract: pin the stable identity (ok + action); leave the
    backend-variable payload unspecified (declare STRUCTURE, not all behaviour). The example
    fields below are always present — B.dispatch() always stamps backend + platform."""
    return Contract(
        version="v1", effect="command", inp=inp,
        out={"ok": "const:true", "action": f"const:{action}"},
        examples=({"payload": example_payload,
                   "result": {"ok": True, "connector": "kvm", "action": action,
                              "backend": "ydotool", "platform": "linux/wayland"}},),
    )


_XY = {"x": "?int", "y": "?int"}
CONTRACTS.update({
    "input/command/type": _input_cmd("type", {"text": "?str"}, example_payload={"text": "hello"}),
    "input/command/key": _input_cmd("key", {"key": "?str", "keys": "?str"}, example_payload={"keys": "ctrl+a"}),
    "input/command/click": _input_cmd("click", {"button": "?str", **_XY}, example_payload={"x": 840, "y": 612}),
    "input/command/move": _input_cmd("move", dict(_XY), example_payload={"x": 100, "y": 200}),
    "input/command/scroll": _input_cmd("scroll", {"dy": "?int"}, example_payload={"dy": -3}),
    "input/command/double-click": _input_cmd("double-click", dict(_XY), example_payload={"x": 840, "y": 612}),
    "input/command/triple-click": _input_cmd("triple-click", dict(_XY), example_payload={"x": 840, "y": 612}),
    "input/command/right-click": _input_cmd("right-click", dict(_XY), example_payload={"x": 840, "y": 612}),
    "input/command/middle-click": _input_cmd("middle-click", dict(_XY), example_payload={"x": 840, "y": 612}),
    "input/command/hover": _input_cmd("hover", dict(_XY), example_payload={"x": 840, "y": 612}),
    "input/command/drag-and-drop": _input_cmd(
        "drag-and-drop", {"x": "int", "y": "int", "destination_x": "int", "destination_y": "int"},
        example_payload={"x": 100, "y": 100, "destination_x": 300, "destination_y": 300}),
})

# wait is the odd one: no backend dispatch — it returns its own seconds.
CONTRACTS["input/command/wait"] = Contract(
    version="v1", effect="command",
    inp={"seconds": "?num", "ms": "?int"},
    out={"ok": "const:true", "action": "const:wait", "seconds": "num"},
    examples=(
        {"payload": {"seconds": 1.0},
         "result": {"ok": True, "connector": "kvm", "action": "wait", "seconds": 1.0}},
    ))
