# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Brama dla wielu scenariuszy kontraktów (urirun-contract-*) z wieloma URI.

Uruchamia examples/contract_scenarios.py (in-process, przez nowy pakiet urirun_contract) i podnosi
jego werdykt do pytest. Pomija się czysto, gdy brak siostrzanych pakietów scenariuszy albo samego
pakietu urirun_contract (np. instalacja samego connectora bez monorepo).
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys

import pytest

CONTRACT_CHECK = os.environ.get("URIRUN_CONTRACT_CHECK") == "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IFURI = os.path.dirname(REPO)
RUNNER = os.path.join(REPO, "examples", "contract_scenarios.py")

_have_scenarios = bool(glob.glob(os.path.join(IFURI, "urirun-contract-*", "contracts.json")))
_have_gate = os.path.isdir(os.path.join(IFURI, "urirun-contract", "urirun_contract"))

pytestmark = [
    pytest.mark.skipif(not CONTRACT_CHECK, reason="set URIRUN_CONTRACT_CHECK=1"),
    pytest.mark.skipif(not (_have_scenarios and _have_gate),
                       reason="wymaga siostrzanych urirun-contract-* i pakietu urirun-contract"),
]


def test_all_scenarios_many_uris():
    res = subprocess.run([sys.executable, RUNNER], capture_output=True, text=True)
    combined = res.stdout + res.stderr
    assert res.returncode == 0, combined
    assert "OK:" in res.stdout, combined
    assert "BŁĄD" not in res.stdout, combined
    # potwierdź, że realnie pokryto wiele scenariuszy i wiele URI (nie pusty przebieg)
    assert "scenariuszy," in res.stdout and "URI," in res.stdout, combined
