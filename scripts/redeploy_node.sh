#!/usr/bin/env bash
# Author: Tom Sapletta · Part of the ifURI solution.
#
# Redeploy the kvm connector to a mesh node that lost its merge-deployed routes
# (symptom: "Route not found: kvm.screen.query", routeCount collapses to built-ins).
# Merge-deploy does not reliably survive a node restart — this makes recovery one
# command, and vguard.Screen calls it automatically on NOT_FOUND (self-heal).
#
# Usage: scripts/redeploy_node.sh [NODE_URL]
#   NODE_URL   default http://192.168.188.201:8765 (lenovo)
#   URIRUN_PY  python of a venv that has BOTH urirun and urirun-connector-kvm
#              (default: ~/github/if-uri/urirun/venv/bin/python — the connector's
#               own venv has no urirun, do not use it)
set -euo pipefail

NODE_URL="${1:-http://192.168.188.201:8765}"
PY="${URIRUN_PY:-$HOME/github/if-uri/urirun/venv/bin/python}"
URIRUN="$(dirname "$PY")/urirun"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../urirun_connector_kvm" && pwd)"

BINDINGS="$(mktemp --suffix=.kvm-bindings.json)"
trap 'rm -f "$BINDINGS"' EXIT

# Neutral cwd: launched from ~/github/if-uri the repo FOLDER `urirun/` shadows the
# installed package (`urirun has no attribute connector`) — see urirun-package-shadow.
cd "$PKG_DIR"

# Flat-module refs: /deploy --code pushes files FLAT, so python.module must be
# "core", not "urirun_connector_kvm.core" (each module has a flat-import fallback).
"$PY" -c "import json; from urirun_connector_kvm.core import urirun_bindings; \
print(json.dumps(urirun_bindings()).replace('urirun_connector_kvm.', ''))" > "$BINDINGS"

CODE=()
for f in core.py backends.py cdp.py _cdp_impl.py control.py environment.py \
         strategies.py surface.py _backends_surface.py _backends_uinput.py \
         launch_backends.py vnc.py contracts.py; do
  CODE+=(--code "$PKG_DIR/$f")
done

exec "$URIRUN" host deploy "$NODE_URL" --bindings "$BINDINGS" \
  --allow 'kvm://**' --allow 'app://**' "${CODE[@]}" \
  --merge --persist --identity ~/.ssh/id_ed25519
