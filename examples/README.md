# kvm connector — examples

KVM keyboard/mouse control (gated by a device).

## Install
```bash
urirun install urirun-connector-kvm
```
`urirun install` resolves catalog ids via connect.ifuri.com; `--catalog <url>` points at a
local/on-prem registry; a full package name / git URL / path falls back to `pip install`.

## Run
```bash
# KVM keyboard/mouse control (gated by a device) (read)
urirun run 'kvm://host/input/command/key' --payload '{"key": "a"}' --allow 'kvm://*'

# preview without running (dry-run): drop --execute
urirun run 'kvm://host/input/command/key' --payload '{"key": "a"}' --allow 'kvm://*'
```
> Config-gated: without runtime config this prints the plan (dry-run).

## Inspect the runtime (no path — like error:// / log://)
```bash
urirun list | grep 'kvm://'                                   # this connector's routes
urirun run 'registry://local/routes/query/list' --payload '{"scheme":"kvm"}' --allow 'registry://*'
urirun run 'registry://local/bindings/query/show' --payload '{"uri":"kvm://host/input/command/key"}' --allow 'registry://*'   # full typed contract
urirun errors                                                      # recent runtime errors (error://)
```

## Contract scenarios — many URIs, one gate (`urirun-contract-*`)
Drive every route + every wire across the sibling scenario packages (capture-click, windowpair,
filepair, kvstore) through the standalone `urirun_contract` gate, then optionally the live
cross-process/cross-language handoff:
```bash
python examples/contract_scenarios.py                 # in-process: conform each URI + each wire + teeth
bash   examples/contract_scenarios.sh integration     # + real HTTP producer→consumer (py & go)
```
Covers 4 scenarios × 2 URIs × 1 wire each (8 routes, 4 edges): each golden payload/envelope is
checked against the shared `contracts.json`, each wire's handoff is typed (FULL/PARTIAL), and a
corrupted envelope is rejected. Enforced in CI by `tests/test_contract_scenarios.py`.

## Generate a client / API surface from the binding
```bash
urirun discover | urirun gen openapi - --out openapi.json   # OpenAPI 3 (one path per route)
urirun discover | urirun gen proto   - --out service.proto  # protobuf + gRPC (typed rpc per route)
urirun discover | urirun gen client  - --out client.py      # typed Python client
```
