# urirun-connector-kvm

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `urirun-connector-kvm`
- **version**: `0.3.0`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, testql(1), app.doql.less, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: urirun-connector-kvm;
  version: 0.3.0;
}

dependencies {
  runtime: urirun>=0.4.14;
  test: pytest>=8;
  capture: "mss>=9.0, Pillow>=10.0";
  portal: "PyGObject>=3.42, dbus-python>=1.3";
  input: pynput>=1.7;
  ocr: "pytesseract>=0.3.10, Pillow>=10.0";
  easyocr: "easyocr>=1.7, Pillow>=10.0";
  windows: pygetwindow>=0.0.9;
  full: "mss>=9.0, Pillow>=10.0, pynput>=1.7, pytesseract>=0.3.10";
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="urirun-kvm"] {
  entry: urirun_connector_kvm.core:main;
}

workflow[name="manifest"] {
  trigger: manual;
  step-1: run cmd=urirun-kvm manifest;
}

workflow[name="bindings"] {
  trigger: manual;
  step-1: run cmd=urirun-kvm bindings;
}

workflow[name="smoke"] {
  trigger: manual;
  step-1: run cmd=urirun-kvm bindings | urirun connectors smoke - \;
  step-2: run cmd=--run 'kvm://host/screen/query/capture' --payload '{"output":"shot.png"}' \;
  step-3: run cmd=--allow 'kvm://*' --name kvm;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=pip install -e . && python3 -m pytest -q && $(MAKE) smoke;
}

tests {
  import: testql-scenarios/**/*.testql.toon.yaml;
}

deploy {
  target: makefile;
}

environment[name="local"] {
  runtime: python;
  python_version: >=3.10;
}
```

## Workflows

## Dependencies

### Runtime

```text markpact:deps python
urirun>=0.4.14
```

## Call Graph

*150 nodes · 214 edges · 9 modules · CC̄=3.5*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `uinput_abs_click` *(in urirun_connector_kvm.backends)* | 15 ⚠ | 1 | 46 | **47** |
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 39 | 6 | **45** |
| `_locate_tesseract` *(in urirun_connector_kvm.backends)* | 31 ⚠ | 0 | 44 | **44** |
| `capture` *(in urirun_connector_kvm.core)* | 15 ⚠ | 0 | 43 | **43** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `ui_act` *(in urirun_connector_kvm.core)* | 22 ⚠ | 0 | 38 | **38** |
| `_ok` *(in urirun_connector_kvm.core)* | 1 | 37 | 1 | **38** |
| `_run` *(in urirun_connector_kvm.backends)* | 4 | 26 | 4 | **30** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.08s
# nodes: 150 | edges: 214 | modules: 9
# CC̄=3.5

HUBS[20]:
  urirun_connector_kvm.backends.uinput_abs_click
    CC=15  in:1  out:46  total:47
  urirun_connector_kvm.backends.backend
    CC=1  in:39  out:6  total:45
  urirun_connector_kvm.backends._locate_tesseract
    CC=31  in:0  out:44  total:44
  urirun_connector_kvm.core.capture
    CC=15  in:0  out:43  total:43
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.ui_act
    CC=22  in:0  out:38  total:38
  urirun_connector_kvm.core._ok
    CC=1  in:37  out:1  total:38
  urirun_connector_kvm.backends._run
    CC=4  in:26  out:4  total:30
  urirun_connector_kvm.launch_backends._launch_xdg
    CC=20  in:0  out:27  total:27
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.core._fail_from
    CC=1  in:23  out:3  total:26
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.control.route
    CC=20  in:2  out:18  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.core._positioned_click
    CC=8  in:6  out:12  total:18
  urirun_connector_kvm.environment.profile
    CC=10  in:0  out:18  total:18
  urirun_connector_kvm.cdp.launch_session
    CC=10  in:0  out:17  total:17
  urirun_connector_kvm.backends._screen_wh
    CC=8  in:2  out:15  total:17

MODULES:
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [66 funcs]
    available  CC=3  out:2
    missing  CC=5  out:2
    _a11y_atspi  CC=6  out:11
    _atspi_python  CC=5  out:4
    _calib  CC=3  out:3
    _cap_gnome  CC=1  out:2
    _cap_grim  CC=1  out:2
    _cap_im  CC=1  out:2
    _cap_macos  CC=1  out:2
    _cap_mss  CC=2  out:6
  urirun_connector_kvm.cdp  [16 funcs]
    _call  CC=4  out:7
    _copy_auth  CC=4  out:8
    _evaluate  CC=4  out:12
    _find_chrome  CC=4  out:4
    _pages  CC=8  out:9
    _run  CC=2  out:6
    _ws_connect  CC=6  out:14
    _ws_recv  CC=6  out:11
    _ws_send  CC=4  out:13
    act  CC=2  out:3
  urirun_connector_kvm.control  [4 funcs]
    _safe_avail  CC=2  out:1
    act  CC=15  out:14
    report  CC=2  out:2
    route  CC=20  out:18
  urirun_connector_kvm.core  [45 funcs]
    _capture_native  CC=1  out:4
    _cdp_mod  CC=2  out:0
    _click_hit  CC=7  out:14
    _fail_from  CC=1  out:3
    _ok  CC=1  out:1
    _positioned_click  CC=8  out:12
    _router_return  CC=5  out:6
    _surface_mod  CC=2  out:0
    a11y_act  CC=3  out:6
    capture  CC=15  out:43
  urirun_connector_kvm.environment  [3 funcs]
    _safe  CC=2  out:2
    atspi_ready  CC=4  out:3
    profile  CC=10  out:18
  urirun_connector_kvm.launch_backends  [10 funcs]
    _cdp_port  CC=3  out:6
    _desktop_entries  CC=5  out:7
    _find_app  CC=8  out:6
    _launch_macos  CC=5  out:7
    _launch_windows  CC=5  out:8
    _launch_xdg  CC=20  out:27
    _list_macos  CC=5  out:9
    _list_xdg  CC=7  out:10
    _parse_desktop  CC=15  out:10
    _xdg_app_dirs  CC=8  out:11
  urirun_connector_kvm.strategies  [2 funcs]
    available  CC=2  out:2
    is_browser  CC=4  out:3
  urirun_connector_kvm.surface  [2 funcs]
    _active_window  CC=6  out:4
    current  CC=7  out:10

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._xdg_app_dirs
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._parse_desktop
  urirun_connector_kvm.launch_backends._find_app → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._find_app
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._cdp_port
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends._run
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._list_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.strategies.CdpStrategy.available → urirun_connector_kvm.strategies.is_browser
  urirun_connector_kvm.surface.current → urirun_connector_kvm.surface._active_window
  urirun_connector_kvm.backends._wayland_socket → urirun_connector_kvm.backends._runtime_dir
  urirun_connector_kvm.backends.is_wayland → urirun_connector_kvm.backends._wayland_socket
  urirun_connector_kvm.backends.is_x11 → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.is_x11 → urirun_connector_kvm.backends._x_display
  urirun_connector_kvm.backends.platform_tag → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_bin
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_mod
  urirun_connector_kvm.backends.Backend.available → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends.dispatch → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends._run → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._portal_python
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_mss → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_pillow → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_im → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_im → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_gnome → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_gnome → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_macos → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends.ensure_ydotoold → urirun_connector_kvm.backends._ydotool_socket
  urirun_connector_kvm.backends._yd_env → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._yd_env → urirun_connector_kvm.backends.ensure_ydotoold
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._runtime_dir
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._x_display
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._wayland_socket
  urirun_connector_kvm.backends._clipboard_set → urirun_connector_kvm.backends.have_bin
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends.backend
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.08s
# nodes: 150 | edges: 214 | modules: 9
# CC̄=3.5

HUBS[20]:
  urirun_connector_kvm.backends.uinput_abs_click
    CC=15  in:1  out:46  total:47
  urirun_connector_kvm.backends.backend
    CC=1  in:39  out:6  total:45
  urirun_connector_kvm.backends._locate_tesseract
    CC=31  in:0  out:44  total:44
  urirun_connector_kvm.core.capture
    CC=15  in:0  out:43  total:43
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.ui_act
    CC=22  in:0  out:38  total:38
  urirun_connector_kvm.core._ok
    CC=1  in:37  out:1  total:38
  urirun_connector_kvm.backends._run
    CC=4  in:26  out:4  total:30
  urirun_connector_kvm.launch_backends._launch_xdg
    CC=20  in:0  out:27  total:27
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.core._fail_from
    CC=1  in:23  out:3  total:26
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.control.route
    CC=20  in:2  out:18  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.core._positioned_click
    CC=8  in:6  out:12  total:18
  urirun_connector_kvm.environment.profile
    CC=10  in:0  out:18  total:18
  urirun_connector_kvm.cdp.launch_session
    CC=10  in:0  out:17  total:17
  urirun_connector_kvm.backends._screen_wh
    CC=8  in:2  out:15  total:17

MODULES:
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [66 funcs]
    available  CC=3  out:2
    missing  CC=5  out:2
    _a11y_atspi  CC=6  out:11
    _atspi_python  CC=5  out:4
    _calib  CC=3  out:3
    _cap_gnome  CC=1  out:2
    _cap_grim  CC=1  out:2
    _cap_im  CC=1  out:2
    _cap_macos  CC=1  out:2
    _cap_mss  CC=2  out:6
  urirun_connector_kvm.cdp  [16 funcs]
    _call  CC=4  out:7
    _copy_auth  CC=4  out:8
    _evaluate  CC=4  out:12
    _find_chrome  CC=4  out:4
    _pages  CC=8  out:9
    _run  CC=2  out:6
    _ws_connect  CC=6  out:14
    _ws_recv  CC=6  out:11
    _ws_send  CC=4  out:13
    act  CC=2  out:3
  urirun_connector_kvm.control  [4 funcs]
    _safe_avail  CC=2  out:1
    act  CC=15  out:14
    report  CC=2  out:2
    route  CC=20  out:18
  urirun_connector_kvm.core  [45 funcs]
    _capture_native  CC=1  out:4
    _cdp_mod  CC=2  out:0
    _click_hit  CC=7  out:14
    _fail_from  CC=1  out:3
    _ok  CC=1  out:1
    _positioned_click  CC=8  out:12
    _router_return  CC=5  out:6
    _surface_mod  CC=2  out:0
    a11y_act  CC=3  out:6
    capture  CC=15  out:43
  urirun_connector_kvm.environment  [3 funcs]
    _safe  CC=2  out:2
    atspi_ready  CC=4  out:3
    profile  CC=10  out:18
  urirun_connector_kvm.launch_backends  [10 funcs]
    _cdp_port  CC=3  out:6
    _desktop_entries  CC=5  out:7
    _find_app  CC=8  out:6
    _launch_macos  CC=5  out:7
    _launch_windows  CC=5  out:8
    _launch_xdg  CC=20  out:27
    _list_macos  CC=5  out:9
    _list_xdg  CC=7  out:10
    _parse_desktop  CC=15  out:10
    _xdg_app_dirs  CC=8  out:11
  urirun_connector_kvm.strategies  [2 funcs]
    available  CC=2  out:2
    is_browser  CC=4  out:3
  urirun_connector_kvm.surface  [2 funcs]
    _active_window  CC=6  out:4
    current  CC=7  out:10

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._xdg_app_dirs
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._parse_desktop
  urirun_connector_kvm.launch_backends._find_app → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._find_app
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._cdp_port
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends._run
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._list_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.strategies.CdpStrategy.available → urirun_connector_kvm.strategies.is_browser
  urirun_connector_kvm.surface.current → urirun_connector_kvm.surface._active_window
  urirun_connector_kvm.backends._wayland_socket → urirun_connector_kvm.backends._runtime_dir
  urirun_connector_kvm.backends.is_wayland → urirun_connector_kvm.backends._wayland_socket
  urirun_connector_kvm.backends.is_x11 → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.is_x11 → urirun_connector_kvm.backends._x_display
  urirun_connector_kvm.backends.platform_tag → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_bin
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_mod
  urirun_connector_kvm.backends.Backend.available → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends.dispatch → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends._run → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._portal_python
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_mss → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_pillow → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_im → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_im → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_gnome → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_gnome → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_macos → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends.ensure_ydotoold → urirun_connector_kvm.backends._ydotool_socket
  urirun_connector_kvm.backends._yd_env → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._yd_env → urirun_connector_kvm.backends.ensure_ydotoold
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._runtime_dir
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._x_display
  urirun_connector_kvm.backends.session_env → urirun_connector_kvm.backends._wayland_socket
  urirun_connector_kvm.backends._clipboard_set → urirun_connector_kvm.backends.have_bin
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends.backend
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 30f 5248L | python:20,yaml:3,shell:3,toml:1,json:1,txt:1 | 2026-06-25
# generated in 0.01s
# CC̅=3.5 | critical:12/286 | dups:0 | cycles:0

HEALTH[12]:
  🟡 CC    _parse_desktop CC=15 (limit:15)
  🟡 CC    _launch_xdg CC=20 (limit:15)
  🟡 CC    _locate_tesseract CC=31 (limit:15)
  🟡 CC    uinput_abs_click CC=15 (limit:15)
  🟡 CC    surface_report CC=28 (limit:15)
  🟡 CC    capture CC=15 (limit:15)
  🟡 CC    ui_act CC=22 (limit:15)
  🟡 CC    route CC=20 (limit:15)
  🟡 CC    act CC=15 (limit:15)
  🟡 CC    handle_action CC=26 (limit:15)
  🟡 CC    handle_legacy_action CC=17 (limit:15)
  🟡 CC    run_one_iteration CC=37 (limit:15)

REFACTOR[1]:
  1. split 12 high-CC methods  (CC>15)

PIPELINES[188]:
  [1] Src [cap]: cap → run
      PURITY: 100% pure
  [2] Src [magenta_frac]: magenta_frac
      PURITY: 100% pure
  [3] Src [find_box]: find_box
      PURITY: 100% pure
  [4] Src [_launch_xdg]: _launch_xdg → backend
      PURITY: 100% pure
  [5] Src [_launch_macos]: _launch_macos → backend
      PURITY: 100% pure
  [6] Src [_launch_windows]: _launch_windows → backend
      PURITY: 100% pure
  [7] Src [_list_xdg]: _list_xdg → backend
      PURITY: 100% pure
  [8] Src [_list_macos]: _list_macos → backend
      PURITY: 100% pure
  [9] Src [available]: available → is_browser
      PURITY: 100% pure
  [10] Src [locate]: locate
      PURITY: 100% pure
  [11] Src [click]: click
      PURITY: 100% pure
  [12] Src [fill]: fill
      PURITY: 100% pure
  [13] Src [available]: available
      PURITY: 100% pure
  [14] Src [locate]: locate
      PURITY: 100% pure
  [15] Src [click]: click
      PURITY: 100% pure
  [16] Src [fill]: fill
      PURITY: 100% pure
  [17] Src [available]: available
      PURITY: 100% pure
  [18] Src [locate]: locate
      PURITY: 100% pure
  [19] Src [_click_xy]: _click_xy
      PURITY: 100% pure
  [20] Src [click]: click
      PURITY: 100% pure
  [21] Src [fill]: fill
      PURITY: 100% pure
  [22] Src [current]: current → _active_window
      PURITY: 100% pure
  [23] Src [is_x11]: is_x11 → is_wayland → _wayland_socket → _runtime_dir
      PURITY: 100% pure
  [24] Src [missing]: missing → have_bin
      PURITY: 100% pure
  [25] Src [available]: available → platform_tag → is_wayland → _wayland_socket → ...(1 more)
      PURITY: 100% pure
  [26] Src [registry_report]: registry_report
      PURITY: 100% pure
  [27] Src [_cap_portal]: _cap_portal → backend
      PURITY: 100% pure
  [28] Src [_cap_grim]: _cap_grim → backend
      PURITY: 100% pure
  [29] Src [_cap_mss]: _cap_mss → backend
      PURITY: 100% pure
  [30] Src [_cap_pillow]: _cap_pillow → backend
      PURITY: 100% pure
  [31] Src [_cap_scrot]: _cap_scrot → backend
      PURITY: 100% pure
  [32] Src [_cap_im]: _cap_im → backend
      PURITY: 100% pure
  [33] Src [_cap_gnome]: _cap_gnome → backend
      PURITY: 100% pure
  [34] Src [_cap_macos]: _cap_macos → backend
      PURITY: 100% pure
  [35] Src [_type_ydotool]: _type_ydotool → backend
      PURITY: 100% pure
  [36] Src [_type_wtype]: _type_wtype → backend
      PURITY: 100% pure
  [37] Src [_type_xdotool]: _type_xdotool → backend
      PURITY: 100% pure
  [38] Src [_type_pynput]: _type_pynput → backend
      PURITY: 100% pure
  [39] Src [_click_ydotool]: _click_ydotool → backend
      PURITY: 100% pure
  [40] Src [_click_xdotool]: _click_xdotool → backend
      PURITY: 100% pure
  [41] Src [_click_pynput]: _click_pynput → backend
      PURITY: 100% pure
  [42] Src [_move_uinput_abs]: _move_uinput_abs → backend
      PURITY: 100% pure
  [43] Src [_move_ydotool]: _move_ydotool → backend
      PURITY: 100% pure
  [44] Src [_move_xdotool]: _move_xdotool → backend
      PURITY: 100% pure
  [45] Src [_move_pynput]: _move_pynput → backend
      PURITY: 100% pure
  [46] Src [_key_ydotool]: _key_ydotool → backend
      PURITY: 100% pure
  [47] Src [_key_xdotool]: _key_xdotool → backend
      PURITY: 100% pure
  [48] Src [_key_pynput]: _key_pynput → backend
      PURITY: 100% pure
  [49] Src [_scroll_ydotool]: _scroll_ydotool → backend
      PURITY: 100% pure
  [50] Src [_scroll_pynput]: _scroll_pynput → backend
      PURITY: 100% pure

LAYERS:
  urirun_connector_kvm/           CC̄=4.3    ←in:0  →out:0
  │ !! backends                  1214L  2C   71m  CC=31     ←2
  │ !! core                       788L  0C   49m  CC=22     ←0
  │ cdp                        307L  0C   16m  CC=10     ←0
  │ !! launch_backends            245L  0C   12m  CC=20     ←0
  │ !! control                    187L  0C    6m  CC=20     ←0
  │ strategies                 129L  3C   14m  CC=4      ←0
  │ environment                 82L  0C    3m  CC=10     ←0
  │ connector.manifest.json     82L  0C    0m  CC=0.0    ←0
  │ surface                     60L  0C    2m  CC=7      ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │
  computer-use-preview/           CC̄=2.3    ←in:0  →out:0
  │ !! agent                      585L  1C   12m  CC=37     ←0
  │ playwright                 418L  1C   33m  CC=5      ←0
  │ computer                   198L  2C   27m  CC=1      ←0
  │ kvm                        190L  1C   33m  CC=11     ←0
  │ main                       101L  0C    1m  CC=4      ←0
  │ browserbase                 80L  1C    3m  CC=3      ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ requirements.txt             8L  0C    0m  CC=0.0    ←0
  │ __init__                     2L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=1.5    ←in:0  →out:0
  │ calibrate_abs               75L  0C    4m  CC=2      ←0
  │ quickstart.sh                5L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ planfile.yaml              188L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                94L  0C    0m  CC=0.0    ←0
  │ project.sh                  69L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              41L  0C    0m  CC=0.0    ←0
  │ Makefile                    13L  0C    0m  CC=0.0    ←0
  │ tree.sh                      4L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     computer-use-preview/computers/browserbase/__init__.py  0L
     computer-use-preview/computers/playwright/__init__.py  0L

COUPLING: no cross-package imports detected

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 0 groups | 0f 0L | 2026-06-25

SUMMARY:
  files_scanned: 0
  total_lines:   0
  dup_groups:    0
  dup_fragments: 0
  saved_lines:   0
  scan_ms:       3
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 282 func | 14f | 2026-06-25
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           urirun_connector_kvm/backends.py
      WHY: 1214L, 2 classes, max CC=31
      EFFORT: ~4h  IMPACT: 37634

  [2] !! SPLIT           computer-use-preview/agent.py
      WHY: 585L, 1 classes, max CC=37
      EFFORT: ~4h  IMPACT: 21645

  [3] !! SPLIT           urirun_connector_kvm/core.py
      WHY: 788L, 0 classes, max CC=22
      EFFORT: ~4h  IMPACT: 17336

  [4] !! SPLIT-FUNC      BrowserAgent.run_one_iteration  CC=37  fan=25
      WHY: CC=37 exceeds 15
      EFFORT: ~1h  IMPACT: 925

  [5] !! SPLIT-FUNC      _locate_tesseract  CC=31  fan=28
      WHY: CC=31 exceeds 15
      EFFORT: ~1h  IMPACT: 868

  [6] !! SPLIT-FUNC      BrowserAgent.handle_action  CC=26  fan=28
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 728

  [7] !  SPLIT-FUNC      ui_act  CC=22  fan=26
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 572

  [8] !  SPLIT-FUNC      _launch_xdg  CC=20  fan=19
      WHY: CC=20 exceeds 15
      EFFORT: ~1h  IMPACT: 380

  [9] !  SPLIT-FUNC      capture  CC=15  fan=24
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 360

  [10] !  SPLIT-FUNC      BrowserAgent.handle_legacy_action  CC=17  fan=19
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 323


RISKS[3]:
  ⚠ Splitting urirun_connector_kvm/backends.py may break 71 import paths
  ⚠ Splitting urirun_connector_kvm/core.py may break 49 import paths
  ⚠ Splitting computer-use-preview/agent.py may break 12 import paths

METRICS-TARGET:
  CC̄:          3.5 → ≤2.4
  max-CC:      37 → ≤18
  god-modules: 3 → 0
  high-CC(≥15): 12 → ≤6
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=3.9 → now CC̄=3.5
```

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
