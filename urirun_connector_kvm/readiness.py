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
# browser; vision grounding (capture -> analyse -> click) beats BLIND HID because it aims at a
# pixel it can see rather than guessing — and, crucially, it needs no window enumeration, so it
# is the safe desktop path on GNOME-Wayland where window listing is OS-blocked.
SURFACE_RANK = ("api", "browser-existing-auth", "browser-cdp", "os-accessibility",
                "kvm-vision", "kvm-hid")

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


def _browser_auth_cand(service: str, authed: list[dict], signals: dict) -> dict:
    ok = bool(authed) and bool(signals.get("cdp_reachable"))
    needs = ([] if authed else [f"a browser profile logged in to {service}"]) + (
        [] if signals.get("cdp_reachable") else ["relaunch that profile with --remote-debugging-port"])
    return {"surface": "browser-existing-auth",
            "uri": f"browser://existing/{authed[0]['profile']}" if authed else "browser://existing",
            "available": ok, "requires": [] if ok else needs,
            "profile": authed[0]["profile"] if authed else None}


# Tasks that a desktop surface (vision/HID) can actually accomplish: driving THIS machine.
# A named external service (linkedin, gmail, slack) is NOT one of them — clicking a desktop
# pixel does not publish to LinkedIn; those need an API or an authenticated browser. So the
# desktop surfaces are only offered for a desktop-class task.
_DESKTOP_SERVICES = ("", "desktop", "host", "screen")


def _hid_cand(signals: dict, desktop_task: bool) -> dict:
    # kvm-hid needs a CONFIRMED focus owner: ambiguous windows OR a degraded window list
    # (can't even see the app) both make blind typing unsafe. And only for a desktop task.
    needs = []
    if not desktop_task:
        needs.append("a desktop task (HID cannot fulfil a named service)")
    if signals.get("window_ambiguous"):
        needs.append("unambiguous focused window")
    if signals.get("window_list_degraded"):
        needs.append("working window enumeration (confirm focus owner)")
    return {"surface": "kvm-hid", "uri": "kvm://host/input",
            "available": bool(signals.get("input_available")) and not needs, "requires": needs}


def _rank_surfaces(service: str, signals: dict) -> list[dict]:
    """Build the ranked candidate list with availability + what each one still needs."""
    authed = _authed_profiles(signals.get("browser_sessions") or [], service)
    api_ok = bool(signals.get("api_connector_available"))
    desktop_task = service in _DESKTOP_SERVICES
    vision_ok = bool(signals.get("vision_available")) and desktop_task
    cands = [
        {"surface": "api", "uri": f"{service}://post/command/publish", "available": api_ok,
         "requires": [] if api_ok else [f"install/serve {service} connector",
                                        f"secret://keyring/{service}#token"]},
        _browser_auth_cand(service, authed, signals),
        {"surface": "browser-cdp", "uri": "browser://cdp/reachable",
         "available": bool(signals.get("cdp_reachable")),
         "requires": [] if signals.get("cdp_auth_known") else ["auth unknown for the CDP profile"]},
        # kvm-vision: capture -> analyse (vql) -> click a pixel it can SEE. No window list needed,
        # so it is the honest desktop path on GNOME-Wayland and safer than blind HID.
        {"surface": "kvm-vision", "uri": "vql://host/image/query/regions", "available": vision_ok,
         "requires": [] if vision_ok else ["screen capture + a vision analyser (vql) + input"]},
        _hid_cand(signals, desktop_task),
    ]
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


def _hard_blockers(blockers: list[str], surfaces: list[dict]) -> list[str]:
    """Blockers that actually prevent readiness. ``user_active`` is advisory. And
    ``window_enumeration_degraded`` only blocks WINDOW-based grounding — if a surface that
    needs no window list (api / kvm-vision / an authed browser) is available, it is advisory,
    because vision grounds by pixels, not the window manager."""
    non_window = any(s["available"] and s["surface"] != "kvm-hid" for s in surfaces)
    advisory = {"user_active"}
    if non_window:
        advisory.add("window_enumeration_degraded")
    return [b for b in blockers if b not in advisory]


def _recommend(surfaces: list[dict]) -> dict:
    """Highest-ranked AVAILABLE surface; else the highest-ranked ACTIONABLE one (an authed
    profile to relaunch / an API to install) — never blind kvm-hid as a fallback."""
    available = [s for s in surfaces if s["available"]]
    if available:
        return available[0]
    actionable = [s for s in surfaces
                  if s["surface"] != "kvm-hid" and (s.get("profile") or s.get("requires"))]
    return actionable[0] if actionable else surfaces[0]


def resolve(task: str, service: str, signals: dict) -> dict[str, Any]:
    """Resolve the execution surface for a task and gate readiness.

    ``signals`` (gathered live by the route): ``browser_sessions`` list,
    ``cdp_reachable``/``cdp_auth_known``, ``input_available``, ``window_list_degraded``,
    ``vision_available``, ``api_connector_available``, ``user_active``. Returns a ready://
    decision: ``ready``, ``blockers``, ``recommended_surface``, ``forbidden``, ranked ``surfaces``.
    """
    amb = _chrome_window_ambiguity(signals.get("browser_sessions") or [])
    signals = {**signals, "window_ambiguous": amb["ambiguous"]}
    surfaces = _rank_surfaces(service, signals)
    blockers = _collect_blockers(service, signals, amb)
    recommended = _recommend(surfaces)
    ready = any(s["available"] for s in surfaces) and not _hard_blockers(blockers, surfaces)

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
