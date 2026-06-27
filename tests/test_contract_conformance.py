# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Conformance gate for the kvm connector's route contracts.

``test_contracts_conform`` is the always-on CI oracle (pure declaration check — no hardware, no
backend imports): effect↔verb agree, a reversible command names an inverse that exists, golden
examples satisfy in/out, and each example's ``inverse.args`` satisfy the inverse route's INPUT schema
(so a broken rollback fails here, declaratively, not at runtime mid-rollback).

``test_code_matches_contract_inputs`` (gated by ``URIRUN_CONTRACT_CHECK=1``) imports the live
connector and asserts each contract's inputs exist in the real handler signature and that the
contract is attached to the binding — catching code↔contract drift. It is gated because importing
``core`` pulls the kvm backends.
"""
from __future__ import annotations

import os

import pytest

from urirun_connector_kvm.contracts import CONTRACTS
from urirun_connectors_toolkit.contract_gate import attach_contracts, conform


def test_contracts_conform():
    conform(CONTRACTS)


@pytest.mark.skipif(not os.environ.get("URIRUN_CONTRACT_CHECK"),
                    reason="set URIRUN_CONTRACT_CHECK=1 to cross-check contracts against live bindings")
def test_code_matches_contract_inputs():
    import urirun_connector_kvm.core as core

    attach_contracts(core.conn, CONTRACTS)
    bindings = core.conn.bindings()["bindings"]
    for route, c in CONTRACTS.items():
        uri = core.conn.uri(route)
        assert uri in bindings, f"{route}: no live binding at {uri}"
        binding = bindings[uri]
        props = set((binding.get("inputSchema") or {}).get("properties") or {})
        assert set(c.inp) <= props, \
            f"{route}: contract inputs {set(c.inp)} not all in handler signature {props}"
        assert (binding.get("meta") or {}).get("contract"), \
            f"{route}: contract not attached to the binding meta"


@pytest.mark.skipif(not os.environ.get("URIRUN_CONTRACT_CHECK"),
                    reason="set URIRUN_CONTRACT_CHECK=1 to report contract coverage against live routes")
def test_contract_coverage_report():
    """Surface (don't hide) which kvm routes still lack a contract — no silent gaps.

    Warns with the uncovered route list so the gap is visible in the pytest summary without
    blocking; only hard-fails if a contract points at a route that no longer exists.
    """
    import warnings

    import urirun_connector_kvm.core as core

    live = {b["uri"] for b in core.conn.bindings()["bindings"].values()}
    contracted = {core.conn.uri(route) for route in CONTRACTS}

    dangling = contracted - live
    assert not dangling, f"contracts point at routes that no longer exist: {sorted(dangling)}"

    uncovered = sorted(live - contracted)
    covered, total = len(contracted), len(live)
    if uncovered:
        warnings.warn(
            f"contract coverage {covered}/{total} kvm routes; {len(uncovered)} uncovered: {uncovered}",
            stacklevel=2,
        )
