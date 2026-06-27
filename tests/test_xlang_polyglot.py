# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Polyglot jako EGZEKWOWANY niezmiennik — ta sama brama pytest co test_contract_composition.

Te trzy testy uruchamiają dowody z xlang/ przez subprocess i podnoszą ich werdykt do poziomu
pytest, więc `URIRUN_CONTRACT_CHECK=1 pytest` egzekwuje je tak samo jak kompozycję kontraktów.
ci/contract_ci.sh woła te same skrypty wprost (czytelne logi macierzy); tu jest parytet dla
dewelopera w jego zwykłym przebiegu pytest.

Aktywne pod URIRUN_CONTRACT_CHECK=1 (dyscyplina „validate on w CI"); pomijane bez node/go.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

CONTRACT_CHECK = os.environ.get("URIRUN_CONTRACT_CHECK") == "1"
HAVE_NODE = shutil.which("node") is not None
HAVE_GO = shutil.which("go") is not None

pytestmark = [
    pytest.mark.skipif(not CONTRACT_CHECK, reason="set URIRUN_CONTRACT_CHECK=1"),
    pytest.mark.skipif(not (HAVE_NODE and HAVE_GO), reason="dowód polyglota wymaga node i go"),
]

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLANG = os.path.join(REPO, "xlang")


def _toolkit_dir() -> str:
    """Katalog z urirun_connectors_toolkit na PYTHONPATH dla podprocesów — niezależnie od
    tego, czy toolkit jest pip-installed, czy tylko na dysku dev."""
    try:
        import urirun_connectors_toolkit as t
        return os.path.dirname(os.path.dirname(os.path.abspath(t.__file__)))
    except Exception:
        return os.environ.get("URIRUN_TOOLKIT", "")


def _run(script: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    tk = _toolkit_dir()
    if tk:
        env["URIRUN_TOOLKIT"] = tk
    return subprocess.run(["bash", os.path.join(XLANG, script)],
                          capture_output=True, text=True, env=env)


def _assert_ok(res: subprocess.CompletedProcess) -> None:
    combined = res.stdout + res.stderr
    assert res.returncode == 0, combined
    assert res.stdout.startswith("SKIP") is False  # node/go są (skipif wyżej), więc musi realnie przejść
    assert "OK:" in res.stdout, combined
    assert "BŁĄD" not in res.stdout and "!!" not in res.stdout, combined


def test_roundtrip_matrix():
    """run.sh: jeden neutralny contracts.json, 3×3 macierz wymiany, drift odrzucany symetrycznie."""
    _assert_ok(_run("run.sh"))


def test_external_conformance_driver():
    """driver.sh: strona trzecia waliduje WYJŚCIE każdego węzła po transporcie; kłamstwo złapane."""
    _assert_ok(_run("driver.sh"))


def test_transport_invariance():
    """transport_swap.sh: ten sam węzeł × stdio vs HTTP → identyczna, zgodna koperta."""
    _assert_ok(_run("transport_swap.sh"))
