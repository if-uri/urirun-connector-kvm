# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Live ENVIRONMENT capability profile — what UI control ACTUALLY works in THIS session, so
# the router fits the machine instead of guessing, and the diagnostics layer recommends only
# remediation the environment can support (no "use CDP" where Chrome can't, no "OCR" where
# tesseract is absent). Pure detection; cheap; no side effects. Exposed as a URI:
#     kvm://<host>/env/query/profile
import os
import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

try:  # normal package import / flat deploy
    from urirun_connector_kvm import backends as B
except ImportError:  # pragma: no cover
    import backends as B  # type: ignore

try:
    from urirun_connector_kvm import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore


def _safe(fn: Callable) -> bool:
    try:
        return bool(fn())
    except Exception:  # noqa: BLE001
        return False


def atspi_ready() -> bool:
    """An AT-SPI locate backend is registered AND available on this platform (Chrome a11y on
    / native apps). Cheap registry probe — the real query runs in the strategy."""
    try:
        return any(b.name == "atspi" and b.available() for b in B._REGISTRY.get("locate", []))
    except Exception:  # noqa: BLE001
        return False


def action_matrix(prof: dict) -> dict:
    """Per-action executability across all control surfaces for the current session.

    Answers 'can THIS surface perform THIS action on THIS platform?' — distinct from listing
    available surfaces. Encodes hard-wired platform rules that detection alone cannot discover:
    Wayland compositor withholds keyboard focus from atspi/uinput → type NOT EXECUTABLE outside
    CDP-DOM; XDG portal blocks OS-level screen capture in headless/service sessions.

    Actions: locate, click, type, navigate, screenshot
    Surfaces: cdp, atspi, uinput, vision
    Values: executable | degraded | not_executable | not_applicable | blocked
    """
    wayland = prof.get("wayland", False)
    cs = prof.get("controlStrategies") or {}
    inp = prof.get("input") or {}
    ocr = prof.get("ocr") or {}
    cdp_ok = cs.get("cdp", False)
    atspi_ok = cs.get("atspi", False)
    has_uinput = bool(inp.get("uinput") or inp.get("ydotool") or inp.get("xdotool"))
    vision_ok = cs.get("vision", False)
    os_reliable = prof.get("osLevelReliable")

    def _cdp_col() -> dict:
        e = "executable" if cdp_ok else "not_executable"
        return {"locate": e, "click": e, "type": e, "navigate": e,
                "screenshot": "executable" if cdp_ok else "not_applicable"}

    def _atspi_col() -> dict:
        if not atspi_ok:
            return {k: "not_applicable" for k in ("locate", "click", "type", "navigate", "screenshot")}
        # Wayland compositor withholds keyboard focus from atspi for web compositor inputs
        type_v = "not_executable" if wayland else "degraded"
        return {"locate": "executable", "click": "executable", "type": type_v,
                "navigate": "not_applicable", "screenshot": "not_applicable"}

    def _uinput_col() -> dict:
        if not has_uinput:
            return {k: "not_applicable" for k in ("locate", "click", "type", "navigate", "screenshot")}
        # Wayland: coordinate input works for click but compositor blocks synthetic keyboard for web
        type_v = "not_executable" if wayland else "degraded"
        shot_v = "blocked" if os_reliable is False else ("degraded" if os_reliable is None else "executable")
        return {"locate": "not_applicable", "click": "executable", "type": type_v,
                "navigate": "not_applicable", "screenshot": shot_v}

    def _vision_col() -> dict:
        if not vision_ok:
            return {k: "not_applicable" for k in ("locate", "click", "type", "navigate", "screenshot")}
        shot_v = "blocked" if os_reliable is False else ("degraded" if os_reliable is None else "executable")
        return {"locate": "degraded", "click": "degraded", "type": "not_applicable",
                "navigate": "not_applicable", "screenshot": shot_v}

    return {"cdp": _cdp_col(), "atspi": _atspi_col(), "uinput": _uinput_col(), "vision": _vision_col()}


def profile() -> dict:
    """Capabilities of the current session, plus a derived ``controlStrategies`` map saying
    which router strategy CAN work here (cdp needs a reachable debug endpoint; atspi needs
    the a11y tree; vision needs OCR AND writable /dev/uinput for the click)."""
    ocr = {"tesseract": shutil.which("tesseract") is not None, "easyocr": B.have_mod("easyocr")}
    inp = {
        "uinput": _safe(B.uinput_available),
        "ydotool": shutil.which("ydotool") is not None,
        "xdotool": shutil.which("xdotool") is not None,
    }
    try:
        sw, sh = B._screen_wh()
    except Exception:  # noqa: BLE001
        sw, sh = 0, 0
    cdp_ok = _safe(_cdp.reachable)
    # cdp is FEASIBLE (not necessarily live) when a chrome-family binary exists: a remediation
    # can launch a CDP session. Distinct from `reachable` (a debug endpoint up RIGHT NOW).
    cdp_feasible = any(shutil.which(c) for c in
                       ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser",
                        "brave-browser", "microsoft-edge"))
    atspi = atspi_ready()
    has_ocr = ocr["tesseract"] or ocr["easyocr"]
    has_click = inp["uinput"] or inp["ydotool"] or inp["xdotool"]
    prof = {
        "platform": B.platform_tag(),
        "wayland": B.is_wayland(),
        "display": {"width": int(sw), "height": int(sh)},
        "cdp": {"reachable": cdp_ok, "feasible": bool(cdp_feasible), "endpoint": _cdp.endpoint()},
        "atspi": atspi,
        "ocr": ocr,
        "input": inp,
        "controlStrategies": {
            "cdp": cdp_ok,
            "atspi": atspi,
            "vision": bool(has_ocr and has_click),
        },
        "cdpFeasible": bool(cdp_feasible),
    }
    # Surface trustworthiness (env-independent, via Mutter ground truth): on Wayland
    # multi-monitor / fractional-HiDPI the OS-level pixel path is UNRELIABLE (screenshot and
    # input live in different coordinate spaces) — a recovery INPUT, not just a doctor warning.
    try:
        sr = B.surface_report()
        prof["osLevelReliable"] = bool(sr.get("osLevelReliable"))
        prof["recommendedSurfaces"] = list(sr.get("recommended") or [])
        prof["monitors"] = list(sr.get("monitors") or [])
    except Exception:  # noqa: BLE001
        prof["osLevelReliable"] = None
        prof["recommendedSurfaces"] = []
    # An honest top-line: can this environment drive a UI at all, and how best?
    cs = prof["controlStrategies"]
    prof["best"] = "cdp" if cs["cdp"] else "atspi" if cs["atspi"] else "vision" if cs["vision"] else None
    prof["controllable"] = prof["best"] is not None
    # Per-action executability matrix — what each surface can actually DO here, not just whether it exists.
    prof["actionMatrix"] = action_matrix(prof)
    return prof


# ── Known service cookie sentinels ────────────────────────────────────────────
# Each entry: service name -> list of (host_pattern, cookie_name) pairs.
# A session is considered ACTIVE when at least one cookie is found and not expired.
_SERVICE_SENTINELS: dict[str, list[tuple[str, str]]] = {
    "linkedin":  [("%linkedin%", "li_at"), ("%linkedin%", "bscookie")],
    "google":    [("%google%", "SID"), ("%google%", "SSID")],
    "github":    [("%github%", "user_session"), ("%github%", "dotcom_user")],
    "facebook":  [("%facebook%", "c_user"), ("%facebook%", "xs")],
    "twitter":   [("%twitter%", "auth_token"), ("%x.com%", "auth_token")],
    "openai":    [("%openai%", "__Secure-next-auth.session-token")],
}

# Known browser config dirs and their names
_BROWSER_CONFIGS: list[tuple[str, str]] = [
    ("~/.config/google-chrome", "chrome"),
    ("~/.config/chromium",      "chromium"),
    ("~/.mozilla/firefox",      "firefox"),
    ("~/.config/brave-browser", "brave"),
]


def _check_cookies_for_services(cookie_db: str, services: list[str] | None = None) -> dict[str, bool]:
    """Read a Chromium-family Cookies SQLite file (copied to avoid lock) and return which
    service sessions are present. Firefox uses a different format and is skipped here."""
    tmp = tempfile.mktemp(suffix=".db")
    try:
        import shutil as _sh
        _sh.copy2(cookie_db, tmp)
        conn = sqlite3.connect(tmp)
        targets = services or list(_SERVICE_SENTINELS.keys())
        result: dict[str, bool] = {}
        for svc in targets:
            sentinels = _SERVICE_SENTINELS.get(svc, [])
            found = False
            for host_pat, cookie_name in sentinels:
                rows = conn.execute(
                    "SELECT 1 FROM cookies WHERE host_key LIKE ? AND name = ? AND expires_utc > 0 LIMIT 1",
                    (host_pat, cookie_name),
                ).fetchone()
                if rows:
                    found = True
                    break
            result[svc] = found
        conn.close()
        return result
    except Exception:  # noqa: BLE001
        return {s: False for s in (services or list(_SERVICE_SENTINELS.keys()))}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _proc_argv(pid: int) -> list[bytes]:
    """Read full argv from /proc/<pid>/cmdline. Returns [] on error.
    Handles both standard null-separated format and the single-string format
    that appears when Chrome is launched via shell with a combined command string."""
    try:
        data = Path(f"/proc/{pid}/cmdline").read_bytes()
        if not data:
            return []
        stripped = data.rstrip(b"\x00")
        # Standard format: args separated by null bytes
        if b"\x00" in stripped:
            return stripped.split(b"\x00")
        # Non-standard: single blob (shell-launched process) — split by spaces
        return stripped.split(b" ")
    except OSError:
        return []


def _proc_ppid(pid: int) -> int | None:
    """Return parent PID of process, or None on error."""
    try:
        for line in Path(f"/proc/{pid}/status").read_text(errors="replace").splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _running_browser_processes() -> list[dict]:
    """Return info about running browser MAIN processes by scanning /proc for full cmdlines.
    Only returns ROOT browser processes — child/helper processes (renderers, GPU, snap wrappers)
    are excluded by checking that their parent is not also a browser process."""
    _CHILD_FLAGS = (b"--type=", b"-contentproc", b"crashpad", b"zygote",
                    b"--extension", b"--no-sandbox")
    # Known snap/flatpak wrapper binary suffixes that are not the real browser
    _WRAPPER_NAMES = (b"snap-confine", b"snapd", b"bwrap", b"snap.run")

    try:
        pids = [int(p) for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return []

    # First pass: collect all browser pids and their argv
    candidates: list[tuple[int, str, list[bytes]]] = []
    browser_pids: set[int] = set()
    for pid in pids:
        argv = _proc_argv(pid)
        if not argv:
            continue
        binary_b = argv[0]
        binary = binary_b.decode(errors="replace")
        # Filter obvious non-main processes by flags in argv
        if any(f in b" ".join(argv[1:]) for f in _CHILD_FLAGS):
            continue
        if any(w in binary_b for w in _WRAPPER_NAMES):
            continue
        browser_name = None
        if b"google-chrome" in binary_b or (binary.endswith("/chrome") and b"google" in binary_b.lower()):
            browser_name = "chrome"
        elif b"chromium" in binary_b:
            browser_name = "chromium"
        elif b"firefox" in binary_b and b"crashhelper" not in binary_b and b"plugincontainer" not in binary_b:
            browser_name = "firefox"
        elif b"brave" in binary_b:
            browser_name = "brave"
        if not browser_name:
            continue
        candidates.append((pid, browser_name, argv))
        browser_pids.add(pid)

    # Second pass: keep only processes whose parent is NOT a browser (i.e. root browser processes)
    browsers: list[dict] = []
    for pid, browser_name, argv in candidates:
        ppid = _proc_ppid(pid)
        if ppid is not None and ppid in browser_pids:
            continue  # child of another browser process
        cdp_port = None
        user_data_dir = None
        for arg in argv[1:]:
            s = arg.decode(errors="replace")
            if s.startswith("--remote-debugging-port="):
                try:
                    cdp_port = int(s.split("=", 1)[1])
                except ValueError:
                    pass
            elif s.startswith("--user-data-dir="):
                user_data_dir = s.split("=", 1)[1]
        browsers.append({
            "pid": str(pid), "browser": browser_name,
            "cdp_port": cdp_port, "user_data_dir": user_data_dir,
            "throwaway": user_data_dir is not None and user_data_dir.startswith("/tmp"),
        })
    return browsers


def _find_cookie_db(user_data_dir: str | None, browser_config_dir: str) -> str | None:
    """Locate the Cookies file for a Chromium-family browser profile dir."""
    candidates = []
    if user_data_dir:
        candidates += [
            os.path.join(user_data_dir, "Network", "Cookies"),
            os.path.join(user_data_dir, "Cookies"),
        ]
    cfg = os.path.expanduser(browser_config_dir)
    if os.path.isdir(cfg):
        for sub in ["Default", "Profile 1", "Profile 2"]:
            candidates += [
                os.path.join(cfg, sub, "Network", "Cookies"),
                os.path.join(cfg, sub, "Cookies"),
            ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def browser_sessions(services: list[str] | None = None) -> list[dict]:
    """Scan running browsers and installed browser profiles for active service sessions.

    Returns a list of entries, one per detected browser/profile combination, each with:
      - browser: 'chrome'|'chromium'|'firefox'|'brave'
      - profile: directory path
      - running: whether this browser is currently running
      - cdp_port: int or None (None = no CDP, running without debug port or not running)
      - throwaway: True if user_data_dir is in /tmp (no real session)
      - sessions: {service_name: bool} — which services are logged in
    """
    targets = services or list(_SERVICE_SENTINELS.keys())
    results: list[dict] = []
    seen_profiles: set[str] = set()

    # Running processes first
    running = _running_browser_processes()
    for proc in running:
        udd = proc.get("user_data_dir")
        # Find cookie db from the running process's user_data_dir
        db = None
        if udd and not proc["throwaway"]:
            db = _find_cookie_db(udd, "")
        sessions = _check_cookies_for_services(db, targets) if db else {s: False for s in targets}
        profile_key = udd or f"pid:{proc['pid']}"
        seen_profiles.add(profile_key)
        results.append({
            "browser": proc["browser"],
            "profile": udd,
            "running": True,
            "cdp_port": proc.get("cdp_port"),
            "throwaway": proc["throwaway"],
            "sessions": sessions,
        })

    # Also scan installed (not necessarily running) browser profiles
    for config_template, browser_name in _BROWSER_CONFIGS:
        config_dir = os.path.expanduser(config_template)
        if not os.path.isdir(config_dir):
            continue
        for profile_name in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
            profile_dir = os.path.join(config_dir, profile_name)
            if profile_dir in seen_profiles:
                continue
            db = _find_cookie_db(None, config_template) if profile_name == "Default" else None
            # Try exact profile dir
            for sub in ["Network/Cookies", "Cookies"]:
                candidate = os.path.join(profile_dir, *sub.split("/"))
                if os.path.isfile(candidate):
                    db = candidate
                    break
            if not db:
                continue
            seen_profiles.add(profile_dir)
            sessions = _check_cookies_for_services(db, targets)
            if not any(sessions.values()):
                continue  # skip profiles with no relevant sessions
            results.append({
                "browser": browser_name,
                "profile": profile_dir,
                "running": False,
                "cdp_port": None,
                "throwaway": False,
                "sessions": sessions,
            })

    return results
