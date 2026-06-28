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

CONTRACTS: dict[str, Contract] = {

    # ── query z UNIĄ w wyjściu: kontrakt ZMUSZA nazwać messy capture() jako Sukces | Degraded
    "screen/query/capture": Contract(
        version="v1",
        effect="query",
        inp={"monitor": "?int", "max_width": "?int", "base64": "?bool",
             "cx": "?int", "cy": "?int"},
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
                        "kind": "screenshot", "path": "/home/u/.urirun/artifacts/s.png",
                        "bytes": 204931, "fullSize": [2560, 1440], "via": "grim"}},
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "action": "capture",
                        "kind": "screenshot", "degraded": True, "bytes": 3811,
                        "degradedReason": "xdg-portal returned a 3811-byte placeholder"}},
            {"payload": {},
             "result": {"ok": True, "connector": "kvm", "kind": "screenshot",
                        "path": "/home/u/.urirun/artifacts/screenshots/shot.png", "bytes": 66573,
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
            "ready": "bool",
            "inverse": "?obj",   # optional: absent when no prior page was loaded
        },
        errors=("unreachable",),
        examples=(
            # no prior page — inverse absent
            {"payload": {"url": "https://example.test/a"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "cdp-navigate",
                 "url": "https://example.test/a", "ready": True}},
            # prior page captured — inverse present (self-referential undo)
            {"payload": {"url": "https://example.test/b"},
             "result": {
                 "ok": True, "connector": "kvm", "action": "cdp-navigate",
                 "url": "https://example.test/b", "ready": True,
                 "inverse": {"path": "cdp/page/command/navigate",
                             "args": {"url": "https://example.test/a"}}}},
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
