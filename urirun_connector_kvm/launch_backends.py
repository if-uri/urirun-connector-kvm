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
from typing import Any

try:  # normal package import
    from .backends import BackendError, _run, backend, session_env
except ImportError:  # flat-module deploy (node `host deploy --code backends.py launch_backends.py`)
    from backends import BackendError, _run, backend, session_env  # type: ignore


def _cdp_port() -> str:
    """The debug port to launch Chrome on — derived from the SAME source the CDP client
    (cdp.endpoint) and the readiness poll use, so all three agree. URIRUN_KVM_CDP_URL is
    authoritative (that's what the `cdp` strategy connects to); URIRUN_KVM_CDP_PORT is a
    fallback. Binding a different port than the client polls is why a launch could bind
    9333 while the client looked at 9222 — Chrome was up but invisible to the strategy."""
    url = os.environ.get("URIRUN_KVM_CDP_URL")
    if url:
        tail = url.rstrip("/").rsplit(":", 1)[-1].split("/")[0]
        if tail.isdigit():
            return tail
    return os.environ.get("URIRUN_KVM_CDP_PORT", "9222")


def _cdp_wait(port: str, wait: float) -> dict:
    """Poll the CDP debug endpoint until it is reachable (early-exit) so a chrome launch
    can honestly report whether the debug socket actually bound — instead of assuming the
    injected ``--remote-debugging-port`` took effect."""
    import urllib.request
    url = (os.environ.get("URIRUN_KVM_CDP_URL") or f"http://127.0.0.1:{port}").rstrip("/")
    deadline = time.monotonic() + max(0.0, float(wait))
    while True:
        try:
            with urllib.request.urlopen(url + "/json/version", timeout=2.0) as r:
                if r.status == 200:  # noqa: PLR2004
                    return {"ready": True, "port": port, "endpoint": url}
        except Exception:  # noqa: BLE001 - not up yet; keep polling until the deadline
            pass
        if time.monotonic() >= deadline:
            return {"ready": False, "port": port, "endpoint": url,
                    "error": "debugger did not come up within timeout"}
        time.sleep(0.5)


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


def _parse_desktop_section(fh: Any) -> tuple[str, str, bool]:
    """Parse [Desktop Entry] lines for Name, Exec, NoDisplay. Returns (name, exec, nodisplay)."""
    name = exec_line = ""
    nodisplay = False
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
    return name, exec_line, nodisplay


def _parse_desktop(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            name, exec_line, nodisplay = _parse_desktop_section(fh)
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
        if len(p) == 2 and p[0] == "%":  # noqa: PLR2004  # %f %u %F %U %i %c %k ...
            continue
        if p.startswith("@@"):               # flatpak arg wrappers
            continue
        out.append(p)
    return out


def _find_app(query: str) -> dict | None:
    q = (query or "").strip().lower()
    entries = _desktop_entries()
    for e in entries:                        # exact id
        if e["id"].lower() == q:
            return e
    for e in entries:                        # id / name contains
        if q and (q in e["id"].lower() or q in e["name"].lower()):
            return e
    return None


def _resolve_launch_argv(app: str, extra: list) -> tuple[list, dict]:
    """Resolve ``app`` to a runnable ``argv`` + ``resolved`` descriptor the way the system app
    search does: prefer a matching XDG ``.desktop`` entry (field codes stripped), then a PATH
    binary, else raise. Shared boundary for ``_launch_xdg``."""
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
    return argv, resolved


def _inject_cdp_profile(argv: list, cdp_port: str) -> None:
    """Inject --user-data-dir (isolated profile) and startup flags so the debug port actually
    binds — Chrome 136+ silently drops --remote-debugging-port on the default profile."""
    if not any("user-data-dir" in a for a in argv):
        ddir = os.environ.get("URIRUN_KVM_CDP_PROFILE") or f"/tmp/urirun-kvm-cdp-{cdp_port}"
        argv.insert(1, f"--user-data-dir={ddir}")
        for flag in ("--no-first-run", "--no-default-browser-check"):
            if flag not in argv:
                argv.insert(1, flag)


def _inject_chrome_flags(argv: list, debug: bool) -> str:
    """Add Chrome/Chromium control-surface flags in place (a11y always; CDP debug profile when
    opted in) and return the chosen CDP port (``""`` when none). Mutates ``argv`` exactly as the
    inline block in ``_launch_xdg`` did; no-op for non-chrome binaries or when URIRUN_KVM_NO_A11Y."""
    cdp_port = ""
    is_chrome = any(b in argv[0].lower() for b in ("chrome", "chromium", "brave", "edge"))
    if os.environ.get("URIRUN_KVM_NO_A11Y") or not is_chrome:
        return cdp_port
    if not any("force-renderer-accessibility" in a for a in argv):
        argv.insert(1, "--force-renderer-accessibility")
    if not (debug or os.environ.get("URIRUN_KVM_CDP_ON_LAUNCH")):
        return cdp_port
    cdp_port = _cdp_port()
    if not any("remote-debugging-port" in a for a in argv):
        argv.insert(1, f"--remote-debugging-port={cdp_port}")
    _inject_cdp_profile(argv, cdp_port)
    return cdp_port


@backend("launch", "xdg", priority=80, platforms=("linux-wayland", "linux-x11"))
def _launch_xdg(app: str = "", compose: str = "", args: list | None = None, settle: float = 0,
                debug: bool = False, **_: Any) -> dict:
    extra = list(args or [])
    if compose:
        extra += ["-compose", compose]
    argv, resolved = _resolve_launch_argv(app, extra)
    # Chrome/Chromium control surfaces:
    #   --force-renderer-accessibility → the atspi/OCR strategies can see web elements.
    #     Harmless and does NOT change which profile opens — applied to every chrome launch.
    #   --remote-debugging-port + dedicated --user-data-dir → the `cdp` strategy drives the
    #     DOM. This is OPT-IN (debug=True or URIRUN_KVM_CDP_ON_LAUNCH): a dedicated profile is
    #     required for the debug port to actually bind (Chrome 136+ blocks it on the default
    #     profile, and a bare port is swallowed by an already-running default-profile Chrome),
    #     BUT that profile is UNAUTHENTICATED — forcing it by default would break logged-in
    #     workflows (e.g. an OCR-driven LinkedIn post). For an authenticated CDP session use
    #     the cdp/session/command/ensure route (it clones auth via copy_from). Off via
    #     URIRUN_KVM_NO_A11Y=1.
    cdp_port = _inject_chrome_flags(argv, debug)
    # session_env() points the child at the live compositor/X/D-Bus; a node process is
    # often spawned without those, and the old hardcoded WAYLAND_DISPLAY=wayland-0 was
    # wrong on any seat whose socket isn't wayland-0.
    p = subprocess.Popen(argv, env=session_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    settled = max(0.0, min(float(settle or 0), 30.0))
    result = {"via": "xdg", "app": resolved, "pid": p.pid, "argv": argv,
              "compose": bool(compose), "settled": settled}
    if cdp_port:
        # Spend the settle window (or a short default) polling for the debug port so the
        # result honestly reports whether CDP came up instead of assuming it did.
        # headful Chrome cold-start on a real desktop binds the debug port well after the
        # process exists (~12-15s observed on the lenovo node) — too short a window reports a
        # false "debugger did not come up" while Chrome is in fact coming up. Match cdp.launch_session.
        result["cdp"] = _cdp_wait(cdp_port, max(settled, 15.0))
    elif settled:
        time.sleep(settled)
    return result


@backend("launch", "macos", priority=70, platforms=("macos",), needs_bin=("open",))
def _launch_macos(app: str = "", args: list | None = None, settle: float = 0, **_: Any) -> dict:
    argv = ["open", "-a", app] + (["--args", *map(str, args or [])] if args else [])
    _run(argv)
    settled = max(0.0, min(float(settle or 0), 30.0))
    if settled:
        time.sleep(settled)
    return {"via": "open", "app": {"id": app, "name": app, "how": "open"}, "settled": settled}


@backend("launch", "windows", priority=70, platforms=("windows",))
def _launch_windows(app: str = "", args: list | None = None, settle: float = 0, **_: Any) -> dict:
    try:
        os.startfile(app)  # type: ignore[attr-defined]
    except OSError:
        _run(["cmd", "/c", "start", "", app, *map(str, args or [])])
    settled = max(0.0, min(float(settle or 0), 30.0))
    if settled:
        time.sleep(settled)
    return {"via": "startfile", "app": {"id": app, "name": app, "how": "startfile"}, "settled": settled}


@backend("launch_list", "xdg", priority=80, platforms=("linux-wayland", "linux-x11"))
def _list_xdg(filter: str = "", **_: Any) -> dict:  # noqa: A002 - matches route field name
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
def _list_macos(filter: str = "", **_: Any) -> dict:  # noqa: A002
    q = (filter or "").lower()
    out = []
    for entry in sorted(glob.glob("/Applications/*.app")):
        app_id = os.path.basename(entry)[:-len(".app")]
        if q and q not in app_id.lower():
            continue
        out.append({"id": app_id, "name": app_id})
    return {"via": "open", "count": len(out), "apps": out}
