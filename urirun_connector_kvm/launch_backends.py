"""App launch/list backends for the ``launch``/``launch_list`` actions — split out of
``backends.py`` because launching apps is its own domain (it shares no state with
capture/input/locate, and `app://...` is conceptually a separate connector). Resolves
apps the way the system app search does (XDG ``.desktop`` on Linux, covering Flatpak/Snap;
``open -a`` on macOS; ``startfile`` on Windows), not via ``which()``.

Imported for its side effect: the ``@backend`` decorators register into the shared
registry in ``backends.py`` (which imports this module at the end of its own load).
"""

from __future__ import annotations

import glob
import os
import shlex
import shutil
import subprocess
import time

try:  # normal package import
    from .backends import BackendError, _run, backend
except ImportError:  # flat-module deploy (node `host deploy --code backends.py launch_backends.py`)
    from backends import BackendError, _run, backend  # type: ignore


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
    # Chrome/Chromium: force the renderer accessibility tree on so AT-SPI (and thus the
    # kvm ui/* locate path with real role/name) can see web elements — otherwise locate
    # falls back to flat OCR which has no role/name concept. Off via URIRUN_KVM_NO_A11Y=1.
    if not os.environ.get("URIRUN_KVM_NO_A11Y") and any(
            b in argv[0].lower() for b in ("chrome", "chromium", "brave", "edge")):
        if not any("force-renderer-accessibility" in a for a in argv):
            argv.insert(1, "--force-renderer-accessibility")
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
