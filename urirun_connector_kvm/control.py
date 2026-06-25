# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Universal CONTROL-TOOL ROUTER for kvm://ui/*.
#
# A high-level UI action (find / click / fill / wait by text|role|name) is routed to the
# best available control STRATEGY, in capability order — so the same `ui/*` URI works
# whatever the target is, and degrades gracefully instead of guessing:
#
#   1. cdp     — browser DOM via the Chrome DevTools Protocol. Finds elements by
#                role / accessible-name / visible-text and ACTS through the DOM
#                (el.click(), focus + insertText). Coordinate-free and role-exact, so it
#                is immune to the OCR problems (dark-theme misreads, "Post" matching a
#                label not the button). Available when a CDP endpoint is reachable
#                (Chrome launched with --remote-debugging-port). confidence=0.95.
#   2. atspi   — AT-SPI accessibility tree (native apps, or Chrome with a11y on).
#                Coordinate-free element actions. Delegated to the `a11y`/`locate`
#                backends. confidence=0.85.
#   3. vision  — OCR (tesseract/easyocr) locate + uinput-absolute click. Universal
#                last resort; pixel-grounded but has no role concept. confidence per OCR.
#
# Each strategy reports `strategy` + `confidence` so callers know HOW a target was hit.
from __future__ import annotations

import json as _json
import os
import time
from typing import Any

try:  # normal package import / flat deploy
    from . import backends as B
except ImportError:  # pragma: no cover
    import backends as B  # type: ignore

try:
    from . import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore


# --------------------------------------------------------------------------- #
# strategy registry
# --------------------------------------------------------------------------- #
_STRATEGIES: list = []


def strategy(cls):
    _STRATEGIES.append(cls())
    _STRATEGIES.sort(key=lambda s: -s.priority)
    return cls


def _is_browser(app: str) -> bool:
    a = (app or "").lower()
    return (not a) or any(b in a for b in ("chrome", "chromium", "brave", "edge", "browser"))


# --------------------------------------------------------------------------- #
# 1) CDP — browser DOM, coordinate-free, role/name exact
# --------------------------------------------------------------------------- #
@strategy
class CdpStrategy:
    name = "cdp"
    priority = 95
    confidence = 0.95

    def available(self, app: str) -> bool:
        return _is_browser(app) and _cdp.reachable()

    def locate(self, t: dict) -> dict:
        return _cdp.find(t.get("text", ""), t.get("role", ""), t.get("name", ""))

    def click(self, t: dict) -> dict:
        return _cdp.act("click", t.get("text", ""), t.get("role", ""), t.get("name", ""))

    def fill(self, t: dict) -> dict:
        return _cdp.act("fill", t.get("text", ""), t.get("role", ""), t.get("name", ""),
                        value=t.get("value", ""))


# --------------------------------------------------------------------------- #
# 2) AT-SPI — native / Chrome-a11y accessibility tree (coordinate-free)
# --------------------------------------------------------------------------- #
@strategy
class AtspiStrategy:
    name = "atspi"
    priority = 85
    confidence = 0.85

    def available(self, app: str) -> bool:
        # only worth trying when the locate registry actually has an a11y backend that
        # produces ACTIONABLE hits (Chrome a11y on / native apps). Cheap probe via locate.
        try:
            hit = B.dispatch("locate", text="", role="", app=app)
            return bool(hit.get("source") == "atspi")
        except Exception:  # noqa: BLE001
            return False

    def locate(self, t: dict) -> dict:
        hit = B.dispatch("locate", text=t.get("text") or t.get("name", ""),
                         role=t.get("role", ""), app=t.get("app", ""))
        return hit

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
# 3) vision — OCR locate + uinput-absolute click (universal pixel fallback)
# --------------------------------------------------------------------------- #
@strategy
class VisionStrategy:
    name = "vision"
    priority = 50

    def available(self, app: str) -> bool:
        return True  # always available as the last resort

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


# --------------------------------------------------------------------------- #
# the router
# --------------------------------------------------------------------------- #
def route(op: str, text: str = "", role: str = "", app: str = "", name: str = "",
          value: str = "", verify: bool = True, cheap: bool = False) -> dict[str, Any]:
    """Route a UI ``op`` (locate|click|fill) to the best available control strategy and
    return ``{ok, strategy, ...}``. Tries strategies highest-confidence-first; on a
    strategy error or a 'not found' it falls through to the next, recording attempts.
    ``cheap=True`` skips the vision (OCR) strategy — used by polling waits so a single
    poll stays fast (DOM/a11y presence checks only) and can't blow the node's exec cap."""
    target = {"text": text, "role": role, "app": app, "name": name, "value": value}
    if op != "locate" and not (text or name or role):
        return {"ok": False, "error": "a target (text/name/role) is required"}
    attempts = []
    for st in _STRATEGIES:
        if cheap and st.name == "vision":
            attempts.append({"strategy": st.name, "skipped": "cheap-mode"})
            continue
        try:
            if not st.available(app):
                attempts.append({"strategy": st.name, "skipped": "unavailable"})
                continue
        except Exception as exc:  # noqa: BLE001
            attempts.append({"strategy": st.name, "skipped": f"probe-error: {exc}"})
            continue
        try:
            if op == "locate":
                hit = st.locate(target)
                if hit.get("found"):
                    return {"ok": True, "strategy": st.name, "attempts": attempts, **hit}
                attempts.append({"strategy": st.name, "found": False})
                continue
            res = st.click(target) if op == "click" else st.fill(target)
            if res.get("ok"):
                res = {"strategy": st.name, "attempts": attempts, **res}
                if op == "fill" and verify and st.name == "vision":
                    res["verified"] = _verify_value(value, app)
                    if not res["verified"]:
                        attempts.append({"strategy": st.name, "verify": False})
                        continue   # typed into the wrong place — let no other strategy lie; report below
                return res
        except B.BackendError as exc:
            attempts.append({"strategy": st.name, "error": str(exc)})
            continue
        except Exception as exc:  # noqa: BLE001
            attempts.append({"strategy": st.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
    return {"ok": False, "strategy": None, "attempts": attempts,
            "error": f"no control strategy could {op} target "
                     f"(text={text!r} role={role!r} name={name!r})"}


def _verify_value(value: str, app: str) -> bool:
    if not value:
        return True
    probe = "".join(ch for ch in value[:24] if ord(ch) < 128).strip() or value[:24]
    try:
        time.sleep(0.4)
        return bool(B.dispatch("locate", text=probe, app=app).get("found"))
    except Exception:  # noqa: BLE001
        return False


def report() -> dict:
    """Diagnostics: which control strategies exist and are available right now."""
    return {"strategies": [{"name": s.name, "priority": s.priority,
                            "available": _safe_avail(s)} for s in _STRATEGIES]}


def _safe_avail(s) -> Any:
    try:
        return s.available("")
    except Exception as exc:  # noqa: BLE001
        return f"probe-error: {exc}"
