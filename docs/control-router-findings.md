# Control-router findings — strategy-by-strategy test + fixes

> Live test 2026-06-25 on the lenovo node (gen 21). Each `kvm://ui/*` call routes through
> `control.route()` → cdp(95) → atspi(85) → vision(50). Tested every strategy in isolation
> and read the algorithm. Buckets: **algorithm fixes**, **add orchestration**, **split into
> more URIs**.

## Test matrix (what each strategy actually did)

| Strategy | Test | Result |
| --- | --- | --- |
| **cdp** | `ui/query/find` + `ui/command/click` "Learn more", `app=chrome`, CDP up | ✅ found + clicked, page navigated example.com→iana.org — **coordinate-free, role-exact** |
| **cdp** | same find with `app=""` (desktop target "Apps") | ⚠️ CDP tried first and wasted a round-trip on the wrong DOM before falling through |
| **atspi** | availability probe (`locate text=""`) | ❌ never returns `source=atspi` → **strategy is effectively dead** (never engages) |
| **vision** | `ui/query/find` "Apps" (real screen top-bar) | ✅ found, `strategy=vision` — but `center=None` in the returned hit |

## 1) Algorithm fixes (`control.py` / `cdp.py`)

1. **`_is_browser("") == True` is wrong.** An empty `app` is treated as a browser, so *every*
   `ui/*` call with no `app` probes CDP first. Two harms: wasted round-trip on desktop tasks,
   and a stray debug-Chrome on :9222 silently hijacks desktop `ui/*`. Fix: empty `app` →
   NOT-browser, or resolve the foreground app (see `surface/query/current` below).
2. **atspi availability is mis-probed.** `available()` calls `dispatch("locate", text="")` and
   demands `source=="atspi"` — an empty-text locate almost never yields an atspi hit, so atspi
   never runs. Fix: probe only that an a11y backend exists + the target app exposes a tree;
   let `locate(target)` decide and fall through on miss (don't gate on an empty probe).
3. **No post-condition verify on `click`.** `route()` returns `ok` when the strategy's click
   *fired*, not when it had an *effect*. (CDP click returned ok; a separate `eval` right after
   still showed the old URL — the page was mid-navigation.) Fix: after an act, confirm a state
   change — re-locate, target-disappeared, DOM mutation, or `Page.loadEventFired`.
4. **CDP has no tab targeting.** `cdp.find/act` bind to `_pages()[0]` (arbitrary). With >1 tab
   it acts on the wrong one. Fix: a tab selector (url/title) in the target.
5. **Hit schema is inconsistent across strategies.** cdp locate returns `confidence=None`
   despite `confidence=0.95`; vision `find` returns `center=None` even though vision `click`
   needs `center`. Fix: one hit contract — `{found, strategy, confidence, center, bbox,
   role, name}` — emitted identically by all three, so locate↔click compose.

## 2) Where to ADD ORCHESTRATION

The router is **per-op and one-shot** (locate XOR click XOR fill). The closed loop
*perceive → act → verify → retry/escalate* lives **nowhere** — today the NL planner hand-builds
`wait`/`verify` steps around each action.

- Add an orchestrated verb, e.g. `kvm://host/ui/command/act` (or extend `task/command/run`):
  `capture → locate → act → re-capture/verify → retry (escalate strategy on repeat miss) →
  stop`. This is the home for the closed loop, bounded retries, and a `safe=false` gate before
  irreversible acts (Post/Send/Buy).
- **Bind act+observe.** The stale-eval proves that acting and observing as *separate* URIs race
  (page mid-nav). Orchestration must couple "act-then-await-settled" inside one route (wait for
  `Page.loadEventFired` / DOM-stable / target gone) instead of fire-and-forget.
- Result: the planner emits one high-level intent; orchestration handles wait/verify/retry —
  far less brittle than the current 7-step hand-rolled flow.

## 3) Where to SPLIT into more URIs

- **CDP tab control** (the missing browser Window-layer): `browser://cdp/tab/query/list`,
  `tab/command/activate`, `tab/command/close`. Resolves "which tab" — the root of fix #4.
- **`session/command/launch` params as URI fields**: `profile` / `user-data-dir` / `headless`
  explicit (we hit the Chrome 136+ "no debug on default profile" wall — profile must be a
  first-class param, and `app://launch` (XDG) can't pass these flags at all).
- **Split guarantees**: keep `ui/command/click` (one-shot, low guarantee) AND add
  `ui/command/act` (orchestrated perceive→act→verify, high guarantee) — different contracts,
  explicit in the URI rather than hidden in router internals.
- **`surface/query/current`**: "what is foreground right now (app / window / url)" so the router
  picks cdp/atspi/vision from *fact*, not from guessing on an empty `app`.
- **`ui/query/locate?strategy=cdp|atspi|vision`**: force/inspect a single strategy — needed for
  exactly this kind of testing and for the planner to pin a surface.
- **`proc/query/find`** (by name) as the read pair to `proc/command/kill` — list before you kill.
