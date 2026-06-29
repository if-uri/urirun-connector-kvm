#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Wrapper zewnętrznego drivera konformansu: regeneruje contracts.json ze źródła,
# buduje węzeł Go i puszcza driver, który odpytuje py/js/go po transporcie i waliduje
# ICH WYJŚCIE wobec wspólnego kontraktu. Dowód uzupełniający round-trip (run.sh):
# round-trip sprawdza konsumpcję, driver sprawdza produkcję przez drut + łapie kłamstwo.
set -euo pipefail
cd "$(dirname "$0")"

command -v node >/dev/null 2>&1 || { echo "SKIP: node nieobecny — pomijam driver konformansu"; exit 0; }
command -v go   >/dev/null 2>&1 || { echo "SKIP: go nieobecny — pomijam driver konformansu"; exit 0; }

TOOLKIT="${URIRUN_TOOLKIT:-~/github/if-uri/urirun/adapters/python}"
export PYTHONPATH="..:${TOOLKIT}"

python emit_contracts.py
go build -o peer_go peer.go
# Rust opcjonalnie — driver dołącza węzeł rs tylko gdy peer_rs istnieje (patrz conformance_driver.py).
if command -v cargo >/dev/null 2>&1 \
   && cargo build --release --offline --manifest-path rust/Cargo.toml >/dev/null 2>&1; then
  cp rust/target/release/peer_rs ./peer_rs
fi
echo
python conformance_driver.py
