# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""KVM (keyboard / video / mouse) routes for urirun — cross-platform.

One ``kvm://`` surface for capturing the screen and driving keyboard/mouse on
Linux (Wayland *and* X11), Windows and macOS. Every capability is served by a
**decorator-registered backend** (see ``backends.py``): the connector auto-selects
the best available tool/library for the live session and falls through on failure,
so the same routes work everywhere a suitable helper is installed.

Routes (each a typed ``@conn.handler``, ``isolated=True`` so it stays
registry-portable through ``python -m urirun.exec``):

* ``kvm://{host}/screen/query/capture``     — screenshot (portal/grim/mss/scrot/…)
* ``kvm://{host}/input/command/type``        — type a whole string
* ``kvm://{host}/input/command/key``         — a key / hotkey combo
* ``kvm://{host}/input/command/click``       — mouse click (optionally at x,y)
* ``kvm://{host}/input/command/move``        — move the pointer (absolute)
* ``kvm://{host}/input/command/scroll``      — scroll wheel
* ``kvm://{host}/task/command/run``          — a bounded sequence of the above
* ``kvm://{host}/window/command/focus``      — activate a window by title
* ``kvm://{host}/window/query/list``         — list windows
* ``kvm://{host}/doctor/query/report``       — which backend serves each action

Backend chains (auto, highest-priority available wins):
  capture: portal(Wayland) → grim → mss → pillow → scrot → imagemagick → gnome-screenshot → screencapture(macOS)
  input:   ydotool(Wayland) → wtype/xdotool(X11) → pynput(any)
Helpful optional libraries (install for more platforms): ``mss``, ``pynput``,
``Pillow``, ``pytesseract`` + system tools ``ydotool``/``ydotoold``, ``wmctrl``,
``grim``/``scrot``, ``python3-gobject``+``python3-dbus`` (Wayland portal capture).
"""

from __future__ import annotations

import base64 as _b64
import os
import tempfile
import time
from typing import Any

import urirun

try:  # normal package import
    from . import backends as B
except ImportError:  # flat-module deploy (host `deploy --code core.py backends.py`)
    import backends as B  # type: ignore

try:  # universal control-tool router (cdp -> atspi -> vision)
    from . import control as C
except ImportError:  # flat-module deploy (push control.py + cdp.py too)
    import control as C  # type: ignore

CONNECTOR_ID = "kvm"
conn = urirun.connector(CONNECTOR_ID, scheme="kvm")


def _ok(**kw: Any) -> dict[str, Any]:
    return urirun.ok(connector=CONNECTOR_ID, **kw)


def _fail_from(action: str, exc: Exception) -> dict[str, Any]:
    return urirun.fail(str(exc), connector=CONNECTOR_ID, action=action, platform=B.platform_tag())


def _spread(d: dict | None, *also_exclude: str) -> dict[str, Any]:
    """Strip the envelope-reserved keys from an inner result dict BEFORE spreading it into
    ``urirun.ok``/``urirun.fail`` — passing the inner ``error``/``ok``/``connector``/``action``
    (or a key the caller sets explicitly) collides with the envelope's own and raises
    TypeError, which used to mask the real result behind a generic handler crash."""
    reserved = {"ok", "error", "connector", "action", *also_exclude}
    return {k: v for k, v in (d or {}).items() if k not in reserved}


def _positioned_click(button: str, x: int | None, y: int | None, clicks: int = 1) -> dict[str, Any]:
    """Position+click as ONE uinput absolute device when /dev/uinput is writable.
    On a GNOME/Wayland node that lacks WAYLAND_DISPLAY, ydotool's ``mousemove -a``
    mismaps and dumps the cursor at the top-left hot-corner (opens Activities); and a
    split move(uinput-abs)+click(ydotool) clicks at the wrong place because the abs
    device is destroyed before the click. ``uinput_abs_click`` does both atomically on
    one device (auto-detecting screen size), so the click lands where we positioned.
    Falls back to the move+click chain only when /dev/uinput is not writable."""
    if x is not None and y is not None and B.uinput_available():
        return B.uinput_abs_click(int(x), int(y), 0, 0, button=button, do_click=True, clicks=clicks)
    moved = None
    if x is not None and y is not None:
        moved = B.dispatch("move", x=int(x), y=int(y))
        time.sleep(0.15)
    last: dict[str, Any] = {}
    for _ in range(max(1, clicks)):
        last = B.dispatch("click", button=button)
        time.sleep(0.05)
    return {**last, "moved": moved} if moved else last


def _apply_capture_postprocessing(out: str, cx: int, cy: int, zoom: int,
                                   crop_w: int, crop_h: int, max_width: int) -> tuple:
    """Apply PIL post-processing to a captured PNG.
    Returns (full_size, crop_info) — both may be None when PIL is absent."""
    from PIL import Image
    with Image.open(out) as im:
        full = list(im.size)
        wpx, hpx = im.size
        want_crop = int(cx) >= 0 and int(cy) >= 0 and (int(zoom) > 1 or (crop_w and crop_h))
        if want_crop:
            cw = int(crop_w) if crop_w else max(64, wpx // int(zoom))
            ch = int(crop_h) if crop_h else max(64, hpx // int(zoom))
            x0 = max(0, min(int(cx) - cw // 2, wpx - cw))
            y0 = max(0, min(int(cy) - ch // 2, hpx - ch))
            im = im.crop((x0, y0, x0 + cw, y0 + ch))
            crop = {"x": x0, "y": y0, "w": cw, "h": ch, "cx": int(cx), "cy": int(cy)}
        else:
            crop = None
            if max_width and im.width > int(max_width):
                ratio = int(max_width) / im.width
                im = im.resize((int(max_width), int(im.height * ratio)))
        im.convert("RGB").save(out, format="PNG", optimize=True)
    return full, crop


# --------------------------------------------------------------------------- #
# screen capture
# --------------------------------------------------------------------------- #
@conn.handler("screen/query/capture", isolated=True, meta={"label": "Capture the screen (auto backend)"})
def capture(output: str = "", monitor: int = 0, max_width: int = 0, base64: bool = False,
            cx: int = -1, cy: int = -1, zoom: int = 0, crop_w: int = 0, crop_h: int = 0) -> dict[str, Any]:
    """Capture the live screen via the best available backend. ``max_width`` downscales
    (so coords map 1:1 to a logical screen on HiDPI); ``base64`` returns the PNG inline.
    Focus crop: pass ``cx``/``cy`` (+ ``zoom`` N -> a full/N window, or explicit
    ``crop_w``/``crop_h``) to return ONLY a zoomed tile around that point — so a
    remote caller transfers a small region where the action is, not the whole screen.
    ``crop`` in the result gives the tile's origin/size for mapping coords back."""
    out = output or os.path.join(tempfile.gettempdir(), f"urirun-kvm-shot-{os.getpid()}.png")
    try:
        res = B.dispatch("capture", output=out, monitor=monitor)
    except B.BackendError as exc:
        return _fail_from("capture", exc)
    full = crop = None
    try:
        full, crop = _apply_capture_postprocessing(out, cx, cy, zoom, crop_w, crop_h, max_width)
    except Exception:  # noqa: BLE001 - PIL optional; keep raw capture
        pass
    payload: dict[str, Any] = {"path": out, "monitor": monitor, "via": res.get("via"),
                               "backend": res.get("backend"), "fullSize": full, "crop": crop,
                               "bytes": os.path.getsize(out) if os.path.exists(out) else 0}
    if base64:
        with open(out, "rb") as fh:
            payload["pngBase64"] = _b64.b64encode(fh.read()).decode()
    return urirun.tag(_ok(**payload), "screenshot")


# --------------------------------------------------------------------------- #
# display geometry — a first-class query (callers hit a missing display/query/info
# 374x to get screen size; capture only returned it as a side effect)
# --------------------------------------------------------------------------- #
@conn.handler("display/query/info", isolated=True, meta={"label": "Screen size, monitors, scale (the capture/action coordinate space)"})
def display_info() -> dict[str, Any]:
    """The display geometry callers need without taking a screenshot: full pixel size (the
    space capture and click coordinates live in), per-monitor geometry+scale, and whether
    OS-level pixel input is trustworthy here. Cheap — no capture unless size is uncached."""
    try:
        w, h = B._screen_wh()
        surf = B.surface_report()
        mons = B._gnome_monitors() or surf.get("monitors") or []
        return _ok(action="display-info", fullSize=[w, h], width=w, height=h,
                   monitors=mons, monitorCount=len(mons), platform=B.platform_tag(),
                   wayland=surf.get("wayland"), multiMonitor=surf.get("multiMonitor"),
                   fractionalHiDPI=surf.get("fractionalHiDPI"),
                   osLevelReliable=surf.get("osLevelReliable"),
                   recommendedSurfaces=surf.get("recommendedSurfaces"))
    except Exception as exc:  # noqa: BLE001
        return _fail_from("display-info", exc)


# --------------------------------------------------------------------------- #
# input
# --------------------------------------------------------------------------- #
@conn.handler("input/command/type", isolated=True, meta={"label": "Type a whole string"})
def type_text(text: str = "") -> dict[str, Any]:
    if not text:
        return urirun.fail("text is required", connector=CONNECTOR_ID)
    try:
        return _ok(action="type", **B.dispatch("type", text=text))
    except B.BackendError as exc:
        return _fail_from("type", exc)


@conn.handler("input/command/key", isolated=True, meta={"label": "Send a key or hotkey combo"})
def key(key: str = "", keys: str = "") -> dict[str, Any]:
    combo = keys or key
    if not combo:
        return urirun.fail("key/keys is required", connector=CONNECTOR_ID)
    try:
        return _ok(action="key", **B.dispatch("key", keys=combo))
    except B.BackendError as exc:
        return _fail_from("key", exc)


@conn.handler("input/command/click", isolated=True, meta={"label": "Mouse click (optionally at x,y)"})
def click(button: str = "left", x: int | None = None, y: int | None = None) -> dict[str, Any]:
    if button not in ("left", "middle", "right"):
        return urirun.fail("button must be left|middle|right", connector=CONNECTOR_ID)
    try:
        return _ok(action="click", **_positioned_click(button, x, y))
    except B.BackendError as exc:
        return _fail_from("click", exc)


@conn.handler("input/command/move", isolated=True, meta={"label": "Move the mouse pointer (absolute)"})
def move(x: int = 0, y: int = 0) -> dict[str, Any]:
    try:
        return _ok(action="move", **B.dispatch("move", x=int(x), y=int(y)))
    except B.BackendError as exc:
        return _fail_from("move", exc)


@conn.handler("input/command/wait", isolated=True, meta={"label": "Pause for N seconds (let the UI settle)"})
def wait(seconds: float = 1.0, ms: int = 0) -> dict[str, Any]:
    """Sleep so a UI can settle between actions (page load, animation, focus change).
    A primitive the NL planner reaches for between type/click steps — pass ``seconds``
    (float) or ``ms``. Capped at 30s so a bad plan can't hang the node."""
    try:
        secs = min(30.0, max(0.0, float(ms) / 1000.0 if ms else float(seconds)))
        time.sleep(secs)
        return _ok(action="wait", seconds=secs)
    except Exception as exc:  # noqa: BLE001
        return _fail_from("wait", exc)



@conn.handler("input/command/scroll", isolated=True, meta={"label": "Scroll the wheel (dy<0 = down)"})
def scroll(dy: int = -3) -> dict[str, Any]:
    try:
        return _ok(action="scroll", **B.dispatch("scroll", dy=int(dy)))
    except B.BackendError as exc:
        return _fail_from("scroll", exc)


@conn.handler("input/command/double-click", isolated=True, meta={"label": "Double click (optionally at x,y)"})
def double_click(x: int | None = None, y: int | None = None) -> dict[str, Any]:
    try:
        return _ok(action="double-click", **_positioned_click("left", x, y, clicks=2))
    except B.BackendError as exc:
        return _fail_from("double-click", exc)


@conn.handler("input/command/triple-click", isolated=True, meta={"label": "Triple click (optionally at x,y)"})
def triple_click(x: int | None = None, y: int | None = None) -> dict[str, Any]:
    try:
        return _ok(action="triple-click", **_positioned_click("left", x, y, clicks=3))
    except B.BackendError as exc:
        return _fail_from("triple-click", exc)


@conn.handler("input/command/right-click", isolated=True, meta={"label": "Right click (optionally at x,y)"})
def right_click(x: int | None = None, y: int | None = None) -> dict[str, Any]:
    try:
        return _ok(action="right-click", **_positioned_click("right", x, y))
    except B.BackendError as exc:
        return _fail_from("right-click", exc)


@conn.handler("input/command/middle-click", isolated=True, meta={"label": "Middle click (optionally at x,y)"})
def middle_click(x: int | None = None, y: int | None = None) -> dict[str, Any]:
    try:
        return _ok(action="middle-click", **_positioned_click("middle", x, y))
    except B.BackendError as exc:
        return _fail_from("middle-click", exc)


@conn.handler("input/command/hover", isolated=True, meta={"label": "Hover/move the mouse pointer to x,y"})
def hover(x: int = 0, y: int = 0) -> dict[str, Any]:
    try:
        return _ok(action="hover", **B.dispatch("move", x=int(x), y=int(y)))
    except B.BackendError as exc:
        return _fail_from("hover", exc)


@conn.handler("input/command/drag-and-drop", isolated=True, meta={"label": "Drag and drop (approximate move->click->move)"})
def drag_and_drop(x: int, y: int, destination_x: int, destination_y: int) -> dict[str, Any]:
    try:
        B.dispatch("move", x=int(x), y=int(y))
        time.sleep(0.1)
        res = B.dispatch("move", x=int(destination_x), y=int(destination_y))
        return _ok(action="drag-and-drop", **_spread(res))
    except B.BackendError as exc:
        return _fail_from("drag-and-drop", exc)





@conn.handler("abs/command/click", isolated=True, meta={"label": "Pixel-accurate click via a uinput absolute device"})
def click_abs(x: int = 0, y: int = 0, sw: int = 0, sh: int = 0, button: str = "left",
              do_click: bool = True) -> dict[str, Any]:
    """Click pixel (x,y) of a screenshot sized (sw,sh) using a raw uinput ABSOLUTE
    device. Coordinates map by FRACTION onto the desktop, so HiDPI/multi-monitor scaling
    and pointer acceleration (which break ydotool here) are bypassed — a screenshot pixel
    maps straight to a click point. Linux only."""
    try:
        return _ok(action="click-abs", screen=[sw, sh],
                   **B.uinput_abs_click(int(x), int(y), int(sw), int(sh), button, bool(do_click)))
    except B.BackendError as exc:
        return _fail_from("click-abs", exc)


# --------------------------------------------------------------------------- #
# batched task — one bounded sequence (move/click/type/key/scroll/focus/sleep)
# --------------------------------------------------------------------------- #
@conn.handler("task/command/run", isolated=True, meta={"label": "Run a bounded input sequence"})
def task_run(steps: list | None = None) -> dict[str, Any]:
    """Execute an ordered list of ``{op, ...}`` steps in one call (so a focus→click→
    type→submit flow shares the same ydotoold session). ops: focus, move, click, type,
    key, scroll, sleep. Input is structured data — never arbitrary code."""
    log: list[dict] = []
    for st in (steps or []):
        op = str(st.get("op", ""))
        try:
            if op == "sleep":
                time.sleep(min(float(st.get("seconds", 0.2)), 5.0))
                log.append({"op": op})
                continue
            if op == "focus":
                r = B.dispatch("focus", title=str(st.get("title", "")))
            elif op == "move":
                r = B.dispatch("move", x=int(st["x"]), y=int(st["y"]))
            elif op == "click":
                if "x" in st and "y" in st:
                    B.dispatch("move", x=int(st["x"]), y=int(st["y"]))
                    time.sleep(0.15)
                r = B.dispatch("click", button=str(st.get("button", "left")))
            elif op == "type":
                r = B.dispatch("type", text=str(st.get("text", "")))
            elif op == "key":
                r = B.dispatch("key", keys=str(st.get("keys", st.get("key", ""))))
            elif op == "scroll":
                r = B.dispatch("scroll", dy=int(st.get("dy", -3)))
            else:
                log.append({"op": op, "skipped": "unknown op"})
                continue
            log.append({"op": op, "via": r.get("via"), "ok": True})
            time.sleep(float(st.get("after", 0.25)))
        except (B.BackendError, KeyError, ValueError) as exc:
            log.append({"op": op, "ok": False, "error": str(exc)[:160]})
            return urirun.fail(f"step {op!r} failed", connector=CONNECTOR_ID, steps=log)
    return _ok(action="task", steps=log)


# --------------------------------------------------------------------------- #
# windows + diagnostics
# --------------------------------------------------------------------------- #
@conn.handler("window/command/focus", isolated=True, meta={"label": "Activate a window by title"})
def focus(title: str = "") -> dict[str, Any]:
    if not title:
        return urirun.fail("title is required", connector=CONNECTOR_ID)
    try:
        return _ok(action="focus", **B.dispatch("focus", title=title))
    except B.BackendError as exc:
        return _fail_from("focus", exc)


@conn.handler("window/query/list", isolated=True, meta={"label": "List open windows"})
def window_list() -> dict[str, Any]:
    try:
        return _ok(**B.dispatch("window_list"))
    except B.BackendError as exc:
        return _fail_from("window_list", exc)


@conn.handler("window/command/close", isolated=True,
              meta={"label": "Snapshot the active page, then close it (reversible: restore)"})
def window_close(id: str = "") -> dict[str, Any]:
    """Checkpoint-before-mutate: capture the page's serializable state (URL, scroll, form
    values, sessionStorage) in one CDP round-trip, return it as ``snapshot``, then close the
    tab. The reversible engine pairs this with window/command/restore as the inverse. Fidelity
    is bounded to what the snapshot serialized; ephemeral in-memory state (live sockets, JS-only
    vars) is outside the edge and is not claimed restorable."""
    cdp = _cdp_mod()
    snapshot_js = """(() => ({
        url: location.href, scrollX: scrollX, scrollY: scrollY,
        forms: [...document.querySelectorAll('input,textarea,[contenteditable]')].map(
            (el, i) => ({i: i, ce: !!el.isContentEditable, v: el.isContentEditable ? el.textContent : el.value})),
        session: (() => { try { return Object.fromEntries(Object.entries(sessionStorage)); } catch (e) { return {}; } })()
    }))()"""
    try:
        snap = cdp.evaluate(snapshot_js)
    except (B.BackendError, cdp.CdpError) as exc:
        return _fail_from("window-close", exc)
    if isinstance(snap, dict):
        snap["id"] = id or "active"
    try:
        cdp.evaluate("window.close()")
    except (B.BackendError, cdp.CdpError):
        # some pages refuse window.close(); the tab may persist, the snapshot stays valid
        pass
    return _ok(action="window-close", did=f"close({id or 'active'})", reversible=True, snapshot=snap,
               inverse={"path": "window/command/restore", "args": {"snapshot": snap}})


@conn.handler("window/command/restore", isolated=True,
              meta={"label": "Reopen and rehydrate a window from a close snapshot"})
def window_restore(snapshot: dict | None = None) -> dict[str, Any]:
    """Inverse of window/command/close: navigate to the snapshot URL, then rehydrate scroll and
    form values (dispatching input/change so React/contenteditable register them). Honest
    caveats: sessionStorage set post-load is missed by on-load scripts and back/forward history
    is not reconstructable by a single navigate; fidelity is bounded to the snapshot."""
    import json as _json
    s = snapshot or {}
    if not s.get("url"):
        return urirun.fail("snapshot.url is required to restore", connector=CONNECTOR_ID, action="window-restore")
    rehydrate_js = """(() => {
        scrollTo(__SX__, __SY__);
        const f = __FORMS__;
        const els = document.querySelectorAll('input,textarea,[contenteditable]');
        f.forEach(x => {
            const el = els[x.i];
            if (!el) return;
            if (x.ce) el.textContent = x.v; else el.value = x.v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        });
    })()"""
    expr = (rehydrate_js.replace("__SX__", str(int(s.get("scrollX", 0))))
            .replace("__SY__", str(int(s.get("scrollY", 0))))
            .replace("__FORMS__", _json.dumps(s.get("forms") or [])))
    cdp = _cdp_mod()
    try:
        cdp.navigate(s["url"])
        cdp.page_ready()
        cdp.evaluate(expr)
    except (B.BackendError, cdp.CdpError) as exc:
        return _fail_from("window-restore", exc)
    return _ok(action="window-restore", did=f"restore({s.get('id', '?')})", reversible=True,
               inverse={"path": "window/command/close", "args": {"id": s.get("id")}})


@conn.handler("proc/command/kill", isolated=True, meta={"label": "Terminate a process by PID or name (node lifecycle control)"})
def proc_kill(pid: int = 0, name: str = "", signal: str = "TERM") -> dict[str, Any]:
    """Send a signal to a process so process lifecycle is controllable *via a URI*, not a
    side-channel shell — e.g. close a stray CDP/headless browser or restart Chrome with a
    debug port. Target by ``pid`` OR by ``name`` (pgrep -f pattern → signals every match).
    Defaults to SIGTERM (graceful); pass ``signal="KILL"`` to force. Refuses pid<=1 and a
    name shorter than 3 chars (avoid over-broad kills)."""
    import os as _os
    import signal as _sig
    import subprocess as _sp
    sig = getattr(_sig, signal if signal.startswith("SIG") else f"SIG{signal.upper()}", _sig.SIGTERM)
    targets: list[int] = []
    if name:
        if len(name) < 3:  # noqa: PLR2004
            return urirun.fail("name must be >= 3 chars", connector=CONNECTOR_ID, action="kill")
        try:
            out = _sp.run(["pgrep", "-f", name], capture_output=True, text=True, timeout=8).stdout
            targets = [int(x) for x in out.split() if x.isdigit() and int(x) != _os.getpid()]
        except Exception as exc:  # noqa: BLE001
            return urirun.fail(f"pgrep failed: {exc}", connector=CONNECTOR_ID, action="kill")
    elif int(pid) > 1:
        targets = [int(pid)]
    else:
        return urirun.fail("pass pid>1 or name>=3 chars", connector=CONNECTOR_ID, action="kill")
    killed, errs = [], []
    for p in targets:
        try:
            _os.kill(p, sig)
            killed.append(p)
        except ProcessLookupError:
            pass
        except PermissionError:
            errs.append(p)
    return _ok(action="kill", signal=sig.name, matched=len(targets), killed=killed, denied=errs)


@conn.handler("a11y/command/act", isolated=True, meta={"label": "Find a UI element by role/name and focus/click/set-text it (AT-SPI)"})
def a11y_act(app: str = "", role: str = "", name: str = "", action: str = "focus",
             text: str = "", nth: int = 0) -> dict[str, Any]:
    """Resolution-independent UI control via the accessibility tree: locate an element
    by ``app``/``role``/``name`` and ``focus``/``click``/``settext`` it — no coordinates.
    Web content (Chrome/Firefox) must have a11y enabled. Returns the element's screen
    ``bbox`` so a caller can fall back to a ``kvm`` click when no action is exposed."""
    if action not in ("focus", "click", "settext", "gettext"):
        return urirun.fail("action must be focus|click|settext|gettext", connector=CONNECTOR_ID)
    try:
        res = B.dispatch("a11y", app=app, role=role, name=name, op=action, text=text, nth=int(nth))
        return _ok(action="a11y", request={"app": app, "role": role, "name": name, "op": action}, **_spread(res))
    except B.BackendError as exc:
        return _fail_from("a11y", exc)


# --------------------------------------------------------------------------- #
# ui/* — semantic perceive → act → verify layer over locate (AT-SPI → imgl → vql)
# + input. Targets are named by text/role/app, not coordinates.
# --------------------------------------------------------------------------- #
def _click_hit(hit: dict, app: str, role: str, text: str) -> dict:
    """Act on a located hit: AT-SPI native click when actionable (no coords), else a
    kvm click at the element's centre. Prefers the locate ``center`` (OCR backends emit
    it directly), falls back to the bbox centre, and raises a clean error when the target
    was not located — instead of ``KeyError: 'bbox'`` on a tesseract miss, which returns
    ``found: false`` with no bbox."""
    if hit.get("source") == "atspi" and hit.get("actionable"):
        return {"how": "atspi-action", **B.dispatch("a11y", app=app, role=role, name=text, op="click")}
    if not hit.get("found"):
        raise B.BackendError(f"ui-click: target not located (text={text!r} role={role!r})")
    center = hit.get("center")
    if center and len(center) == 2:  # noqa: PLR2004
        cx, cy = int(center[0]), int(center[1])
    elif hit.get("bbox"):
        cx, cy = B.bbox_center(hit["bbox"])
    else:
        raise B.BackendError(f"ui-click: located hit has no center/bbox (source={hit.get('source')!r})")
    return {"how": "kvm-click", "at": [cx, cy], **_positioned_click("left", cx, cy)}


def _router_return(action: str, r: dict[str, Any]) -> dict[str, Any]:
    """Serialise a control-router result safely: drop the router's own ``ok``/``error``
    (urirun.ok/fail set those) so spreading the rest never collides, and surface the
    ``attempts`` trail either way so a miss explains which strategies were tried."""
    body = {k: v for k, v in r.items() if k not in ("ok", "error")}
    if r.get("ok") or r.get("found"):
        return _ok(action=action, **body)
    return urirun.fail(r.get("error", "no control strategy succeeded"),
                       connector=CONNECTOR_ID, action=action, **body)


@conn.handler("ui/query/find", isolated=True,
              meta={"label": "Locate a UI element (router: cdp→atspi→vision)"})
def ui_find(text: str = "", role: str = "", app: str = "", nth: int = 0, name: str = "") -> dict[str, Any]:
    return _router_return("find", C.route("locate", text=text, role=role, app=app, name=name))


@conn.handler("ui/command/click", isolated=True,
              meta={"label": "Find a target and click it (router: cdp→atspi→vision)"})
def ui_click(text: str = "", role: str = "", app: str = "", name: str = "") -> dict[str, Any]:
    return _router_return("ui-click", C.route("click", text=text, role=role, app=app, name=name))


@conn.handler("ui/command/fill", isolated=True,
              meta={"label": "Find a field, focus it and type a value (router; verifies)"})
def ui_fill(text: str = "", role: str = "entry", app: str = "", value: str = "",
            verify: bool = True, name: str = "") -> dict[str, Any]:
    """Route a fill to the best control tool (cdp DOM → atspi → vision OCR+uinput): locate
    the field by ``text``/``role``/``name``, focus it, type ``value``. The vision fallback
    VERIFIES the value actually appeared and FAILS honestly if it focused the wrong
    element; the cdp/atspi strategies act on the real element so they don't need it."""
    if not value:
        return urirun.fail("value is required", connector=CONNECTOR_ID)
    return _router_return("ui-fill", C.route("fill", text=text, role=role, app=app,
                                             name=name, value=value, verify=verify))


@conn.handler("ui/query/strategies", isolated=True,
              meta={"label": "Which control strategies are available right now"})
def ui_strategies() -> dict[str, Any]:
    return _ok(action="strategies", **C.report())


@conn.handler("env/query/profile", isolated=True,
              meta={"label": "Live capability profile of this session (cdp/atspi/ocr/input/display)"})
def env_profile() -> dict[str, Any]:
    """What UI control ACTUALLY works here — so the router fits the machine and the
    diagnostics layer recommends only feasible remediation. ``controlStrategies`` says which
    of cdp/atspi/vision can run; ``best`` is the preferred one; ``controllable`` is the
    honest top-line (false ⇒ install tesseract / grant /dev/uinput / launch a CDP Chrome)."""
    try:
        from . import environment as _env
    except ImportError:
        import environment as _env  # type: ignore
    return _ok(action="env-profile", **_env.profile())


def _surface_mod() -> Any:
    try:
        from . import surface as _s
    except ImportError:
        import surface as _s  # type: ignore
    return _s


@conn.handler("surface/query/current", isolated=True,
              meta={"label": "What UI surface is in the foreground (browser via CDP, or desktop)"})
def surface_current() -> dict[str, Any]:
    """Foreground surface so a flow need not name ``app``: a reachable CDP page ⇒ browser
    (router uses the DOM path); otherwise a desktop surface + the env's best strategy."""
    return _ok(action="surface", **_surface_mod().current())


@conn.handler("cdp/session/command/ensure", isolated=True,
              meta={"label": "Reuse or launch a dedicated-profile CDP Chrome (so the router's cdp strategy is available)"})
def cdp_ensure(url: str = "", user_data_dir: str = "", copy_from: str = "",
               wait: float = 0.0) -> dict[str, Any]:
    """Make the CDP control surface AVAILABLE — LAUNCH/PROBE SPLIT so Chrome's cold-start
    can't blow the node handler's exec cap. Reuses a live endpoint, else FIRES the launch and
    returns ``launching: True`` *without* awaiting the bind (default ``wait=0``). Poll
    ``cdp/session/query/ready`` for readiness — it won't spawn a competing Chrome (re-calling
    *this* would, fighting over the profile lock). ``wait>0`` blocks up to a cap-safe bound
    (min(wait,25)s) for convenience, but a timeout there is ``pending``, NOT a failure — Chrome
    may still be coming up. ``copy_from`` clones auth files for a logged-in session."""
    _cdp = _cdp_mod()
    r = _cdp.start_session(url=url, user_data_dir=user_data_dir, copy_from=copy_from)
    if r.get("ok") and r.get("launching") and float(wait) > 0:
        ready = _cdp.await_ready(timeout=min(float(wait), 25.0))
        r["launching"] = not ready.get("ready")
        if not ready.get("ready"):
            r["pending"] = True                       # not an error: poll cdp/session/query/ready
            r["readyError"] = ready.get("error")
    return _ok(action="cdp-ensure", **_spread(r)) if r.get("ok") else \
        urirun.fail(r.get("error", "cdp ensure failed"), connector=CONNECTOR_ID, action="cdp-ensure", **_spread(r))


@conn.handler("cdp/session/query/ready", isolated=True,
              meta={"label": "Poll until the CDP debug endpoint is reachable (no launch)"})
def cdp_session_ready(timeout: float = 12.0) -> dict[str, Any]:
    """Readiness half of the launch/probe split: poll the debug endpoint WITHOUT launching
    (distinct from ``cdp/page/query/ready``, which waits on document load). Call after
    ``cdp/session/command/ensure``; repeatable — a pure probe never spawns a competing Chrome.
    ``timeout`` is capped under the node handler exec cap; call again if not ready yet."""
    r = _cdp_mod().await_ready(timeout=min(float(timeout), 25.0))
    return _ok(action="cdp-ready", **_spread(r)) if r.get("ready") else \
        urirun.fail(r.get("error", "debugger not reachable within timeout"),
                    connector=CONNECTOR_ID, action="cdp-ready",
                    **{k: v for k, v in r.items() if k != "error"})


def _cdp_mod() -> Any:
    try:
        from . import cdp as _cdp
    except ImportError:
        import cdp as _cdp  # type: ignore
    return _cdp


@conn.handler("cdp/page/command/navigate", isolated=True,
              meta={"label": "Navigate the CDP page and wait until it finishes loading"})
def cdp_navigate(url: str = "", ready_timeout: float = 8.0) -> dict[str, Any]:
    if not url:
        return urirun.fail("url is required", connector=CONNECTOR_ID)
    cdp = _cdp_mod()
    try:
        prev = None
        try:
            prev = cdp.evaluate("location.href")   # capture before leaving, for the inverse
        except Exception:  # noqa: BLE001 - no page yet -> the inverse is simply unavailable
            prev = None
        nav = cdp.navigate(url)
        ready = cdp.page_ready(timeout=float(ready_timeout))
        out = _ok(action="cdp-navigate", url=url, ready=ready, **_spread(nav, "url"))
        if isinstance(prev, str) and prev and prev != url:
            # navigate(new) reverse navigate(old): return to the URL we left
            out["inverse"] = {"path": "cdp/page/command/navigate", "args": {"url": prev}}
        return out
    except Exception as exc:  # noqa: BLE001
        return urirun.fail(str(exc), connector=CONNECTOR_ID, action="cdp-navigate")


@conn.handler("cdp/page/query/ready", isolated=True,
              meta={"label": "Wait until the CDP page document is fully loaded"})
def cdp_ready(timeout: float = 8.0) -> dict[str, Any]:
    r = _cdp_mod().page_ready(timeout=float(timeout))
    return _ok(action="cdp-ready", **_spread(r)) if r.get("ok") else \
        urirun.fail("page not ready within timeout", connector=CONNECTOR_ID, action="cdp-ready", **_spread(r))


def _resolve_act_app(app: str) -> tuple[str, dict | None]:
    """Detect the foreground surface if app is empty. Returns (resolved_app, surface_or_None)."""
    surface = None
    if not app:
        try:
            surface = _surface_mod().current()
            if surface.get("app"):
                app = surface["app"]
        except Exception:  # noqa: BLE001
            surface = None
    return app, surface


def _act_retry_loop(op: str, text: str, role: str, app: str, name: str, value: str,
                    cheap: bool, retries: int, settle: float, budget: float,
                    start: float) -> tuple:
    """Run the route/retry loop. Returns (tries, last_result)."""
    tries: list = []
    last: dict = {}
    for attempt in range(max(1, int(retries))):
        last = C.route(op, text=text, role=role, app=app, name=name, value=value, cheap=cheap)
        ok = last.get("ok") or last.get("found")
        tries.append({"attempt": attempt + 1, "ok": bool(ok), "strategy": last.get("strategy")})
        if ok:
            return tries, last
        if time.monotonic() - start + float(settle) >= budget:
            break
        time.sleep(float(settle))
    return tries, last


def _act_reject(do: str, text: str, name: str, value: str, safe: bool) -> dict[str, Any] | None:
    """Reject a malformed/unsafe act request; return a fail dict, else None to proceed.
    Human-in-the-loop gate: refuse an irreversible label (Post/Publish/Send/Delete…) unless
    the caller explicitly drops safe — so an autonomous planner can't publish on its own."""
    if do not in ("click", "fill", "find", "wait"):
        return urirun.fail("do must be click|fill|find|wait", connector=CONNECTOR_ID)
    if do == "fill" and not value:
        return urirun.fail("value is required for fill", connector=CONNECTOR_ID)
    label = (text or name or "").strip().lower()
    if safe and do in ("click", "fill") and any(w in label for w in C._IRREVERSIBLE):
        return urirun.fail(f"refusing to {do} {label!r} with safe=true (pass safe=false to allow)",
                           connector=CONNECTOR_ID, action="act", blocked="irreversible", do=do)
    return None


def _act_ready(ready_timeout: float) -> dict[str, Any] | None:
    """If a CDP page is reachable, wait for it to finish loading; else None."""
    cdp = _cdp_mod()
    if not cdp.reachable():
        return None
    try:
        return cdp.page_ready(timeout=min(float(ready_timeout), 8.0))
    except Exception:  # noqa: BLE001
        return {"ok": False}


@conn.handler("ui/command/act", isolated=True,
              meta={"label": "Self-orchestrating UI action: wait-ready → route → retry → verify"})
def ui_act(do: str = "click", text: str = "", role: str = "", name: str = "", value: str = "",
           app: str = "", retries: int = 3, settle: float = 0.7, ready_timeout: float = 6.0,
           safe: bool = True) -> dict[str, Any]:
    """ONE high-level URI an LLM planner can target instead of hand-assembling
    wait+find+click+verify (which it gets wrong: dumb sleeps, OCR label guesses, no verify).
    Internally: (1) if a CDP page is reachable, wait for it to finish loading; (2) route the
    action (click|fill|find|wait) through cdp→atspi→vision with up to ``retries`` attempts and
    a ``settle`` pause between (covers spinners / late-rendered elements); (3) return the
    winning strategy + the per-try trail. Acting via the router means it's role/name exact on
    CDP and degrades to OCR only when it must."""
    bad = _act_reject(do, text, name, value, safe)
    if bad is not None:
        return bad
    app, surface = _resolve_act_app(app)
    budget = 25.0
    start = time.monotonic()
    ready = _act_ready(ready_timeout)
    op = "locate" if do in ("find", "wait") else do
    cheap = do in ("find", "wait")
    tries, last = _act_retry_loop(op, text, role, app, name, value, cheap, retries, settle, budget, start)
    if last.get("ok") or last.get("found"):
        body = {k: v for k, v in last.items() if k not in ("ok", "error", "attempts")}
        return _ok(action="act", do=do, app=app, surface=surface, ready=ready, tries=tries,
                   strategyAttempts=last.get("attempts"), **body)
    return urirun.fail(last.get("error", f"act:{do} failed after {len(tries)} tries"),
                       connector=CONNECTOR_ID, action="act", do=do, app=app, surface=surface,
                       ready=ready, tries=tries, waited=round(time.monotonic() - start, 1),
                       strategyAttempts=last.get("attempts"))


@conn.handler("cdp/session/query/status", isolated=True,
              meta={"label": "Is a CDP debug endpoint reachable, and on what page"})
def cdp_status() -> dict[str, Any]:
    try:
        from . import cdp as _cdp
    except ImportError:
        import cdp as _cdp  # type: ignore
    reachable = _cdp.reachable()
    return _ok(action="cdp-status", reachable=reachable, endpoint=_cdp.endpoint())


@conn.handler("ui/query/wait", isolated=True, meta={"label": "Poll until a target appears (router)"})
def ui_wait(text: str = "", role: str = "", app: str = "", timeout: float = 10.0,
            interval: float = 0.7, name: str = "") -> dict[str, Any]:
    # Bound by REAL elapsed time, capped below the node's ~30s subprocess cap: counting
    # `interval` increments let a slow CDP/OCR poll run far past `timeout` and the node
    # killed core:ui_wait with TimeoutExpired. Poll the CHEAP strategies only (cdp/atspi
    # DOM-presence) so a single poll can't stall — OCR is reserved for the click itself.
    budget = max(0.0, min(float(timeout), 22.0))
    start = time.monotonic()
    last: dict[str, Any] = {}
    while True:
        last = C.route("locate", text=text, role=role, app=app, name=name, cheap=True)
        elapsed = time.monotonic() - start
        if last.get("found"):
            # _spread also drops `found`/`waited`/`action`/`strategy` — keys this _ok sets
            # explicitly — so the route hit doesn't collide ("_ok() got multiple values for 'found'").
            return _ok(action="wait", found=True, waited=round(elapsed, 1),
                       **_spread(last, "found", "waited"))
        if elapsed >= budget:
            break
        time.sleep(min(float(interval), max(0.0, budget - elapsed)))
    return urirun.fail(f"target not found within {timeout}s", connector=CONNECTOR_ID,
                       action="wait", waited=round(time.monotonic() - start, 1),
                       attempts=last.get("attempts"))


@conn.handler("ui/query/verify", isolated=True, meta={"label": "Assert a string is present on screen"})
def ui_verify(expect: str = "", app: str = "") -> dict[str, Any]:
    if not expect:
        return urirun.fail("expect is required", connector=CONNECTOR_ID)
    try:
        hit = B.dispatch("locate", text=expect, app=app)
        return _ok(action="verify", present=bool(hit.get("found")), via=hit.get("source"))
    except B.BackendError:
        return _ok(action="verify", present=False)


# --------------------------------------------------------------------------- #
# composite UI verbs — capture + locate (VQL/OCR) + KVM act, in one route
# The "specialized commands wired to libraries" layer: a caller asks for a label,
# not pixels. Coordinates from locate map 1:1 to a native-resolution capture.
# --------------------------------------------------------------------------- #
def _capture_native(monitor: int = 0) -> str:
    """Capture at native resolution (no downscale) so OCR boxes are screen pixels."""
    out = os.path.join(tempfile.gettempdir(), f"urirun-kvm-ui-{os.getpid()}.png")
    B.dispatch("capture", output=out, monitor=monitor)
    return out


@conn.handler("ui/query/locate", isolated=True,
              meta={"label": "Locate on-screen elements by text (capture + OCR/VQL) → coordinates"})
def ui_locate(query: str = "", min_conf: int = 40, monitor: int = 0) -> dict[str, Any]:
    """Screenshot the screen and return elements whose text matches ``query`` (empty =
    all), each with a pixel ``box`` and click ``center`` — the perceive+locate half of
    the autonomous loop. Feed a ``center`` straight into ui/command/click-text or a
    kvm click."""
    try:
        shot = _capture_native(monitor)
        loc = B.dispatch("locate", image=shot, query=query, min_conf=int(min_conf))
    except B.BackendError as exc:
        return _fail_from("locate", exc)
    screen = None
    try:
        from PIL import Image
        with Image.open(shot) as im:
            screen = list(im.size)
    except Exception:  # noqa: BLE001 - PIL optional
        pass
    return _ok(action="locate", screenshot=shot, screen=screen, **_spread(loc, "screenshot", "screen"))


@conn.handler("ui/command/click-text", isolated=True,
              meta={"label": "Find on-screen text and click it via KVM (optionally type + submit)"})
def ui_click_text(text: str = "", button: str = "left", nth: int = 0, min_conf: int = 40,
                  then_type: str = "", then_key: str = "", monitor: int = 0) -> dict[str, Any]:
    """Close the perceive→locate→act loop in one call: screenshot, OCR-locate ``text``,
    move+click its center via KVM, then optionally type ``then_type`` and press
    ``then_key`` (e.g. ctrl+enter to submit). ``nth`` picks among multiple matches
    (sorted by confidence)."""
    if not text:
        return urirun.fail("text is required", connector=CONNECTOR_ID)
    try:
        shot = _capture_native(monitor)
        loc = B.dispatch("locate", image=shot, query=text, min_conf=int(min_conf))
    except B.BackendError as exc:
        return _fail_from("locate", exc)
    matches = loc.get("matches") or []
    if not matches:
        return urirun.fail(f"no on-screen text matches {text!r}", connector=CONNECTOR_ID,
                           action="click-text", screenshot=shot, candidates=0)
    target = matches[min(int(nth), len(matches) - 1)]
    cx, cy = target["center"]
    try:
        B.dispatch("move", x=cx, y=cy)
        time.sleep(0.15)
        clicked = B.dispatch("click", button=button)
        result: dict[str, Any] = {"clicked": target, "via": clicked.get("via"),
                                  "screenshot": shot, "matchCount": len(matches)}
        if then_type:
            time.sleep(0.2)
            B.dispatch("type", text=then_type)
            result["typed"] = len(then_type)
        if then_key:
            time.sleep(0.2)
            B.dispatch("key", keys=then_key)
            result["submitted"] = then_key
    except B.BackendError as exc:
        return _fail_from("click-text", exc)
    return _ok(action="click-text", text=text, **result)


@conn.handler("doctor/query/report", isolated=True, meta={"label": "Report available backends + which surface to trust"})
def doctor() -> dict[str, Any]:
    """Backends per action AND a surface report: whether OS-level pixel input is actually
    reliable on this session (it is not on Wayland multi-monitor / fractional-HiDPI), with
    the recommended surface (browser-cdp / remotedesktop-portal / vdisplay) and warnings."""
    return _ok(platform=B.platform_tag(), wayland=B.is_wayland(),
               surfaces=B.surface_report(), backends=B.registry_report())


# --------------------------------------------------------------------------- #
# desktop apps — launch / list the way the system app search does (XDG/open/start)
# --------------------------------------------------------------------------- #
@conn.handler("app://host/desktop/command/launch", isolated=True,
              meta={"label": "Launch a desktop app (XDG .desktop / open / startfile)"})
def launch(app: str = "", compose: str = "", args: list | None = None, settle: float = 0) -> dict[str, Any]:
    """Launch a desktop app by resolving it the way the system app search does —
    XDG ``.desktop`` entries on Linux (covers Flatpak/Snap/PATH), ``open -a`` on macOS,
    ``startfile`` on Windows. ``compose`` appends Thunderbird's ``-compose`` draft;
    ``settle`` seconds (<=30) are slept so a follow-up capture/keypress sees the window."""
    if not app:
        return urirun.fail("app is required", connector=CONNECTOR_ID)
    try:
        res = B.dispatch("launch", app=app, compose=compose, args=args or [], settle=settle)
        out = _ok(action="launch", **res)
        # reversibility contract: launch ⟂ kill(pid). Returning the concrete inverse lets the host
        # transition ledger undo this launch (close the app we opened) — create⟂delete, no CDP.
        pid = res.get("pid")
        if pid:
            node = os.environ.get("URIRUN_NODE_NAME", "host")
            out["inverse"] = {"uri": f"kvm://{node}/proc/command/kill", "args": {"pid": int(pid)}}
        return out
    except B.BackendError as exc:
        return _fail_from("launch", exc)


@conn.handler("app://host/desktop/query/list", isolated=True,
              meta={"label": "List launchable desktop apps"})
def list_apps(filter: str = "") -> dict[str, Any]:  # noqa: A002 - route input field name
    """The action space for launch: installed apps (id + name), so an LLM picks by name
    instead of guessing a PATH binary."""
    try:
        return _ok(action="list_apps", **B.dispatch("launch_list", filter=filter))
    except B.BackendError as exc:
        return _fail_from("list_apps", exc)



def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings)."""
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    return conn.manifest(urirun.load_manifest(__package__))


def main(argv: list[str] | None = None) -> int:
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    raise SystemExit(main())
