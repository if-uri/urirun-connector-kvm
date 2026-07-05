# Author: Tom Sapletta · Part of the ifURI solution.
"""Readiness kernel + surface resolver — the "resolve surface first, act last" gate.

The lesson from 2026-07-05: a runner that has a logged-in LinkedIn profile in
``browser_sessions`` still opened a throwaway debug Chrome, causing a window-focus
conflict and an auth failure. The root cause was PLANNING on assumptions instead of
resolving the observed environment first.

This module answers, BEFORE any input is sent, a single deterministic question:
*on which surface may this task run, and is it safe?* It composes the signals that
already exist (``browser_sessions``, CDP reachability, window enumeration, running
processes) into a ranked, policy-gated decision — it never touches the screen.

Pure and dependency-free (takes signals as input); the connector route wires it to
the live introspection. Testable without a node.
"""
from __future__ import annotations

from typing import Any

# Preference order for execution surfaces (most reliable / least invasive first).
# Policy, not hard-coded per task: an official API beats driving an existing logged-in
# browser, which beats a throwaway, which beats blind HID.
SURFACE_RANK = ("api", "browser-existing-auth", "browser-cdp", "os-accessibility", "kvm-hid")

# Surfaces a plan may NEVER auto-select without an explicit allow — the exact mistake
# that broke the LinkedIn run.
FORBIDDEN_BY_DEFAULT = ("browser-throwaway", "cookie-copy-linux-keyring")


def _authed_profiles(browser_sessions: list[dict], service: str) -> list[dict]:
    """Installed/running browser profiles whose cookie DB shows ``service`` logged in."""
    out = []
    for b in browser_sessions or []:
        if (b.get("sessions") or {}).get(service) and b.get("profile") and not b.get("throwaway"):
            out.append(b)
    return out


def _chrome_window_ambiguity(browser_sessions: list[dict]) -> dict:
    """Detect the focus hazard: more than one running Chrome competing for keystrokes."""
    running_chrome = [b for b in (browser_sessions or [])
                      if b.get("running") and b.get("browser") in ("chrome", "chromium")]
    throwaway_running = [b for b in running_chrome if b.get("throwaway")]
    return {
        "running_chrome": len(running_chrome),
        "throwaway_running": len(throwaway_running),
        "ambiguous": len(running_chrome) > 1,
    }


def _rank_surfaces(service: str, signals: dict) -> list[dict]:
    """Build the ranked candidate list with availability + what each one still needs."""
    bs = signals.get("browser_sessions") or []
    authed = _authed_profiles(bs, service)
    cands: list[dict] = []

    cands.append({
        "surface": "api", "uri": f"{service}://post/command/publish",
        "available": bool(signals.get("api_connector_available")),
        "requires": [] if signals.get("api_connector_available")
        else [f"install/serve {service} connector", f"secret://keyring/{service}#token"],
    })
    cands.append({
        "surface": "browser-existing-auth",
        "uri": (f"browser://existing/{authed[0]['profile']}" if authed else "browser://existing"),
        "available": bool(authed) and bool(signals.get("cdp_reachable")),
        "requires": ([] if bool(authed) and signals.get("cdp_reachable")
                     else ([] if authed else [f"a browser profile logged in to {service}"])
                     + ([] if signals.get("cdp_reachable")
                        else ["relaunch that profile with --remote-debugging-port"])),
        "profile": authed[0]["profile"] if authed else None,
    })
    cands.append({
        "surface": "browser-cdp", "uri": "browser://cdp/reachable",
        "available": bool(signals.get("cdp_reachable")),
        # a reachable CDP with NO known auth is only the throwaway trap
        "requires": [] if signals.get("cdp_auth_known") else ["auth unknown for the CDP profile"],
    })
    # kvm-hid is only usable when we can CONFIRM which window has focus: an ambiguous set of
    # windows OR a degraded window list (can't even see Chrome) both make blind typing unsafe.
    hid_focus_ok = not signals.get("window_ambiguous") and not signals.get("window_list_degraded")
    hid_needs = []
    if signals.get("window_ambiguous"):
        hid_needs.append("unambiguous focused window")
    if signals.get("window_list_degraded"):
        hid_needs.append("working window enumeration (confirm focus owner)")
    cands.append({
        "surface": "kvm-hid", "uri": "kvm://host/input",
        "available": bool(signals.get("input_available")) and hid_focus_ok,
        "requires": hid_needs,
    })
    order = {name: i for i, name in enumerate(SURFACE_RANK)}
    cands.sort(key=lambda c: order.get(c["surface"], 99))
    return cands


def _collect_blockers(service: str, signals: dict, amb: dict) -> list[str]:
    blockers: list[str] = []
    if amb["ambiguous"]:
        blockers.append("multiple_chrome_windows")
    if amb["throwaway_running"]:
        blockers.append("throwaway_chrome_running")  # my leftover debug Chrome
    if signals.get("window_list_degraded"):
        blockers.append("window_enumeration_degraded")  # atspi can't see Chrome windows
    if signals.get("cdp_reachable") and not signals.get("cdp_auth_known"):
        blockers.append("auth_unknown_for_debug_profile")
    if signals.get("user_active"):
        blockers.append("user_active")
    return blockers


def resolve(task: str, service: str, signals: dict) -> dict[str, Any]:
    """Resolve the execution surface for a task and gate readiness.

    ``signals`` (gathered live by the route): ``browser_sessions`` list,
    ``cdp_reachable``/``cdp_auth_known``, ``input_available``, ``window_list_degraded``,
    ``api_connector_available``, ``user_active``. Returns a ready:// decision:
    ``ready``, ``blockers``, ``recommended_surface``, ``forbidden``, ranked ``surfaces``.
    """
    amb = _chrome_window_ambiguity(signals.get("browser_sessions") or [])
    signals = {**signals, "window_ambiguous": amb["ambiguous"]}
    surfaces = _rank_surfaces(service, signals)
    blockers = _collect_blockers(service, signals, amb)

    # The recommendation is the highest-ranked AVAILABLE surface; if none is available,
    # recommend the highest-ranked one and surface exactly what it still requires — so the
    # answer is actionable, not just "no".
    available = [s for s in surfaces if s["available"]]
    hard_blockers = [b for b in blockers if b not in ("user_active",)]  # user_active is advisory

    # Recommendation: the highest-ranked AVAILABLE surface. When nothing is cleanly available,
    # DON'T fall back to blind kvm-hid — recommend the highest-ranked surface that is actually
    # actionable (an authed profile to relaunch, or an API path), surfacing what it needs, so
    # the answer is "log in via debug-port / use the API", never "type blindly and hope".
    if available:
        recommended = available[0]
    else:
        actionable = [s for s in surfaces
                      if s["surface"] != "kvm-hid" and (s.get("profile") or s.get("requires"))]
        recommended = actionable[0] if actionable else surfaces[0]
    ready = bool(available) and not hard_blockers

    return {
        "task": task, "service": service,
        "ready": ready,
        "blockers": blockers,
        "recommended_surface": recommended["surface"],
        "recommended_uri": recommended.get("uri"),
        "recommended_requires": recommended.get("requires") or [],
        "forbidden": list(FORBIDDEN_BY_DEFAULT),
        "surfaces": surfaces,
        "signals": {
            "authed_profiles": [b.get("profile") for b in _authed_profiles(
                signals.get("browser_sessions") or [], service)],
            "chrome_windows": amb,
            "cdp_reachable": bool(signals.get("cdp_reachable")),
            "window_list_degraded": bool(signals.get("window_list_degraded")),
            "window_backend": signals.get("window_backend"),
        },
    }
