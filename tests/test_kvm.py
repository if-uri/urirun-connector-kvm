# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import json

import urirun
from urirun import v2
from urirun_connector_kvm import (
    capture,
    connector_manifest,
    doctor,
    key,
    main,
    type_text,
    urirun_bindings,
)
import urirun_connector_kvm.backends as B
import urirun_connector_kvm.core as core

ROUTE_KEY = "kvm://host/input/command/key"
ROUTE_MOVE = "kvm://host/input/command/move"
ROUTE_CAPTURE = "kvm://host/screen/query/capture"
ROUTE_TYPE = "kvm://host/input/command/type"
ROUTE_DOCTOR = "kvm://host/doctor/query/report"
EXPECTED_ROUTES = {
    ROUTE_KEY, ROUTE_MOVE, ROUTE_CAPTURE, ROUTE_TYPE, ROUTE_DOCTOR,
    "kvm://host/input/command/click", "kvm://host/input/command/scroll",
    "kvm://host/input/command/double-click", "kvm://host/input/command/triple-click",
    "kvm://host/input/command/right-click", "kvm://host/input/command/middle-click",
    "kvm://host/input/command/hover", "kvm://host/input/command/drag-and-drop",
    "kvm://host/input/command/wait", "kvm://host/proc/command/kill",
    "kvm://host/task/command/run", "kvm://host/window/command/focus",
    "kvm://host/window/command/close", "kvm://host/window/command/restore",
    "kvm://host/window/query/list", "kvm://host/a11y/command/act", "kvm://host/abs/command/click",
    "kvm://host/ui/query/locate", "kvm://host/ui/command/click-text",
    "kvm://host/ui/query/find", "kvm://host/ui/command/click", "kvm://host/ui/command/fill",
    "kvm://host/ui/query/wait", "kvm://host/ui/query/verify", "kvm://host/ui/query/strategies",
    "kvm://host/cdp/session/command/ensure", "kvm://host/cdp/session/query/status",
    "kvm://host/cdp/session/query/ready",
    "kvm://host/cdp/page/command/navigate", "kvm://host/cdp/page/query/ready",
    "kvm://host/ui/command/act", "kvm://host/env/query/profile", "kvm://host/surface/query/current", "kvm://host/display/query/info",
    "kvm://host/browser/query/sessions",
    "app://host/desktop/command/launch", "app://host/desktop/query/list",
}


def test_key_requires_value() -> None:
    assert key("")["ok"] is False


def test_type_requires_value() -> None:
    assert type_text("")["ok"] is False


def test_no_backend_reports_install_hint(monkeypatch) -> None:
    # With no tools/modules present, dispatch must fail cleanly with an install hint,
    # never raise — so a route stays usable to report what is missing.
    monkeypatch.setattr(B.shutil, "which", lambda _t: None)
    monkeypatch.setattr(B, "have_mod", lambda _m: False)
    r = key("Return")
    assert r["ok"] is False and "no available backend" in r["error"]


# --- decorator-registered backend registry -------------------------------- #
def test_backend_decorator_registers_and_sorts() -> None:
    calls = []

    @B.backend("unit_probe", "low", priority=10)
    def _low(**_):
        calls.append("low"); return {"hit": "low"}

    @B.backend("unit_probe", "high", priority=90)
    def _high(**_):
        calls.append("high"); return {"hit": "high"}

    # highest priority + available wins
    assert B.dispatch("unit_probe")["hit"] == "high"
    assert calls == ["high"]


def test_dispatch_falls_through_on_failure() -> None:
    @B.backend("unit_fall", "broken", priority=90)
    def _broken(**_):
        raise RuntimeError("boom")

    @B.backend("unit_fall", "works", priority=10)
    def _works(**_):
        return {"ok": True}

    out = B.dispatch("unit_fall")
    assert out["backend"] == "works"


def test_unavailable_backend_skipped_by_needs(monkeypatch) -> None:
    @B.backend("unit_need", "needs_ghost", priority=90, needs_bin=("definitely-not-a-real-binary",))
    def _ghost(**_):
        return {"hit": "ghost"}

    @B.backend("unit_need", "fallback", priority=10)
    def _fb(**_):
        return {"hit": "fallback"}

    assert B.dispatch("unit_need")["hit"] == "fallback"


def test_bindings_are_isolated_handlers() -> None:
    b = urirun_bindings()["bindings"]
    assert set(b) == EXPECTED_ROUTES
    binding = b[ROUTE_CAPTURE]
    assert binding["adapter"] == "local-function-subprocess"
    assert binding["python"]["module"] == "urirun_connector_kvm.core"
    assert binding["python"]["export"] == "capture"
    assert "argv" not in binding
    json.dumps(urirun_bindings())  # serializable: no live ref leaks


def test_runtime_executes_from_compiled_registry(monkeypatch) -> None:
    # A serialized->compiled registry still runs the route end-to-end. Runs out-of-process
    # (urirun.exec); env propagates, so clear PATH + force have_mod False in the child via
    # an env flag the backends module honours is overkill -- instead assert plumbing ok.
    monkeypatch.setenv("PATH", "")
    registry = urirun.compile_registry(json.loads(json.dumps(urirun_bindings())))
    env = v2.run(
        ROUTE_DOCTOR,
        registry,
        payload={},
        mode="execute",
        policy=urirun.policy(allow=["kvm://*"]),
    )
    assert env["ok"] is True
    data = urirun.result_data(env)
    assert data["ok"] is True and "backends" in data


def test_doctor_reports_backends() -> None:
    r = doctor()
    assert r["ok"] is True
    assert "capture" in r["backends"] and "type" in r["backends"]
    # every registered backend entry carries availability + install hints
    for entry in r["backends"]["capture"]:
        assert set(entry) >= {"name", "priority", "available", "missing"}


def test_capture_tags_screenshot_as_frozen_artifact(monkeypatch) -> None:
    monkeypatch.setattr(
        B, "dispatch",
        lambda action, **kw: {"backend": "stub", "via": "stub", "path": kw.get("output")},
    )
    monkeypatch.setattr(core.os.path, "getsize", lambda _p: 123)
    monkeypatch.setattr(core.os.path, "exists", lambda _p: True)
    r = capture(output="/tmp/x.png")
    assert r["ok"] is True and r["kind"] == "screenshot" and r["live"] is False


def test_manifest_prose_plus_derived_routes() -> None:
    m = connector_manifest()
    assert m["id"] == "kvm"
    assert set(m["routes"]) == EXPECTED_ROUTES
    assert m["uriSchemes"] == ["app", "kvm"]
    assert m["summary"]


def test_cli_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    assert ROUTE_KEY in json.loads(capsys.readouterr().out)["bindings"]
    assert main(["manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "kvm"


# --------------------------------------------------------------------------- #
# universal control-tool router
# --------------------------------------------------------------------------- #
import urirun_connector_kvm.control as C  # noqa: E402
import urirun_connector_kvm.cdp as cdp  # noqa: E402


def test_router_prefers_cdp_when_reachable(monkeypatch) -> None:
    monkeypatch.setattr(cdp, "reachable", lambda: True)
    monkeypatch.setattr(cdp, "act", lambda op, text="", role="", name="", value="":
                        {"ok": True, "found": True, "clicked": True, "via": "cdp", "role": role})
    r = C.route("click", text="Post", role="button", app="google-chrome")
    assert r["ok"] is True and r["strategy"] == "cdp" and r["clicked"] is True


def test_router_falls_through_cdp_to_vision(monkeypatch) -> None:
    # cdp reachable but the element is not in the DOM -> raises -> vision takes over
    monkeypatch.setattr(cdp, "reachable", lambda: True)
    def _boom(*a, **k):
        raise B.BackendError("cdp: element not found")
    monkeypatch.setattr(cdp, "act", _boom)
    monkeypatch.setattr(B, "dispatch", lambda action, **k:
                        {"source": "tesseract", "found": True, "center": [120, 240],
                         "matches": [{"conf": 88.0}]} if action == "locate" else {"via": "stub"})
    monkeypatch.setattr(B, "uinput_abs_click",
                        lambda x, y, *a, **k: {"via": "uinput-absolute", "pixel": [x, y]})
    r = C.route("click", text="Start a post", app="google-chrome")
    assert r["ok"] is True and r["strategy"] == "vision" and r["at"] == [120, 240]
    assert any(a.get("strategy") == "cdp" for a in r["attempts"])


def test_router_empty_target_is_error() -> None:
    r = C.route("click", text="", role="", name="")
    assert r["ok"] is False and "required" in r["error"]


def test_ui_act_retries_then_succeeds(monkeypatch) -> None:
    # orchestrator: page-ready probe + retry loop through the router until ok
    import urirun_connector_kvm.cdp as _cdp
    monkeypatch.setattr(_cdp, "reachable", lambda: True)
    monkeypatch.setattr(_cdp, "page_ready", lambda timeout=8.0: {"ok": True, "readyState": "complete"})
    calls = {"n": 0}
    def _route(op, **k):
        calls["n"] += 1
        if calls["n"] < 2:                       # first try misses, second wins
            return {"ok": False, "error": "not yet", "attempts": []}
        return {"ok": True, "strategy": "cdp", "clicked": True}
    monkeypatch.setattr(core.C, "route", _route)
    monkeypatch.setattr(core.time, "sleep", lambda *_a: None)
    r = core.ui_act(do="click", text="Compose", retries=3)
    assert r["ok"] is True and r["do"] == "click"
    assert len(r["tries"]) == 2 and r["tries"][-1]["ok"] is True


def test_ui_act_rejects_bad_verb() -> None:
    assert core.ui_act(do="frobnicate", text="x")["ok"] is False


# --------------------------------------------------------------------------- #
# Wayland/session detection + session env (the linux-x11 misreport fix)
# --------------------------------------------------------------------------- #
def test_is_wayland_detects_via_socket_when_env_absent(monkeypatch) -> None:
    # A node process spawned without graphical session vars must still detect Wayland
    # from the live compositor socket -- else the box mis-tags as linux-x11 and drops
    # grim/portal from the capture candidates.
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setattr(B, "_wayland_socket", lambda: "wayland-1")
    assert B.is_wayland() is True
    monkeypatch.setattr(B, "_wayland_socket", lambda: None)
    assert B.is_wayland() is False


def test_platform_tag_wayland_via_socket(monkeypatch) -> None:
    monkeypatch.setattr(B.sys, "platform", "linux")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setattr(B, "_wayland_socket", lambda: "wayland-0")
    assert B.platform_tag() == "linux-wayland"
    monkeypatch.setattr(B, "_wayland_socket", lambda: None)
    monkeypatch.setattr(B, "_x_display", lambda: None)
    assert B.platform_tag() == "linux-x11"


def test_session_env_fills_display_and_bus(monkeypatch, tmp_path) -> None:
    (tmp_path / "wayland-0").write_text("")
    (tmp_path / "bus").write_text("")
    monkeypatch.setattr(B, "_runtime_dir", lambda: str(tmp_path))
    monkeypatch.setattr(B, "_x_display", lambda: ":7")
    for v in ("WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "DISPLAY"):
        monkeypatch.delenv(v, raising=False)
    env = B.session_env()
    assert env["XDG_RUNTIME_DIR"] == str(tmp_path)
    assert env["WAYLAND_DISPLAY"] == "wayland-0"
    assert env["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={tmp_path}/bus"
    assert env["DISPLAY"] == ":7"


def test_session_env_preserves_existing_vars(monkeypatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-9")
    monkeypatch.setenv("DISPLAY", ":3")
    env = B.session_env()
    assert env["WAYLAND_DISPLAY"] == "wayland-9" and env["DISPLAY"] == ":3"


# --------------------------------------------------------------------------- #
# chrome launch: dedicated profile + debug port (the "debugger did not come up" fix)
# --------------------------------------------------------------------------- #
import urirun_connector_kvm.launch_backends as LB  # noqa: E402


def test_chrome_launch_injects_dedicated_profile_and_debug_port(monkeypatch) -> None:
    captured = {}

    class _Proc:
        pid = 4321

    monkeypatch.setattr(LB, "_find_app", lambda app: None)
    monkeypatch.setattr(LB.shutil, "which", lambda b: "/usr/bin/google-chrome" if "chrome" in b else None)
    monkeypatch.setattr(LB, "session_env", lambda: {})
    monkeypatch.setattr(LB, "_cdp_wait", lambda port, wait: {"ready": False, "port": port})
    monkeypatch.setattr(LB.subprocess, "Popen",
                        lambda argv, **kw: (captured.__setitem__("argv", argv), _Proc())[1])
    monkeypatch.delenv("URIRUN_KVM_NO_A11Y", raising=False)
    monkeypatch.delenv("URIRUN_KVM_CDP_PROFILE", raising=False)
    monkeypatch.delenv("URIRUN_KVM_CDP_ON_LAUNCH", raising=False)

    # debug=True OPTS IN to the CDP surface: a dedicated --user-data-dir is required for the
    # debug port to bind (Chrome 136+ blocks it on the default profile, and a bare port is
    # swallowed by a running default-profile chrome).
    res = LB._launch_xdg(app="google-chrome", settle=0, debug=True)
    argv = captured["argv"]
    assert any(a.startswith("--remote-debugging-port=") for a in argv)
    assert any(a.startswith("--user-data-dir=") for a in argv)
    assert "--no-first-run" in argv and "--no-default-browser-check" in argv
    assert res["cdp"]["ready"] is False   # readiness is probed + reported, not assumed


def test_chrome_launch_default_keeps_real_profile(monkeypatch) -> None:
    # Without debug, launch must NOT force a dedicated profile — that would open an
    # UNAUTHENTICATED chrome and break logged-in OCR workflows (e.g. a LinkedIn post).
    captured = {}

    class _Proc:
        pid = 99

    monkeypatch.setattr(LB, "_find_app", lambda app: None)
    monkeypatch.setattr(LB.shutil, "which", lambda b: "/usr/bin/google-chrome" if "chrome" in b else None)
    monkeypatch.setattr(LB, "session_env", lambda: {})
    monkeypatch.setattr(LB.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(LB.subprocess, "Popen",
                        lambda argv, **kw: (captured.__setitem__("argv", argv), _Proc())[1])
    monkeypatch.delenv("URIRUN_KVM_NO_A11Y", raising=False)
    monkeypatch.delenv("URIRUN_KVM_CDP_ON_LAUNCH", raising=False)

    res = LB._launch_xdg(app="google-chrome", args=["https://www.linkedin.com"], settle=0)
    argv = captured["argv"]
    assert not any("user-data-dir" in a for a in argv)      # real (logged-in) profile preserved
    assert not any("remote-debugging-port" in a for a in argv)
    assert "--force-renderer-accessibility" in argv          # a11y/OCR help is still applied
    assert "cdp" not in res                                   # no CDP readiness probe


def test_non_chrome_launch_skips_cdp(monkeypatch) -> None:
    captured = {}

    class _Proc:
        pid = 11

    monkeypatch.setattr(LB, "_find_app", lambda app: None)
    monkeypatch.setattr(LB.shutil, "which", lambda b: "/usr/bin/gedit")
    monkeypatch.setattr(LB, "session_env", lambda: {})
    monkeypatch.setattr(LB.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(LB.subprocess, "Popen",
                        lambda argv, **kw: (captured.__setitem__("argv", argv), _Proc())[1])

    res = LB._launch_xdg(app="gedit", settle=0)
    assert not any("remote-debugging-port" in a for a in captured["argv"])
    assert "cdp" not in res


# --------------------------------------------------------------------------- #
# environment-adapted routing (vision is gated on real OCR + input capability)
# --------------------------------------------------------------------------- #
import urirun_connector_kvm.strategies as S  # noqa: E402
import urirun_connector_kvm.environment as E  # noqa: E402


def test_vision_strategy_is_environment_gated(monkeypatch) -> None:
    monkeypatch.setattr(E, "profile", lambda: {"controlStrategies": {"vision": False}})
    assert S.VisionStrategy().available("") is False        # no tesseract / no uinput -> off
    monkeypatch.setattr(E, "profile", lambda: {"controlStrategies": {"vision": True}})
    assert S.VisionStrategy().available("") is True


def test_environment_profile_shape() -> None:
    p = E.profile()
    assert set(p) >= {"platform", "display", "cdp", "ocr", "input", "controlStrategies", "best", "controllable"}
    assert set(p["controlStrategies"]) == {"cdp", "atspi", "vision"}
    assert p["best"] in (None, "cdp", "atspi", "vision")
    assert p["controllable"] is (p["best"] is not None)
    # actionMatrix must be present and structurally complete
    assert "actionMatrix" in p
    m = p["actionMatrix"]
    assert set(m) == {"cdp", "atspi", "uinput", "vision"}
    ACTIONS = {"locate", "click", "type", "navigate", "screenshot"}
    VALID = {"executable", "degraded", "not_executable", "not_applicable", "blocked"}
    for surface, row in m.items():
        assert set(row) == ACTIONS, f"{surface} missing actions"
        for a, v in row.items():
            assert v in VALID, f"{surface}.{a}={v!r} not a valid executability value"


def test_action_matrix_wayland_type_rule() -> None:
    """On Wayland, atspi and uinput CANNOT type — this is a hard platform rule, not detection."""
    wayland_prof = {
        "wayland": True, "controlStrategies": {"cdp": True, "atspi": True, "vision": False},
        "input": {"uinput": True, "ydotool": False, "xdotool": False},
        "ocr": {"tesseract": True, "easyocr": False},
        "osLevelReliable": False,
    }
    m = E.action_matrix(wayland_prof)
    assert m["cdp"]["type"] == "executable",      "CDP must be able to type"
    assert m["atspi"]["type"] == "not_executable", "atspi cannot type on Wayland (compositor focus)"
    assert m["uinput"]["type"] == "not_executable","uinput cannot type on Wayland (compositor focus)"


def test_action_matrix_wayland_screenshot_blocked() -> None:
    """On Wayland with osLevelReliable=False, OS-level screenshot is blocked."""
    prof = {
        "wayland": True, "controlStrategies": {"cdp": False, "atspi": False, "vision": True},
        "input": {"uinput": True, "ydotool": False, "xdotool": False},
        "ocr": {"tesseract": True, "easyocr": False},
        "osLevelReliable": False,
    }
    m = E.action_matrix(prof)
    assert m["uinput"]["screenshot"] == "blocked"
    assert m["vision"]["screenshot"] == "blocked"


def test_action_matrix_x11_type_degraded_not_blocked() -> None:
    """On X11 (not Wayland), atspi type is degraded (works but unreliably) not blocked."""
    x11_prof = {
        "wayland": False, "controlStrategies": {"cdp": False, "atspi": True, "vision": False},
        "input": {"uinput": True, "ydotool": False, "xdotool": False},
        "ocr": {"tesseract": False, "easyocr": False},
        "osLevelReliable": True,
    }
    m = E.action_matrix(x11_prof)
    assert m["atspi"]["type"] == "degraded",  "X11 atspi type should be degraded, not blocked"
    assert m["uinput"]["type"] == "degraded", "X11 uinput type should be degraded, not blocked"


def test_report_includes_environment() -> None:
    import urirun_connector_kvm.control as Ctl
    rep = Ctl.report()
    assert "environment" in rep and "strategies" in rep
    assert {s["name"] for s in rep["strategies"]} == {"cdp", "atspi", "vision"}


def test_cdp_port_prefers_client_url(monkeypatch) -> None:
    # launch must bind the port the cdp client/readiness poll use (URIRUN_KVM_CDP_URL),
    # not a divergent URIRUN_KVM_CDP_PORT — else Chrome binds a port nothing watches.
    monkeypatch.setenv("URIRUN_KVM_CDP_URL", "http://127.0.0.1:9222")
    monkeypatch.setenv("URIRUN_KVM_CDP_PORT", "9333")
    assert LB._cdp_port() == "9222"
    monkeypatch.delenv("URIRUN_KVM_CDP_URL", raising=False)
    assert LB._cdp_port() == "9333"
    monkeypatch.delenv("URIRUN_KVM_CDP_PORT", raising=False)
    assert LB._cdp_port() == "9222"


# --------------------------------------------------------------------------- #
# Phase 0: envelope-collision regression (inner result with ok/error/url spread
# into urirun.ok/fail used to raise TypeError and mask the real CDP result)
# --------------------------------------------------------------------------- #
def test_spread_strips_envelope_reserved_keys() -> None:
    assert core._spread({"ok": True, "error": "e", "connector": "k", "action": "a", "keep": 1}) == {"keep": 1}
    assert core._spread({"url": "u", "keep": 2}, "url") == {"keep": 2}
    assert core._spread(None) == {}


def test_cdp_navigate_has_no_url_collision(monkeypatch) -> None:
    class FakeCdp:
        @staticmethod
        def navigate(url):
            return {"ok": True, "url": url}            # 'url' would collide with the handler's url=
        @staticmethod
        def page_ready(timeout=8.0):
            return {"ok": True, "readyState": "complete"}
    monkeypatch.setattr(core, "_cdp_mod", lambda: FakeCdp)
    r = core.cdp_navigate(url="https://x")
    assert r["ok"] is True and r["url"] == "https://x"   # no TypeError; url present exactly once


# --------------------------------------------------------------------------- #
# CDP launch/probe split (cold-start must not blow the node handler exec cap)
# --------------------------------------------------------------------------- #
def test_cdp_start_session_reuses_without_spawn(monkeypatch) -> None:
    import subprocess
    monkeypatch.setattr(cdp, "reachable", lambda: True)
    spawned = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: spawned.append(a) or object())
    r = cdp.start_session(url="")
    assert r["reused"] is True and r["launching"] is False
    assert spawned == []                                  # reuse never spawns


def test_cdp_start_session_launches_and_returns_immediately(monkeypatch) -> None:
    import subprocess
    monkeypatch.setattr(cdp, "reachable", lambda: False)  # not up
    monkeypatch.setattr(cdp, "_find_chrome", lambda: "/usr/bin/google-chrome")
    monkeypatch.setattr(cdp.os, "makedirs", lambda *a, **k: None)

    class _P:
        pid = 555
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _P())
    r = cdp.start_session(url="https://example.com")
    # returns AT ONCE with launching:true — does NOT block polling for the bind
    assert r["ok"] is True and r["launching"] is True and r["reused"] is False and r["pid"] == 555


def test_cdp_await_ready_polls_without_spawn(monkeypatch) -> None:
    import subprocess, time as _t
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("await_ready must not spawn")))
    monkeypatch.setattr(_t, "sleep", lambda *_a: None)
    monkeypatch.setattr(cdp, "reachable", lambda: True)
    assert cdp.await_ready(timeout=1)["ready"] is True
    # times out cleanly when never reachable (bounded; no spawn)
    monkeypatch.setattr(cdp, "reachable", lambda: False)
    out = cdp.await_ready(timeout=0)
    assert out["ready"] is False and "timeout" in out["error"]


def test_ui_wait_success_has_no_found_collision(monkeypatch) -> None:
    # the route hit carries `found` -> _ok(found=True, **hit) used to raise
    # "_ok() got multiple values for keyword argument 'found'" on the SUCCESS path
    monkeypatch.setattr(core.C, "route",
                        lambda op, **k: {"ok": True, "found": True, "strategy": "cdp", "name": "X"})
    r = core.ui_wait(text="X", timeout=1)
    assert r["ok"] is True and r["found"] is True and r["waited"] is not None and r["strategy"] == "cdp"
