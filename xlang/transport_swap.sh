#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Wrapper dowodu niezmienniczości transportu: regeneruje contracts.json, buduje węzeł Go
# i puszcza driver, który dla każdego języka porównuje kopertę po stdio vs HTTP.
set -euo pipefail
cd "$(dirname "$0")"

command -v node >/dev/null 2>&1 || { echo "SKIP: node nieobecny — pomijam swap transportu"; exit 0; }
command -v go   >/dev/null 2>&1 || { echo "SKIP: go nieobecny — pomijam swap transportu"; exit 0; }

TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}"
export PYTHONPATH="..:${TOOLKIT}"

python emit_contracts.py
go build -o peer_go peer.go
# Rust opcjonalnie — driver dołącza węzeł rs tylko gdy peer_rs istnieje (patrz transport_swap.py).
if command -v cargo >/dev/null 2>&1 \
   && cargo build --release --offline --manifest-path rust/Cargo.toml >/dev/null 2>&1; then
  cp rust/target/release/peer_rs ./peer_rs
fi
echo
python transport_swap.py
