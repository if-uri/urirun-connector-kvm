# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Live ENVIRONMENT capability profile — what UI control ACTUALLY works in THIS session, so
# the router fits the machine instead of guessing, and the diagnostics layer recommends only
# remediation the environment can support (no "use CDP" where Chrome can't, no "OCR" where
# tesseract is absent). Pure detection; cheap; no side effects. Exposed as a URI:
#     kvm://<host>/env/query/profile
from __future__ import annotations

import shutil

try:  # normal package import / flat deploy
    from . import backends as B
except ImportError:  # pragma: no cover
    import backends as B  # type: ignore

try:
    from . import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore


def _safe(fn) -> bool:
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
    return prof
