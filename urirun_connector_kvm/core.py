# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""KVM (keyboard/video/mouse) routes for urirun.

Routes match the connect.ifuri.com contract:

* ``kvm://host/input/command/key``      -- send a key press
* ``kvm://host/input/command/move``     -- move the mouse pointer
* ``kvm://host/screen/query/capture``   -- capture the screen to a file

Each route is declared once with a typed ``@conn.handler`` decorated
``isolated=True``: the function signature becomes the input schema and the body is
the implementation — no argv template, no ``_exec.py``, no ``run_route``
dispatcher. ``isolated=True`` runs the route out-of-process through the shared
``python -m urirun.exec`` runner, so the binding stays **registry-portable**.

**Backend selection (X11 *and* Wayland).** Each route picks a host tool that
matches the live session. On X11 it uses ``scrot`` (capture) and ``xdotool``
(input). On Wayland those tools see only a rootless Xwayland root window (a black
frame) and cannot reach native Wayland windows, so the route instead tries
Wayland-native tools — ``gnome-screenshot``/``grim`` for capture (both go through
the compositor/portal) and ``ydotool``/``wtype`` for input (these inject at the
``/dev/uinput`` kernel level, below the compositor, so they reach any window).
The first tool that exists and succeeds wins; the result reports it as ``via``.
When no usable tool is present the route returns ``ok: false`` rather than raising.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import urirun

CONNECTOR_ID = "kvm"
conn = urirun.connector(CONNECTOR_ID, scheme="kvm")


# --- session / backend detection ------------------------------------------

def _is_wayland() -> bool:
    """True when the live session is Wayland (so X11 tools would capture black)."""
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _first_available(names: list[str]) -> str | None:
    for name in names:
        if shutil.which(name):
            return name
    return None


def _try_run(argv: list[str]) -> tuple[bool, str]:
    """Run a tool, returning (ok, stderr). Missing binary / non-zero exit -> not ok."""
    if shutil.which(argv[0]) is None:
        return False, f"{argv[0]} is not installed"
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr or f"{argv[0]} exited {proc.returncode}").strip()
    return True, ""


# --- capture: ordered backend chain ---------------------------------------

def _capture_argv(tool: str, output: str) -> list[str]:
    if tool == "scrot":
        return ["scrot", "-o", output]
    if tool == "grim":
        return ["grim", output]
    if tool == "gnome-screenshot":
        return ["gnome-screenshot", "-f", output]
    if tool == "spectacle":
        return ["spectacle", "-b", "-n", "-o", output]
    raise ValueError(f"unknown capture tool: {tool}")


def _capture_backends() -> list[str]:
    # Wayland first when on Wayland (X11 scrot would be a black frame there).
    if _is_wayland():
        return ["grim", "gnome-screenshot", "spectacle", "scrot"]
    return ["scrot", "gnome-screenshot", "grim", "spectacle"]


# --- input: ordered backend chain ------------------------------------------

def _key_argv(tool: str, key: str) -> list[str]:
    if tool == "xdotool":
        return ["xdotool", "key", key]
    if tool == "wtype":
        return ["wtype", "-k", key]          # keysym name, e.g. Return, a, ctrl
    if tool == "ydotool":
        return ["ydotool", "key", key]       # ydotool >=1.0 accepts key names
    raise ValueError(f"unknown key tool: {tool}")


def _move_argv(tool: str, x: int, y: int) -> list[str]:
    if tool == "xdotool":
        return ["xdotool", "mousemove", str(x), str(y)]
    if tool == "ydotool":
        return ["ydotool", "mousemove", "-a", str(x), str(y)]   # -a = absolute
    raise ValueError(f"unknown move tool: {tool}")


def _input_backends(kind: str) -> list[str]:
    if _is_wayland():
        return ["ydotool", "wtype"] if kind == "key" else ["ydotool"]
    return ["xdotool"]


def _dispatch(action: str, backends: list[str], argv_for, extra: dict) -> dict[str, Any]:
    """Try each backend in order; report the one that worked as ``via``."""
    last_err = "no backend available"
    tried: list[str] = []
    for tool in backends:
        if shutil.which(tool) is None:
            continue
        tried.append(tool)
        ok, err = _try_run(argv_for(tool))
        if ok:
            return urirun.ok(connector=CONNECTOR_ID, action=action, executed=True,
                             via=tool, wayland=_is_wayland(), **extra)
        last_err = f"{tool}: {err}"
    detail = f" (tried: {', '.join(tried)})" if tried else " (no matching tool installed)"
    return urirun.fail(last_err + detail, connector=CONNECTOR_ID, action=action,
                       wayland=_is_wayland())


# --- route declarations: schema + implementation, registry-portable -------

@conn.handler("input/command/key", isolated=True, meta={"label": "Send a key press"})
def key(key: str = "") -> dict[str, Any]:
    """Send a key press (xdotool on X11; ydotool/wtype on Wayland)."""
    if not key:
        return urirun.fail("key is required", connector=CONNECTOR_ID)
    return _dispatch("key", _input_backends("key"), lambda t: _key_argv(t, key), {"key": key})


@conn.handler("input/command/move", isolated=True, meta={"label": "Move the mouse pointer"})
def move(x: int = 0, y: int = 0) -> dict[str, Any]:
    """Move the mouse pointer (xdotool on X11; ydotool absolute on Wayland)."""
    return _dispatch("move", _input_backends("move"), lambda t: _move_argv(t, x, y),
                     {"x": x, "y": y})


@conn.handler("screen/query/capture", isolated=True, meta={"label": "Capture the screen"})
def capture(output: str = "screen.png") -> dict[str, Any]:
    """Capture the screen to a file (scrot on X11; grim/gnome-screenshot on Wayland)."""
    if not output:
        return urirun.fail("output is required", connector=CONNECTOR_ID)
    result = _dispatch("capture", _capture_backends(),
                       lambda t: _capture_argv(t, output), {"output": output})
    # A backend can exit 0 yet write nothing (or a black frame); surface that.
    if result.get("ok"):
        try:
            size = os.path.getsize(output)
        except OSError:
            size = 0
        if size == 0:
            return urirun.fail(f"{result.get('via')} produced no image at {output}",
                               connector=CONNECTOR_ID, action="capture", wayland=_is_wayland())
        result["bytes"] = size
    return result


# --- authoring surface: bindings / manifest / CLI --------------------------

def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings)."""
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    """Full manifest: prose (connector.manifest.json) + routes/uriSchemes/
    adapterKinds/examples derived from the handlers."""
    return conn.manifest(urirun.load_manifest(__package__))


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point: subcommands + dispatch derived from the handlers."""
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
