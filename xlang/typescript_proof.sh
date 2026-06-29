#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Dowód egzekucji kontraktu w CZASIE KOMPILACJI: z tego samego źródła generujemy typy TS,
# po czym tsc akceptuje złoty kształt (check_ok.ts) i ODRZUCA to samo kłamstwo na drucie
# (check_bad.ts: screen jako stringi). Udana kompilacja check_bad.ts = brak zębów = porażka.
# Pomija się czysto bez tsc.
set -euo pipefail
cd "$(dirname "$0")"

command -v tsc >/dev/null 2>&1 || { echo "SKIP: brak tsc — pomijam dowód czasu kompilacji"; exit 0; }

TOOLKIT="${URIRUN_TOOLKIT:-~/github/if-uri/urirun/adapters/python}"
PYTHONPATH="..:${TOOLKIT}" python emit_typescript.py
echo

TSC=(tsc --noEmit --strict --skipLibCheck --target ES2020 --module ESNext)

echo "== off-the-shelf tsc na wygenerowanych typach (egzekucja w czasie kompilacji) =="
if "${TSC[@]}" ts/check_ok.ts; then
  echo "  [OK] check_ok.ts kompiluje się — złoty kształt zgodny z typami z kontraktu"
else
  echo "  [FAIL] check_ok.ts NIE skompilował się (złoty kształt powinien być poprawny)"; exit 1
fi

echo
echo "== teeth: to samo kłamstwo (screen=stringi) MUSI nie skompilować się =="
if err=$("${TSC[@]}" ts/check_bad.ts 2>&1); then
  echo "  [!! PRZESZŁO !!] check_bad.ts skompilował się — brak zębów"; exit 1
else
  line=$(printf '%s\n' "$err" | grep -m1 "not assignable" || printf '%s' "$err" | head -1)
  echo "  [ZŁAPANE w kompilacji] ${line}"
fi

echo
echo "OK: kontrakt egzekwowany w czasie kompilacji — kłamstwo na drucie nie przechodzi przez tsc."
