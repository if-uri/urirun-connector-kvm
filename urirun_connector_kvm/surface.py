# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# surface/query/current — what UI surface is in the FOREGROUND right now, so the router and
# the planner can pick the right control path (CDP browser DOM vs desktop OCR/a11y) WITHOUT
# the flow having to name `app`. The strong signal is a reachable CDP debug page (=> browser);
# otherwise a best-effort active-window probe + the environment's best non-cdp strategy.
import shutil
import subprocess

try:  # normal package import / flat deploy
    from urirun_connector_kvm import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore

try:
    from urirun_connector_kvm import environment as _env
except ImportError:  # pragma: no cover
    import environment as _env  # type: ignore


_BROWSERS = ("chrome", "chromium", "brave", "edge", "firefox", "opera", "vivaldi")


def _active_window() -> dict:
    """Best-effort foreground window title — X11/Xwayland only (pure Wayland has no public
    active-window query). Empty dict when nothing answers; never raises."""
    for argv in (["xdotool", "getactivewindow", "getwindowname"],
                 ["xdotool", "getwindowfocus", "getwindowname"]):
        if not shutil.which(argv[0]):
            continue
        try:
            out = subprocess.run(argv, capture_output=True, text=True, timeout=3)
            if out.returncode == 0 and out.stdout.strip():
                return {"title": out.stdout.strip(), "via": argv[0]}
        except Exception:  # noqa: BLE001
            continue
    return {}


def current() -> dict:
    """Foreground surface: ``{kind: browser|desktop, app, recommend, ...}``. ``recommend`` is the
    control strategy the router should use; ``app`` is what to pass to ``ui/*`` so CDP engages."""
    best = _env.profile().get("best")
    # 1) a reachable CDP page => the surface IS a browser; the cdp DOM path is exact + OCR-free
    try:
        if _cdp.reachable():
            pages = _cdp._pages()
            top = pages[0] if pages else {}
            return {"kind": "browser", "app": "chrome", "recommend": "cdp",
                    "browser": {"url": top.get("url"), "title": top.get("title")}, "best": best}
    except Exception:  # noqa: BLE001
        pass
    # 2) otherwise a desktop surface; name the app from the active window when we can
    win = _active_window()
    title = (win.get("title") or "").lower()
    app = next((b for b in _BROWSERS if b in title), "")
    return {"kind": "desktop", "app": app, "recommend": best, "window": win, "best": best}
