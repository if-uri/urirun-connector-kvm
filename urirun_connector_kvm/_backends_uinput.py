"""Pixel-accurate pointer via raw uinput ABSOLUTE device — extracted from backends.py."""
from __future__ import annotations

import fcntl as _fcntl
import os
import struct as _struct
import tempfile
import time
from collections.abc import Callable
from typing import Any

from urirun.connectors.backend_registry import BackendError

_UI = ord("U")


def _ui_io(nr: int) -> int:       return (0 << 30) | (_UI << 8) | nr
def _ui_iow(nr: int, sz: int) -> int:  return (1 << 30) | (sz << 16) | (_UI << 8) | nr


_UI_DEV_CREATE, _UI_DEV_DESTROY = _ui_io(1), _ui_io(2)
_UI_SET_EVBIT, _UI_SET_KEYBIT, _UI_SET_ABSBIT = _ui_iow(100, 4), _ui_iow(101, 4), _ui_iow(103, 4)
_EV_SYN, _EV_KEY, _EV_ABS = 0, 1, 3
_ABS_X, _ABS_Y = 0, 1
_BTN_CODE = {"left": 0x110, "right": 0x111, "middle": 0x112}
_BTN_TOUCH = 0x14A
_ABS_RANGE = 65535

_SCREEN_WH_CACHE = os.path.join(tempfile.gettempdir(), "urirun-kvm-screen-wh")


def uinput_available() -> bool:
    return os.path.exists("/dev/uinput") and os.access("/dev/uinput", os.W_OK)


def _uinput_create_abs() -> int:
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    for ev in (_EV_KEY, _EV_ABS, _EV_SYN):
        _fcntl.ioctl(fd, _UI_SET_EVBIT, ev)
    for b in (0x110, 0x111, 0x112, _BTN_TOUCH):
        _fcntl.ioctl(fd, _UI_SET_KEYBIT, b)
    _fcntl.ioctl(fd, _UI_SET_ABSBIT, _ABS_X)
    _fcntl.ioctl(fd, _UI_SET_ABSBIT, _ABS_Y)
    absmax = [0] * 64
    absmax[_ABS_X] = absmax[_ABS_Y] = _ABS_RANGE
    dev = _struct.pack("<80s4HI", b"urirun-abs-pointer", 0x03, 0x1234, 0x5678, 1, 0)
    dev += _struct.pack("<64i", *absmax) + _struct.pack("<192i", *([0] * 192))
    os.write(fd, dev)
    _fcntl.ioctl(fd, _UI_DEV_CREATE)
    return fd


def _read_text(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def _screen_wh() -> tuple[int, int]:
    """The full screen size in pixels that ``capture`` produces — the space callers'
    coordinates live in (capture-space == action-space). Sources, in order: the
    ``URIRUN_KVM_SCREEN=WxH`` env (set it at deploy time when known), a tmp cache, then
    one portal capture (cached). ``isolated=True`` handlers re-import per call, so the
    cache is a file, not a module global. Returns ``(0, 0)`` if it cannot be determined,
    in which case ``uinput_abs_click`` treats the coords as already absolute."""
    env = os.environ.get("URIRUN_KVM_SCREEN", "").lower()
    for src in (env, _read_text(_SCREEN_WH_CACHE).lower()):
        if "x" in src:
            try:
                w, h = src.split("x")[:2]
                return int(w), int(h)
            except ValueError:
                pass
    try:
        try:
            from urirun_connector_kvm.backends import dispatch  # lazy to avoid circular at module level
        except ImportError:  # flat-module deploy
            from backends import dispatch  # type: ignore
        out = os.path.join(tempfile.gettempdir(), "urirun-kvm-wh.png")
        dispatch("capture", output=out, monitor=0)
        from PIL import Image
        with Image.open(out) as im:
            w, h = int(im.size[0]), int(im.size[1])
        if w and h:
            try:
                with open(_SCREEN_WH_CACHE, "w") as f:
                    f.write(f"{w}x{h}")
            except OSError:
                pass
            return w, h
    except Exception:  # noqa: BLE001 - best effort; fall back to absolute coords
        pass
    return 0, 0


def _calib() -> tuple | None:
    """Runtime calibration of the abs-device->screenshot transform, learned per display
    (the uinput [0,65535] range does NOT map 1:1 to the portal screenshot under
    fractional-HiDPI / multi-region Mutter). ``URIRUN_KVM_CALIB="ax,bx,ay,by"`` encodes
    ``landing_pixel = a*commanded_pixel + b`` per axis (fit by the host calibration pass).
    Returns the 4 floats, or ``None`` when unset/invalid (then coords are used as-is)."""
    try:
        ax, bx, ay, by = (float(v) for v in os.environ.get("URIRUN_KVM_CALIB", "").split(","))
        return ax, bx, ay, by
    except (ValueError, TypeError):
        return None


def _compute_abs_coords(px: float, py: float, sw: int, sh: int) -> tuple[int, int]:
    """Apply calibration (if set) and map pixel coords to uinput [0,65535] ABS range."""
    cal = _calib()
    if cal:
        ca_x, cb_x, ca_y, cb_y = cal
        if ca_x:
            px = (px - cb_x) / ca_x
        if ca_y:
            py = (py - cb_y) / ca_y
        px = max(0.0, min(float(sw), px))
        py = max(0.0, min(float(sh), py))
    ax = max(0, min(_ABS_RANGE, int(px / sw * _ABS_RANGE) if sw else int(px)))
    ay = max(0, min(_ABS_RANGE, int(py / sh * _ABS_RANGE) if sh else int(py)))
    return ax, ay


def _uinput_emit_clicks(ev: Callable, fd: int, button: str, clicks: int) -> None:
    """Emit ``clicks`` press/release pairs on the open uinput ``fd`` via the ``ev`` writer.
    N presses on ONE device = a real double/triple-click. Factored out of ``uinput_abs_click``."""
    bc = _BTN_CODE.get(button, 0x110)
    for _i in range(max(1, int(clicks))):
        ev(fd, _EV_KEY, bc, 1)
        ev(fd, _EV_KEY, _BTN_TOUCH, 1)
        ev(fd, _EV_SYN, 0, 0)
        time.sleep(0.06)
        ev(fd, _EV_KEY, bc, 0)
        ev(fd, _EV_KEY, _BTN_TOUCH, 0)
        ev(fd, _EV_SYN, 0, 0)
        time.sleep(0.06)


def uinput_abs_click(x: int, y: int, sw: int, sh: int, button: str = "left",
                     do_click: bool = True, settle: float = 0.9, clicks: int = 1) -> dict:
    if not uinput_available():
        raise BackendError("no write access to /dev/uinput (add user to 'input' group or udev rule)")
    if not sw or not sh:  # auto-detect from the capture surface when the caller omits it
        dsw, dsh = _screen_wh()
        sw, sh = sw or dsw, sh or dsh
    ax, ay = _compute_abs_coords(float(x), float(y), sw, sh)

    def ev(fd: int, t: int, c: int, v: int) -> None:
        os.write(fd, _struct.pack("llHHi", 0, 0, t, c, v))
    fd = _uinput_create_abs()
    try:
        time.sleep(float(settle))  # compositor discovers + maps the new device
        ev(fd, _EV_ABS, _ABS_X, ax)
        ev(fd, _EV_ABS, _ABS_Y, ay)
        ev(fd, _EV_SYN, 0, 0)
        time.sleep(0.25)
        if do_click:
            _uinput_emit_clicks(ev, fd, button, clicks)
        time.sleep(0.2)
        return {"via": "uinput-absolute", "abs": [ax, ay], "pixel": [x, y],
                "clicked": bool(do_click), "clicks": int(clicks) if do_click else 0}
    finally:
        try:
            _fcntl.ioctl(fd, _UI_DEV_DESTROY)
        except Exception:  # noqa: BLE001
            pass
        os.close(fd)
