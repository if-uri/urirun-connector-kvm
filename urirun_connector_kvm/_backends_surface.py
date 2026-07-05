"""Surface awareness / monitor geometry helpers extracted from backends.py."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

from urirun.connectors.backend_registry import have_bin


def _gnome_monitors() -> list[dict]:
    """Best-effort logical-monitor geometry via Mutter DisplayConfig (gdbus); [] if absent."""
    try:
        from urirun_connector_kvm.backends import _portal_python, session_env  # lazy circular-safe
    except ImportError:  # flat-module deploy
        from backends import _portal_python, session_env  # type: ignore
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
    try:
        from urirun_connector_kvm.backends import is_wayland  # lazy circular-safe
    except ImportError:  # flat-module deploy
        from backends import is_wayland  # type: ignore
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
    try:
        from urirun_connector_kvm.backends import platform_tag  # lazy circular-safe
    except ImportError:  # flat-module deploy
        from backends import platform_tag  # type: ignore
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
