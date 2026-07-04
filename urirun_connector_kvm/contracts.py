# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Route contracts for the kvm connector — the LLM-editable declaration (single source of truth).

Trzy poziomy deklaracji:
  Contract — pojedyncza trasa: schemat wejścia/wyjścia, efekt, odwracalność, błędy, przykłady.
  Wire     — KRAWĘDŹ między dwoma trasami: które pole wyjścia producenta zasila które pole
             wejścia konsumenta. Czyni KOMPOZYCJĘ jawną i sprawdzalną PRZED uruchomieniem.
  WIRES    — zadeklarowany graf przepływu danych między kontraktami (host↔node, krok↔krok).

Brama z ``urirun_connectors_toolkit.contract_gate`` egzekwuje to wszystko w dev/CI:
  check_wire(w, CONTRACTS)  — statyczna zgodność typów + dostępność pola
  conform(CONTRACTS)        — efekt↔verb, wzajemność inverse, złote przykłady, rollback-args
"""
from __future__ import annotations

from urirun_connectors_toolkit.contract_gate import Contract, Wire

# ── mini-język schematu (wartości w inp/out) ────────────────────────────────
#   "str"/"int"/"bool"/"obj"/"list"/"num"/"any"  — typ (int wyklucza bool)
#   "?str"                       — KLUCZ opcjonalny (nieobecny OK; obecny musi pasować)
#   "const:window-close"         — literał string; "const:true"/"const:false" → bool
#   "enum:click|fill|find|wait"  — jeden z
#   {...}                        — zagnieżdżony obiekt (rekurencja)
#   ["int"]                      — homogeniczna lista (element wg schematu [0])
#   {"oneOf": [A, B]}            — unia: wartość pasuje do CO NAJMNIEJ jednego wariantu
# Klucze nadmiarowe w obiektach SĄ dozwolone: koperta zawsze niesie też ok/connector/action.


def _result(action: str, **extra) -> dict:
    return {"ok": True, "connector": "kvm", "action": action, **extra}


def _command(
    action: str,
    inp: dict,
    *,
    out: dict | None = None,
    payload: dict | None = None,
    result: dict | None = None,
    errors: tuple[str, ...] = ("degraded-backend", "precondition-unmet"),
) -> Contract:
    """Compact declaration for primitive KVM commands.

    The concrete backends add platform-specific fields; contracts pin the stable envelope only.
    """
    declared = {"action": f"const:{action}", **(out or {})}
    return Contract(
        version="v1",
        effect="command",
        inp=inp,
        out=declared,
        errors=errors,
        examples=(
            {
                "payload": payload or {},
                "result": result or _result(action, via="ydotool"),
            },
        ),
    )


CONTRACTS: dict[str, Contract] = {

    # ── query z UNIĄ w wyjściu: kontrakt ZMUSZA nazwać messy capture() jako Sukces | Degraded
    "screen/query/capture": Contract(
        version="v1",
        effect="query",
        inp={"monitor": "?int", "max_width": "?int", "base64": "?bool",
             "cx": "?int", "cy": "?int", "scope": "?str"},
        domains={
            "monitor": {
                "type": "enum",
                "domain": "env:monitors.id",
                "optional": True,
                "allValue": -1,
                "emptyValues": [0, ""],
                "preference": "screen.capture.default",
                "skipWhen": {"scope": ["all", "all-monitors", "desktop", "browser", "browser-page"]},
            },
        },
        out={"oneOf": [
            # Sukces — niesie path + fullSize do dalszego łańcucha
            {"kind": "const:screenshot", "path": "str", "bytes": "int",
             "fullSize": ["int"], "via": "str"},
            # Degraded — DWA kształty: placeholder (ma kind+bytes) i portal-denied/backend-error
            # (urirun.ok(degraded=True, degradedReason, platform) — BEZ kind/bytes). Wspólny rdzeń:
            # degraded:true + degradedReason; kind/bytes/path to nadmiar dozwolony, gdy są.
            {"degraded": "const:true", "degradedReason": "str"},
            # Fallback CDP — realny zrzut STRONY przeglądarki (portal OS zablokowany, CDP osiągalny);
            # viewport, nie cały pulpit, więc bez fullSize — `scope` to oznacza
            {"kind": "const:screenshot", "path": "str", "bytes": "int",
             "via": "const:cdp", "scope": "const:browser-page"},
        ]},
        errors=("precondition-unmet", "degraded-backend"),
        examples=(
            {"payload": {"base64": False},
             "result": {"ok": True, "connector": "kvm", "action": "capture",
                        "kind": "screenshot", "path": "~/.urirun/artifacts/s.png",
                        "bytes": 204931, "fullSize": [2560, 1440], "via": "grim"}},
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "action": "capture",
                        "kind": "screenshot", "degraded": True, "bytes": 3811,
                        "degradedReason": "xdg-portal returned a 3811-byte placeholder"}},
            {"payload": {"scope": "browser"},
             "result": {"ok": True, "connector": "kvm", "kind": "screenshot",
                        "path": "~/.urirun/artifacts/screenshots/shot.png", "bytes": 66573,
                        "via": "cdp", "backend": "cdp-page", "scope": "browser-page"}},
        ),
    ),

    # ── command konsumujący wymiary ekranu (sw,sh) z poprzedniego kroku capture
    "abs/command/click": Contract(
        version="v1",
        effect="command",
        inp={"x": "int", "y": "int", "sw": "?int", "sh": "?int",
             "button": "?str", "do_click": "?bool"},
        out={"action": "const:click-abs", "screen": ["int"]},
        errors=("degraded-backend",),
        examples=(
            {"payload": {"x": 840, "y": 612, "sw": 2560, "sh": 1440},
             "result": {"ok": True, "connector": "kvm", "action": "click-abs",
                        "screen": [2560, 1440], "did": "click@(840,612)"}},
        ),
    ),

    # ── input primitives: intentionally explicit, because abs/ui click are different semantics
    "input/command/type": _command(
        "type",
        inp={"text": "str"},
        payload={"text": "hello"},
        result=_result("type", via="ydotool"),
    ),

    "input/command/key": _command(
        "key",
        inp={"key": "?str", "keys": "?str"},
        payload={"keys": "ctrl+l"},
        result=_result("key", via="ydotool"),
    ),

    "input/command/click": _command(
        "click",
        inp={"button": "?str", "x": "?int", "y": "?int"},
        payload={"button": "left", "x": 200, "y": 160},
        result=_result("click", via="ydotool", at=[200, 160]),
    ),

    "input/command/move": _command(
        "move",
        inp={"x": "int", "y": "int"},
        payload={"x": 200, "y": 160},
        result=_result("move", via="ydotool"),
    ),

    "input/command/wait": _command(
        "wait",
        inp={"seconds": "?num", "ms": "?int"},
        out={"seconds": "num"},
        payload={"seconds": 0.2},
        result=_result("wait", seconds=0.2),
    ),

    "input/command/scroll": _command(
        "scroll",
        inp={"dy": "?int"},
        payload={"dy": -3},
        result=_result("scroll", via="ydotool"),
    ),

    "input/command/double-click": _command(
        "double-click",
        inp={"x": "?int", "y": "?int"},
        payload={"x": 200, "y": 160},
        result=_result("double-click", via="ydotool", at=[200, 160]),
    ),

    "input/command/triple-click": _command(
        "triple-click",
        inp={"x": "?int", "y": "?int"},
        payload={"x": 200, "y": 160},
        result=_result("triple-click", via="ydotool", at=[200, 160]),
    ),

    "input/command/right-click": _command(
        "right-click",
        inp={"x": "?int", "y": "?int"},
        payload={"x": 200, "y": 160},
        result=_result("right-click", via="ydotool", at=[200, 160]),
    ),

    "input/command/middle-click": _command(
        "middle-click",
        inp={"x": "?int", "y": "?int"},
        payload={"x": 200, "y": 160},
        result=_result("middle-click", via="ydotool", at=[200, 160]),
    ),

    "input/command/hover": _command(
        "hover",
        inp={"x": "int", "y": "int"},
        payload={"x": 200, "y": 160},
        result=_result("hover", via="ydotool"),
    ),

    "input/command/drag-and-drop": _command(
        "drag-and-drop",
        inp={"x": "int", "y": "int", "destination_x": "int", "destination_y": "int"},
        payload={"x": 200, "y": 160, "destination_x": 400, "destination_y": 320},
        result=_result("drag-and-drop", via="ydotool"),
    ),

    "task/command/run": Contract(
        version="v1",
        effect="command",
        inp={"steps": ["obj"]},
        out={"action": "const:task", "steps": ["obj"]},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"steps": [{"op": "type", "text": "hello"}]},
             "result": _result("task", steps=[{"op": "type", "via": "ydotool", "ok": True}])},
        ),
    ),

    "window/command/focus": _command(
        "focus",
        inp={"title": "str"},
        payload={"title": "Chrome"},
        result=_result("focus", via="wmctrl"),
        errors=("unreachable", "degraded-backend", "precondition-unmet"),
    ),

    "proc/command/kill": Contract(
        version="v1",
        effect="command",
        inp={"pid": "?int", "name": "?str", "signal": "?str"},
        out={"action": "const:kill", "signal": "str", "matched": "int",
             "killed": ["int"], "denied": ["int"]},
        errors=("unreachable", "precondition-unmet"),
        examples=(
            {"payload": {"pid": 4242, "signal": "TERM"},
             "result": _result("kill", signal="SIGTERM", matched=1, killed=[4242], denied=[])},
        ),
    ),

    "a11y/command/act": Contract(
        version="v1",
        effect="command",
        inp={"app": "?str", "role": "?str", "name": "?str", "action": "?str",
             "text": "?str", "nth": "?int"},
        out={"action": "const:a11y", "request": "obj"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"role": "button", "name": "Sign in", "action": "focus"},
             "result": _result("a11y", request={"app": "", "role": "button",
                                                "name": "Sign in", "op": "focus"})},
        ),
    ),

    # ── odwracalna para close/restore: checkpoint okna + przywrócenie po JSON round-trip
    "window/command/close": Contract(
        version="v1",
        effect="command",
        reversible=True,
        inverse_route="window/command/restore",
        inp={"id": "?str"},
        out={
            "action": "const:window-close",
            "reversible": "const:true",
            "snapshot": "obj",
            "inverse": {"path": "const:window/command/restore", "args": {"snapshot": "obj"}},
        },
        errors=("unreachable",),
        examples=(
            {"payload": {"id": "active"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "window-close",
                 "did": "close(active)", "reversible": True,
                 "snapshot": {"url": "https://example.test/x", "scrollX": 0, "scrollY": 240,
                              "forms": [], "id": "active"},
                 "inverse": {"path": "window/command/restore",
                             "args": {"snapshot": {"url": "https://example.test/x",
                                                   "scrollX": 0, "scrollY": 240,
                                                   "forms": [], "id": "active"}}},
             }},
        ),
    ),

    "window/command/restore": Contract(
        version="v1",
        effect="command",
        reversible=True,
        inverse_route="window/command/close",
        inp={"snapshot": "obj"},
        out={
            "action": "const:window-restore",
            "reversible": "const:true",
            "inverse": {"path": "const:window/command/close", "args": {"id": "?str"}},
        },
        errors=("unreachable", "unknown"),
        examples=(
            {"payload": {"snapshot": {"url": "https://example.test/x", "scrollY": 240,
                                      "forms": [], "id": "active"}},
             "result": {
                 "ok": True, "connector": "kvm", "action": "window-restore",
                 "did": "restore(active)", "reversible": True,
                 "inverse": {"path": "window/command/close", "args": {"id": "active"}},
             }},
        ),
    ),

    # ── self-inverse navigate: UNDO = re-navigate to the URL we left ─────────────
    # inverse is CONDITIONAL (absent if no prior page was loaded → the route is still
    # declared reversible because when it IS present, it is a proper inverse).
    "cdp/page/command/navigate": Contract(
        version="v1",
        effect="command",
        reversible=True,
        inverse_route="cdp/page/command/navigate",   # self-inverse
        inp={"url": "str", "ready_timeout": "?num"},
        out={
            "action": "const:cdp-navigate",
            "url": "str",
            # `ready` to KOPERTA cdp.page_ready() — {ok, readyState, (waited)}, nie bool
            "ready": {"ok": "bool", "readyState": "str"},
            "inverse": "?obj",   # optional: absent when no prior page was loaded
        },
        errors=("unreachable",),
        examples=(
            # no prior page — inverse absent
            {"payload": {"url": "https://example.test/a"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "cdp-navigate",
                 "url": "https://example.test/a",
                 "ready": {"ok": True, "readyState": "complete"}}},
            # prior page captured — inverse present (self-referential undo)
            {"payload": {"url": "https://example.test/b"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "cdp-navigate",
                 "url": "https://example.test/b",
                 "ready": {"ok": True, "readyState": "complete"},
                 "inverse": {"path": "cdp/page/command/navigate",
                             "args": {"url": "https://example.test/a"}}}},
        ),
    ),

    "cdp/session/command/ensure": Contract(
        version="v1",
        effect="command",
        inp={"url": "?str", "user_data_dir": "?str", "copy_from": "?str", "wait": "?num"},
        out={"action": "const:cdp-ensure", "launching": "?bool", "pending": "?bool",
             "endpoint": "?str", "readyError": "?str"},
        errors=("unreachable", "precondition-unmet", "degraded-backend"),
        examples=(
            {"payload": {"url": "https://example.test", "wait": 0},
             "result": _result("cdp-ensure", launching=True,
                                endpoint="http://127.0.0.1:9222")},
        ),
    ),

    "ui/command/click": Contract(
        version="v1",
        effect="command",
        inp={"text": "?str", "role": "?str", "app": "?str", "name": "?str"},
        out={"action": "const:ui-click", "attempts": "?list", "strategy": "?str",
             "how": "?str", "at": "?list"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"text": "Sign in"},
             "result": _result("ui-click", strategy="cdp", attempts=[{"strategy": "cdp", "ok": True}])},
        ),
    ),

    # ── self-inverse fill: UNDO = refill the same field with the old value ────────
    # inverse is CONDITIONAL (absent if locate didn't capture the prior value, or if
    # the value was already correct). Declared reversible for the same reason as navigate.
    "ui/command/fill": Contract(
        version="v1",
        effect="command",
        reversible=True,
        inverse_route="ui/command/fill",   # self-inverse
        inp={"value": "str", "text": "?str", "role": "?str", "name": "?str",
             "app": "?str", "verify": "?bool"},
        out={
            "action": "const:ui-fill",
            "inverse": "?obj",   # optional: absent when prev value wasn't captured
        },
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            # locate captured the prev value → inverse present
            {"payload": {"text": "Email", "value": "new@example.com"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "ui-fill",
                 "inverse": {"path": "ui/command/fill",
                             "args": {"text": "Email", "value": "old@example.com"}}}},
            # locate didn't capture prev (field empty or locate failed) → inverse absent
            {"payload": {"text": "Search", "value": "hello"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "ui-fill"}},
        ),
    ),

    "ui/command/act": Contract(
        version="v1",
        effect="command",
        inp={"do": "enum:click|fill|find|wait", "text": "?str", "role": "?str",
             "name": "?str", "value": "?str", "app": "?str", "retries": "?int",
             "settle": "?num", "ready_timeout": "?num", "safe": "?bool"},
        out={"action": "const:act", "do": "str", "app": "?str", "surface": "?obj",
             "ready": "?obj", "tries": ["obj"], "strategyAttempts": "?list"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"do": "click", "text": "Sign in"},
             "result": _result("act", do="click", app="", surface=None, ready=None,
                                tries=[{"attempt": 1, "ok": True, "strategy": "cdp"}],
                                strategyAttempts=[{"strategy": "cdp", "ok": True}])},
        ),
    ),

    "ui/command/click-text": Contract(
        version="v1",
        effect="command",
        inp={"text": "str", "button": "?str", "nth": "?int", "min_conf": "?int",
             "then_type": "?str", "then_key": "?str", "monitor": "?int"},
        out={"action": "const:click-text", "text": "str", "clicked": "obj",
             "screenshot": "str", "matchCount": "int", "via": "?str",
             "typed": "?int", "submitted": "?str"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"text": "Post"},
             "result": _result("click-text", text="Post",
                                clicked={"center": [840, 612], "text": "Post"},
                                screenshot="/tmp/urirun-kvm-ui.png",
                                matchCount=1, via="ydotool")},
        ),
    ),

    # ── vnc/* — direct RFB surface for noVNC-hosted desktops (vnc.py). Golden examples
    # are LIVE-measured outputs from the example-11 container (fluxbox menu sequence).
    "vnc/query/status": Contract(
        version="v1",
        effect="query",
        inp={"target": "?str"},
        out={"target": "str", "width": "?int", "height": "?int", "via": "const:rfb"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"target": "172.19.0.2::5900"},
             "result": {"ok": True, "connector": "kvm", "target": "172.19.0.2::5900",
                        "width": 1280, "height": 900, "via": "rfb"}},
        ),
    ),

    "vnc/query/capture": Contract(
        version="v1",
        effect="query",
        inp={"target": "?str", "out": "?str", "base64": "?bool"},
        out={"action": "const:capture", "path": "str", "width": "?int", "height": "?int",
             "via": "const:rfb", "coord_space": "const:framebuffer-px", "base64": "?str"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"target": "172.19.0.2::5900"},
             "result": _result("capture", path="/home/tom/.urirun/artifacts/screenshots/vnc_capture.png",
                                width=1280, height=900, via="rfb", coord_space="framebuffer-px")},
        ),
    ),

    "vnc/query/find": Contract(
        version="v1",
        effect="query",
        inp={"text": "?str", "role": "?str", "target": "?str"},
        out={"action": "const:find", "frame": "str", "found": "bool",
             "coord_space": "const:framebuffer-px", "center": "?list", "bbox": "?list",
             "source": "?str", "text": "?str", "misses": "?list", "candidates": "?int",
             "query": "?str", "fullSize": "?obj", "actionable": "?bool", "matches": "?list"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"text": "Reconfigure", "target": "172.19.0.2::5900"},
             "result": _result("find", frame="/home/tom/.urirun/artifacts/screenshots/vnc_capture.png",
                                found=True, center=[612, 574], bbox=[578, 567, 68, 14],
                                source="tesseract", coord_space="framebuffer-px")},
            {"payload": {"text": "NoSuchLabel", "target": "172.19.0.2::5900"},
             "result": _result("find", frame="/home/tom/.urirun/artifacts/screenshots/vnc_capture.png",
                                found=False, coord_space="framebuffer-px",
                                misses=["tesseract: found=false (0 candidates)"])},
        ),
    ),

    # perceive→act→verify in one route; `verified` is honest (False = expect-text absent
    # after the click+settle+re-look), so flows can branch instead of assuming success.
    "vnc/command/click": Contract(
        version="v1",
        effect="command",
        inp={"text": "?str", "x": "?int", "y": "?int", "button": "?int", "double": "?bool",
             "verify": "?str", "settle": "?num", "target": "?str"},
        out={"action": "const:click", "clicked": "list", "button": "int", "double": "bool",
             "via": "const:rfb", "located": "?list", "source": "?str",
             "verified": "?bool", "verify": "?obj"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"text": "Reconfigure", "verify": "Workspace 1",
                         "settle": 1.2, "target": "172.19.0.2::5900"},
             "result": _result("click", clicked=[612, 574], button=1, double=False, via="rfb",
                                located=[612, 574], source="tesseract", verified=True,
                                verify={"text": "Workspace 1", "center": [62, 891]})},
            {"payload": {"x": 640, "y": 450, "button": 3, "target": "172.19.0.2::5900"},
             "result": _result("click", clicked=[640, 450], button=3, double=False, via="rfb",
                                located=None, source=None)},
        ),
    ),

    "vnc/command/type": Contract(
        version="v1",
        effect="command",
        inp={"text": "?str", "enter": "?bool", "target": "?str"},
        out={"action": "const:type", "typed": "int", "enter": "bool", "via": "const:rfb"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"text": "hello", "enter": True, "target": "172.19.0.2::5900"},
             "result": _result("type", typed=5, enter=True, via="rfb")},
        ),
    ),

    "vnc/command/key": Contract(
        version="v1",
        effect="command",
        inp={"combo": "str", "target": "?str"},
        out={"action": "const:key", "combo": "str", "via": "const:rfb"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"combo": "ctrl-alt-t", "target": "172.19.0.2::5900"},
             "result": _result("key", combo="ctrl-alt-t", via="rfb")},
        ),
    ),

    "app://host/desktop/command/launch": Contract(
        version="v1",
        effect="command",
        inp={"app": "str", "compose": "?str", "args": "?list", "settle": "?num"},
        out={"action": "const:launch", "pid": "?int", "inverse": "?obj"},
        errors=("degraded-backend", "precondition-unmet"),
        examples=(
            {"payload": {"app": "firefox", "args": [], "settle": 0},
             "result": _result("launch", pid=4242,
                                inverse={"uri": "kvm://host/proc/command/kill",
                                         "args": {"pid": 4242}})},
        ),
    ),
}


# ── Zadeklarowany graf przepływu danych między kontraktami ───────────────────
# Każda krawędź jest sprawdzana statycznie (zgodność typów + dostępność pola we
# WSZYSTKICH wariantach wyjścia) ORAZ przez JSON round-trip producent→konsument.
WIRES: list[Wire] = [
    # Pełny handoff: stan okna z procesu A → odtworzenie w procesie B
    Wire("window/command/close", "window/command/restore",
         {"snapshot": "snapshot"},
         note="checkpoint okna z jednego node → restore na innym (pełne wejście)"),
    # Wkład częściowy: wymiary ekranu ze zrzutu → przestrzeń współrzędnych kliknięcia.
    # sw/sh są opcjonalne u konsumenta → warunkowość wariantu degraded jest dozwolona.
    Wire("screen/query/capture", "abs/command/click",
         {"sw": "fullSize.0", "sh": "fullSize.1"},
         note="rozmiar ekranu ze zrzutu zasila przestrzeń kliknięcia (x,y z kroku locate)"),
    # Wkład częściowy: URL z nawigacji → wartość do wypełnienia w polu formularza.
    # Typowy scenariusz: navigate(login-page) → fill(Email/value=URL). value to wymagane
    # pole konsumenta → krawędź jest ZAWSZE partial (x,y z locate-step).
    Wire("cdp/page/command/navigate", "ui/command/fill",
         {"value": "url"},
         note="URL strony po nawigacji trafia do pola formularza (np. adres→email)"),
]
