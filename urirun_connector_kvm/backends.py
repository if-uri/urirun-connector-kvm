"""Decorator-registered, cross-platform desktop-control backends for ``kvm://``.

Each backend wraps **one** helpful library or OS tool and registers itself with a
``@backend(action, name, ...)`` decorator. At call time ``dispatch(action, ...)``
picks the highest-priority backend that is *available* on the live
platform/session and tries it, falling through to the next on failure — so the
same ``kvm://`` routes work on Linux (Wayland *and* X11), Windows and macOS,
using whatever capture/input libraries happen to be installed.

Add a backend for a new tool by writing one decorated function; nothing else in
the connector changes. ``needs_bin``/``needs_mod`` gate availability and double as
install hints surfaced by the ``doctor`` route.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable


# --------------------------------------------------------------------------- #
# platform / session detection
# --------------------------------------------------------------------------- #
def is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def is_x11() -> bool:
    return bool(os.environ.get("DISPLAY")) and not is_wayland()


def platform_tag() -> str:
    if sys.platform.startswith("linux"):
        return "linux-wayland" if is_wayland() else "linux-x11"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith(("win", "cygwin")):
        return "windows"
    return "linux-x11"


ALL_PLATFORMS = ("linux-wayland", "linux-x11", "windows", "macos")


# --------------------------------------------------------------------------- #
# registry + @backend decorator
# --------------------------------------------------------------------------- #
def have_bin(name: str) -> bool:
    return shutil.which(name) is not None


def have_mod(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:  # noqa: BLE001
        return False


@dataclass
class Backend:
    action: str
    name: str
    fn: Callable[..., Any]
    priority: int = 50
    platforms: tuple = ALL_PLATFORMS
    needs_bin: tuple = ()
    needs_mod: tuple = ()

    def missing(self) -> dict:
        return {
            "bin": [b for b in self.needs_bin if not have_bin(b)],
            "mod": [m for m in self.needs_mod if not have_mod(m)],
        }

    def available(self) -> bool:
        if platform_tag() not in self.platforms:
            return False
        m = self.missing()
        return not m["bin"] and not m["mod"]


_REGISTRY: dict[str, list[Backend]] = {}


def backend(action: str, name: str, *, priority: int = 50, platforms: tuple = ALL_PLATFORMS,
            needs_bin: tuple = (), needs_mod: tuple = ()) -> Callable:
    """Register ``fn`` as a backend for ``action``. Highest priority + available wins."""
    def deco(fn: Callable) -> Callable:
        _REGISTRY.setdefault(action, []).append(
            Backend(action, name, fn, priority, platforms, tuple(needs_bin), tuple(needs_mod)))
        _REGISTRY[action].sort(key=lambda b: -b.priority)
        return fn
    return deco


class BackendError(RuntimeError):
    pass


def dispatch(action: str, **kwargs) -> dict:
    """Run ``action`` through the best available backend, returning a result dict
    with ``backend`` set, or raising ``BackendError`` with per-backend diagnostics."""
    candidates = _REGISTRY.get(action, [])
    if not candidates:
        raise BackendError(f"no backends registered for action {action!r}")
    tried, errors = [], []
    for b in candidates:
        if not b.available():
            continue
        tried.append(b.name)
        try:
            result = b.fn(**kwargs) or {}
            result.setdefault("backend", b.name)
            result["platform"] = platform_tag()
            return result
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{b.name}: {exc}")
    if not tried:
        hints = []
        for b in candidates:
            if platform_tag() in b.platforms:
                miss = b.missing()
                want = miss["bin"] + miss["mod"]
                if want:
                    hints.append(f"{b.name} (install: {', '.join(want)})")
        raise BackendError(f"no available backend for {action!r} on {platform_tag()}; "
                           f"options: {'; '.join(hints) or 'none'}")
    raise BackendError(f"all backends failed for {action!r}: {' | '.join(errors)}")


def registry_report() -> dict:
    """Diagnostics for the ``doctor`` route: which backend serves each action."""
    out = {}
    for action, backs in _REGISTRY.items():
        out[action] = [{"name": b.name, "priority": b.priority, "available": b.available(),
                        "platforms": list(b.platforms), "missing": b.missing()} for b in backs]
    return out


def _run(argv: list[str], *, env=None, timeout: float = 30) -> subprocess.CompletedProcess:
    p = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
    if p.returncode != 0:
        raise BackendError((p.stderr or f"{argv[0]} exit {p.returncode}").strip()[:200])
    return p


# --------------------------------------------------------------------------- #
# CAPTURE backends
# --------------------------------------------------------------------------- #
_PORTAL_SCRIPT = r"""
import sys, dbus, dbus.mainloop.glib
from gi.repository import GLib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus(); token = "urisys_portal"
sender = bus.get_unique_name()[1:].replace(".", "_")
rp = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
state = {"uri": None, "error": None}
def _r(resp, res):
    state["error"] = (f"portal code {resp}" if int(resp) else (None if "uri" in res else "missing uri"))
    state["uri"] = str(res.get("uri")) if "uri" in res else None; loop.quit()
bus.add_signal_receiver(_r, dbus_interface="org.freedesktop.portal.Request", path=rp, signal_name="Response")
proxy = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
dbus.Interface(proxy, "org.freedesktop.portal.Screenshot").Screenshot("", {"handle_token": token, "interactive": False})
loop = GLib.MainLoop(); GLib.timeout_add(12000, lambda: (loop.quit(), False)[1]); loop.run()
if state["error"]: print(state["error"], file=sys.stderr); sys.exit(2)
if not state["uri"]: print("timeout", file=sys.stderr); sys.exit(3)
print(state["uri"])
"""


def _portal_python() -> str | None:
    """A python interpreter that can import dbus+gi (the node venv often can't, but
    the system python can after `dnf/apt install python3-gobject python3-dbus`)."""
    for c in (os.environ.get("URISYS_PORTAL_PYTHON"), "/usr/bin/python3", shutil.which("python3"), sys.executable):
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", "import dbus, gi"], capture_output=True, timeout=5).returncode == 0:
                return c
        except Exception:  # noqa: BLE001
            continue
    return None


@backend("capture", "portal", priority=95, platforms=("linux-wayland",))
def _cap_portal(output: str, **_) -> dict:
    """XDG Desktop Portal screenshot — the only sanctioned live capture on GNOME/KDE
    Wayland. Runs via a system python with dbus+gi; needs a one-time permission grant."""
    py = _portal_python()
    if not py:
        raise BackendError("portal needs python3 with dbus+gi (install python3-gobject python3-dbus)")
    import urllib.parse
    from pathlib import Path
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    p = _run([py, "-c", _PORTAL_SCRIPT], env=env, timeout=20)
    src = Path(urllib.parse.urlparse(p.stdout.strip()).path)
    data = src.read_bytes()
    Path(output).write_bytes(data)
    return {"path": output, "bytes": len(data), "via": "xdg-portal"}


@backend("capture", "grim", priority=85, platforms=("linux-wayland",), needs_bin=("grim",))
def _cap_grim(output: str, **_) -> dict:
    _run(["grim", output]); return {"path": output, "via": "grim"}


@backend("capture", "mss", priority=70, platforms=("linux-x11", "windows", "macos"), needs_mod=("mss",))
def _cap_mss(output: str, monitor: int = 0, **_) -> dict:
    import mss as _mss
    with _mss.mss() as sct:
        mons = sct.monitors
        mon = mons[monitor if 0 <= monitor < len(mons) else 0]
        img = sct.grab(mon)
        _mss.tools.to_png(img.rgb, img.size, output=output)
    return {"path": output, "via": "mss", "size": list(img.size)}


@backend("capture", "pillow", priority=65, platforms=("windows", "macos"), needs_mod=("PIL",))
def _cap_pillow(output: str, **_) -> dict:
    from PIL import ImageGrab
    ImageGrab.grab().save(output)
    return {"path": output, "via": "PIL.ImageGrab"}


@backend("capture", "scrot", priority=60, platforms=("linux-x11",), needs_bin=("scrot",))
def _cap_scrot(output: str, **_) -> dict:
    _run(["scrot", "-o", output]); return {"path": output, "via": "scrot"}


@backend("capture", "imagemagick", priority=40, platforms=("linux-x11",), needs_bin=("import",))
def _cap_im(output: str, **_) -> dict:
    _run(["import", "-window", "root", output]); return {"path": output, "via": "imagemagick"}


@backend("capture", "gnome-screenshot", priority=35, platforms=("linux-x11",), needs_bin=("gnome-screenshot",))
def _cap_gnome(output: str, **_) -> dict:
    _run(["gnome-screenshot", "-f", output], timeout=20); return {"path": output, "via": "gnome-screenshot"}


@backend("capture", "screencapture", priority=80, platforms=("macos",), needs_bin=("screencapture",))
def _cap_macos(output: str, **_) -> dict:
    _run(["screencapture", "-x", output]); return {"path": output, "via": "screencapture"}


# --------------------------------------------------------------------------- #
# INPUT backends — ydotool (Wayland), wtype, xdotool (X11), pynput (cross-platform)
# --------------------------------------------------------------------------- #
def _ydotool_socket() -> str:
    return os.environ.get("YDOTOOL_SOCKET") or f"/run/user/{os.getuid()}/.ydotool_socket"


def ensure_ydotoold() -> str:
    """ydotool needs the ydotoold daemon holding /dev/uinput. Start it (user-owned
    socket; works without root when the user can open /dev/uinput) if not running."""
    sock = _ydotool_socket()
    running = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True).returncode == 0
    if not running:
        env = os.environ.copy(); env["YDOTOOL_SOCKET"] = sock
        subprocess.Popen(["ydotoold", "-p", sock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=env)
        for _ in range(40):
            if os.path.exists(sock):
                break
            time.sleep(0.1)
        time.sleep(0.3)
    return sock


def _yd_env() -> dict:
    env = os.environ.copy(); env["YDOTOOL_SOCKET"] = ensure_ydotoold(); return env


_YD_BUTTON = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}

# evdev keycodes for ydotool `key` (subset; extend as needed)
_YD_KEY = {"enter": "28", "return": "28", "tab": "15", "esc": "1", "escape": "1", "space": "57",
           "backspace": "14", "ctrl": "29", "shift": "42", "alt": "56", "super": "125", "meta": "125",
           "left": "105", "right": "106", "up": "103", "down": "108", "a": "30", "c": "46", "v": "47",
           "x": "45", "z": "44", "t": "20", "w": "17", "l": "38", "f4": "62"}


def _yd_keyseq(combo: str) -> list[str]:
    keys = [_YD_KEY.get(k.strip().lower()) for k in combo.replace("-", "+").split("+")]
    keys = [k for k in keys if k]
    return [f"{k}:1" for k in keys] + [f"{k}:0" for k in reversed(keys)]


# ---- type ----
@backend("type", "ydotool", priority=80, platforms=("linux-wayland",), needs_bin=("ydotool", "ydotoold"))
def _type_ydotool(text: str, **_) -> dict:
    _run(["ydotool", "type", "--", text], env=_yd_env()); return {"via": "ydotool", "chars": len(text)}


@backend("type", "wtype", priority=60, platforms=("linux-wayland",), needs_bin=("wtype",))
def _type_wtype(text: str, **_) -> dict:
    _run(["wtype", "--", text]); return {"via": "wtype", "chars": len(text)}


@backend("type", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _type_xdotool(text: str, **_) -> dict:
    _run(["xdotool", "type", "--", text]); return {"via": "xdotool", "chars": len(text)}


@backend("type", "pynput", priority=40, needs_mod=("pynput",))
def _type_pynput(text: str, **_) -> dict:
    from pynput.keyboard import Controller
    Controller().type(text); return {"via": "pynput", "chars": len(text)}


# ---- click ----
@backend("click", "ydotool", priority=80, platforms=("linux-wayland",), needs_bin=("ydotool", "ydotoold"))
def _click_ydotool(button: str = "left", **_) -> dict:
    _run(["ydotool", "click", _YD_BUTTON.get(button, "0xC0")], env=_yd_env()); return {"via": "ydotool", "button": button}


@backend("click", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _click_xdotool(button: str = "left", **_) -> dict:
    _run(["xdotool", "click", {"left": "1", "middle": "2", "right": "3"}.get(button, "1")])
    return {"via": "xdotool", "button": button}


@backend("click", "pynput", priority=40, needs_mod=("pynput",))
def _click_pynput(button: str = "left", **_) -> dict:
    from pynput.mouse import Button, Controller
    Controller().click({"left": Button.left, "right": Button.right, "middle": Button.middle}[button])
    return {"via": "pynput", "button": button}


# ---- move (absolute) ----
@backend("move", "ydotool", priority=80, platforms=("linux-wayland",), needs_bin=("ydotool", "ydotoold"))
def _move_ydotool(x: int, y: int, **_) -> dict:
    _run(["ydotool", "mousemove", "-a", "-x", str(int(x)), "-y", str(int(y))], env=_yd_env())
    return {"via": "ydotool", "x": x, "y": y}


@backend("move", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _move_xdotool(x: int, y: int, **_) -> dict:
    _run(["xdotool", "mousemove", str(int(x)), str(int(y))]); return {"via": "xdotool", "x": x, "y": y}


@backend("move", "pynput", priority=40, needs_mod=("pynput",))
def _move_pynput(x: int, y: int, **_) -> dict:
    from pynput.mouse import Controller
    Controller().position = (int(x), int(y)); return {"via": "pynput", "x": x, "y": y}


# ---- key / hotkey ----
@backend("key", "ydotool", priority=80, platforms=("linux-wayland",), needs_bin=("ydotool", "ydotoold"))
def _key_ydotool(keys: str, **_) -> dict:
    seq = _yd_keyseq(keys)
    if not seq:
        raise BackendError(f"unknown key combo {keys!r}")
    _run(["ydotool", "key", *seq], env=_yd_env()); return {"via": "ydotool", "keys": keys}


@backend("key", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _key_xdotool(keys: str, **_) -> dict:
    _run(["xdotool", "key", keys.replace("+", "+")]); return {"via": "xdotool", "keys": keys}


@backend("key", "pynput", priority=40, needs_mod=("pynput",))
def _key_pynput(keys: str, **_) -> dict:
    from pynput.keyboard import Controller, Key
    kb = Controller()
    parts = keys.replace("-", "+").split("+")
    mods = [getattr(Key, p, None) for p in parts[:-1]]
    last = parts[-1]
    for m in mods:
        if m:
            kb.press(m)
    kb.press(last); kb.release(last)
    for m in reversed(mods):
        if m:
            kb.release(m)
    return {"via": "pynput", "keys": keys}


# ---- scroll ----
@backend("scroll", "ydotool", priority=80, platforms=("linux-wayland",), needs_bin=("ydotool", "ydotoold"))
def _scroll_ydotool(dy: int = -3, **_) -> dict:
    _run(["ydotool", "mousemove", "-w", "-x", "0", "-y", str(int(dy))], env=_yd_env()); return {"via": "ydotool", "dy": dy}


@backend("scroll", "pynput", priority=40, needs_mod=("pynput",))
def _scroll_pynput(dy: int = -3, **_) -> dict:
    from pynput.mouse import Controller
    Controller().scroll(0, int(dy)); return {"via": "pynput", "dy": dy}


# --------------------------------------------------------------------------- #
# WINDOW focus / list
# --------------------------------------------------------------------------- #
@backend("focus", "wmctrl", priority=70, platforms=("linux-x11", "linux-wayland"), needs_bin=("wmctrl",))
def _focus_wmctrl(title: str, **_) -> dict:
    _run(["wmctrl", "-a", title]); return {"via": "wmctrl", "title": title}


@backend("focus", "pygetwindow", priority=40, platforms=("windows", "macos"), needs_mod=("pygetwindow",))
def _focus_pgw(title: str, **_) -> dict:
    import pygetwindow as gw
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        raise BackendError(f"no window matching {title!r}")
    wins[0].activate(); return {"via": "pygetwindow", "title": title}


@backend("window_list", "wmctrl", priority=70, platforms=("linux-x11", "linux-wayland"), needs_bin=("wmctrl",))
def _winlist_wmctrl(**_) -> dict:
    p = _run(["wmctrl", "-l"])
    wins = [" ".join(line.split()[3:]) for line in p.stdout.splitlines() if line.strip()]
    return {"via": "wmctrl", "windows": wins}
