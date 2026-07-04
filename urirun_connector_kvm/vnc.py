# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Direct RFB (VNC) surface — the reliable way to drive a noVNC-hosted desktop. Instead of
# synthesizing browser events against the scaled noVNC <canvas> (lossy for OCR, fragile for
# focus/keymaps), this speaks the RFB protocol to the VNC server itself: capture reads the
# NATIVE framebuffer (pixel-perfect, so OCR locate actually works) and input injects RFB
# pointer/key events at exact remote coordinates — no canvas-scale mapping, no keyboard-focus
# races. Requires the [vnc] extra (vncdotool). The web noVNC client and this surface can be
# used side by side: a human watches through noVNC while URIs act through RFB.
#
# Target resolution order: explicit ``target=`` on the route, else URIRUN_KVM_VNC
# (vncdotool syntax: 'host::5900' for a raw port, 'host:1' for display :1).
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


class VncError(RuntimeError):
    pass


def resolve_target(target: str = "") -> str:
    t = (target or os.environ.get("URIRUN_KVM_VNC", "")).strip()
    if not t:
        raise VncError("no VNC target: pass target='host::5900' or set URIRUN_KVM_VNC")
    return t


@contextmanager
def session(target: str = "", password: str | None = None, timeout: float = 12) -> Iterator[Any]:
    """Connect for one operation batch and always disconnect: routes run isolated
    (subprocess per call), so a cached client would never be reused anyway."""
    try:
        from vncdotool import api
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise VncError("vncdotool not installed — pip install 'urirun-connector-kvm[vnc]'") from exc
    client = api.connect(resolve_target(target), password=password, timeout=timeout)
    try:
        yield client
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001 - disconnect is best-effort cleanup
            pass


def capture(target: str = "", out: str = "", password: str | None = None) -> dict:
    """Native-resolution framebuffer grab. Returns path + size; size doubles as the
    coordinate space for click/move (RFB coords == image px, always)."""
    out = out or os.path.join(_shots_dir(), "vnc_capture.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with session(target, password) as c:
        c.captureScreen(out)
    w = h = None
    try:
        from PIL import Image
        with Image.open(out) as im:
            w, h = im.size
    except Exception:  # noqa: BLE001 - Pillow optional; size is informative only
        pass
    return {"path": out, "width": w, "height": h, "via": "rfb", "coord_space": "framebuffer-px"}


def click(x: int, y: int, button: int = 1, double: bool = False,
          target: str = "", password: str | None = None) -> dict:
    """Pointer press+release at EXACT framebuffer coords (1=left 2=middle 3=right)."""
    with session(target, password) as c:
        c.mouseMove(int(x), int(y))
        c.mousePress(int(button))
        if double:
            c.pause(0.08)
            c.mousePress(int(button))
    return {"clicked": [int(x), int(y)], "button": int(button), "double": bool(double), "via": "rfb"}


def move(x: int, y: int, target: str = "", password: str | None = None) -> dict:
    with session(target, password) as c:
        c.mouseMove(int(x), int(y))
    return {"moved": [int(x), int(y)], "via": "rfb"}


_CHAR_KEYS = {" ": "space", "\n": "enter", "\t": "tab"}


def type_text(text: str, enter: bool = False, target: str = "", password: str | None = None) -> dict:
    """Type text char-by-char as RFB key events (keysyms carry case/symbols natively —
    no host keyboard-layout dependency, unlike ydotool/xdotool)."""
    with session(target, password) as c:
        for ch in text:
            c.keyPress(_CHAR_KEYS.get(ch, ch))
        if enter:
            c.keyPress("enter")
    return {"typed": len(text), "enter": bool(enter), "via": "rfb"}


def key_combo(combo: str, target: str = "", password: str | None = None) -> dict:
    """Press a chord like 'ctrl-alt-t', 'alt-F2', 'enter': modifiers held, final key
    pressed, modifiers released in reverse order."""
    parts = [p for p in combo.replace("+", "-").split("-") if p]
    if not parts:
        raise VncError("empty key combo")
    mods, last = parts[:-1], parts[-1]
    with session(target, password) as c:
        for m in mods:
            c.keyDown(m)
        c.keyPress(_CHAR_KEYS.get(last, last))
        for m in reversed(mods):
            c.keyUp(m)
    return {"combo": combo, "via": "rfb"}


def _shots_dir() -> str:
    base = os.environ.get("URIRUN_ARTIFACTS_DIR",
                          os.path.join(os.path.expanduser("~"), ".urirun", "artifacts"))
    return os.path.join(base, "screenshots")
