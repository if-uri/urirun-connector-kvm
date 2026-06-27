#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Contract CI gate — nine questions in one run:
#   1. is each contract SELF-CONSISTENT (effect, reversibility, golden examples),
#   2. do contracts COMPOSE (producer output feeds consumer input without type errors),
#   3. do two INDEPENDENTLY LOADED contracts exchange data correctly ACROSS PROCESSES via JSON,
#   4. SHAPE LINT: handler signatures + envelope keys match declared contracts,
#   5. POLYGLOT: same contracts.json passes py/js/go/rust validators + full N×N exchange matrix,
#   6. PRODUCTION CHECK: external driver queries every node by transport, validates OUTPUT,
#   7. TRANSPORT INVARIANCE: same node × stdio vs HTTP yields the identical, conformant envelope,
#   8. STANDARD SCHEMA: same source → JSON Schema; off-the-shelf validator accepts golden, rejects lie,
#   9. COMPILE-TIME: same source → TypeScript types; tsc accepts golden, rejects the lie before runtime.
#
# Steps 5-7 (polyglot) self-skip when node/go are absent; step 8 self-skips without `jsonschema`;
# step 9 self-skips without `tsc`, so python-only CI stays green. URIRUN_CONTRACT_CHECK=1 is hardcoded
# here: a gate that defaults off is a green shim that silently lies. Enforcement is permanently on.
set -euo pipefail
cd "$(dirname "$0")/.."
export URIRUN_CONTRACT_CHECK=1
export PYTHONPATH="${PYTHONPATH:-.}"

# pre-brama: kernel (gate/codegen) NIE może być redefiniowany tu — tylko re-eksport/CLI nad
# urirun_contract. Skanujemy connector + KANONICZNE źródło pakietu razem, więc każda lokalna
# kopia daje 2 definicje → FAIL (sam connector dałby 1 i fałszywie przeszedł). (Pomija się bez pakietu.)
PKG_DIR=$(python -c "import os,urirun_contract; print(os.path.dirname(urirun_contract.__file__))" 2>/dev/null || true)
if [ -n "$PKG_DIR" ]; then
  echo "== 0/9 jedno źródło kernela (gate/codegen nie redefiniowane w connectorze) =="
  python -m urirun_contract.check_single_source . "$PKG_DIR"
  echo
fi

echo "== 1/9 self-conformance (each contract individually) =="
python -m pytest tests/test_contract_conformance.py -q

echo
echo "== 2/9 contract composition (static wire type-checking) =="
python -m pytest tests/test_contract_composition.py -q

echo
echo "== 3/9 cross-process IPC (two separate OS processes, JSON on a pipe) =="
python ci/cross_process_roundtrip.py drive window/command/close window/command/restore
python ci/cross_process_roundtrip.py drive screen/query/capture abs/command/click

echo
echo "== 4/9 shape lint (handler signatures + envelope keys match declared contracts) =="
python ci/contract_shape_lint.py

echo
echo "== 5/9 polyglot (py · js · go · rust read the SAME contracts.json — N×N exchange matrix) =="
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/run.sh

echo
echo "== 6/9 production check (external driver queries each node via transport, validates OUTPUT) =="
# round-trip (step 3) proved CONSUMPTION; driver proves PRODUCTION through the wire.
# --lie mode: each node passes its own in-language gate but lies on the wire — only the third-party
# driver (holding the contract) catches it, showing contracts are enforced OUTSIDE the node too.
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/driver.sh

echo
echo "== 7/9 transport invariance (same node × stdio vs HTTP → identical conformant envelope) =="
# operation identity is the URI, not the transport: if the envelope differed by transport,
# the "contract" was secretly a transport detail.
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/transport_swap.sh

echo
echo "== 8/9 standard schema (export to JSON Schema; off-the-shelf validator enforces it) =="
# neutral source feeds NON-hand-written consumers (codegen/API gateways/IDE tooling): the
# mini-language is exported to standard JSON Schema and a spec validator accepts the golden
# corpus + rejects the same wire-lie — zero custom validation code on the consumer side.
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/jsonschema_proof.sh

echo
echo "== 9/9 compile-time (export to TypeScript types; tsc rejects the lie before runtime) =="
# moves enforcement from runtime to COMPILE TIME: the same wire-lie (screen as strings) becomes
# a tsc type error, caught before the program runs — a different kind of teeth than the runtime gates.
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/typescript_proof.sh

echo
echo "OK: contracts self-consistent, composable, shape-linted, IPC-compatible, polyglot, wire-honest, transport-invariant, standard-schema-exportable, compile-time-checked."
