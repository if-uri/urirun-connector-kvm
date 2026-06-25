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

CONNECTOR_ID = "kvm"
conn = urirun.connector(CONNECTOR_ID, scheme="kvm")


def _ok(**kw) -> dict[str, Any]:
    return urirun.ok(connector=CONNECTOR_ID, **kw)


def _fail_from(action: str, exc: Exception) -> dict[str, Any]:
    return urirun.fail(str(exc), connector=CONNECTOR_ID, action=action, platform=B.platform_tag())


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
            elif max_width and im.width > int(max_width):
                ratio = int(max_width) / im.width
                im = im.resize((int(max_width), int(im.height * ratio)))
            im.convert("RGB").save(out, format="PNG", optimize=True)
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
        moved = None
        if x is not None and y is not None:
            moved = B.dispatch("move", x=int(x), y=int(y))
            time.sleep(0.15)
        return _ok(action="click", moved=moved, **B.dispatch("click", button=button))
    except B.BackendError as exc:
        return _fail_from("click", exc)


@conn.handler("input/command/move", isolated=True, meta={"label": "Move the mouse pointer (absolute)"})
def move(x: int = 0, y: int = 0) -> dict[str, Any]:
    try:
        return _ok(action="move", **B.dispatch("move", x=int(x), y=int(y)))
    except B.BackendError as exc:
        return _fail_from("move", exc)


@conn.handler("input/command/scroll", isolated=True, meta={"label": "Scroll the wheel (dy<0 = down)"})
def scroll(dy: int = -3) -> dict[str, Any]:
    try:
        return _ok(action="scroll", **B.dispatch("scroll", dy=int(dy)))
    except B.BackendError as exc:
        return _fail_from("scroll", exc)


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
                time.sleep(min(float(st.get("seconds", 0.2)), 5.0)); log.append({"op": op}); continue
            if op == "focus":
                r = B.dispatch("focus", title=str(st.get("title", "")))
            elif op == "move":
                r = B.dispatch("move", x=int(st["x"]), y=int(st["y"]))
            elif op == "click":
                if "x" in st and "y" in st:
                    B.dispatch("move", x=int(st["x"]), y=int(st["y"])); time.sleep(0.15)
                r = B.dispatch("click", button=str(st.get("button", "left")))
            elif op == "type":
                r = B.dispatch("type", text=str(st.get("text", "")))
            elif op == "key":
                r = B.dispatch("key", keys=str(st.get("keys", st.get("key", ""))))
            elif op == "scroll":
                r = B.dispatch("scroll", dy=int(st.get("dy", -3)))
            else:
                log.append({"op": op, "skipped": "unknown op"}); continue
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
        return _ok(action="a11y", request={"app": app, "role": role, "name": name, "op": action}, **res)
    except B.BackendError as exc:
        return _fail_from("a11y", exc)


# --------------------------------------------------------------------------- #
# ui/* — semantic perceive → act → verify layer over locate (AT-SPI → imgl → vql)
# + input. Targets are named by text/role/app, not coordinates.
# --------------------------------------------------------------------------- #
def _click_hit(hit: dict, app: str, role: str, text: str) -> dict:
    """Act on a located hit: AT-SPI native click when actionable (no coords), else a
    kvm click at the element's centre."""
    if hit.get("source") == "atspi" and hit.get("actionable"):
        return {"how": "atspi-action", **B.dispatch("a11y", app=app, role=role, name=text, op="click")}
    cx, cy = B.bbox_center(hit["bbox"])
    B.dispatch("move", x=cx, y=cy); time.sleep(0.15)
    return {"how": "kvm-click", "at": [cx, cy], **B.dispatch("click", button="left")}


@conn.handler("ui/query/find", isolated=True, meta={"label": "Locate a UI element by text/role (AT-SPI→imgl→vql)"})
def ui_find(text: str = "", role: str = "", app: str = "", nth: int = 0) -> dict[str, Any]:
    try:
        return _ok(action="find", **B.dispatch("locate", text=text, role=role, app=app, nth=int(nth)))
    except B.BackendError as exc:
        return _fail_from("locate", exc)


@conn.handler("ui/command/click", isolated=True, meta={"label": "Find a target and click it (a11y action or centre click)"})
def ui_click(text: str = "", role: str = "", app: str = "") -> dict[str, Any]:
    try:
        hit = B.dispatch("locate", text=text, role=role, app=app)
        return _ok(action="ui-click", target={"text": text, "role": role}, hit=hit,
                   result=_click_hit(hit, app, role, text))
    except B.BackendError as exc:
        return _fail_from("ui-click", exc)


@conn.handler("ui/command/fill", isolated=True, meta={"label": "Find a field, focus it and type a value (+verify)"})
def ui_fill(text: str = "", role: str = "entry", app: str = "", value: str = "", verify: bool = False) -> dict[str, Any]:
    """Locate a field by ``text``/``role``, focus it (AT-SPI grab or centre click), type
    ``value``, and optionally verify the value landed."""
    if not value:
        return urirun.fail("value is required", connector=CONNECTOR_ID)
    try:
        hit = B.dispatch("locate", text=text, role=role, app=app)
        focused = _click_hit(hit, app, role, text) if hit.get("source") != "atspi" else \
            {"how": "atspi-focus", **B.dispatch("a11y", app=app, role=role, name=text, op="focus")}
        time.sleep(0.3)
        typed = B.dispatch("type", text=value)
        out = {"action": "ui-fill", "hit": hit, "focused": focused, "typed": typed}
        if verify:
            v = B.dispatch("locate", text=value[:24], app=app)
            out["verified"] = bool(v.get("found"))
        return _ok(**out)
    except B.BackendError as exc:
        return _fail_from("ui-fill", exc)


@conn.handler("ui/query/wait", isolated=True, meta={"label": "Poll until a target appears (or timeout)"})
def ui_wait(text: str = "", role: str = "", app: str = "", timeout: float = 10.0, interval: float = 0.7) -> dict[str, Any]:
    deadline = float(timeout)
    waited = 0.0
    while waited <= deadline:
        try:
            hit = B.dispatch("locate", text=text, role=role, app=app)
            return _ok(action="wait", found=True, waited=round(waited, 1), **hit)
        except B.BackendError:
            time.sleep(float(interval)); waited += float(interval)
    return urirun.fail(f"target not found within {timeout}s", connector=CONNECTOR_ID, action="wait")


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
    return _ok(action="locate", screenshot=shot, screen=screen, **loc)


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
        return _ok(action="launch", **B.dispatch("launch", app=app, compose=compose,
                                                 args=args or [], settle=settle))
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


# --- authoring surface: bindings / manifest / CLI --------------------------
def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings)."""
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    return conn.manifest(urirun.load_manifest(__package__))


def main(argv: list[str] | None = None) -> int:
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
