# Author: Tom Sapletta · Part of the ifURI solution.
from __future__ import annotations
from urirun_connector_kvm import readiness as R


def _sessions_authed():
    return [
        {"browser": "chrome", "profile": None, "running": True, "cdp_port": None,
         "throwaway": False, "sessions": {"linkedin": False}},
        {"browser": "chrome", "profile": "/tmp/urirun-kvm-cdp-9222", "running": True,
         "cdp_port": 9222, "throwaway": True, "sessions": {"linkedin": False}},
        {"browser": "chrome", "profile": "/home/tom/.config/google-chrome/Default",
         "running": False, "cdp_port": None, "throwaway": False, "sessions": {"linkedin": True}},
    ]


def test_forbids_throwaway_and_recommends_authed_profile():
    # The exact 2026-07-05 failure: authed Default profile exists, a throwaway debug Chrome
    # is running. Resolver must forbid throwaway and NOT be blindly ready.
    out = R.resolve("linkedin.post.publish", "linkedin", {
        "browser_sessions": _sessions_authed(),
        "cdp_reachable": True, "cdp_auth_known": False,
        "input_available": True, "window_list_degraded": True,
        "api_connector_available": False,
    })
    assert "browser-throwaway" in out["forbidden"]
    assert "/home/tom/.config/google-chrome/Default" in out["signals"]["authed_profiles"]
    # a throwaway Chrome is running alongside -> ambiguity + auth-unknown are hard blockers
    assert "multiple_chrome_windows" in out["blockers"]
    assert "auth_unknown_for_debug_profile" in out["blockers"]
    assert out["ready"] is False
    # blind HID must NOT be recommended under a focus hazard -> recommend the
    # actionable authed-profile path (relaunch with debug port) instead
    assert out["recommended_surface"] != "kvm-hid"
    assert out["recommended_surface"] == "browser-existing-auth"


def test_api_connector_wins_when_available():
    out = R.resolve("linkedin.post.publish", "linkedin", {
        "browser_sessions": [], "cdp_reachable": False, "cdp_auth_known": False,
        "input_available": True, "window_list_degraded": False,
        "api_connector_available": True,
    })
    assert out["recommended_surface"] == "api"
    assert out["ready"] is True


def test_clean_kvm_when_nothing_else_and_window_ok():
    out = R.resolve("desktop.click", "linkedin", {
        "browser_sessions": [], "cdp_reachable": False, "cdp_auth_known": False,
        "input_available": True, "window_list_degraded": False,
        "api_connector_available": False,
    })
    # no api, no authed browser, single/again no ambiguity -> kvm-hid is the honest last resort
    assert out["recommended_surface"] == "kvm-hid"


def test_vision_surface_available_on_wayland():
    # The Wayland answer: window enumeration is degraded, but VISION grounding (capture->vql->
    # click) needs no window list, so it is available and beats blind kvm-hid.
    out = R.resolve("desktop.click", "desktop", {
        "browser_sessions": [], "cdp_reachable": False, "cdp_auth_known": False,
        "input_available": True, "window_list_degraded": True,   # Wayland: no window list
        "vision_available": True, "api_connector_available": False,
    })
    assert out["recommended_surface"] == "kvm-vision"
    assert out["ready"] is True
