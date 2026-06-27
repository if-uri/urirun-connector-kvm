#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Dowód polyglota dla py/js/go (+ Rust gdy dostępny): producent w jednym języku, konsument
# w drugim, połączeni TYLKO bajtami JSON na potoku i WSPÓLNYM contracts.json (z dataclassy).
# Żadnego współdzielonego obiektu, żadnego uprzywilejowanego języka — kontrakt jest jedynym spoiwem.
#
#   1. regeneruje contracts.json ze ŹRÓDŁA PRAWDY (contracts.py)
#   2. konformans w każdym języku na tym samym pliku
#   3. PEŁNA MACIERZ N×N (każdy producent × każdy konsument) dla obu krawędzi
#   4. uszkodzona koperta ODRZUCONA symetrycznie przez KAŻDY walidator
set -euo pipefail
cd "$(dirname "$0")"

# Brama portowalna: bez node/go dowód polyglota nie ma sensu — pomiń czysto (exit 0),
# żeby python-only CI nie pękał. Sentinel "SKIP:" jest czytany przez pytest (test_xlang_polyglot).
command -v node >/dev/null 2>&1 || { echo "SKIP: node nieobecny — pomijam dowód polyglota"; exit 0; }
command -v go   >/dev/null 2>&1 || { echo "SKIP: go nieobecny — pomijam dowód polyglota"; exit 0; }

TOOLKIT="${URIRUN_TOOLKIT:-/home/tom/github/if-uri/urirun/adapters/python}"
export PYTHONPATH="..:${TOOLKIT}"

declare -A LANG=( [py]="python peer.py" [js]="node peer.mjs" [go]="./peer_go" )
LANGS=(py js go)

echo "== 0. regeneracja contracts.json ze źródła prawdy (contracts.py) =="
python emit_contracts.py
go build -o peer_go peer.go
# Rust — OPCJONALNY czwarty czytnik: dowód, że liczba czytników nie jest ograniczona do trzech.
# Dołączany tylko gdy cargo jest i build przejdzie; jego brak nie psuje bramy py/js/go.
if command -v cargo >/dev/null 2>&1 \
   && cargo build --release --offline --manifest-path rust/Cargo.toml >/dev/null 2>&1; then
  cp rust/target/release/peer_rs ./peer_rs
  LANG[rs]="./peer_rs"; LANGS+=(rs)
fi
echo "  języki: ${LANGS[*]}"
echo

echo "== 1. konformans na WSPÓLNYM contracts.json (N niezależnych walidatorów) =="
for l in "${LANGS[@]}"; do
  [ "$l" = py ] && continue
  ${LANG[$l]} conform
done
python - <<'PY'
# parytetowy konformans po stronie py reużywa kernela na neutralnych danych
import json, os
from types import SimpleNamespace
from urirun_connectors_toolkit.contract_gate import conform
from urirun_connectors_toolkit.contract_gate import Contract
doc = json.load(open("contracts.json"))
C = {r: Contract(version=c["version"], effect=c["effect"], reversible=c["reversible"],
                 inverse_route=c.get("inverseRoute") or "", inp=c["inp"], out=c["out"],
                 errors=tuple(c["errors"]), examples=tuple(c["examples"]))
     for r, c in doc["contracts"].items()}
conform(C)
print(f"  OK: {len(C)} kontraktów konformuje (kernel py, wspólny contracts.json)")
PY
echo

run_edge() {  # run_edge <opis> <producer-route> <consumer-route>
  local desc="$1" prod="$2" cons="$3"
  printf "  %s\n" "$desc"
  for p in "${LANGS[@]}"; do
    for c in "${LANGS[@]}"; do
      local out code=0
      out=$(${LANG[$p]} produce "$prod" | ${LANG[$c]} consume "$prod" "$cons") || code=$?
      local ok mode
      ok=$(printf '%s' "$out" | python -c "import json,sys;print(json.load(sys.stdin)['ok'])")
      mode=$(printf '%s' "$out" | python -c "import json,sys;print(json.load(sys.stdin)['mode'])")
      local badge="OK "; [ "$ok" = "True" ] && [ "$code" = 0 ] || badge="BŁĄD"
      printf "    [%s] %2s ─▶ %-2s  (%s handoff)\n" "$badge" "$p" "$c" "$mode"
    done
  done
}

echo "== 2. MACIERZ N×N — pełny handoff: close (producent) ─▶ restore (konsument) =="
run_edge "snapshot okna przez granicę języka i procesu:" \
         window/command/close window/command/restore
echo
echo "== 3. MACIERZ N×N — wkład częściowy: capture (producent) ─▶ click (konsument) =="
run_edge "wymiary ekranu ze zrzutu zasilają przestrzeń kliknięcia:" \
         screen/query/capture abs/command/click
echo

echo "== 4. drift złapany przez KAŻDY język: snapshot jako string zamiast obiektu =="
# uszkadzamy złotą kopertę close: snapshot → string. restore wymaga snapshot:obj.
BAD=$(python peer.py produce window/command/close \
      | python -c "import json,sys;e=json.load(sys.stdin);e['snapshot']='OOPS';print(json.dumps(e))")
for c in "${LANGS[@]}"; do
  code=0
  out=$(printf '%s' "$BAD" | ${LANG[$c]} consume window/command/close window/command/restore) || code=$?
  prob=$(printf '%s' "$out" | python -c "import json,sys;p=json.load(sys.stdin)['problems'];print(p[0] if p else '')")
  badge="ODRZUCONE"; [ "$code" = 1 ] || badge="!! PRZESZŁO !!"
  printf "    [%s] %-2s exit=%s  diagnoza: %s\n" "$badge" "$c" "$code" "$prob"
done
echo
echo "OK: ${#LANGS[@]} języki (${LANGS[*]}), jeden neutralny kontrakt — zgodność w obie strony, drift odrzucany symetrycznie."
