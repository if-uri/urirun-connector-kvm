#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Contract CI gate — five questions in one run:
#   1. is each contract SELF-CONSISTENT (effect, reversibility, golden examples),
#   2. do contracts COMPOSE (producer output feeds consumer input without type errors),
#   3. do two INDEPENDENTLY LOADED contracts exchange data correctly ACROSS PROCESSES via JSON,
#   4. POLYGLOT: same contracts.json passes py/js/go validators + full 3×3 exchange matrix,
#   5. PRODUCTION CHECK: external driver queries every node by transport, validates OUTPUT.
#
# URIRUN_CONTRACT_CHECK=1 is hardcoded here: a gate that defaults off is a green shim
# that silently lies. This script is where enforcement is permanently on.
set -euo pipefail
cd "$(dirname "$0")/.."
export URIRUN_CONTRACT_CHECK=1
export PYTHONPATH="${PYTHONPATH:-.}"

echo "== 1/3 self-conformance (each contract individually) =="
python -m pytest tests/test_contract_conformance.py -q

echo
echo "== 2/3 contract composition (static wire type-checking) =="
python -m pytest tests/test_contract_composition.py -q

echo
echo "== 3/3 cross-process IPC (two separate OS processes, JSON on a pipe) =="
python ci/cross_process_roundtrip.py drive window/command/close window/command/restore
python ci/cross_process_roundtrip.py drive screen/query/capture abs/command/click

echo
echo "== 4/4 polyglot (py · js · go read the SAME contracts.json — 3×3 exchange matrix) =="
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/run.sh

echo
echo "== 5/5 production check (external driver queries each node via transport, validates OUTPUT) =="
# round-trip (step 3/4) proved CONSUMPTION; driver proves PRODUCTION through the wire.
# --lie mode: each node passes its own in-language gate but lies on the wire — only the third-party
# driver (holding the contract) catches it, showing contracts are enforced OUTSIDE the node too.
URIRUN_TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}" \
  bash xlang/driver.sh

echo
echo "OK: contracts self-consistent, composable, IPC-compatible, polyglot, and wire-honest."
