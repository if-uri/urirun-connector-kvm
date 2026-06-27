#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""IPC proof: two INDEPENDENTLY LOADED contracts from different routes exchange data
via JSON across an OS process boundary — no shared Python object.

  produce <route>          — write the golden ok-envelope as JSON to stdout  (producer process)
  consume <prod> <cons>    — read JSON from stdin, build consumer input via wire, validate
  drive   <prod> <cons>    — spawn both as SEPARATE processes connected by a pipe  (default)

Producer and consumer are two OS processes that share nothing but JSON bytes on a pipe —
exactly as a host and a node, or two flow steps on different machines. The test proves that
the CONTRACT (not a native object snapshot) is sufficient for correct data exchange.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from urirun_connector_kvm.contracts import CONTRACTS, WIRES
from urirun_connectors_toolkit.contract_gate import (
    consumer_input_check,
    find_wire,
    wire_payload,
)


def _ok_example(route: str) -> dict:
    for ex in CONTRACTS[route].examples:
        if ex["result"].get("ok") and not ex["result"].get("degraded"):
            return ex["result"]
    raise SystemExit(f"{route}: no golden ok (non-degraded) envelope")


def produce(route: str) -> int:
    json.dump(_ok_example(route), sys.stdout)
    return 0


def consume(producer: str, consumer: str) -> int:
    envelope = json.load(sys.stdin)
    wire = find_wire(WIRES, producer, consumer)
    payload = wire_payload(wire, envelope)
    mode, problems = consumer_input_check(CONTRACTS[consumer], payload, wire)
    json.dump({"ok": not problems, "mode": mode, "builtInput": payload, "problems": problems},
              sys.stdout)
    return 0 if not problems else 1


def drive(producer: str, consumer: str) -> int:
    env = dict(os.environ, PYTHONPATH=os.environ.get("PYTHONPATH", "."))
    p = subprocess.run([sys.executable, __file__, "produce", producer],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        print(f"  producer {producer} failed: {p.stderr.strip()}", file=sys.stderr)
        return 1
    c = subprocess.run([sys.executable, __file__, "consume", producer, consumer],
                       input=p.stdout, capture_output=True, text=True, env=env)
    try:
        res = json.loads(c.stdout.strip())
    except json.JSONDecodeError:
        print(f"  consumer {consumer} failed: {c.stderr.strip() or c.stdout.strip()}",
              file=sys.stderr)
        return 1
    badge = "OK " if res["ok"] else "ERR"
    print(f"  [{badge}] {producer}  ──JSON──▶  {consumer}   "
          f"({res['mode']} handoff)   consumer input = {res['builtInput']}")
    for pr in res["problems"]:
        print(f"        ✗ {pr}")
    return c.returncode


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "drive"
    if cmd == "produce":
        raise SystemExit(produce(sys.argv[2]))
    if cmd == "consume":
        raise SystemExit(consume(sys.argv[2], sys.argv[3]))
    if cmd == "drive":
        raise SystemExit(drive(sys.argv[2], sys.argv[3]))
    raise SystemExit(f"unknown mode {cmd!r}")
