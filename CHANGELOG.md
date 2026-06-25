# Changelog

## [0.3.0] - 2026-06-25

### Added
- **UI grounding layer** (perceive → locate → act → verify) as `kvm://…/ui/*`:
  `ui/query/find`, `ui/query/locate`, `ui/command/click`, `ui/command/click-text`,
  `ui/command/fill`, `ui/query/wait` (poll-until), `ui/query/verify` (assert-visible).
- **`locate` backend action** with a decorator chain: AT-SPI (accessibility tree,
  exact) → **EasyOCR** → tesseract → imgl/vql (vision). Genuine text matching with an
  honest `found:false` instead of a saliency guess; word-level boxes.
- **`a11y/command/act`** — resolution-independent focus/click/set-text by role/name over AT-SPI.
- **`abs/command/click`** — pixel-accurate click via a uinput absolute device; `sw`/`sh`
  declare the coordinate space to scale from (fixes HiDPI / changed-resolution drift).
- **Focus crop** on `screen/query/capture` (`cx`/`cy`/`zoom` or `crop_w`/`crop_h`) — ship
  only a zoomed tile around the action, not the whole screen.
- Extra `easyocr` (stronger UI/low-contrast OCR locate). `doctor/query/report` lists the new actions.

### Fixed
- `ydotool`/portal backends were gated to `linux-wayland` only; a node with no
  `WAYLAND_DISPLAY` was detected as `linux-x11`, leaving input empty even though ydotool
  worked. Broadened to `linux-x11` too (uinput is session-agnostic).
- `have_mod` availability check uses `find_spec` (no longer imports heavy modules like torch).
- `import mss.tools` (was `import mss`, which does not expose `mss.tools`).

## [0.2.0] - 2026-06-24

### Added
- Cross-platform rewrite onto a **decorator backend registry** (`@backend(action, name,
  platforms, needs_bin/mod)` + `dispatch()`): one `kvm://` surface, best-available backend
  per OS/session, graceful fallthrough.
- Desktop **app launch** via `app://host/desktop/{command/launch,query/list}` (XDG
  `.desktop` incl. Flatpak/Snap, `open -a` on macOS, `startfile` on Windows).
- Optional extras (`capture`, `portal`, `input`, `ocr`, `windows`, `full`); degrades to
  whatever tools/libraries are present.

## [0.1.10] - 2026-06-25

### Fixed
- Fix relative-imports issues (ticket-1314dcdf)
- Fix unused-imports issues (ticket-3a58f65b)
- Fix relative-imports issues (ticket-2ef10f92)
- Fix string-concat issues (ticket-622a0065)
- Fix unused-imports issues (ticket-481ae787)
- Fix magic-numbers issues (ticket-20568dcc)
- Fix ai-boilerplate issues (ticket-bf71af4b)
- Fix duplicate-imports issues (ticket-8ad0a7a9)
- Fix smart-return-type issues (ticket-25543e4a)
- Fix string-concat issues (ticket-bbd7d709)
- Fix unused-imports issues (ticket-1f9d23be)
- Fix magic-numbers issues (ticket-9a90772f)
- Fix llm-generated-code issues (ticket-9a184235)

## [0.1.0] - 2026-06-20

### Added
- Initial KVM connector: key, move and screen-capture `kvm://` routes on the
  urirun connector SDK, dry-run by default, backed by `xdotool`/`scrot` when
  `dry_run=false`. CLI, manifest, pytest suite, smoke target, CI and entry point.
