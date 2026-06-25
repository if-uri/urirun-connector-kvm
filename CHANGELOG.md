# Changelog

## [0.1.10] - 2026-06-25

### Fixed
- Fix relative-imports issues (ticket-79eaa6e7)
- Fix magic-numbers issues (ticket-ce81629f)
- Fix llm-generated-code issues (ticket-e2651440)
- Fix ai-boilerplate issues (ticket-c368fb94)
- Fix relative-imports issues (ticket-43e12f56)
- Fix llm-generated-code issues (ticket-807f8586)
- Fix ai-boilerplate issues (ticket-b5820d19)
- Fix relative-imports issues (ticket-9455ee3a)
- Fix string-concat issues (ticket-d92105df)
- Fix unused-imports issues (ticket-58b1e102)
- Fix magic-numbers issues (ticket-659b4d9c)
- Fix relative-imports issues (ticket-984142d3)
- Fix smart-return-type issues (ticket-6ebfaa23)
- Fix string-concat issues (ticket-8b959f92)
- Fix unused-imports issues (ticket-33ae3754)
- Fix magic-numbers issues (ticket-3ef7f0c8)
- Fix llm-generated-code issues (ticket-1152a366)
- Fix ai-boilerplate issues (ticket-b2674c4f)
- Fix unused-imports issues (ticket-8e71108a)
- Fix magic-numbers issues (ticket-459ae995)
- Fix llm-generated-code issues (ticket-f86f0238)
- Fix ai-boilerplate issues (ticket-6365edd1)
- Fix llm-generated-code issues (ticket-361c9e4b)
- Fix ai-boilerplate issues (ticket-994bf414)
- Fix smart-return-type issues (ticket-5484e752)
- Fix string-concat issues (ticket-118e21a5)
- Fix magic-numbers issues (ticket-27af1b78)
- Fix llm-generated-code issues (ticket-6e100258)
- Fix ai-boilerplate issues (ticket-4f89c7f7)
- Fix smart-return-type issues (ticket-6852a5d1)
- Fix llm-hallucinations issues (ticket-55f807b0)
- Fix llm-generated-code issues (ticket-9a5c8198)
- Fix ai-boilerplate issues (ticket-c381e28f)
- Fix smart-return-type issues (ticket-88d28c9e)
- Fix llm-generated-code issues (ticket-44a6c129)
- Fix ai-boilerplate issues (ticket-7978a82d)
- Fix relative-imports issues (ticket-224cf91b)
- Fix smart-return-type issues (ticket-e343a07a)
- Fix string-concat issues (ticket-debb4ef4)
- Fix unused-imports issues (ticket-c5240c81)
- Fix relative-imports issues (ticket-5be5bd29)
- Fix string-concat issues (ticket-2857dbae)
- Fix unused-imports issues (ticket-a96c49cd)
- Fix magic-numbers issues (ticket-35879577)
- Fix relative-imports issues (ticket-0c933642)
- Fix unused-imports issues (ticket-95db4a94)
- Fix relative-imports issues (ticket-35f56b66)
- Fix string-concat issues (ticket-8a0b977d)
- Fix unused-imports issues (ticket-90029d07)
- Fix magic-numbers issues (ticket-cabe7ec1)
- Fix relative-imports issues (ticket-d24b0cfc)
- Fix relative-imports issues (ticket-16dba733)
- Fix unused-imports issues (ticket-4ecdb092)
- Fix magic-numbers issues (ticket-e98e3056)
- Fix relative-imports issues (ticket-9c829c22)
- Fix unused-imports issues (ticket-811cf512)

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
