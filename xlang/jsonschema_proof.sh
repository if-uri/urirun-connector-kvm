#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Dowód, że neutralne źródło feeduje konsumenta NIEPISANEGO RĘCZNIE: regeneruje contracts.json
# i contracts.schema.json ze źródła prawdy, po czym off-the-shelf walidator (jsonschema)
# egzekwuje kontrakt zerowym własnym kodem. Pomija się czysto bez biblioteki jsonschema.
set -euo pipefail
cd "$(dirname "$0")"

python -c "import jsonschema" 2>/dev/null || { echo "SKIP: brak biblioteki jsonschema — pomijam"; exit 0; }

TOOLKIT="${URIRUN_TOOLKIT:-~/github/if-uri/urirun/adapters/python}"
export PYTHONPATH="..:${TOOLKIT}"

python emit_contracts.py
python emit_jsonschema.py
echo
python jsonschema_proof.py
