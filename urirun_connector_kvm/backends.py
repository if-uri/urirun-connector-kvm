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

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from urirun.connectors.backend_registry import BackendError, have_bin, have_mod  # noqa: F401


# --------------------------------------------------------------------------- #
# platform / session detection
# --------------------------------------------------------------------------- #
def _runtime_dir() -> str:
    return os.environ.get("XDG_RUNTIME_DIR") or (f"/run/user/{os.getuid()}" if hasattr(os, "getuid") else "")


def _wayland_socket() -> str | None:
    """Name of a live ``wayland-*`` socket under the runtime dir, if any."""
    xrd = _runtime_dir()
    if not xrd:
        return None
    try:
        socks = sorted(n for n in os.listdir(xrd)
                       if n.startswith("wayland-") and not n.endswith(".lock"))
    except OSError:
        return None
    return socks[0] if socks else None


def _x_display() -> str | None:
    """First X display socket under ``/tmp/.X11-unix``, as a ``:N`` display string."""
    try:
        socks = sorted(n for n in os.listdir("/tmp/.X11-unix") if n.startswith("X") and n[1:].isdigit())
    except OSError:
        return None
    return f":{socks[0][1:]}" if socks else None


def is_wayland() -> bool:
    if bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return True
    # A node process is usually spawned without the graphical session's env, so the
    # vars above are empty even on a live Wayland seat — which mis-tags the box as
    # linux-x11 and drops grim/portal from the capture candidates. Probe the
    # compositor socket under the runtime dir as ground truth (same discovery the
    # input/capture paths already use via session_env()).
    return _wayland_socket() is not None


def is_x11() -> bool:
    return (bool(os.environ.get("DISPLAY")) or _x_display() is not None) and not is_wayland()


def platform_tag() -> str:
    if sys.platform.startswith("linux"):
        return "linux-wayland" if is_wayland() else "linux-x11"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith(("win", "cygwin")):
        return "windows"
    return "linux-x11"


ALL_PLATFORMS = ("linux-wayland", "linux-x11", "windows", "macos")

_TESSERACT_TSV_COLS = 12    # number of tab-separated columns in tesseract TSV output
_TESSERACT_WORD_LEVEL = "5" # level=5 means word in tesseract's page-hierarchy
_MIN_QUERY_TERM_LEN = 3     # ignore 1-2 char tokens in multi-word query expansion
_MAX_SCREEN_COORD = 100_000 # sanity bound: reject AT-SPI bboxes outside plausible screen area


# --------------------------------------------------------------------------- #
# registry + @backend decorator — have_bin / have_mod / BackendError re-exported
# from urirun.connectors.backend_registry (generic kernel); Backend / @backend /
# dispatch stay kvm-local so test patches on B.have_mod / B.platform_tag reach
# the right lookup in kvm's module globals.
# --------------------------------------------------------------------------- #
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


def dispatch(action: str, **kwargs: Any) -> dict:
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


def _run(argv: list[str], *, env: dict | None = None, timeout: float = 30) -> subprocess.CompletedProcess:
    # Default to the discovered session env so display-dependent tools (grim, scrot,
    # gnome-screenshot, wtype, xdotool…) can reach the compositor/X server even when the
    # node process was spawned without graphical session vars. Callers that pass an
    # explicit env (ydotool's _yd_env) keep full control.
    p = subprocess.run(argv, capture_output=True, text=True,
                       env=session_env() if env is None else env, timeout=timeout)
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
_CODES = {1: "portal cancelled (code 1)",
          2: "portal denied (code 2) — capture needs a one-time screenshot permission grant "
             "for this app (accept the portal dialog once, or grant it in the desktop's "
             "Privacy/Screenshot settings); on locked-down GNOME the shell may block it entirely"}
def _r(resp, res):
    state["error"] = (_CODES.get(int(resp), f"portal code {resp}") if int(resp)
                      else (None if "uri" in res else "missing uri"))
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


_MIN_REAL_PORTAL_BYTES = 20_000  # real screenshots are hundreds of KB; ~3.8 KB = empty/denied placeholder


@backend("capture", "portal", priority=95, platforms=("linux-wayland", "linux-x11"))
def _cap_portal(output: str, **_: Any) -> dict:
    """XDG Desktop Portal screenshot — the only sanctioned live capture on GNOME/KDE
    Wayland. Runs via a system python with dbus+gi; needs a one-time permission grant."""
    py = _portal_python()
    if not py:
        raise BackendError("portal needs python3 with dbus+gi (install python3-gobject python3-dbus)")
    import urllib.parse
    from pathlib import Path
    # Needs the session D-Bus address + XDG_RUNTIME_DIR to reach the portal; session_env()
    # fills both in from the runtime dir when the node process was started without them.
    p = _run([py, "-c", _PORTAL_SCRIPT], env=session_env(), timeout=20)
    src = Path(urllib.parse.urlparse(p.stdout.strip()).path)
    data = src.read_bytes()
    if len(data) < _MIN_REAL_PORTAL_BYTES:
        # The portal accepted the call but returned a tiny placeholder — this is the
        # GNOME-Wayland "screenshot permission denied / no active session" failure mode.
        # Raise BackendError so dispatch() falls through to the mutter-screencast backend.
        raise BackendError(
            f"xdg-portal returned a {len(data)}-byte placeholder "
            "(portal blocked or screenshot permission not granted — "
            "grant it in GNOME Settings → Privacy → Screen Sharing, "
            "or install gstreamer pipewiresrc for the mutter-screencast backend)"
        )
    Path(output).write_bytes(data)
    return {"path": output, "bytes": len(data), "via": "xdg-portal"}


_MUTTER_SCRIPT = r"""
import sys, json, dbus, dbus.mainloop.glib, gi
gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst
out = sys.argv[1]
selector = sys.argv[2] if len(sys.argv) > 2 else "0"
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
def _logical_monitors():
    dc = dbus.Interface(bus.get_object("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig"),
                        "org.gnome.Mutter.DisplayConfig")
    _s, physical, logical, _p = dc.GetCurrentState()
    modes = {}
    names = {}
    for mon in physical:
        spec, mode_list, props = mon
        conn = str(spec[0])
        names[conn] = str(props.get("display-name") or "")
        for mode in mode_list:
            mprops = mode[6]
            if bool(mprops.get("is-current")):
                modes[conn] = (int(mode[1]), int(mode[2]))
                break
    out = []
    fb = None
    primary_conn = None
    for idx, lm in enumerate(logical):
        x, y, scale = int(lm[0]), int(lm[1]), float(lm[2])
        primary, mons = lm[4], lm[5]
        if mons:
            conn = str(mons[0][0]); fb = fb or conn
            width, height = modes.get(conn, (0, 0))
            logical_width = int(round(width / scale)) if scale and width else 0
            logical_height = int(round(height / scale)) if scale and height else 0
            if primary: primary_conn = conn
            out.append({"index": idx + 1, "connector": conn, "primary": bool(primary),
                        "x": x, "y": y, "scale": scale,
                        "width": width, "height": height,
                        "logicalWidth": logical_width, "logicalHeight": logical_height,
                        "displayName": names.get(conn, "")})
    bbox = None
    rects = [(m["x"], m["y"], m.get("logicalWidth") or 0, m.get("logicalHeight") or 0)
             for m in out if (m.get("logicalWidth") or 0) > 0 and (m.get("logicalHeight") or 0) > 0]
    if rects:
        minx = min(r[0] for r in rects); miny = min(r[1] for r in rects)
        maxx = max(r[0] + r[2] for r in rects); maxy = max(r[1] + r[3] for r in rects)
        bbox = [int(minx), int(miny), int(maxx - minx), int(maxy - miny)]
    return out, primary_conn or fb, bbox
monitors, primary, bbox = _logical_monitors()
record_all = selector in ("all", "-1")
conn = None
if not record_all:
    try:
        num = int(selector)
    except Exception:
        num = 0
    if num > 0 and num <= len(monitors):
        conn = monitors[num - 1]["connector"]
    else:
        conn = primary
    if not conn: print("no active monitor", file=sys.stderr); sys.exit(4)
sc = dbus.Interface(bus.get_object("org.gnome.Mutter.ScreenCast", "/org/gnome/Mutter/ScreenCast"),
                    "org.gnome.Mutter.ScreenCast")
session = dbus.Interface(bus.get_object("org.gnome.Mutter.ScreenCast", sc.CreateSession({})),
                         "org.gnome.Mutter.ScreenCast.Session")
if record_all:
    if bbox:
        stream = session.RecordArea(bbox[0], bbox[1], bbox[2], bbox[3], {"cursor-mode": dbus.UInt32(1)})
    else:
        stream = session.RecordVirtual({"cursor-mode": dbus.UInt32(1)})
else:
    stream = session.RecordMonitor(conn, {"cursor-mode": dbus.UInt32(1)})
state = {}; loop = GLib.MainLoop()
bus.add_signal_receiver(lambda n: (state.__setitem__("node", int(n)), loop.quit()),
                        dbus_interface="org.gnome.Mutter.ScreenCast.Stream",
                        path=stream, signal_name="PipeWireStreamAdded")
session.Start()
GLib.timeout_add_seconds(10, lambda: (loop.quit(), False)[1])
loop.run()
node = state.get("node")
if node is None: session.Stop(); print("no pipewire node (ScreenCast unavailable/restricted)", file=sys.stderr); sys.exit(5)
Gst.init(None)
pipe = Gst.parse_launch("pipewiresrc path=%d num-buffers=1 ! videoconvert ! pngenc snapshot=true ! filesink location=%s" % (node, out))
pipe.set_state(Gst.State.PLAYING)
msg = pipe.get_bus().timed_pop_filtered(10 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
pipe.set_state(Gst.State.NULL); session.Stop()
if msg and msg.type == Gst.MessageType.ERROR:
    e, _d = msg.parse_error(); print("gstreamer: %s" % e, file=sys.stderr); sys.exit(6)
print(json.dumps({"path": out, "scope": "all-monitors" if record_all else "monitor",
                  "connector": conn or "", "monitor": -1 if record_all else int(selector or "0"),
                  "monitors": monitors, "bbox": bbox or []}))
"""


def _mutter_python() -> "str | None":
    """A python that can import dbus+gi+gstreamer (system python, not the node venv)."""
    chk = "import dbus, gi; gi.require_version('Gst','1.0'); from gi.repository import Gst"
    for c in (os.environ.get("URISYS_PORTAL_PYTHON"), "/usr/bin/python3", shutil.which("python3"), sys.executable):
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", chk], capture_output=True, timeout=5).returncode == 0:
                return c
        except Exception:  # noqa: BLE001
                continue
    return None


def _png_dimensions(path: str) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if len(head) >= 24 and head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    return None


@backend("capture", "mutter", priority=98, platforms=("linux-wayland",))
def _cap_mutter(output: str, monitor: int = 0, scope: str = "", **_: Any) -> dict:
    """GNOME Mutter ScreenCast -> PipeWire capture. Headless and consent-free (the path
    gnome-remote-desktop uses), so it works where the screenshot portal denies non-interactive
    use on GNOME-Wayland. Falls through (BackendError) on non-GNOME (no Mutter bus). Runs via a
    system python with dbus+gi+gstreamer (pipewiresrc)."""
    py = _mutter_python()
    if not py:
        raise BackendError("mutter screencast needs python3 with dbus+gi+gstreamer "
                           "(install python3-gobject python3-dbus gstreamer1.0-plugins-* incl. pipewiresrc)")
    from pathlib import Path
    selector = "all" if str(scope or "").strip().lower() in {"all", "all-monitors", "desktop"} or monitor < 0 else str(monitor)
    proc = _run([py, "-c", _MUTTER_SCRIPT, output, selector], env=session_env(), timeout=30)
    data = Path(output).read_bytes()
    dims = _png_dimensions(output)
    if selector == "all" and dims == (1, 1):
        raise BackendError("mutter RecordVirtual returned a 1x1 placeholder for all monitors")
    try:
        meta = json.loads(proc.stdout.strip() or "{}")
    except Exception:
        meta = {}
    return {"path": output, "bytes": len(data), "via": "mutter-screencast",
            **({"width": dims[0], "height": dims[1]} if dims else {}),
            **{k: v for k, v in meta.items() if k not in {"path"}}}



def _is_wlroots_compositor() -> bool:
    """True only on compositors that support wlr-screencopy-unstable-v1 (Sway, Hyprland, etc.).
    GNOME and KDE use their own Wayland protocols and will always reject grim."""
    desktop = (session_env().get("XDG_CURRENT_DESKTOP") or os.environ.get("XDG_CURRENT_DESKTOP", "")).lower()
    if any(d in desktop for d in ("gnome", "kde", "plasma", "unity", "cinnamon", "budgie")):
        return False
    return True


def _require_nonempty(output: str, via: str) -> int:
    """Validate a file-producing capture. A tool that exits 0 but writes an empty/missing file did NOT
    capture (gnome-screenshot/scrot/grim on a blocked or permission-denied session). Return the byte
    count, or raise BackendError so dispatch() cascades to the next backend instead of yielding a
    0-byte false success the higher layers must later detect and undo."""
    n = os.path.getsize(output) if os.path.exists(output) else 0
    if n == 0:
        raise BackendError(f"{via} exited 0 but produced an empty file — no capture "
                           f"(blocked session or missing screen-capture permission)")
    return n


@backend("capture", "grim", priority=85, platforms=("linux-wayland",), needs_bin=("grim",))
def _cap_grim(output: str, **_: Any) -> dict:
    if not _is_wlroots_compositor():
        desktop = os.environ.get("XDG_CURRENT_DESKTOP") or session_env().get("XDG_CURRENT_DESKTOP") or "unknown"
        raise BackendError(
            f"grim requires a wlroots compositor (Sway/Hyprland); "
            f"detected {desktop!r} — use portal backend instead"
        )
    _run(["grim", output])
    return {"path": output, "via": "grim", "bytes": _require_nonempty(output, "grim")}


@backend("capture", "mss", priority=70, platforms=("linux-x11", "windows", "macos"), needs_mod=("mss",))
def _cap_mss(output: str, monitor: int = 0, **_: Any) -> dict:
    import mss as _mss
    import mss.tools as _mss_tools  # `import mss` alone does not expose mss.tools
    with _mss.mss() as sct:
        mons = sct.monitors
        mon = mons[monitor if 0 <= monitor < len(mons) else 0]
        img = sct.grab(mon)
        _mss_tools.to_png(img.rgb, img.size, output=output)
    return {"path": output, "via": "mss", "size": list(img.size)}


@backend("capture", "pillow", priority=65, platforms=("windows", "macos"), needs_mod=("PIL",))
def _cap_pillow(output: str, **_: Any) -> dict:
    from PIL import ImageGrab
    ImageGrab.grab().save(output)
    return {"path": output, "via": "PIL.ImageGrab"}


@backend("capture", "scrot", priority=60,
         platforms=("linux-x11", "linux-wayland"), needs_bin=("scrot",))
def _cap_scrot(output: str, **_: Any) -> dict:
    # On XWayland sessions DISPLAY is available even when WAYLAND_DISPLAY is set;
    # scrot uses X11 so it works in that environment.
    env = session_env()
    if not env.get("DISPLAY"):
        raise BackendError("scrot requires an X11 DISPLAY; not available on pure Wayland")
    _run(["scrot", "-o", output], env=env)
    return {"path": output, "via": "scrot", "bytes": _require_nonempty(output, "scrot")}


@backend("capture", "imagemagick", priority=40, platforms=("linux-x11",), needs_bin=("import",))
def _cap_im(output: str, **_: Any) -> dict:
    _run(["import", "-window", "root", output])
    return {"path": output, "via": "imagemagick", "bytes": _require_nonempty(output, "imagemagick")}


@backend("capture", "gnome-screenshot", priority=35,
         platforms=("linux-x11", "linux-wayland"), needs_bin=("gnome-screenshot",))
def _cap_gnome(output: str, **_: Any) -> dict:
    _run(["gnome-screenshot", "-f", output], timeout=20)
    return {"path": output, "via": "gnome-screenshot", "bytes": _require_nonempty(output, "gnome-screenshot")}


@backend("capture", "screencapture", priority=80, platforms=("macos",), needs_bin=("screencapture",))
def _cap_macos(output: str, **_: Any) -> dict:
    _run(["screencapture", "-x", output])
    return {"path": output, "via": "screencapture", "bytes": _require_nonempty(output, "screencapture")}


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
        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = sock
        subprocess.Popen(["ydotoold", "-p", sock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=env)
        for _ in range(40):
            if os.path.exists(sock):
                break
            time.sleep(0.1)
        time.sleep(0.3)
    return sock


def _yd_env() -> dict:
    env = session_env()
    env["YDOTOOL_SOCKET"] = ensure_ydotoold()
    return env


_YD_BUTTON = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}

# evdev keycodes for ydotool `key` (subset; extend as needed)
_YD_KEY = {"enter": "28", "return": "28", "tab": "15", "esc": "1", "escape": "1", "space": "57",
           "backspace": "14", "ctrl": "29", "shift": "42", "alt": "56", "super": "125", "meta": "125",
           "left": "105", "right": "106", "up": "103", "down": "108", "a": "30", "c": "46", "v": "47",
           "x": "45", "z": "44", "t": "20", "w": "17", "l": "38",
           "f4": "62", "f5": "63", "f6": "64", "f11": "87", "f12": "88"}


def _yd_keyseq(combo: str) -> list[str]:
    keys = [_YD_KEY.get(k.strip().lower()) for k in combo.replace("-", "+").split("+")]
    keys = [k for k in keys if k]
    return [f"{k}:1" for k in keys] + [f"{k}:0" for k in reversed(keys)]


# ---- type ----
def session_env() -> dict:
    """A child-process env that can reach the live graphical session — the Wayland
    compositor, the X display, and the session D-Bus (which the screenshot portal
    needs). A urirun node process is usually spawned without any of these, so
    wl-copy/wtype/grim hang on connect and the portal's SessionBus() fails — point
    every backend at the sockets discovered under XDG_RUNTIME_DIR / /tmp/.X11-unix."""
    env = os.environ.copy()
    xrd = _runtime_dir()
    if xrd:
        env["XDG_RUNTIME_DIR"] = xrd
        if not env.get("WAYLAND_DISPLAY"):
            sock = _wayland_socket()
            if sock:
                env["WAYLAND_DISPLAY"] = sock
        if not env.get("DBUS_SESSION_BUS_ADDRESS") and os.path.exists(f"{xrd}/bus"):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xrd}/bus"
    if not env.get("DISPLAY"):
        disp = _x_display()
        if disp:
            env["DISPLAY"] = disp
    return env


# Back-compat alias: earlier code called this the wayland env.
_wayland_env = session_env


def _clipboard_set(text: str) -> str:
    """Put UTF-8 ``text`` on the system clipboard via the first available tool, so it can be
    pasted (Ctrl+V) verbatim. This is the only reliable way to enter non-ASCII on this stack:
    ydotool types through the kernel keymap and SILENTLY DROPS characters it can't map (Polish
    ł ą ę ż ó, accents, CJK, emoji). Returns the tool name, or raises so the caller fails
    loudly instead of publishing corrupted text."""
    if have_bin("wl-copy"):
        # wl-copy reads stdin, sets the selection, then forks to serve paste requests; the
        # foreground returns once it has the data. If it can't background it stays foreground
        # (selection IS already set), so don't block on it — write, give it a beat, move on.
        proc = subprocess.Popen(["wl-copy", "--type", "text/plain;charset=utf-8"],
                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=_wayland_env())
        try:
            proc.communicate(input=text.encode(), timeout=4)
        except subprocess.TimeoutExpired:
            pass  # still serving the (already-set) selection in the foreground — fine
        return "wl-copy"
    for argv, name in (
        (["xclip", "-selection", "clipboard"], "xclip"),   # X11
        (["xsel", "--clipboard", "--input"], "xsel"),      # X11
    ):
        if have_bin(argv[0]):
            p = subprocess.run(argv, input=text.encode(), capture_output=True, env=_wayland_env(), timeout=10)
            if p.returncode == 0:
                return name
            raise BackendError(f"{name} failed: {(p.stderr or b'').decode(errors='replace')[:120]}")
    raise BackendError("non-ASCII text needs a clipboard tool (wl-clipboard / xclip / xsel) or the "
                       "browser-cdp surface — none installed on this node; ydotool cannot type it")


@backend("type", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
def _type_ydotool(text: str, **_: Any) -> dict:
    # Non-ASCII: ydotool drops it, so set the clipboard and paste it verbatim instead — or fail
    # loudly (no clipboard tool) rather than silently corrupt the string.
    if not text.isascii():
        tool = _clipboard_set(text)
        _run(["ydotool", "key", *_yd_keyseq("ctrl+v")], env=_yd_env())
        return {"via": f"clipboard:{tool}+ctrl+v", "chars": len(text), "method": "paste"}
    _run(["ydotool", "type", "--", text], env=_yd_env())
    return {"via": "ydotool", "chars": len(text), "method": "keymap"}


@backend("type", "wtype", priority=60, platforms=("linux-wayland",), needs_bin=("wtype",))
def _type_wtype(text: str, **_: Any) -> dict:
    _run(["wtype", "--", text])
    return {"via": "wtype", "chars": len(text)}


@backend("type", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _type_xdotool(text: str, **_: Any) -> dict:
    _run(["xdotool", "type", "--", text])
    return {"via": "xdotool", "chars": len(text)}


@backend("type", "pynput", priority=40, needs_mod=("pynput",))
def _type_pynput(text: str, **_: Any) -> dict:
    from pynput.keyboard import Controller
    Controller().type(text)
    return {"via": "pynput", "chars": len(text)}


# ---- click ----
@backend("click", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
def _click_ydotool(button: str = "left", **_: Any) -> dict:
    _run(["ydotool", "click", _YD_BUTTON.get(button, "0xC0")], env=_yd_env())
    return {"via": "ydotool", "button": button}


@backend("click", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _click_xdotool(button: str = "left", **_: Any) -> dict:
    _run(["xdotool", "click", {"left": "1", "middle": "2", "right": "3"}.get(button, "1")])
    return {"via": "xdotool", "button": button}


@backend("click", "pynput", priority=40, needs_mod=("pynput",))
def _click_pynput(button: str = "left", **_: Any) -> dict:
    from pynput.mouse import Button, Controller
    Controller().click({"left": Button.left, "right": Button.right, "middle": Button.middle}[button])
    return {"via": "pynput", "button": button}


# ---- move (absolute) ----
# uinput-absolute wins over ydotool: a raw [0,65535] ABS device maps pixel->screen
# deterministically, so capture-space == action-space regardless of the ydotool version's
# coordinate convention. (ydotool `mousemove -a` takes RAW pixels on some builds and a
# [0,65535] range on others; on the latter a raw pixel maps near (0,0) and trips the
# GNOME hot-corner — observed live on the lenovo node.) Falls through to ydotool if
# /dev/uinput is not writable. See `uinput_abs_click` / `_screen_wh` below.
@backend("move", "uinput-abs", priority=90, platforms=("linux-wayland", "linux-x11"))
def _move_uinput_abs(x: int, y: int, **_: Any) -> dict:
    sw, sh = _screen_wh()
    settle = float(os.environ.get("URIRUN_KVM_ABS_SETTLE", "0.6"))
    r = uinput_abs_click(int(x), int(y), sw, sh, do_click=False, settle=settle)
    return {"via": "uinput-absolute", "x": x, "y": y, "abs": r.get("abs"), "screen": [sw, sh]}


@backend("move", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
def _move_ydotool(x: int, y: int, **_: Any) -> dict:
    _run(["ydotool", "mousemove", "-a", "-x", str(int(x)), "-y", str(int(y))], env=_yd_env())
    return {"via": "ydotool", "x": x, "y": y}


@backend("move", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _move_xdotool(x: int, y: int, **_: Any) -> dict:
    _run(["xdotool", "mousemove", str(int(x)), str(int(y))])
    return {"via": "xdotool", "x": x, "y": y}


@backend("move", "pynput", priority=40, needs_mod=("pynput",))
def _move_pynput(x: int, y: int, **_: Any) -> dict:
    from pynput.mouse import Controller
    Controller().position = (int(x), int(y))
    return {"via": "pynput", "x": x, "y": y}


# ---- key / hotkey ----
@backend("key", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
def _key_ydotool(keys: str, **_: Any) -> dict:
    seq = _yd_keyseq(keys)
    if not seq:
        raise BackendError(f"unknown key combo {keys!r}")
    _run(["ydotool", "key", *seq], env=_yd_env())
    return {"via": "ydotool", "keys": keys}


@backend("key", "xdotool", priority=70, platforms=("linux-x11",), needs_bin=("xdotool",))
def _key_xdotool(keys: str, **_: Any) -> dict:
    _run(["xdotool", "key", keys.replace("+", "+")])
    return {"via": "xdotool", "keys": keys}


@backend("key", "pynput", priority=40, needs_mod=("pynput",))
def _key_pynput(keys: str, **_: Any) -> dict:
    from pynput.keyboard import Controller, Key
    kb = Controller()
    parts = keys.replace("-", "+").split("+")
    mods = [getattr(Key, p, None) for p in parts[:-1]]
    last = parts[-1]
    for m in mods:
        if m:
            kb.press(m)
    kb.press(last)
    kb.release(last)
    for m in reversed(mods):
        if m:
            kb.release(m)
    return {"via": "pynput", "keys": keys}


# ---- scroll ----
@backend("scroll", "ydotool", priority=80, platforms=("linux-wayland", "linux-x11"), needs_bin=("ydotool", "ydotoold"))
def _scroll_ydotool(dy: int = -3, **_: Any) -> dict:
    _run(["ydotool", "mousemove", "-w", "-x", "0", "-y", str(int(dy))], env=_yd_env())
    return {"via": "ydotool", "dy": dy}


@backend("scroll", "pynput", priority=40, needs_mod=("pynput",))
def _scroll_pynput(dy: int = -3, **_: Any) -> dict:
    from pynput.mouse import Controller
    Controller().scroll(0, int(dy))
    return {"via": "pynput", "dy": dy}


# --------------------------------------------------------------------------- #
# WINDOW focus / list
# --------------------------------------------------------------------------- #
@backend("focus", "wmctrl", priority=70, platforms=("linux-x11", "linux-wayland"), needs_bin=("wmctrl",))
def _focus_wmctrl(title: str, **_: Any) -> dict:
    _run(["wmctrl", "-a", title])
    return {"via": "wmctrl", "title": title}


@backend("focus", "pygetwindow", priority=40, platforms=("windows", "macos"), needs_mod=("pygetwindow",))
def _focus_pgw(title: str, **_: Any) -> dict:
    import pygetwindow as gw
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        raise BackendError(f"no window matching {title!r}")
    wins[0].activate()
    return {"via": "pygetwindow", "title": title}


@backend("window_list", "wmctrl", priority=70, platforms=("linux-x11", "linux-wayland"), needs_bin=("wmctrl",))
def _winlist_wmctrl(app: str = "", title: str = "", **_: Any) -> dict:
    p = _run(["wmctrl", "-l"])
    wins = [" ".join(line.split()[3:]) for line in p.stdout.splitlines() if line.strip()]
    app_q = str(app or "").strip().lower()
    title_q = str(title or "").strip().lower()
    if app_q or title_q:
        wins = [
            title
            for title in wins
            if (not app_q or app_q in title.lower())
            and (not title_q or title_q in title.lower())
        ]
    selected = {"title": wins[0]} if wins else None
    return {"via": "wmctrl", "windows": wins, "selected": selected}


# APP LAUNCH / LIST backends moved to launch_backends.py (own domain; app:// is logically
# a separate connector). Imported at the end of this module so they register.


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


_ATSPI_WINDOW_LIST_SCRIPT = r"""
import sys, json
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
selector = json.loads(sys.argv[1] if len(sys.argv) > 1 else "{}")
app_q = str(selector.get("app") or "").lower()
title_q = str(selector.get("title") or "").lower()
Atspi.init()
desktop = Atspi.get_desktop(0)
windows = []

def bbox_for(node):
    try:
        comp = node.get_component_iface()
        if comp is None:
            return None
        ext = comp.get_extents(Atspi.CoordType.SCREEN)
        return [int(ext.x), int(ext.y), int(ext.width), int(ext.height)]
    except Exception:
        return None

for i in range(desktop.get_child_count()):
    app = desktop.get_child_at_index(i)
    if app is None:
        continue
    try:
        app_name = app.get_name() or ""
    except Exception:
        app_name = ""
    for j in range(app.get_child_count()):
        frame = app.get_child_at_index(j)
        if frame is None:
            continue
        try:
            title = frame.get_name() or ""
            role = frame.get_role_name() or ""
        except Exception:
            continue
        hay_app = app_name.lower()
        hay_title = title.lower()
        if app_q and app_q not in hay_app and app_q not in hay_title:
            continue
        if title_q and title_q not in hay_title:
            continue
        windows.append({
            "app": app_name,
            "title": title,
            "role": role,
            "bbox": bbox_for(frame),
        })
print(json.dumps({"windows": windows}))
"""


def _monitor_for_bbox(bbox: list | None, monitors: list[dict]) -> dict | None:
    if not bbox or len(bbox) < 4:
        return None
    x, y, w, h = [int(v) for v in bbox[:4]]
    cx, cy = x + max(0, w) / 2, y + max(0, h) / 2
    best: tuple[int, dict] | None = None
    for mon in monitors or []:
        mx = int(mon.get("x") or 0)
        my = int(mon.get("y") or 0)
        mw = int(mon.get("logicalWidth") or mon.get("width") or 0)
        mh = int(mon.get("logicalHeight") or mon.get("height") or 0)
        if mw <= 0 or mh <= 0:
            continue
        if mx <= cx < mx + mw and my <= cy < my + mh:
            return mon
        overlap_w = max(0, min(x + w, mx + mw) - max(x, mx))
        overlap_h = max(0, min(y + h, my + mh) - max(y, my))
        area = overlap_w * overlap_h
        if area and (best is None or area > best[0]):
            best = (area, mon)
    return best[1] if best else None


@backend("window_list", "atspi", priority=85, platforms=("linux-wayland", "linux-x11"))
def _winlist_atspi(app: str = "", title: str = "", **_: Any) -> dict:
    py = _atspi_python()
    if not py:
        raise BackendError("AT-SPI window list needs python3 with gi + Atspi (install python3-gobject + gnome a11y)")
    payload = json.dumps({"app": app, "title": title})
    p = _run([py, "-c", _ATSPI_WINDOW_LIST_SCRIPT, payload], env=session_env(), timeout=12)
    data = json.loads((p.stdout or "{}").strip() or "{}")
    windows = data.get("windows") if isinstance(data, dict) else []
    if not isinstance(windows, list):
        windows = []
    monitors = _gnome_monitors()
    enriched = []
    for win in windows:
        if not isinstance(win, dict):
            continue
        mon = _monitor_for_bbox(win.get("bbox"), monitors)
        item = dict(win)
        if mon:
            item["monitor"] = mon.get("index")
            item["monitorConnector"] = mon.get("connector")
        enriched.append(item)
    selected = enriched[0] if enriched else None
    return {"via": "atspi", "windows": enriched, "selected": selected, "monitors": monitors}


@backend("focus", "atspi", priority=85, platforms=("linux-wayland", "linux-x11"))
def _focus_atspi(title: str, **_: Any) -> dict:
    py = _atspi_python()
    if not py:
        raise BackendError("AT-SPI focus needs python3 with gi + Atspi (install python3-gobject + gnome a11y)")
    # AT-SPI talks over the session bus; session_env() supplies DBUS_SESSION_BUS_ADDRESS
    # (and XDG_RUNTIME_DIR) when the node process was started without them.
    p = _run([py, "-c", _ATSPI_FOCUS_SCRIPT, title], env=session_env(), timeout=12)
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
                text: str = "", nth: int = 0, **_: Any) -> dict:
    py = _atspi_python()
    if not py:
        raise BackendError("AT-SPI needs python3 with gi + Atspi (install python3-gobject + gnome a11y)")
    import json as _json
    # AT-SPI talks over the session bus — session_env() supplies DBUS_SESSION_BUS_ADDRESS.
    # Bound the tree walk: on a busy desktop a MISS walks the whole a11y tree, and the
    # router runs locate twice (atspi strategy + vision strategy each dispatch locate), so a
    # long timeout stacks past the node's exec cap and hangs. Keep it short → fall through to
    # OCR fast. Tune with URIRUN_KVM_ATSPI_TIMEOUT.
    cmd = _json.dumps({"app": app, "role": role, "name": name, "op": op, "text": text, "nth": nth})
    timeout = float(os.environ.get("URIRUN_KVM_ATSPI_TIMEOUT", "5"))
    try:
        p = _run([py, "-c", _ATSPI_ACT_SCRIPT, cmd], env=session_env(), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise BackendError(f"atspi: tree walk exceeded {timeout}s (name~{name or text!r}) — falling through") from exc
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
        if len(c) < _TESSERACT_TSV_COLS or c[0] != _TESSERACT_WORD_LEVEL:
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


def _tesseract_words_by_line(tsv_stdout: str, min_conf: float) -> dict[tuple, list]:
    """Group tesseract TSV word rows (level 5, conf ≥ min) by (page,block,par,line)."""
    words: dict[tuple, list] = {}
    for raw in tsv_stdout.splitlines()[1:]:
        c = raw.split("\t")
        if len(c) < _TESSERACT_TSV_COLS or c[0] != _TESSERACT_WORD_LEVEL:
            continue
        try:
            left, top, w, h, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
        except ValueError:
            continue
        t = c[11].strip()
        if t and conf >= min_conf:
            words.setdefault((c[1], c[2], c[3], c[4]), []).append(
                {"text": t, "conf": conf, "box": [left, top, w, h]})
    return words


def _line_match(ws: list, ql: str, terms: list) -> dict | None:
    """Build a match box for one TSV line if it contains ``ql``; else ``None``."""
    if ql not in " ".join(x["text"] for x in ws).lower():
        return None
    sel = [x for x in ws if any(term in x["text"].lower() for term in terms)] or ws
    x0 = min(x["box"][0] for x in sel)
    y0 = min(x["box"][1] for x in sel)
    x1 = max(x["box"][0] + x["box"][2] for x in sel)
    y1 = max(x["box"][1] + x["box"][3] for x in sel)
    return {"text": " ".join(x["text"] for x in sel),
            "conf": round(sum(x["conf"] for x in sel) / len(sel), 1),
            "box": [x0, y0, x1 - x0, y1 - y0],
            "center": [(x0 + x1) // 2, (y0 + y1) // 2]}


def _tesseract_query_matches(tsv_stdout: str, ql: str, min_conf: float) -> list[dict]:
    """Find word spans in tesseract TSV output whose line contains ``ql``."""
    words = _tesseract_words_by_line(tsv_stdout, float(min_conf))
    terms = [t for t in ql.split() if len(t) >= _MIN_QUERY_TERM_LEN] or ql.split()
    matches = [m for ws in words.values() if (m := _line_match(ws, ql, terms)) is not None]
    matches.sort(key=lambda m: -m["conf"])
    return matches


@backend("locate", "tesseract", priority=65, needs_bin=("tesseract",))
def _locate_tesseract(image: str = "", query: str = "", text: str = "", role: str = "",
                      name: str = "", min_conf: float = 40, **_: Any) -> dict:
    """OCR-locate on-screen text. Unlike a saliency detector this GENUINELY matches the
    query against recognised text, so it is preferred (priority 65 > imgl 60) for text
    targets. Returns the unified ``found``/``bbox``/``center`` schema AND the full
    ``matches`` list; ``found: false`` (honestly) when the text is not on screen — never
    a bogus hit. Captures its own screenshot when no ``image`` is supplied. ``name`` (the
    accessibility name an LLM planner emits for textboxes) is accepted as a query alias."""
    q = (query or text or name or "").strip()
    full = None
    if not image or not os.path.exists(image):
        cap = _capture_tmp()           # find/click handlers call us without an image
        image, full = cap["path"], cap.get("fullSize")
    p = _run(["tesseract", image, "stdout", "tsv"], timeout=60)
    ql = q.lower()
    if not ql:
        matches = sorted(_tsv_lines(p.stdout, float(min_conf)), key=lambda m: -m["conf"])
    else:
        matches = _tesseract_query_matches(p.stdout, ql, float(min_conf))
    out = {"via": "tesseract", "source": "tesseract", "coord_space": "image-px",
           "query": q, "count": len(matches), "matches": matches, "fullSize": full}
    if matches and ql:
        best = matches[0]
        out.update({"found": True, "bbox": best["box"], "center": best["center"],
                    "text": best["text"], "candidates": len(matches), "actionable": False})
    else:
        # Empty query is NOT a located hit: returning the highest-confidence arbitrary
        # glyph as found:true makes wait/fill/click act on garbage (e.g. "©"). Keep
        # `matches` for the ui_locate text-dump, but report found:false so callers that
        # need a target fail honestly instead of clicking nowhere.
        out["found"] = False           # honest miss — do NOT fall through to a guesser
        out["candidates"] = len(matches)
    return out


_EASYOCR_READER = None


def _easyocr_reader() -> Any:
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
                    min_conf: float = 40, **_: Any) -> dict:
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
def bbox_center(bbox: list | tuple) -> tuple:
    x, y, w, h = bbox
    return int(x + w / 2), int(y + h / 2)


@backend("locate", "atspi", priority=90, platforms=("linux-wayland", "linux-x11"))
def _locate_atspi(text: str = "", role: str = "", app: str = "", nth: int = 0, **_: Any) -> dict:
    res = _a11y_atspi(app=app, role=role, name=text, op="find", nth=int(nth))
    if not res.get("found") or not res.get("bbox"):
        raise BackendError(f"atspi: no element role~{role!r} name~{text!r}")
    x, y, w, h = res["bbox"]   # reject off-screen / collapsed elements (a11y tree noise)
    if x < 0 or y < 0 or w < 2 or h < 2 or x > _MAX_SCREEN_COORD or y > _MAX_SCREEN_COORD:  # noqa: PLR2004
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
def _locate_imgl(text: str = "", role: str = "", **_: Any) -> dict:
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
def _locate_vql(text: str = "", role: str = "", **_: Any) -> dict:
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
def _ui_io(nr: int) -> int:       return (0 << 30) | (_UI << 8) | nr
def _ui_iow(nr: int, sz: int) -> int:  return (1 << 30) | (sz << 16) | (_UI << 8) | nr
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


_SCREEN_WH_CACHE = os.path.join(tempfile.gettempdir(), "urirun-kvm-screen-wh")


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


def _read_text(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


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


# --------------------------------------------------------------------------- #
# Surface awareness — honest self-diagnosis of WHETHER OS-level pixel input will
# actually work on this session, not just which tool is installed. Encodes the
# lesson from three debugging sessions: live GNOME/Wayland multi-monitor +
# fractional HiDPI breaks the screenshot<->input coordinate correspondence.
# --------------------------------------------------------------------------- #
def _gnome_monitors() -> list[dict]:
    """Best-effort logical-monitor geometry via Mutter DisplayConfig (gdbus); [] if absent."""
    py = _portal_python()
    if py:
        script = r"""
import json, dbus
bus = dbus.SessionBus()
dc = dbus.Interface(bus.get_object("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig"),
                    "org.gnome.Mutter.DisplayConfig")
_serial, physical, logical, _props = dc.GetCurrentState()
phys = {}
for item in physical:
    spec, modes, props = item[0], item[1], item[2]
    conn = str(spec[0])
    cur = None
    for mode in modes:
        mprops = mode[6] if len(mode) > 6 else {}
        if bool(mprops.get("is-current")):
            cur = mode
            break
    cur = cur or (modes[0] if modes else None)
    if cur:
        phys[conn] = {"width": int(cur[1]), "height": int(cur[2]), "refresh": float(cur[3]),
                      "displayName": str(props.get("display-name", ""))}
out = []
for idx, lm in enumerate(logical):
    x, y, scale, primary, mons = int(lm[0]), int(lm[1]), float(lm[2]), bool(lm[4]), lm[5]
    conn = str(mons[0][0]) if mons else ""
    p = phys.get(conn, {})
    width, height = int(p.get("width") or 0), int(p.get("height") or 0)
    out.append({"index": idx + 1, "connector": conn, "x": x, "y": y,
                "scale": round(scale, 3), "primary": primary,
                "width": width, "height": height,
                "logicalWidth": round(width / scale) if width and scale else 0,
                "logicalHeight": round(height / scale) if height and scale else 0,
                "displayName": p.get("displayName") or conn})
print(json.dumps(out))
"""
        try:
            proc = subprocess.run([py, "-c", script], capture_output=True, text=True,
                                  timeout=8, env=session_env())
            if proc.returncode == 0:
                data = json.loads(proc.stdout or "[]")
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    if not have_bin("gdbus"):
        return []
    env = os.environ.copy()   # a node process often lacks the session-bus env; point gdbus at it
    if hasattr(os, "getuid"):
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={env['XDG_RUNTIME_DIR']}/bus")
    try:
        out = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.DisplayConfig",
             "--object-path", "/org/gnome/Mutter/DisplayConfig",
             "--method", "org.gnome.Mutter.DisplayConfig.GetCurrentState"],
            capture_output=True, text=True, timeout=8, env=env).stdout
    except Exception:  # noqa: BLE001
        return []
    import re
    mons = []
    for m in re.finditer(r"\((\d+),\s*(\d+),\s*([\d.]+),\s*uint32\s*\d+,\s*(true|false)", out):
        x, y, scale, prim = m.groups()
        mons.append({"x": int(x), "y": int(y), "scale": round(float(scale), 3), "primary": prim == "true"})
    return mons


def _wayland_present() -> bool | None:
    """True / False / None(unknown) — robust, env-independent (a node process often has
    no WAYLAND_DISPLAY even on a live Wayland session)."""
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return True
    xrd = os.environ.get("XDG_RUNTIME_DIR") or (f"/run/user/{os.getuid()}" if hasattr(os, "getuid") else "")
    try:
        if xrd and any(n.startswith("wayland-") for n in os.listdir(xrd)):
            return True
    except OSError:
        pass
    if have_bin("loginctl"):
        try:
            o = subprocess.run(["loginctl", "show-session", "self", "-p", "Type"],
                               capture_output=True, text=True, timeout=3).stdout.lower()
            if "wayland" in o:
                return True
            if "x11" in o:
                return False
        except Exception:  # noqa: BLE001
            pass
    return None


def _surface_warnings(waylandish: bool, multi: bool, fractional: bool,
                      mons: list, unconfirmed: bool) -> list[str]:
    """Build the human-readable warning list for ``surface_report``."""
    warnings = []
    if waylandish:
        if multi or fractional or not mons:
            why = ", ".join(p for p in (
                "multi-monitor" if multi else "",
                "fractional-HiDPI" if fractional else "",
                "layout unconfirmed (Mutter geometry unreadable)" if not mons else "") if p)
            warnings.append(
                f"OS-level pixel input (move/click/abs/task) is UNRELIABLE here: Wayland + {why} — "
                "screenshot pixels do not map to a fixed input coordinate and focus cannot be stolen. "
                "Use browser-cdp (web) or remotedesktop-portal / vdisplay (native). capture (portal) is fine.")
        else:
            warnings.append(
                "Wayland single-monitor, integer scale: pixel input maps ~1:1 — usable, but keys "
                "reach only the ACTIVE window (no focus-stealing).")
    elif unconfirmed:
        warnings.append(
            "Session type unconfirmed (node env has no WAYLAND_DISPLAY/DISPLAY). If this is GNOME/Wayland, "
            "OS-level pixel input is likely unreliable — prefer browser-cdp / remotedesktop-portal; verify "
            "with a known-coordinate click before trusting move/click/abs.")
    return warnings


def _os_level_reliable(wl: bool | None, multi: bool, fractional: bool, unconfirmed: bool,
                       confirmed_simple: bool) -> bool:
    """True when OS-level pixel input (move/click) can be trusted on this session."""
    return bool(confirmed_simple or (wl is False and not multi and not fractional and not unconfirmed))


def _surface_flags(linux: bool, mons: list[dict], wl: bool | None) -> dict:
    """Derive the Wayland/multi/fractional/reliability booleans from monitor geometry and
    the (True/False/None) Wayland signal. Factored out so ``surface_report`` stays simple."""
    multi = len(mons) > 1
    fractional = any(m["scale"] not in (0, 1.0) for m in mons)
    # GNOME answered DisplayConfig and the session isn't positively X11 → treat as Wayland-ish.
    waylandish = (wl is True) or is_wayland() or (bool(mons) and wl is not False)
    unconfirmed = linux and not waylandish and wl is None and not os.environ.get("DISPLAY")
    confirmed_simple = bool(mons) and not multi and not fractional and wl is False  # positively X11 single+integer
    os_reliable = _os_level_reliable(wl, multi, fractional, unconfirmed, confirmed_simple)
    return {"multi": multi, "fractional": fractional, "waylandish": waylandish,
            "unconfirmed": unconfirmed, "os_reliable": os_reliable}


def surface_report() -> dict:
    """Which execution surface to trust here, and why — env-independent so it is honest
    even on a node process that can't see WAYLAND_DISPLAY. Surfaces: os-level (raw input,
    this connector), browser-cdp (Playwright/CDP), remotedesktop-portal, vdisplay. On
    Wayland multi-monitor / fractional-HiDPI, os-level pixel input is unreliable."""
    plat = platform_tag()
    linux = sys.platform.startswith("linux")
    mons = _gnome_monitors() if linux else []     # ground truth via Mutter (works w/o WAYLAND_DISPLAY)
    wl = _wayland_present()                         # True / False / None
    f = _surface_flags(linux, mons, wl)
    multi, fractional, waylandish = f["multi"], f["fractional"], f["waylandish"]
    unconfirmed, os_reliable = f["unconfirmed"], f["os_reliable"]
    warnings = _surface_warnings(waylandish, multi, fractional, mons, unconfirmed)
    recommended = (["browser-cdp", "remotedesktop-portal", "vdisplay"]
                   if (waylandish or unconfirmed) else ["os-level", "browser-cdp"])
    return {"platform": plat, "wayland": waylandish, "waylandConfirmed": wl, "monitors": mons,
            "multiMonitor": multi, "fractionalHiDPI": fractional, "osLevelReliable": os_reliable,
            "recommendedSurfaces": recommended, "warnings": warnings}


# Register the launch/launch_list backends (their @backend decorators run on import).
try:  # normal package import
    from urirun_connector_kvm import launch_backends  # noqa: E402,F401
except ImportError:  # flat-module deploy (node pushes backends.py + launch_backends.py as flat modules)
    import launch_backends  # type: ignore  # noqa: F401
