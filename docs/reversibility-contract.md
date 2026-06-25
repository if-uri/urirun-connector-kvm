# Reversibility contract — the connector's half (spec for the source template)

> The Twin / reversible engine lives in **urirun** (`urirun/node/reversible.py`, consumed by
> `flow.py`: `ledger_from_execution` + `rollback_flow`). It is connector-agnostic. A connector
> ADOPTS it by providing only three things — and they are ordinary `kvm://` routes, **not** a
> `twin://` scheme. This doc specifies exactly what the KVM connector must return so its routes
> become reversible. Bring it into the connector's **source template** (not the generated
> `core.py`, which the ifuri auto-sync regenerates).

## The three-part contract

1. **Scan route → `{state}`** — a query that returns the MUTABLE slice of the world, so the
   engine can sign a position and prove a return by re-scan.
2. **A mutation returns its `inverse`** — every `…/command/…` route that changes state returns
   `inverse: {uri, args}`, computed AT EXECUTION TIME (it knows the effect: the new id, the
   previous value). The inverse lives in the same URI space.
3. **A schema marks `reversible` per route** — `CallSpec(uri, mutates, reversible, …)` so the
   engine REFUSES (blocks pre-execution) a mutation that cannot be undone here.

## The governing principle: reversibility follows the SURFACE

You can only invert what you can READ. On **CDP** the connector reads DOM state (url, scroll,
field value, created ids) → most mutations get a sound inverse. On **OS-level / vision** the
connector cannot read state → most mutations have NO sound inverse → they are `reversible:false`
and the **invariant blocks them** (unexecutable, not run). That is correct, not a limitation:
it guarantees the prefix stays reversible, and it is exactly why the surface-escalation rule
already prefers CDP. Reversibility is one more reason CDP is the right surface for state-changing
work.

## 1) Scan route → `{state}`

`kvm://<node>/env/query/profile` (extend it) or a dedicated `kvm://<node>/state/query/snapshot`
returns a `state` block — the mutable position, NOT the capabilities:

```jsonc
"state": {
  "surface": "cdp",                       // which world we're in
  "url": "https://…/feed",                // CDP: location.href
  "scrollY": 0,                           // CDP: window.scrollY
  "fields": {"<role|selector>": "<value>"},// CDP: form/input values that a fill would change
  "composer": false,                      // CDP: is a create-dialog open
  "windows": ["<title>@<id>"]             // os-level: window list (coarse)
}
```

`state_sig = sha256(state)` is the position; equality after rollback is the proof.

## 2) Per-route inverse table

| Route | mutates | reversible when | `inverse` it returns | snapshot taken before |
| --- | --- | --- | --- | --- |
| `cdp/page/command/navigate {url}` | ✅ | always (CDP) | `navigate {url: <prev>}` | `location.href` |
| `ui/command/fill {role,value}` | ✅ | CDP or readable field | `fill {role, value: <prev>}` | field's current value |
| `input/command/type {text}` | ✅ | only if field was EMPTY | `key ctrl+a` then `key BackSpace` (clear) | field length (CDP) |
| `ui/command/click` → opens dialog | ✅ | dialog detectable | `key Escape` (or click the close control) | composer/dialog visibility |
| `ui/command/click` → navigates | ✅ | url changed (CDP) | `navigate {url: <prev>}` | `location.href` |
| `ui/command/click` → creates (post/comment) | ✅ | result has `createdId` | app delete of that id (e.g. `cdp/page/command/delete {id}`) | — (id from effect) |
| `ui/command/click` → toggles (like/follow) | ✅ | toggle detectable | the SAME click (toggle⟂toggle) | toggle state |
| `ui/command/click` → plain navigation, no captured effect | ✅ | ❌ | — → `reversible:false` → blocked | — |
| `input/command/click {x,y}` (raw pixel) | ✅ | ❌ (opaque target) | — → blocked | — |
| `input/command/key {keys}` | ✅ | only a known toggle key | the toggle key, else `reversible:false` | — |
| `input/command/scroll {dy}` | ✅ | CDP (absolute) | `scroll-to {y: <prevScrollY>}`; os-level `scroll {dy:-dy}` is APPROXIMATE → mark `reversible:approx` | `window.scrollY` |
| `input/command/move {x,y}` | ❌ | n/a (cursor ≠ world state) | none (non-mutating) | — |
| `window/command/focus {title}` | ✅ | prev window capturable | `focus {title: <prev>}` | focused window |
| `app://desktop/command/launch {app}` | ✅ | launch returns pid | `proc/command/kill {pid}` (close⟂launch) | — (pid from effect) |
| `cdp/session/command/ensure` | ❌ | n/a (idempotent precondition) | none | — |
| `proc/command/kill {pid}` | ✅ | ❌ (cannot un-kill) | — → `reversible:false` → blocked | — |

## 3) Result shape (the only code change in a route)

A mutating handler adds ONE field to its success result — nothing else changes:

```python
# inside e.g. cdp_navigate, AFTER reading the prev url and navigating:
return _ok(action="cdp-navigate", url=url, **_spread(nav),
           inverse={"uri": f"kvm://{node}/cdp/page/command/navigate", "args": {"url": prev_url}})
```

Routes that cannot form a sound inverse on the live surface return **no** `inverse` (or
`inverse: null`). The engine then blocks them via the schema's `reversible:false` — or, if they
slipped through, flags `mutation succeeded without an inverse` (a violation, surfaced, never a
silent green).

## Honesty boundary (carry verbatim)

The inverse restores state to the RESOLUTION of the snapshot taken at mutation time
(url+scroll+field+created-id). Ephemeral state never serialized — a live socket, momentum
scrolling, **someone else's observation of your post** — is OUTSIDE the edge. The engine says so
(re-scan ≠ before → KNOWN-BAD → escalate) rather than pretending to undo it. Reversible is the
state you AUTHOR; irreversible is another world's data you only have an edge INTO, not OVER.

## Where this goes

- **urirun (already done):** `reversible.py` core + `flow.py` consumption (`ledger_from_execution`,
  `rollback_flow`, `result["reversible"]`). Survives auto-sync (it's source).
- **connector source template (this spec):** add the `inverse` field to the mutating handlers
  above + the `state` block to the scan route + a `schema()` marking `reversible`. No `twin://`
  scheme — the engine reads `inverse` from ordinary `kvm://` results.
