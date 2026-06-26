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
import time
from typing import Any

try:  # normal package import / flat deploy
    from . import backends as B
except ImportError:  # pragma: no cover
    import backends as B  # type: ignore

try:
    from . import cdp as _cdp
except ImportError:  # pragma: no cover
    import cdp as _cdp  # type: ignore  # noqa: F401

try:
    from . import environment as _env
except ImportError:  # pragma: no cover
    import environment as _env  # type: ignore

try:  # the strategy classes live in their own module; the router just registers + dispatches
    from . import strategies as _strategies
except ImportError:  # pragma: no cover
    import strategies as _strategies  # type: ignore


# --------------------------------------------------------------------------- #
# strategy registry
# --------------------------------------------------------------------------- #
_STRATEGIES: list = []


def strategy(cls: type) -> type:
    _STRATEGIES.append(cls())
    _STRATEGIES.sort(key=lambda s: -s.priority)
    return cls


# register the extracted strategies in capability order (cdp > atspi > vision)
for _cls in _strategies.ALL:
    strategy(_cls)


# --------------------------------------------------------------------------- #
# strategy dispatch helpers
# --------------------------------------------------------------------------- #
def _try_locate_one(st: Any, target: dict, attempts: list) -> dict | None:
    """Try one locate strategy. Returns the hit dict if found, None to fall through."""
    try:
        hit = st.locate(target)
    except B.BackendError as exc:
        attempts.append({"strategy": st.name, "error": str(exc)})
        return None
    except Exception as exc:  # noqa: BLE001
        attempts.append({"strategy": st.name, "error": f"{type(exc).__name__}: {exc}"})
        return None
    if not hit.get("found"):
        attempts.append({"strategy": st.name, "found": False})
        return None
    return hit


def _try_act_one(st: Any, op: str, target: dict, verify: bool, value: str,
                 app: str, attempts: list) -> dict | None:
    """Try one click/fill strategy. Returns the result dict if ok, None to fall through."""
    try:
        res = st.click(target) if op == "click" else st.fill(target)
    except B.BackendError as exc:
        attempts.append({"strategy": st.name, "error": str(exc)})
        return None
    except Exception as exc:  # noqa: BLE001
        attempts.append({"strategy": st.name, "error": f"{type(exc).__name__}: {exc}"})
        return None
    if not res.get("ok"):
        return None
    if op == "fill" and verify and st.name == "vision":
        if not _verify_value(value, app):
            attempts.append({"strategy": st.name, "verify": False})
            return None
        res["verified"] = True
    return {"strategy": st.name, "attempts": attempts, **res}


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
        if op == "locate":
            hit = _try_locate_one(st, target, attempts)
            if hit is not None:
                return {"ok": True, "strategy": st.name,
                        "confidence": hit.get("confidence", getattr(st, "confidence", None)),
                        "attempts": attempts, **hit}
        else:
            result = _try_act_one(st, op, target, verify, value, app, attempts)
            if result is not None:
                return result
    return {"ok": False, "strategy": None, "attempts": attempts,
            "error": f"no control strategy could {op} target "
                     f"(text={text!r} role={role!r} name={name!r})"}


def _check_post_condition(expect: str, gone: bool, text: str, name: str, app: str) -> bool:
    """Verify that a post-condition holds after an act (present or gone)."""
    probe = route("locate", text=expect or text or name, app=app, cheap=True)
    present = bool(probe.get("ok"))
    return (not present) if gone else present


def act(op: str = "click", text: str = "", role: str = "", app: str = "", name: str = "",
        value: str = "", expect: str = "", gone: bool = False, retries: int = 2,
        settle: float = 0.6, safe: bool = True) -> dict[str, Any]:
    """Orchestrated perceive→act→verify→retry over ``route()`` — the closed loop the bare
    router lacks. Runs the op, waits ``settle``, then VERIFIES a post-condition and retries
    (escalating through the strategy chain again) until it holds or ``retries`` is spent:
      - ``expect``: this text/label must be present after the act (e.g. composer opened),
      - ``gone=True``: the target must be GONE after the act (e.g. a dialog dismissed).
    With neither, it cannot confirm an effect and returns ``verified: null`` (one-shot).
    ``safe=True`` (default) refuses irreversible labels (Post/Send/Publish/Buy/Delete…) so an
    autonomous caller must pass ``safe=false`` to fire them — the human-in-the-loop gate."""
    label = (text or name or "").strip().lower()
    if safe and op in ("click", "fill") and any(w in label for w in _IRREVERSIBLE):
        return {"ok": False, "blocked": "irreversible",
                "error": f"refusing to {op} {label!r} with safe=true (pass safe=false to allow)"}
    last = {}
    for attempt in range(int(retries) + 1):
        last = route(op, text=text, role=role, app=app, name=name, value=value, verify=False)
        last["attempt"] = attempt + 1
        if not last.get("ok"):
            time.sleep(float(settle))
            continue
        time.sleep(float(settle))
        if not (expect or gone):
            last["verified"] = None
            return last
        verified = _check_post_condition(expect, gone, text, name, app)
        last["verified"] = verified
        if verified:
            return last
        last["error"] = f"post-condition not met (expect={expect!r} gone={gone})"
    return {**last, "ok": False}


_IRREVERSIBLE = ("post", "publish", "opublikuj", "send", "wyślij", "buy", "kup", "pay",
                 "delete", "usuń", "remove", "submit", "confirm", "potwierdź")


def _verify_value(value: str, app: str) -> bool:
    if not value:
        return True
    probe = "".join(ch for ch in value[:24] if ord(ch) < 128).strip() or value[:24]  # noqa: PLR2004
    try:
        time.sleep(0.4)
        return bool(B.dispatch("locate", text=probe, app=app).get("found"))
    except Exception:  # noqa: BLE001
        return False


def report() -> dict:
    """Diagnostics: which control strategies exist + are available, alongside the live
    environment profile they fit (so a caller sees WHY a strategy is on/off)."""
    return {"strategies": [{"name": s.name, "priority": s.priority,
                            "available": _safe_avail(s)} for s in _STRATEGIES],
            "environment": _env.profile()}


def _safe_avail(s: Any) -> Any:
    try:
        return s.available("")
    except Exception as exc:  # noqa: BLE001
        return f"probe-error: {exc}"
