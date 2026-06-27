#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Testy wielu scenariuszy kontraktów (urirun-contract-*) z wieloma URI.
#   (domyślnie)      in-process: konformans każdej trasy + każda krawędź + teeth, przez urirun_contract
#   integration      dodatkowo: prawdziwy handoff międzyprocesowy/międzyjęzykowy (make integration)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== in-process (brama urirun_contract, wiele scenariuszy × wiele URI) =="
python examples/contract_scenarios.py

if [ "${1:-}" = "integration" ]; then
  IFURI=$(cd .. && pwd)
  echo
  echo "== integration (HTTP end-to-end, prawdziwe procesy/języki per scenariusz) =="
  fail=0
  for d in "$IFURI"/urirun-contract-*/; do
    [ -f "$d/contracts.json" ] || continue
    name=$(basename "$d" | sed 's/urirun-contract-//')
    # sprzątnij ewentualne wiszące porty z poprzednich przebiegów
    for p in 8801 8802 8803; do fuser -k "$p/tcp" >/dev/null 2>&1 || true; done
    if timeout 120 make -C "$d" integration >/tmp/_scen_$name.log 2>&1; then
      printf "  [OK ] %s\n" "$name"
    else
      printf "  [BŁĄD] %s (log: /tmp/_scen_%s.log)\n" "$name" "$name"; fail=1
    fi
  done
  [ "$fail" = 0 ] && echo "  wszystkie integracje OK" || { echo "  integracje z błędami"; exit 1; }
fi
