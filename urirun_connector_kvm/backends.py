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

import glob
import importlib
import importlib.util
import os
import shlex
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
    # find_spec, not import_module: checking availability must not *execute* a heavy
    # module (e.g. importing easyocr pulls in torch). The actual import happens lazily
    # inside the backend fn, wrapped by dispatch's try/except.
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
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


@backend("capture", "portal", priority=95, platforms=("linux-wayland", "linux-x11"))
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
    import mss.tools as _mss_tools  # `import mss` alone does not expose mss.tools
    with _mss.mss() as sct:
        mons = sct.monitors
        mon = mons[monitor if 0 <= monitor < len(mons) else 0]
        img = sct.grab(mon)
        _mss_tools.to_png(img.rgb, img.size, output=output)
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
@backend("type", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
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
@backend("click", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
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
@backend("move", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
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
@backend("key", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
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
@backend("scroll", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
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


# --------------------------------------------------------------------------- #
# APP LAUNCH / LIST — resolve apps the way the system app search does, not which()
# Linux: XDG .desktop entries (covers Flatpak/Snap/PATH); macOS: open/-a; Windows: startfile
# --------------------------------------------------------------------------- #
def _xdg_app_dirs() -> list[str]:
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    candidates = [os.path.join(data_home, "applications")]
    candidates += [os.path.join(d, "applications") for d in data_dirs.split(":") if d]
    candidates += [
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
        "/var/lib/snapd/desktop/applications",
    ]
    seen, out = set(), []
    for d in candidates:
        if d not in seen and os.path.isdir(d):
            seen.add(d)
            out.append(d)
    return out


def _parse_desktop(path: str):
    name = exec_line = ""
    nodisplay = False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            in_main = False
            for raw in fh:
                line = raw.rstrip("\n")
                if line.startswith("["):
                    in_main = line.strip() == "[Desktop Entry]"
                    continue
                if not in_main or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k == "Name" and not name:
                    name = v
                elif k == "Exec" and not exec_line:
                    exec_line = v
                elif k == "NoDisplay" and v.strip().lower() == "true":
                    nodisplay = True
    except OSError:
        return None
    if not exec_line:
        return None
    base = os.path.basename(path)
    app_id = base[:-len(".desktop")] if base.endswith(".desktop") else base
    return {"id": app_id, "name": name or app_id, "exec": exec_line, "nodisplay": nodisplay}


def _desktop_entries() -> list[dict]:
    seen: dict[str, dict] = {}
    for d in _xdg_app_dirs():
        for path in sorted(glob.glob(os.path.join(d, "*.desktop"))):
            e = _parse_desktop(path)
            if e and e["id"] not in seen:   # first-wins == XDG precedence
                seen[e["id"]] = e
    return list(seen.values())


def _strip_field_codes(exec_line: str) -> list[str]:
    try:
        parts = shlex.split(exec_line)
    except ValueError:
        parts = exec_line.split()
    out = []
    for p in parts:
        if len(p) == 2 and p[0] == "%":     # %f %u %F %U %i %c %k ...
            continue
        if p.startswith("@@"):               # flatpak arg wrappers
            continue
        out.append(p)
    return out


def _find_app(query: str):
    q = (query or "").strip().lower()
    entries = _desktop_entries()
    for e in entries:                        # exact id
        if e["id"].lower() == q:
            return e
    for e in entries:                        # id / name contains
        if q and (q in e["id"].lower() or q in e["name"].lower()):
            return e
    return None


@backend("launch", "xdg", priority=80, platforms=("linux-wayland", "linux-x11"))
def _launch_xdg(app: str = "", compose: str = "", args: list | None = None, settle: float = 0, **_) -> dict:
    extra = list(args or [])
    if compose:
        extra += ["-compose", compose]
    entry = _find_app(app)
    if entry:
        argv = _strip_field_codes(entry["exec"]) + extra
        resolved = {"id": entry["id"], "name": entry["name"], "how": "desktop-entry"}
    elif shutil.which(app):
        argv = [app, *extra]
        resolved = {"id": app, "name": app, "how": "path"}
    else:
        raise BackendError(f"no .desktop entry or PATH binary matches {app!r} "
                           "(call window/query/list or doctor for what's installed)")
    env = os.environ.copy()
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    p = subprocess.Popen(argv, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    settled = max(0.0, min(float(settle or 0), 30.0))
    if settled:
        time.sleep(settled)
    return {"via": "xdg", "app": resolved, "pid": p.pid, "argv": argv,
            "compose": bool(compose), "settled": settled}


@backend("launch", "macos", priority=70, platforms=("macos",), needs_bin=("open",))
def _launch_macos(app: str = "", args: list | None = None, settle: float = 0, **_) -> dict:
    argv = ["open", "-a", app] + (["--args", *map(str, args or [])] if args else [])
    _run(argv)
    settled = max(0.0, min(float(settle or 0), 30.0))
    if settled:
        time.sleep(settled)
    return {"via": "open", "app": {"id": app, "name": app, "how": "open"}, "settled": settled}


@backend("launch", "windows", priority=70, platforms=("windows",))
def _launch_windows(app: str = "", args: list | None = None, settle: float = 0, **_) -> dict:
    try:
        os.startfile(app)  # type: ignore[attr-defined]
    except OSError:
        _run(["cmd", "/c", "start", "", app, *map(str, args or [])])
    settled = max(0.0, min(float(settle or 0), 30.0))
    if settled:
        time.sleep(settled)
    return {"via": "startfile", "app": {"id": app, "name": app, "how": "startfile"}, "settled": settled}


@backend("launch_list", "xdg", priority=80, platforms=("linux-wayland", "linux-x11"))
def _list_xdg(filter: str = "", **_) -> dict:  # noqa: A002 - matches route field name
    q = (filter or "").lower()
    out = []
    for e in _desktop_entries():
        if e.get("nodisplay"):
            continue
        if q and q not in e["id"].lower() and q not in e["name"].lower():
            continue
        out.append({"id": e["id"], "name": e["name"]})
    out.sort(key=lambda x: x["name"].lower())
    return {"via": "xdg", "count": len(out), "apps": out}


@backend("launch_list", "macos", priority=70, platforms=("macos",))
def _list_macos(filter: str = "", **_) -> dict:  # noqa: A002
    q = (filter or "").lower()
    out = []
    for entry in sorted(glob.glob("/Applications/*.app")):
        app_id = os.path.basename(entry)[:-len(".app")]
        if q and q not in app_id.lower():
            continue
        out.append({"id": app_id, "name": app_id})
    return {"via": "open", "count": len(out), "apps": out}


# --------------------------------------------------------------------------- #
# AT-SPI focus — activate a window by accessible name through the accessibility
# bus. Works on native-Wayland (where wmctrl only sees Xwayland windows). Runs via
# a system python that has gi + the Atspi typelib (the node venv usually doesn't),
# mirroring the portal-capture pattern.
# --------------------------------------------------------------------------- #
def _atspi_python() -> str | None:
    probe = "import gi; gi.require_version('Atspi','2.0'); from gi.repository import Atspi"
    for c in (os.environ.get("URISYS_ATSPI_PYTHON"), os.environ.get("URISYS_PORTAL_PYTHON"),
              "/usr/bin/python3", shutil.which("python3"), sys.executable):
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", probe], capture_output=True, timeout=6).returncode == 0:
                return c
        except Exception:  # noqa: BLE001
            continue
    return None


_ATSPI_FOCUS_SCRIPT = r"""
import sys, json
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
needle = sys.argv[1].lower()
Atspi.init()
hit = None
desktop = Atspi.get_desktop(0)
for i in range(desktop.get_child_count()):
    app = desktop.get_child_at_index(i)
    if app is None:
        continue
    name = (app.get_name() or "")
    for j in range(app.get_child_count()):
        frame = app.get_child_at_index(j)
        if frame is None:
            continue
        fname = (frame.get_name() or "")
        if needle in fname.lower() or needle in name.lower():
            try:
                comp = frame.get_component_iface()
                if comp is not None:
                    comp.grab_focus()
                    hit = {"app": name, "frame": fname}
                    break
            except Exception as exc:  # noqa: BLE001
                hit = {"app": name, "frame": fname, "warn": str(exc)[:80]}
    if hit:
        break
print(json.dumps(hit or {}))
"""


@backend("focus", "atspi", priority=85, platforms=("linux-wayland", "linux-x11"))
def _focus_atspi(title: str, **_) -> dict:
    py = _atspi_python()
    if not py:
        raise BackendError("AT-SPI focus needs python3 with gi + Atspi (install python3-gobject + gnome a11y)")
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    p = _run([py, "-c", _ATSPI_FOCUS_SCRIPT, title], env=env, timeout=12)
    import json as _json
    hit = _json.loads((p.stdout or "{}").strip() or "{}")
    if not hit:
        raise BackendError(f"no accessible window matching {title!r}")
    return {"via": "atspi", "title": title, "matched": hit}


# --------------------------------------------------------------------------- #
# AT-SPI element interaction — find a UI element by (app, role, name) anywhere in
# the accessibility tree and act on it: focus, click (via its Action interface),
# or set text (EditableText). Resolution-independent — no coordinates. Web content
# needs the app's a11y enabled (e.g. Chrome: chrome://accessibility or
# --force-renderer-accessibility). Returns the element's screen bbox so a caller
# can fall back to a kvm click when no Action interface is exposed.
# --------------------------------------------------------------------------- #
_ATSPI_ACT_SCRIPT = r"""
import sys, json
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
Atspi.init()
cmd = json.loads(sys.argv[1])
app_q = cmd.get("app", "").lower()
role_q = cmd.get("role", "").lower()
name_q = cmd.get("name", "").lower()
action = cmd.get("op", "focus")
text = cmd.get("text", "")
nth = int(cmd.get("nth", 0))
budget = [int(cmd.get("limit", 6000))]
matches = []

def walk(node):
    if node is None or budget[0] <= 0:
        return
    budget[0] -= 1
    try:
        role = node.get_role_name() or ""
        name = node.get_name() or ""
    except Exception:
        return
    if (not role_q or role_q in role.lower()) and (not name_q or name_q in name.lower()):
        if role_q or name_q:
            matches.append(node)
    try:
        n = node.get_child_count()
    except Exception:
        n = 0
    for i in range(min(n, 200)):
        try:
            walk(node.get_child_at_index(i))
        except Exception:
            continue

d = Atspi.get_desktop(0)
for i in range(d.get_child_count()):
    app = d.get_child_at_index(i)
    if app is None:
        continue
    if app_q and app_q not in (app.get_name() or "").lower():
        continue
    walk(app)

if not matches:
    print(json.dumps({"found": False, "candidates": 0})); sys.exit(0)
target = matches[min(nth, len(matches) - 1)]
info = {"found": True, "candidates": len(matches),
        "role": target.get_role_name(), "name": (target.get_name() or "")[:80]}
try:
    comp = target.get_component_iface()
    if comp:
        ext = comp.get_extents(Atspi.CoordType.SCREEN)
        info["bbox"] = [ext.x, ext.y, ext.width, ext.height]
    if action == "focus" and comp:
        info["focused"] = bool(comp.grab_focus())
    elif action == "click":
        ai = target.get_action_iface()
        if ai and ai.get_n_actions() > 0:
            ai.do_action(0); info["clicked"] = True
        elif comp:
            comp.grab_focus(); info["focused_only"] = True
    elif action == "settext":
        et = target.get_editable_text_iface()
        if et:
            et.set_text_contents(text); info["set"] = True
        elif comp:
            comp.grab_focus(); info["focused_for_type"] = True
    elif action == "gettext":
        ti = target.get_text_iface()
        if ti:
            info["text"] = ti.get_text(0, ti.get_character_count())[-4000:]
        else:
            info["text"] = target.get_name() or ""
except Exception as exc:  # noqa: BLE001
    info["warn"] = str(exc)[:120]
print(json.dumps(info))
"""


@backend("a11y", "atspi", priority=90, platforms=("linux-wayland", "linux-x11"))
def _a11y_atspi(app: str = "", role: str = "", name: str = "", op: str = "focus",
                text: str = "", nth: int = 0, **_) -> dict:
    py = _atspi_python()
    if not py:
        raise BackendError("AT-SPI needs python3 with gi + Atspi (install python3-gobject + gnome a11y)")
    import json as _json
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    cmd = _json.dumps({"app": app, "role": role, "name": name, "op": op, "text": text, "nth": nth})
    p = _run([py, "-c", _ATSPI_ACT_SCRIPT, cmd], env=env, timeout=15)
    res = _json.loads((p.stdout or "{}").strip() or "{}")
    res["via"] = "atspi"
    return res


# --------------------------------------------------------------------------- #
# LOCATE — find on-screen text and return its pixel coordinates (boxes + center)
# The "where is the button?" half of the screenshot→locate→click pipeline. Pixel
# coordinates here map 1:1 to the captured image, so capture at native resolution.
# --------------------------------------------------------------------------- #
def _tsv_lines(tsv: str, min_conf: float) -> list[dict]:
    """Aggregate tesseract word rows (level 5) into line boxes so a multi-word label
    like 'Start a post' is one match, not three."""
    groups: dict[tuple, dict] = {}
    for raw in tsv.splitlines()[1:]:           # skip header row
        c = raw.split("\t")
        if len(c) < 12 or c[0] != "5":         # level 5 == word
            continue
        try:
            left, top, w, h, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
        except ValueError:
            continue
        word = c[11].strip()
        if not word:
            continue
        key = (c[1], c[2], c[3], c[4])         # page, block, par, line
        g = groups.setdefault(key, {"words": [], "confs": [],
                                    "x0": 1 << 30, "y0": 1 << 30, "x1": 0, "y1": 0})
        g["words"].append(word)
        g["confs"].append(conf)
        g["x0"], g["y0"] = min(g["x0"], left), min(g["y0"], top)
        g["x1"], g["y1"] = max(g["x1"], left + w), max(g["y1"], top + h)
    out = []
    for g in groups.values():
        conf = sum(g["confs"]) / len(g["confs"])
        if conf < min_conf:
            continue
        x0, y0, x1, y1 = int(g["x0"]), int(g["y0"]), int(g["x1"]), int(g["y1"])
        out.append({"text": " ".join(g["words"]), "conf": round(conf, 1),
                    "box": [x0, y0, x1 - x0, y1 - y0], "center": [(x0 + x1) // 2, (y0 + y1) // 2]})
    return out


@backend("locate", "tesseract", priority=65, needs_bin=("tesseract",))
def _locate_tesseract(image: str = "", query: str = "", text: str = "", role: str = "",
                      min_conf: float = 40, **_) -> dict:
    """OCR-locate on-screen text. Unlike a saliency detector this GENUINELY matches the
    query against recognised text, so it is preferred (priority 65 > imgl 60) for text
    targets. Returns the unified ``found``/``bbox``/``center`` schema AND the full
    ``matches`` list; ``found: false`` (honestly) when the text is not on screen — never
    a bogus hit. Captures its own screenshot when no ``image`` is supplied."""
    q = (query or text or "").strip()
    full = None
    if not image or not os.path.exists(image):
        cap = _capture_tmp()           # find/click handlers call us without an image
        image, full = cap["path"], cap.get("fullSize")
    p = _run(["tesseract", image, "stdout", "tsv"], timeout=60)
    ql = q.lower()
    if not ql:
        matches = sorted(_tsv_lines(p.stdout, float(min_conf)), key=lambda m: -m["conf"])
    else:
        # Word-level so a click lands ON the matched word(s), not the whole nav line.
        words: dict[tuple, list] = {}
        for raw in p.stdout.splitlines()[1:]:
            c = raw.split("\t")
            if len(c) < 12 or c[0] != "5":
                continue
            try:
                left, top, w, h, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
            except ValueError:
                continue
            t = c[11].strip()
            if t and conf >= float(min_conf):
                words.setdefault((c[1], c[2], c[3], c[4]), []).append(
                    {"text": t, "conf": conf, "box": [left, top, w, h]})
        terms = ql.split()
        matches = []
        for ws in words.values():
            if ql not in " ".join(x["text"] for x in ws).lower():
                continue
            sel = [x for x in ws if any(term in x["text"].lower() for term in terms)] or ws
            x0 = min(x["box"][0] for x in sel); y0 = min(x["box"][1] for x in sel)
            x1 = max(x["box"][0] + x["box"][2] for x in sel)
            y1 = max(x["box"][1] + x["box"][3] for x in sel)
            matches.append({"text": " ".join(x["text"] for x in sel),
                            "conf": round(sum(x["conf"] for x in sel) / len(sel), 1),
                            "box": [x0, y0, x1 - x0, y1 - y0], "center": [(x0 + x1) // 2, (y0 + y1) // 2]})
        matches.sort(key=lambda m: -m["conf"])
    out = {"via": "tesseract", "source": "tesseract", "coord_space": "image-px",
           "query": q, "count": len(matches), "matches": matches, "fullSize": full}
    if matches:
        best = matches[0]
        out.update({"found": True, "bbox": best["box"], "center": best["center"],
                    "text": best["text"], "candidates": len(matches), "actionable": False})
    else:
        out["found"] = False           # honest miss — do NOT fall through to a guesser
    return out


_EASYOCR_READER = None


def _easyocr_reader():
    """Cache the EasyOCR reader (model load is ~5-10s the first time). Languages from
    URIRUN_KVM_OCR_LANGS (default 'en'); CPU mode for portability."""
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import easyocr
        langs = [x.strip() for x in os.environ.get("URIRUN_KVM_OCR_LANGS", "en").split(",") if x.strip()]
        _EASYOCR_READER = easyocr.Reader(langs or ["en"], gpu=False)
    return _EASYOCR_READER


@backend("locate", "easyocr", priority=70, needs_mod=("easyocr",))
def _locate_easyocr(image: str = "", query: str = "", text: str = "", role: str = "",
                    min_conf: float = 40, **_) -> dict:
    """OCR-locate via EasyOCR (CRAFT detector + CRNN) — stronger than tesseract on UI
    fonts, low contrast, and non-Latin scripts, with no a11y permissions. Returns the
    same unified ``found``/``bbox``/``center`` + ``matches`` schema; genuine text match,
    honest ``found: false``. NOTE: finds TEXT, not icons — icon targets need the
    computer-use/vision path. Heavy import (torch); the reader is process-cached, but
    isolated route calls reload it per call — for hot loops run locate non-isolated."""
    q = (query or text or "").strip()
    full = None
    if not image or not os.path.exists(image):
        cap = _capture_tmp()
        image, full = cap["path"], cap.get("fullSize")
    reader = _easyocr_reader()
    thr = float(min_conf) / 100.0      # our min_conf is 0-100; EasyOCR confidence is 0-1
    matches = []
    for quad, t, conf in reader.readtext(image):
        if conf < thr or not str(t).strip():
            continue
        xs = [int(p[0]) for p in quad]
        ys = [int(p[1]) for p in quad]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        matches.append({"text": str(t), "conf": round(float(conf) * 100, 1),
                        "box": [x0, y0, x1 - x0, y1 - y0], "center": [(x0 + x1) // 2, (y0 + y1) // 2]})
    ql = q.lower()
    if ql:
        matches = [m for m in matches if ql in m["text"].lower()]
    matches.sort(key=lambda m: -m["conf"])
    out = {"via": "easyocr", "source": "easyocr", "coord_space": "image-px",
           "query": q, "count": len(matches), "matches": matches, "fullSize": full}
    if matches:
        best = matches[0]
        out.update({"found": True, "bbox": best["box"], "center": best["center"],
                    "text": best["text"], "candidates": len(matches), "actionable": False})
    else:
        out["found"] = False
    return out


# --------------------------------------------------------------------------- #
# LOCATE — find a target element and return a normalized hit:
#   {found, bbox:[x,y,w,h], source, coord_space, role?, name?, actionable}
# Backends (decorator fallback): AT-SPI (screen-space bbox, can act directly) →
# imgl vision (OCR/layout) → vql. The `ui/*` routes build perceive→act→verify on
# top of this. `coord_space` is "screen" (compositor coords, click 1:1) for AT-SPI
# and "image-px" (screenshot pixels; HiDPI may need scaling) for vision backends.
# --------------------------------------------------------------------------- #
def bbox_center(bbox) -> tuple:
    x, y, w, h = bbox
    return int(x + w / 2), int(y + h / 2)


@backend("locate", "atspi", priority=90, platforms=("linux-wayland", "linux-x11"))
def _locate_atspi(text: str = "", role: str = "", app: str = "", nth: int = 0, **_) -> dict:
    res = _a11y_atspi(app=app, role=role, name=text, op="find", nth=int(nth))
    if not res.get("found") or not res.get("bbox"):
        raise BackendError(f"atspi: no element role~{role!r} name~{text!r}")
    x, y, w, h = res["bbox"]   # reject off-screen / collapsed elements (a11y tree noise)
    if x < 0 or y < 0 or w < 2 or h < 2 or x > 100000 or y > 100000:
        raise BackendError(f"atspi: element name~{text!r} has no on-screen bbox {res['bbox']}")
    return {"found": True, "bbox": res["bbox"], "source": "atspi", "coord_space": "screen",
            "role": res.get("role"), "name": res.get("name"), "actionable": True,
            "candidates": res.get("candidates")}


def _capture_tmp() -> dict:
    import tempfile
    shot = os.path.join(tempfile.gettempdir(), "urirun-kvm-locate.png")
    res = dispatch("capture", output=shot, monitor=0)
    res["path"] = shot
    return res


@backend("locate", "imgl", priority=60, needs_mod=("imgl",))
def _locate_imgl(text: str = "", role: str = "", **_) -> dict:
    """Vision locate: screenshot → imgl find by text → bbox (image-px). Cross-platform;
    on HiDPI the caller should scale image-px → logical coords (see fullSize)."""
    import json as _json
    cap = _capture_tmp()
    args = [sys.executable, "-m", "imgl.cli", "find", cap["path"], "--list"]
    if text:
        args += ["--text", text]
    if role:
        args += ["--type", role]
    p = _run(args, timeout=40)
    hits = _json.loads(p.stdout or "[]")
    if not hits:
        raise BackendError(f"imgl: no element matching text~{text!r} role~{role!r}")
    h = hits[0]
    bb = h.get("bbox") or {}
    return {"found": True, "bbox": [bb.get("x", h["x"]), bb.get("y", h["y"]), bb.get("w", 0), bb.get("h", 0)],
            "source": "imgl", "coord_space": "image-px", "text": h.get("text"),
            "fullSize": cap.get("fullSize"), "actionable": False, "candidates": len(hits)}


@backend("locate", "vql", priority=50, needs_mod=("vql",))
def _locate_vql(text: str = "", role: str = "", **_) -> dict:
    import json as _json
    cap = _capture_tmp()
    p = _run([sys.executable, "-m", "imgl.cli", "vql", cap["path"]], timeout=40)
    doc = _json.loads(p.stdout or "{}")
    needle = (text or role).lower()
    for layer in (doc.get("scene", {}).get("layers") or []):
        for obj in layer.get("objects", []):
            label = " ".join(str(v) for v in (obj.get("text"), obj.get("label")) if v).lower()
            if needle and needle in label and obj.get("bbox"):
                b = obj["bbox"]
                return {"found": True, "bbox": [b.get("x"), b.get("y"), b.get("w"), b.get("h")],
                        "source": "vql", "coord_space": "image-px", "text": obj.get("text"),
                        "fullSize": cap.get("fullSize"), "actionable": False}
    raise BackendError(f"vql: no object matching {needle!r}")


# --------------------------------------------------------------------------- #
# Pixel-accurate pointer via a raw uinput ABSOLUTE device (tablet-style). Absolute
# devices bypass pointer acceleration and map [0,65535] linearly onto the desktop, so a
# click at fraction (x/sw, y/sh) of a screenshot lands at that pixel — no ydotool, no
# calibration. stdlib only; needs r/w on /dev/uinput. Linux-only.
# --------------------------------------------------------------------------- #
import fcntl as _fcntl  # noqa: E402
import struct as _struct  # noqa: E402

_UI = ord("U")
def _ui_io(nr):       return (0 << 30) | (_UI << 8) | nr
def _ui_iow(nr, sz):  return (1 << 30) | (sz << 16) | (_UI << 8) | nr
_UI_DEV_CREATE, _UI_DEV_DESTROY = _ui_io(1), _ui_io(2)
_UI_SET_EVBIT, _UI_SET_KEYBIT, _UI_SET_ABSBIT = _ui_iow(100, 4), _ui_iow(101, 4), _ui_iow(103, 4)
_EV_SYN, _EV_KEY, _EV_ABS = 0, 1, 3
_ABS_X, _ABS_Y = 0, 1
_BTN_CODE = {"left": 0x110, "right": 0x111, "middle": 0x112}
_BTN_TOUCH = 0x14A
_ABS_RANGE = 65535


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


def uinput_abs_click(x: int, y: int, sw: int, sh: int, button: str = "left",
                     do_click: bool = True, settle: float = 0.9) -> dict:
    if not uinput_available():
        raise BackendError("no write access to /dev/uinput (add user to 'input' group or udev rule)")
    ax = max(0, min(_ABS_RANGE, int(x / sw * _ABS_RANGE) if sw else int(x)))
    ay = max(0, min(_ABS_RANGE, int(y / sh * _ABS_RANGE) if sh else int(y)))

    def ev(fd, t, c, v):
        os.write(fd, _struct.pack("llHHi", 0, 0, t, c, v))
    fd = _uinput_create_abs()
    try:
        time.sleep(float(settle))  # compositor discovers + maps the new device
        ev(fd, _EV_ABS, _ABS_X, ax); ev(fd, _EV_ABS, _ABS_Y, ay); ev(fd, _EV_SYN, 0, 0)
        time.sleep(0.25)
        if do_click:
            bc = _BTN_CODE.get(button, 0x110)
            ev(fd, _EV_KEY, bc, 1); ev(fd, _EV_KEY, _BTN_TOUCH, 1); ev(fd, _EV_SYN, 0, 0)
            time.sleep(0.08)
            ev(fd, _EV_KEY, bc, 0); ev(fd, _EV_KEY, _BTN_TOUCH, 0); ev(fd, _EV_SYN, 0, 0)
        time.sleep(0.2)
        return {"via": "uinput-absolute", "abs": [ax, ay], "pixel": [x, y], "clicked": bool(do_click)}
    finally:
        try:
            _fcntl.ioctl(fd, _UI_DEV_DESTROY)
        except Exception:  # noqa: BLE001
            pass
        os.close(fd)


# --------------------------------------------------------------------------- #
# Surface awareness — honest self-diagnosis of WHETHER OS-level pixel input will
# actually work on this session, not just which tool is installed. Encodes the
# lesson from three debugging sessions: live GNOME/Wayland multi-monitor +
# fractional HiDPI breaks the screenshot<->input coordinate correspondence.
# --------------------------------------------------------------------------- #
def _gnome_monitors() -> list[dict]:
    """Best-effort logical-monitor geometry via Mutter DisplayConfig (gdbus); [] if absent."""
    if not have_bin("gdbus"):
        return []
    try:
        out = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.DisplayConfig",
             "--object-path", "/org/gnome/Mutter/DisplayConfig",
             "--method", "org.gnome.Mutter.DisplayConfig.GetCurrentState"],
            capture_output=True, text=True, timeout=8).stdout
    except Exception:  # noqa: BLE001
        return []
    import re
    mons = []
    for m in re.finditer(r"\((\d+),\s*(\d+),\s*([\d.]+),\s*uint32\s*\d+,\s*(true|false)", out):
        x, y, scale, prim = m.groups()
        mons.append({"x": int(x), "y": int(y), "scale": round(float(scale), 3), "primary": prim == "true"})
    return mons


def surface_report() -> dict:
    """Which execution surface to trust here, and why. Surfaces:
    os-level (this connector's raw input), browser-cdp (Playwright/CDP), remotedesktop-portal,
    vdisplay. On Wayland multi-monitor/fractional-HiDPI, os-level pixel input is unreliable."""
    plat = platform_tag()
    mons = _gnome_monitors() if plat == "linux-wayland" else []
    multi = len(mons) > 1
    fractional = any(m["scale"] not in (0, 1.0) for m in mons)
    confirmed_simple = bool(mons) and not multi and not fractional  # POSITIVELY single + integer scale
    warnings = []
    if plat == "linux-wayland":
        if multi or fractional or not mons:
            why = ("multi-monitor" if multi else "") + ("/fractional-HiDPI" if fractional else "")
            why = why or "layout unconfirmed (couldn't read Mutter geometry)"
            warnings.append(
                f"OS-level pixel input (move/click/abs/task) is UNRELIABLE here: Wayland + {why} — "
                "screenshot pixels do not map to a fixed input coordinate and focus cannot be stolen. "
                "Use a browser surface (CDP/Playwright) for web, or the RemoteDesktop portal / a "
                "virtual display for native apps. capture (portal) is fine.")
        else:
            warnings.append(
                "Wayland single-monitor, integer scale: pixel input maps ~1:1 — usable, but keys "
                "still reach only the ACTIVE window (no focus-stealing).")
    os_reliable = (plat != "linux-wayland") or confirmed_simple  # conservative: unconfirmed Wayland = unreliable
    recommended = (["browser-cdp", "remotedesktop-portal", "vdisplay"]
                   if (plat == "linux-wayland") else ["os-level", "browser-cdp"])
    return {"platform": plat, "wayland": is_wayland(), "monitors": mons,
            "multiMonitor": multi, "fractionalHiDPI": fractional,
            "osLevelReliable": os_reliable,
            "recommendedSurfaces": recommended, "warnings": warnings}
