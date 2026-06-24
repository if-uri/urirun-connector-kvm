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
def capture(output: str = "", monitor: int = 0, max_width: int = 0, base64: bool = False) -> dict[str, Any]:
    """Capture the live screen via the best available backend. ``max_width`` downscales
    (so coords map 1:1 to a logical screen on HiDPI); ``base64`` returns the PNG inline
    so a remote caller can analyze it without a file fetch."""
    out = output or os.path.join(tempfile.gettempdir(), f"urirun-kvm-shot-{os.getpid()}.png")
    try:
        res = B.dispatch("capture", output=out, monitor=monitor)
    except B.BackendError as exc:
        return _fail_from("capture", exc)
    full = None
    try:
        from PIL import Image
        with Image.open(out) as im:
            full = list(im.size)
            if max_width and im.width > int(max_width):
                ratio = int(max_width) / im.width
                im = im.resize((int(max_width), int(im.height * ratio)))
            im.convert("RGB").save(out, format="PNG", optimize=True)
    except Exception:  # noqa: BLE001 - PIL optional; keep raw capture
        pass
    payload: dict[str, Any] = {"path": out, "monitor": monitor, "via": res.get("via"),
                               "backend": res.get("backend"), "fullSize": full,
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


@conn.handler("doctor/query/report", isolated=True, meta={"label": "Report available backends per action"})
def doctor() -> dict[str, Any]:
    return _ok(platform=B.platform_tag(), wayland=B.is_wayland(), backends=B.registry_report())


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
