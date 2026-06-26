# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The control STRATEGIES the router (control.py) dispatches to — extracted into their own
# module so each control surface is a self-contained unit and the router stays a thin
# capability-ordered dispatcher. Each strategy declares ``available(app)`` against the LIVE
# environment, so the router fits the machine. Registered by control.py (one-way import:
# control -> strategies -> environment; no cycle).
import time

try:  # normal package import / flat deploy
    from . import backends as B
except ImportError:  # pragma: no cover
    import backends as B  # type: ignore

try:
    from . import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore

try:
    from . import environment as _env
except ImportError:  # pragma: no cover
    import environment as _env  # type: ignore


_CDP_PRIORITY = 95
_ATSPI_PRIORITY = 85
_VISION_PRIORITY = 50


def is_browser(app: str) -> bool:
    """An EMPTY app must NOT count as a browser: otherwise every ui/* call with no app probes
    CDP first (wasted round-trip on desktop targets, and a stray debug-Chrome on :9222 would
    silently hijack desktop control). CDP engages only when the caller names a browser."""
    a = (app or "").lower()
    return bool(a) and any(b in a for b in ("chrome", "chromium", "brave", "edge", "browser"))


# --------------------------------------------------------------------------- #
# 1) CDP — browser DOM, coordinate-free, role/name exact (confidence 0.95)
# --------------------------------------------------------------------------- #
class CdpStrategy:
    name = "cdp"
    priority = _CDP_PRIORITY
    confidence = _CDP_PRIORITY / 100

    def available(self, app: str) -> bool:
        return is_browser(app) and _cdp.reachable()

    def locate(self, t: dict) -> dict:
        return _cdp.find(t.get("text", ""), t.get("role", ""), t.get("name", ""))

    def click(self, t: dict) -> dict:
        return _cdp.act("click", t.get("text", ""), t.get("role", ""), t.get("name", ""))

    def fill(self, t: dict) -> dict:
        return _cdp.act("fill", t.get("text", ""), t.get("role", ""), t.get("name", ""),
                        value=t.get("value", ""))


# --------------------------------------------------------------------------- #
# 2) AT-SPI — native / Chrome-a11y accessibility tree, coordinate-free (0.85)
# --------------------------------------------------------------------------- #
class AtspiStrategy:
    name = "atspi"
    priority = _ATSPI_PRIORITY
    confidence = _ATSPI_PRIORITY / 100

    def available(self, app: str) -> bool:
        return _env.atspi_ready()

    def locate(self, t: dict) -> dict:
        return B.dispatch("locate", text=t.get("text") or t.get("name", ""),
                          role=t.get("role", ""), app=t.get("app", ""))

    def click(self, t: dict) -> dict:
        hit = self.locate(t)
        if hit.get("source") == "atspi" and hit.get("actionable"):
            return {"ok": True, "how": "atspi-action",
                    **B.dispatch("a11y", app=t.get("app", ""), role=t.get("role", ""),
                                 name=t.get("text") or t.get("name", ""), op="click")}
        raise B.BackendError("atspi: target not actionable")

    def fill(self, t: dict) -> dict:
        self.click(t)
        time.sleep(0.2)
        typed = B.dispatch("type", text=t.get("value", ""))
        return {"ok": True, "how": "atspi-fill", "typed": typed}


# --------------------------------------------------------------------------- #
# 3) vision — OCR locate + uinput-absolute click. Universal pixel fallback, but ONLY when
# the environment actually has OCR + a click backend (else it would always "fail to locate"
# and mask the real cause — missing tesseract / no /dev/uinput).
# --------------------------------------------------------------------------- #
class VisionStrategy:
    name = "vision"
    priority = _VISION_PRIORITY
    confidence = 0.6

    def available(self, app: str) -> bool:
        return bool(_env.profile()["controlStrategies"]["vision"])

    def locate(self, t: dict) -> dict:
        return B.dispatch("locate", text=t.get("text") or t.get("name", ""),
                          role=t.get("role", ""), app=t.get("app", ""))

    def _click_xy(self, hit: dict, button: str = "left", clicks: int = 1) -> dict:
        c = hit.get("center")
        if not (hit.get("found") and c):
            raise B.BackendError("vision: target not located")
        return {"ok": True, "how": "uinput-abs", "at": c,
                **B.uinput_abs_click(int(c[0]), int(c[1]), 0, 0, button=button,
                                     do_click=True, clicks=clicks)}

    def click(self, t: dict) -> dict:
        hit = self.locate(t)
        r = self._click_xy(hit)
        r["confidence"] = round(float(hit.get("matches", [{}])[0].get("conf", 0)) / 100, 2)
        return r

    def fill(self, t: dict) -> dict:
        hit = self.locate(t)
        focused = self._click_xy(hit)
        time.sleep(0.3)
        typed = B.dispatch("type", text=t.get("value", ""))
        return {"ok": True, "how": "vision-fill", "focused": focused, "typed": typed}


# the router registers these in capability order (highest priority first)
ALL = (CdpStrategy, AtspiStrategy, VisionStrategy)
