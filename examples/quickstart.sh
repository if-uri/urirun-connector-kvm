#!/usr/bin/env bash
# kvm: install once, then run — auto-discovered, no registry path.
set -euo pipefail
urirun install urirun-connector-kvm            # local dev: pip install -e .
urirun run 'kvm://host/input/command/key' --payload '{"key": "a"}' --allow 'kvm://*'
