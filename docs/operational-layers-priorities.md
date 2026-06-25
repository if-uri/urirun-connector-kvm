# KVM operational layers + priorities

> Status: 2026-06-25, derived from a live LinkedIn-post task on the lenovo node
> (`192.168.188.201:8765`, GNOME/Wayland, 1440×900). The point of this doc: **keep the
> control surface split into clean operational layers**, so an NL planner or an autonomous
> computer-use agent can target one layer without the failure of another silently
> corrupting the task. Each layer is one *kind* of question with its own routes, its own
> failure mode, and its own surface fallback.

## The layers (each independently addressable)

| Layer | Question it answers | KVM routes today | Live state on the node |
| --- | --- | --- | --- |
| **System** | what host/session is this? | `env://`, `proc://`, `shell://…/{date,uname,which}`, `kvm://doctor` | ✅ works; `doctor` is honest (`osLevelReliable:false` on Wayland) |
| **Application** | launch / enumerate apps | `app://desktop/{command/launch,query/list}` | ✅ works (XDG, 108 apps) |
| **Window** | focus / list windows + **browser tabs** | `kvm://window/{command/focus,query/list}` | ❌ **broken on Wayland** — atspi finds no window, `wmctrl: Cannot open display`; cannot switch a Chrome tab |
| **Action** | move / click / scroll / key / capture / locate | `kvm://input/*`, `kvm://abs/command/click`, `kvm://screen/query/capture`, `kvm://ui/*` | ✅ works after this session's fixes (uinput-abs default move, `_click_hit` guard, `wait` route) |
| **Text** | enter a string | `kvm://input/command/type`, `kvm://ui/command/fill` | ⚠️ **ASCII only** — ydotool drops every non-ASCII char (Polish ł ą ę ż ó → gone) |

### Cross-cutting (NOT separate layers — they serve Action/Text)

- **Scan / perception** — yes, part of KVM. `screen/query/capture` (portal/mss/…) + the
  `locate` backends (atspi → easyocr → tesseract → imgl → vql). This is "scanning the
  screen". Capture-space == action-space is the invariant the Action layer depends on.
- **Calibration** — yes, part of KVM. `backends._calib()` reads
  `URIRUN_KVM_CALIB="ax,bx,ay,by"` and inverts `landing = a*commanded + b` per axis, so a
  commanded pixel *lands* where intended on fractional-HiDPI / multi-region Mutter. It is a
  property of the **Action** layer (the abs-pointer transform), fed by `URIRUN_KVM_SCREEN`
  for the base pixel↔ABS-65535 scale. Today: base scale fixed; affine calib unfit (identity).

## Why NL tasks fail today (gap = which layer the planner cannot trust)

1. **Text layer is the #1 blocker.** Any non-English NL task is silently corrupted: the
   flow reports `type ok`, but the characters never arrived. There is no Unicode-safe path
   on the node (no `wl-copy`/`xclip`/`wtype`). → A whole class of NL tasks is unservable.
2. **Window layer cannot target a surface.** The NL planner emitted `window/command/focus
   "LinkedIn"`; it failed, the flow continued blind, and the active Chrome tab drifted
   (example.com → iana.org), so later clicks hit the wrong page. The planner has no reliable
   "make surface X frontmost" primitive on Wayland.
3. **Planner picks the wrong Action route.** It chose `ui/command/click` (atspi-first,
   flaky on web content) over `ui/command/click-text` (OCR, reliable here). No layer-aware
   route preference.
4. **No surface selection.** `doctor` already recommends `browser-cdp` for browser work,
   but the planner never consults it — it drove a browser task through OS-level KVM.
5. **No closed loop.** `ui/query/{wait,verify}` exist but the planner does not insert a
   verify after each act, so a failed step is invisible until a later step crashes.

## Autonomy verdict (Gemini computer-use agent)

`/.urirun/flows/kvm-computer-use-agent.py` (model `gemini-3.5-flash`, `computer_use`) is
**not runnable here**: no `GEMINI_API_KEY` in `.env` (only `OPENROUTER_API_KEY`) and
`google-genai` is not installed. Even once keyed, it shares the connector's walls: it types
through `kvm://input/command/type`, so it would mangle Polish exactly as the manual run did.
A vision agent *would* likely beat the NL planner on the **Window** layer (it can see and
click the LinkedIn tab in the tab strip), but the **Text** gap is connector-level and blocks
both. → Fix the connector layers first; autonomy is gated on Text + Window, not on the model.

## Priorities (ordered by what unblocks real NL tasks, per layer)

**P0 — Text layer: Unicode-safe input.** Add a `type` path that is not keymap-bound. Options,
best→worst for this node: (a) a `paste` backend that sets the clipboard + sends Ctrl+V —
needs `wl-clipboard` on the node (one apt install, user-authorized); (b) drive text through
the **CDP** surface (DOM insert, exact UTF-8, no keyboard at all); (c) per-codepoint GTK
unicode entry (Ctrl+Shift+U …) — fragile. Recommend (b) for browser, (a) for native apps.

**P0 — Window layer: Wayland-native focus / tab control.** `window/command/focus` must work
on Wayland: for apps, GNOME Shell `Eval`/extension or `gdbus` activation; for browser tabs,
this belongs to the **CDP** surface (`browser://…/tab/activate`), not KVM. Until then the
planner must not assume focus succeeded — make `focus` return `ok:false` loudly and have
flows gate on it.

**P1 — Planner: surface selection + layer-aware routing.** Before planning, call
`kvm://doctor`; if the task touches a browser and `recommendedSurfaces` leads with
`browser-cdp`, plan `browser://` routes, not `kvm://input/*`. Prefer `ui/command/click-text`
(OCR) over `ui/command/click` (atspi) for web targets.

**P1 — Planner: insert a verify after each act.** Auto-append `ui/query/verify`/`wait`
between steps so a missed focus/click fails the flow at the cause, not three steps later.

**P1 — Autonomy: enable the agent.** Provide `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY` for the
Claude `computer_20251124` variant) + `pip install google-genai`/`anthropic`; then re-test
the SAME task end-to-end as the autonomous baseline.

**P2 — Action layer hardening.** Run a calibration pass to fit `URIRUN_KVM_CALIB` (today
identity); let `locate` fall through atspi→OCR when atspi returns no on-screen bbox; surface
`focus` failures into `ui/*`.

**P2 — Code hygiene.** The prefact-generated `TODO.md`/`planfile.yaml` (unused imports, magic
numbers, f-strings) are real but **below** every operational item above — they do not block a
single NL task. Keep them, run them last.
