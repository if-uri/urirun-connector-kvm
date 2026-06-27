# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Warstwa kompozycji: czy DWA kontrakty różnych URI łączą się w poprawny pipeline.

Trzy sprawdzenia których konformans pojedynczej trasy nie obejmuje:
  1. każda zadeklarowana krawędź WIRES jest statycznie poprawna (typy + dostępność pola),
  2. po JSON round-trip (granica procesu) konsument umie zbudować i zwalidować swoje wejście,
  3. ZŁA krawędź jest ODRZUCANA — czyli check_wire ma zęby.

Aktywne pod URIRUN_CONTRACT_CHECK=1 (dyscyplina „validate on w CI").
"""
from __future__ import annotations

import json
import os

import pytest

from urirun_connector_kvm.contracts import CONTRACTS, WIRES, Wire
from urirun_connectors_toolkit.contract_gate import (
    check_wire,
    consumer_input_check,
    find_wire,
    wire_payload,
)

CONTRACT_CHECK = os.environ.get("URIRUN_CONTRACT_CHECK") == "1"
pytestmark = pytest.mark.skipif(not CONTRACT_CHECK, reason="set URIRUN_CONTRACT_CHECK=1")


def _ids(wires):
    return [f"{w.producer}->{w.consumer}" for w in wires]


@pytest.mark.parametrize("wire", WIRES, ids=_ids(WIRES))
def test_declared_wire_is_statically_valid(wire):
    """Każda krawędź w WIRES łączy producenta z konsumentem bez problemów typów."""
    problems = check_wire(wire, CONTRACTS)
    assert problems == [], f"{wire.producer} → {wire.consumer}: {problems}"


@pytest.mark.parametrize("wire", WIRES, ids=_ids(WIRES))
def test_wire_survives_json_roundtrip(wire):
    """Producent emituje złotą kopertę → JSON dumps/loads (granica procesu) → konsument
    buduje i waliduje swoje wejście. Dowód: KONTRAKT (nie współdzielony obiekt) niesie wymianę."""
    prod = CONTRACTS[wire.producer]
    ok_example = next(
        ex["result"] for ex in prod.examples if ex["result"].get("ok")
        and not ex["result"].get("degraded")
    )
    # simulate the process boundary: only bytes cross
    on_the_wire = json.loads(json.dumps(ok_example))
    payload = wire_payload(wire, on_the_wire)
    mode, problems = consumer_input_check(CONTRACTS[wire.consumer], payload, wire)
    assert problems == [], f"{wire.producer} → {wire.consumer} ({mode}): {problems}"
    assert mode in ("full", "partial")


def test_full_vs_partial_handoff_is_reported():
    """consumer_input_check says EXPLICITLY whether two contracts form a COMPLETE exchange
    or a PARTIAL contribution — making the pipeline topology visible in the contract layer."""
    close_restore = find_wire(WIRES, "window/command/close", "window/command/restore")
    env = next(e["result"] for e in CONTRACTS["window/command/close"].examples
               if e["result"]["ok"])
    mode, problems = consumer_input_check(
        CONTRACTS["window/command/restore"], wire_payload(close_restore, env), close_restore)
    assert (mode, problems) == ("full", [])   # snapshot IS the full restore input

    cap_click = find_wire(WIRES, "screen/query/capture", "abs/command/click")
    cenv = next(e["result"] for e in CONTRACTS["screen/query/capture"].examples
                if e["result"].get("ok") and "fullSize" in e["result"])
    mode2, problems2 = consumer_input_check(
        CONTRACTS["abs/command/click"], wire_payload(cap_click, cenv), cap_click)
    assert mode2 == "partial" and problems2 == []   # carries sw,sh only; x,y from locate step


# ── proof that a BAD wire is rejected (check_wire has teeth) ──────────────────

def test_conditional_to_required_is_rejected():
    """Binding from a CONDITIONAL output (fullSize exists only in the Success branch of the
    capture oneOf) to a REQUIRED consumer input must be rejected — the pipeline breaks on degraded."""
    bad = Wire("screen/query/capture", "abs/command/click", {"x": "fullSize.0"})
    problems = check_wire(bad, CONTRACTS)
    assert any("warunkowe" in p and "wymagane" in p for p in problems), problems


def test_type_mismatch_is_rejected():
    """Binding an object (snapshot) into an int field (x) must be rejected."""
    bad = Wire("window/command/close", "abs/command/click", {"x": "snapshot"})
    problems = check_wire(bad, CONTRACTS)
    assert any("nie pasuje" in p for p in problems), problems


def test_missing_field_is_rejected():
    """Binding from a non-existent output path must be rejected."""
    bad = Wire("window/command/close", "window/command/restore", {"snapshot": "nope.path"})
    problems = check_wire(bad, CONTRACTS)
    assert any("nie ma ścieżki" in p for p in problems), problems
