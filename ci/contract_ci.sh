#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Contract CI gate — three questions in one run:
#   1. is each contract SELF-CONSISTENT (effect, reversibility, golden examples),
#   2. do contracts COMPOSE (producer output feeds consumer input without type errors),
#   3. do two INDEPENDENTLY LOADED contracts exchange data correctly ACROSS PROCESSES via JSON.
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
echo "OK: contracts self-consistent, composable, and IPC-compatible."
