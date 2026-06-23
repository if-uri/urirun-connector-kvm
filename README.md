# urirun-connector-kvm

KVM (keyboard/video/mouse) connector for [ifURI](https://ifuri.com) / urirun.
Drive input and capture the screen through `kvm://` routes.

Catalog: <https://connect.ifuri.com/connectors/kvm>

| URI | Operation |
| --- | --- |
| `kvm://host/input/command/key` | send a key press |
| `kvm://host/input/command/move` | move the mouse pointer |
| `kvm://host/screen/query/capture` | capture the screen to a file |

Input/capture touch a real display, so routes **default to dry-run** (testable
headless). Set `dry_run=false` to act via optional host tools (`xdotool`, `scrot`).

## License

Released under the terms in [LICENSE](LICENSE).

## Install
```bash
urirun connect add kvm     # from the connect.ifuri.com catalog
# or pin directly:
pip install "git+https://github.com/if-uri/urirun-connector-kvm.git"
```
The connector emits the `urirun.bindings.v2` contract; routes are validated with
`urirun validate` and run via `urirun run 'kvm://…' registry.json`.

## Development
```bash
make test     # bindings validate + dry-run smoke
```
