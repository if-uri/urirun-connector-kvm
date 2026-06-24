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
    "kvm://host/task/command/run", "kvm://host/window/command/focus",
    "kvm://host/window/query/list",
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
    assert m["uriSchemes"] == ["kvm"]
    assert m["summary"]


def test_cli_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    assert ROUTE_KEY in json.loads(capsys.readouterr().out)["bindings"]
    assert main(["manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "kvm"
