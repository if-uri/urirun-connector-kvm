# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Conformance gate for kvm:// route contracts — the always-on CI oracle.

Pure declaration checks (no hardware, no backend dispatch): four parametrized invariants cover
every route in CONTRACTS, and four standalone tests verify the validator, the error taxonomy, and
the runtime enforce() wrapper. These run on EVERY CI run on purpose — a contract gate that defaults
off is a green shim that lets contracts.py rot out of sync with the handlers it claims to describe.

The only reason to skip is a minimal/flat-file env where the contract kernel isn't installed; that
skips *gracefully* via importorskip below — never a silent opt-out behind a flag someone forgets to set.
"""
from __future__ import annotations

import pytest

pytest.importorskip("urirun")                                   # connector runtime dependency
pytest.importorskip("urirun_connectors_toolkit.contract_gate")  # the contract kernel

from urirun_connector_kvm.contracts import CONTRACTS  # noqa: E402  (after importorskip guards)
from urirun_connectors_toolkit.contract_gate import (  # noqa: E402
    ContractViolation,
    check,
    conform,
    enforce,
    envelope_violation,
)

_ROUTES = sorted(CONTRACTS)


# ── 4 × N parametrized invariants ─────────────────────────────────────────────

@pytest.mark.parametrize("route", _ROUTES)
def test_effect_matches_uri_verb(route):
    """effect 'command'/'query' must agree with the /command/ or /query/ segment in the URI."""
    c = CONTRACTS[route]
    assert c.effect in ("query", "command"), f"{route}: unknown effect {c.effect!r}"
    assert ("/query/" in route) == (c.effect == "query"), \
        f"{route}: effect {c.effect!r} contradicts the URI verb"


@pytest.mark.parametrize("route", _ROUTES)
def test_reversible_declares_mutual_inverse(route):
    """A reversible command must name an inverse route that exists AND points back."""
    c = CONTRACTS[route]
    if not c.reversible:
        return
    assert c.effect == "command", f"{route}: only commands can be reversible"
    assert c.inverse_route in CONTRACTS, \
        f"{route}: inverse_route {c.inverse_route!r} not in CONTRACTS"
    back = CONTRACTS[c.inverse_route]
    assert back.inverse_route == route, \
        f"{route} ↔ {c.inverse_route} not mutual (back.inverse={back.inverse_route!r})"


@pytest.mark.parametrize("route", _ROUTES)
def test_golden_examples_satisfy_in_and_out(route):
    """Every golden example must pass both the input and output schema."""
    c = CONTRACTS[route]
    assert c.examples, f"{route}: no golden examples declared"
    for i, ex in enumerate(c.examples):
        check(c.inp, ex.get("payload", {}), f"{route}#ex{i}.payload")
        if ex.get("result", {}).get("ok"):
            check(c.out, ex.get("result", {}), f"{route}#ex{i}.result")


@pytest.mark.parametrize("route", _ROUTES)
def test_inverse_args_satisfy_inverse_input(route):
    """Strongest check: inverse.args from an example must satisfy the INPUT schema of the
    inverse route — so a broken rollback fails declaratively in CI, not mid-rollback in prod."""
    c = CONTRACTS[route]
    if not c.reversible:
        return
    inv = CONTRACTS[c.inverse_route]
    for i, ex in enumerate(c.examples):
        if not ex.get("result", {}).get("ok"):
            continue
        args = (ex["result"].get("inverse") or {}).get("args", {})
        check(inv.inp, args, f"{route}#ex{i}.inverse.args → input of {c.inverse_route}")


# ── standalone validator + gate tests ─────────────────────────────────────────

def test_validator_catches_drifted_output():
    """envelope_violation: a good envelope passes; dropping 'inverse' or lying about
    'reversible' both surface as violations."""
    c = CONTRACTS["window/command/close"]
    good = c.examples[0]["result"]

    assert envelope_violation(c, good) is None

    no_inverse = {k: v for k, v in good.items() if k != "inverse"}
    assert envelope_violation(c, no_inverse) is not None

    lied_reversible = dict(good, reversible=False)
    assert envelope_violation(c, lied_reversible) is not None


def test_error_class_must_be_declared():
    """A known RemediationClass on the error path passes; an undeclared class is a violation."""
    c = CONTRACTS["window/command/close"]
    known = {"ok": False, "remediation": {"class": "unreachable"}}
    assert envelope_violation(c, known) is None

    unknown = {"ok": False, "remediation": {"class": "made-up-class"}}
    assert envelope_violation(c, unknown) is not None


def test_enforce_guards_a_live_handler():
    """enforce() wraps a connector so conformant outputs pass and drifting outputs raise
    ContractViolation at the call site — the guard is injected transparently."""

    class FakeConn:
        def __init__(self):
            self.routes: dict = {}
            self.attached: dict = {}

        def handler(self, route, **kw):
            def deco(fn):
                self.routes[route] = fn
                return fn
            return deco

        def attach_contract(self, route, contract):
            self.attached[route] = contract

    conn = enforce(FakeConn(), CONTRACTS, validate=True)
    good = dict(CONTRACTS["window/command/close"].examples[0]["result"])

    @conn.handler("window/command/close", isolated=True)
    def close_good(id: str = ""):
        return dict(good)

    @conn.handler("window/command/restore", isolated=True)
    def restore_drift(snapshot=None):
        # missing 'inverse' — contract requires it in out
        return {"ok": True, "connector": "kvm", "action": "window-restore", "reversible": True}

    assert conn.attached["window/command/close"].version == "v1"
    assert close_good()["action"] == "window-close"

    with pytest.raises(ContractViolation):
        restore_drift()


def test_conform_passes_all_declared_contracts():
    """conform() is the monolithic oracle — a single assertion that all CONTRACTS are internally
    consistent. Kept as a fast smoke-test alongside the parametrized breakdown."""
    conform(CONTRACTS)
