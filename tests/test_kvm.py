# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import json

import urirun
from urirun import v2
from urirun_connector_kvm import capture, connector_manifest, key, main, move, urirun_bindings
import urirun_connector_kvm.core as core

ROUTE_KEY = "kvm://host/input/command/key"
ROUTE_MOVE = "kvm://host/input/command/move"
ROUTE_CAPTURE = "kvm://host/screen/query/capture"
ROUTES = {ROUTE_KEY, ROUTE_MOVE, ROUTE_CAPTURE}


def test_key_requires_value() -> None:
    assert key("")["ok"] is False


def test_run_tool_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr(core.shutil, "which", lambda _t: None)
    r = key("Return")
    # No backend tool on PATH -> _dispatch reports that none matched.
    assert r["ok"] is False and "no matching tool installed" in r["error"]


def test_bindings_are_isolated_handlers() -> None:
    b = urirun_bindings()["bindings"]
    assert set(b) == ROUTES
    binding = b[ROUTE_CAPTURE]
    # registry-portable in-process handler: runs out-of-process via urirun.exec
    assert binding["adapter"] == "local-function-subprocess"
    assert binding["python"]["module"] == "urirun_connector_kvm.core"
    assert binding["python"]["export"] == "capture"
    assert "argv" not in binding
    json.dumps(urirun_bindings())  # serializable: no live ref leaks


def test_runtime_executes_from_compiled_registry(monkeypatch) -> None:
    # the whole point: a serialized->compiled registry still runs the route end-to-end.
    # The route runs out-of-process (urirun.exec), so an in-process monkeypatch can't reach
    # it -- but env DOES propagate to the child. Clear PATH so the child's shutil.which finds
    # no screen tool and capture() fast-fails instead of touching (or hanging on) real hardware.
    monkeypatch.setenv("PATH", "")
    registry = urirun.compile_registry(json.loads(json.dumps(urirun_bindings())))
    env = v2.run(
        ROUTE_CAPTURE,
        registry,
        payload={"output": "/tmp/x.png"},
        mode="execute",
        policy=urirun.policy(allow=["kvm://*"]),
    )
    # Transport/plumbing succeeded (the compiled route ran); the action itself reports no
    # backend because no screen tool is on PATH.
    assert env["ok"] is True
    data = urirun.result_data(env)
    assert data["ok"] is False
    assert "no matching tool installed" in str(data.get("error", ""))


def test_manifest_prose_plus_derived_routes() -> None:
    m = connector_manifest()
    assert m["id"] == "kvm"
    assert set(m["routes"]) == ROUTES
    assert m["uriSchemes"] == ["kvm"]
    assert m["summary"]  # prose preserved


def test_cli_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    assert ROUTE_KEY in json.loads(capsys.readouterr().out)["bindings"]
    assert main(["manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "kvm"
