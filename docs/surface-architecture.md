# Surface architecture — the real axis of choice

> Status (2026-06-25): **README reclassified** (OS-level → limitations, CDP/RemoteDesktop
> promoted) ✓ · **doctor surface-awareness** implemented + env-independent, honest on the
> node ✓. This doc is the design for the remaining work: the `Surface` contract and the
> `cdp` / `remotedesktop-portal` / `vdisplay` adapters.

## The bug, stated precisely

Today "OS-level" is **not one surface** — it is **portal-capture (physical pixels) +
ydotool (uinput/logical space) stitched together with no shared coordinate system.** That
mismatch *is* the bug that ate three sessions: on Wayland multi-monitor / fractional-HiDPI
the screenshot you observe in and the coordinate you click in are different spaces.

The invariant that fixes it:

> **A surface guarantees capture-space == action-space.** What `capture()` shows at (x,y)
> is exactly where `click(x,y)` lands.

The current os-level path cannot promise that because its capture and its input come from
two unrelated providers. The fix is not better calibration — it is to **execute in the same
space you observe in**.

## The `Surface` contract

```python
from typing import Protocol

class Viability(TypedDict):
    ok: bool          # usable at all here
    confidence: float # 0..1 — how much to trust coordinates/focus
    reason: str

class Surface(Protocol):
    name: str                                   # "os" | "cdp" | "remotedesktop-portal" | "vdisplay"
    def viable(self) -> Viability: ...
    def screen_size(self) -> tuple[int, int]: ...   # THE coordinate space — for capture AND actions
    def capture(self) -> bytes: ...                 # PNG in screen_size space
    def move(self, x: int, y: int) -> None: ...     # x,y in screen_size space
    def click(self, x: int, y: int, button: str = "left") -> None: ...
    def type(self, text: str) -> None: ...
    def key(self, combo: str) -> None: ...
    def scroll(self, x: int, y: int, dy: int) -> None: ...
```

The whole point is the shared space: a caller (or the `ui/*` locate→act layer) captures,
finds a target at (x,y) **in that capture**, and clicks (x,y) — with no cross-space math,
because the surface owns both ends.

## Four surfaces, and why two solve coordinates *by construction*

| surface | capture | input | capture-space == action-space? | cost / caveat |
| --- | --- | --- | --- | --- |
| **os** | portal / grim / mss | ydotool / xdotool / pynput | ❌ on Wayland multi-mon/fractional (physical ≠ logical); ✅ on X11 / single+integer / vdisplay | best-effort fallback; keys hit the ACTIVE window only |
| **cdp** | `Page.captureScreenshot` | `Input.dispatchMouseEvent` / `Input.insertText` | ✅ — both in the viewport's CSS-px (pin `deviceScaleFactor=1` via `Emulation.setDeviceMetricsOverride`) | needs a Chrome with `--remote-debugging-port` + a **logged-in persistent profile**; web targets only |
| **remotedesktop-portal** | ScreenCast (PipeWire) | `RemoteDesktop.NotifyPointerMotionAbsolute` | ✅ — input is bound to the *same stream geometry* as capture | Wayland-sanctioned; needs a one-time permission grant; can take focus |
| **vdisplay** | x11grab / scrot on Xvfb | xdotool on Xvfb | ✅ — one fixed-resolution X11 monitor, 1:1 | headless/CI; no GPU accel; no physical screen |

**CDP caveat (honest):** "screenshot-space == click-space" is *almost* free — there is a
`devicePixelRatio` scalar (screenshot may be at DPR, clicks in CSS-px). But it is **one
known number**, pinned with `Emulation.setDeviceMetricsOverride(deviceScaleFactor=1)` —
incomparably more tractable than the os-level mismatch, which was *unknown and asymmetric*.

## How it slots in without breaking the 12 tests

The existing `@backend` registry stays — it just **drops one level**:

- A new first-class axis selects the **surface** (`dispatch_surface()` / a `surface://`
  or `kvm://…/surface/query/report`), defaulting to the best `viable()` one.
- Inside the **`os`** surface, today's `@backend("click", "ydotool"|…)` registry is
  exactly the implementation — so the 12 tests (which exercise os-level dispatch) become
  the `os` surface's internals **unchanged**. New tests cover `viable()` and surface
  selection.
- `cdp` is a second surface implementing the same contract via the existing
  `cdp-flat-handler` / `urirun-connector-browser-control` code.
- **`ui/*` + `a11y/*` move on top of `Surface`**: `ui/command/click-text` does
  `surface.capture()` → locate → `surface.click()`. Because both come from the *same*
  surface, locate-and-click is in one space regardless of which surface is active. This is
  why `ui/*` must stay co-packaged with the surfaces, **not** split into its own connector
  (splitting it would re-introduce the cross-space bug at the architecture level).

## doctor = honesty (done)

`kvm://…/doctor/query/report` → `surfaces`:
`{platform, wayland, waylandConfirmed, monitors:[{scale}], multiMonitor, fractionalHiDPI,
osLevelReliable, recommendedSurfaces, warnings}`. Detection is **env-independent** (Mutter
DisplayConfig via `gdbus` with a fixed `XDG_RUNTIME_DIR`, plus `loginctl`/wayland-socket) —
so it is honest on a node process that has no `WAYLAND_DISPLAY`. It warns *before* a user
wastes hours on os-level pixels.

## Package split (the only structural change worth making)

- **`app://desktop/*` → its own tiny launcher connector.** It shares no coordinate state
  with anything; a connector named "KVM" launching apps is a misnomer. Clean, mechanical.
- **`ui/*` + `a11y/*` stay** — they sit *on* the surface (see above). The honesty fix for
  the name is to **rename the package** from `kvm` to a `desktop-control` connector that
  truthfully serves transport (`kvm://`) + automation (`ui://`) + capture, unified by the
  surface, rather than to scatter them across three deploy units (which also triples mesh
  deploy friction and forces cross-connector calls on the locate→click hot path).

## Order

1. ✅ README reclassify (OS-level → limitations; CDP/RemoteDesktop recommended).
2. ✅ doctor surface-viability + env-independent Wayland/multi-monitor/scale detection + warnings.
3. **Surface abstraction + `os` (wrap current backends) and `cdp`** — the real fix.
4. `app://` → separate launcher connector.
5. `ui/*` rewritten onto `surface.*`; package renamed to `desktop-control`.
6. (later) `remotedesktop-portal` and `vdisplay` surfaces.

One sentence: **the real axis is not "which connector" but "which surface" — a surface is
the contract that guarantees capture-space == action-space; once it exists, os-level becomes
one (Wayland-unreliable) option, CDP/RemoteDesktop become equals, `ui/*` sits on top with no
mismatch, and the package split falls out (`app://` out, the rest together).**
