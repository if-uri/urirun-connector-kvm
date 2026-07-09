#!/usr/bin/env python3

from __future__ import annotations

import os
import sys

from urirun_llm_runtime import Executor


KVM_DOCTOR_URI = "kvm://host/doctor/query/report"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    node_url = os.environ.get("URIRUN_NODE_URL", "http://127.0.0.1:18765")

    executor = Executor(node_url)

    health = executor.health()
    if not isinstance(health, dict):
        fail(f"/health returned non-dict response: {health!r}")

    routes = executor.routes()

    if KVM_DOCTOR_URI not in routes:
        fail(f"{KVM_DOCTOR_URI} is missing from /routes. Routes: {routes!r}")

    if not any(route.startswith("kvm://") for route in routes):
        fail(f"No kvm:// routes found. Routes: {routes!r}")

    forbidden_prefixes = (
        "browser://",
        "env://",
        "work://",
        "router://",
        "twin://",
        "marksync://",
        "markpact://",
        "http-check://",
    )

    unexpected = [
        route
        for route in routes
        if route.startswith(forbidden_prefixes)
    ]

    if unexpected:
        fail(f"Unexpected non-KVM connector routes found: {unexpected!r}")

    result = executor.execute(KVM_DOCTOR_URI, {})

    if not isinstance(result, dict):
        fail(f"Executor returned non-dict response: {result!r}")

    if result.get("ok") is not True:
        fail(f"Executor returned failed response: {result!r}")

    route_result = result.get("result")
    value = route_result.get("value", route_result) if isinstance(route_result, dict) else route_result

    if not isinstance(value, dict):
        fail(f"Executor returned response without dict result value: {result!r}")

    if value.get("ok") is not True:
        fail(f"KVM doctor route returned failed response: {result!r}")

    if "backends" not in value:
        fail(f"KVM doctor route response is missing backends: {result!r}")

    print("OK: urirun-llm-runtime -> urirun node -> KVM connector smoke test passed")


if __name__ == "__main__":
    main()
