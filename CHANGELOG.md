# Changelog

## [0.1.0] - 2026-06-20

### Added
- Initial KVM connector: key, move and screen-capture `kvm://` routes on the
  urirun connector SDK, dry-run by default, backed by `xdotool`/`scrot` when
  `dry_run=false`. CLI, manifest, pytest suite, smoke target, CI and entry point.
