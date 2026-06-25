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

*181 nodes · 261 edges · 10 modules · CC̄=3.3*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 39 | 6 | **45** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `_ok` *(in urirun_connector_kvm.core)* | 1 | 40 | 1 | **41** |
| `_run` *(in urirun_connector_kvm.backends)* | 4 | 26 | 4 | **30** |
| `_fail_from` *(in urirun_connector_kvm.core)* | 1 | 25 | 3 | **28** |
| `_apply_capture_postprocessing` *(in urirun_connector_kvm.core)* | 10 ⚠ | 1 | 27 | **28** |
| `_locate_easyocr` *(in urirun_connector_kvm.backends)* | 14 ⚠ | 0 | 26 | **26** |
| `profile` *(in urirun_connector_kvm.environment)* | 13 ⚠ | 0 | 25 | **25** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.09s
# nodes: 181 | edges: 261 | modules: 10
# CC̄=3.3

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:39  out:6  total:45
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core._ok
    CC=1  in:40  out:1  total:41
  urirun_connector_kvm.backends._run
    CC=4  in:26  out:4  total:30
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:25  total:25
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action
    CC=11  in:0  out:20  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.core._positioned_click
    CC=8  in:6  out:12  total:18
  urirun_connector_kvm.core.cdp_ensure
    CC=6  in:0  out:18  total:18
  urirun_connector_kvm.core.ui_act
    CC=7  in:0  out:17  total:17
  urirun_connector_kvm.core.capture
    CC=6  in:0  out:17  total:17
  urirun_connector_kvm.backends._screen_wh
    CC=8  in:2  out:15  total:17

MODULES:
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [73 funcs]
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
  urirun_connector_kvm.cdp  [18 funcs]
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
  urirun_connector_kvm.control  [8 funcs]
    _check_post_condition  CC=4  out:3
    _safe_avail  CC=2  out:1
    _try_act_one  CC=9  out:9
    _try_locate_one  CC=4  out:7
    _verify_value  CC=6  out:7
    act  CC=12  out:12
    report  CC=2  out:2
    route  CC=13  out:8
  urirun_connector_kvm.core  [54 funcs]
    _act_ready  CC=3  out:5
    _act_reject  CC=10  out:6
    _act_retry_loop  CC=5  out:13
    _apply_capture_postprocessing  CC=10  out:27
    _capture_native  CC=1  out:4
    _cdp_mod  CC=2  out:0
    _click_hit  CC=7  out:14
    _fail_from  CC=1  out:3
    _ok  CC=1  out:1
    _positioned_click  CC=8  out:12
  urirun_connector_kvm.environment  [3 funcs]
    _safe  CC=2  out:2
    atspi_ready  CC=4  out:3
    profile  CC=13  out:25
  urirun_connector_kvm.launch_backends  [16 funcs]
    _cdp_port  CC=3  out:6
    _cdp_wait  CC=6  out:8
    _desktop_entries  CC=5  out:7
    _find_app  CC=8  out:6
    _inject_cdp_profile  CC=6  out:4
    _inject_chrome_flags  CC=10  out:10
    _launch_macos  CC=5  out:7
    _launch_windows  CC=5  out:8
    _launch_xdg  CC=6  out:13
    _list_macos  CC=5  out:9
  urirun_connector_kvm.strategies  [2 funcs]
    available  CC=2  out:2
    is_browser  CC=4  out:3
  urirun_connector_kvm.surface  [2 funcs]
    _active_window  CC=6  out:4
    current  CC=7  out:10

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
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
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._clipboard_set
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._yd_keyseq
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_pynput → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._click_xdotool → urirun_connector_kvm.backends.backend
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
# generated in 0.09s
# nodes: 181 | edges: 261 | modules: 10
# CC̄=3.3

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:39  out:6  total:45
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core._ok
    CC=1  in:40  out:1  total:41
  urirun_connector_kvm.backends._run
    CC=4  in:26  out:4  total:30
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:25  total:25
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action
    CC=11  in:0  out:20  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.core._positioned_click
    CC=8  in:6  out:12  total:18
  urirun_connector_kvm.core.cdp_ensure
    CC=6  in:0  out:18  total:18
  urirun_connector_kvm.core.ui_act
    CC=7  in:0  out:17  total:17
  urirun_connector_kvm.core.capture
    CC=6  in:0  out:17  total:17
  urirun_connector_kvm.backends._screen_wh
    CC=8  in:2  out:15  total:17

MODULES:
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [73 funcs]
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
  urirun_connector_kvm.cdp  [18 funcs]
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
  urirun_connector_kvm.control  [8 funcs]
    _check_post_condition  CC=4  out:3
    _safe_avail  CC=2  out:1
    _try_act_one  CC=9  out:9
    _try_locate_one  CC=4  out:7
    _verify_value  CC=6  out:7
    act  CC=12  out:12
    report  CC=2  out:2
    route  CC=13  out:8
  urirun_connector_kvm.core  [54 funcs]
    _act_ready  CC=3  out:5
    _act_reject  CC=10  out:6
    _act_retry_loop  CC=5  out:13
    _apply_capture_postprocessing  CC=10  out:27
    _capture_native  CC=1  out:4
    _cdp_mod  CC=2  out:0
    _click_hit  CC=7  out:14
    _fail_from  CC=1  out:3
    _ok  CC=1  out:1
    _positioned_click  CC=8  out:12
  urirun_connector_kvm.environment  [3 funcs]
    _safe  CC=2  out:2
    atspi_ready  CC=4  out:3
    profile  CC=13  out:25
  urirun_connector_kvm.launch_backends  [16 funcs]
    _cdp_port  CC=3  out:6
    _cdp_wait  CC=6  out:8
    _desktop_entries  CC=5  out:7
    _find_app  CC=8  out:6
    _inject_cdp_profile  CC=6  out:4
    _inject_chrome_flags  CC=10  out:10
    _launch_macos  CC=5  out:7
    _launch_windows  CC=5  out:8
    _launch_xdg  CC=6  out:13
    _list_macos  CC=5  out:9
  urirun_connector_kvm.strategies  [2 funcs]
    available  CC=2  out:2
    is_browser  CC=4  out:3
  urirun_connector_kvm.surface  [2 funcs]
    _active_window  CC=6  out:4
    current  CC=7  out:10

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
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
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._clipboard_set
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._yd_keyseq
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_pynput → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._click_xdotool → urirun_connector_kvm.backends.backend
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 29f 6219L | python:19,yaml:3,shell:3,toml:1,json:1,txt:1 | 2026-06-25
# generated in 0.01s
# CC̅=3.3 | critical:0/321 | dups:0 | cycles:0

HEALTH[0]: ok

REFACTOR[0]: none needed

PIPELINES[200]:
  [1] Src [cap]: cap → run
      PURITY: 100% pure
  [2] Src [magenta_frac]: magenta_frac
      PURITY: 100% pure
  [3] Src [find_box]: find_box
      PURITY: 100% pure
  [4] Src [available]: available → is_browser
      PURITY: 100% pure
  [5] Src [locate]: locate
      PURITY: 100% pure
  [6] Src [click]: click
      PURITY: 100% pure
  [7] Src [fill]: fill
      PURITY: 100% pure
  [8] Src [available]: available
      PURITY: 100% pure
  [9] Src [locate]: locate
      PURITY: 100% pure
  [10] Src [click]: click
      PURITY: 100% pure
  [11] Src [fill]: fill
      PURITY: 100% pure
  [12] Src [available]: available
      PURITY: 100% pure
  [13] Src [locate]: locate
      PURITY: 100% pure
  [14] Src [_click_xy]: _click_xy
      PURITY: 100% pure
  [15] Src [click]: click
      PURITY: 100% pure
  [16] Src [fill]: fill
      PURITY: 100% pure
  [17] Src [current]: current → _active_window
      PURITY: 100% pure
  [18] Src [is_x11]: is_x11 → is_wayland → _wayland_socket → _runtime_dir
      PURITY: 100% pure
  [19] Src [missing]: missing → have_bin
      PURITY: 100% pure
  [20] Src [available]: available → platform_tag → is_wayland → _wayland_socket → ...(1 more)
      PURITY: 100% pure
  [21] Src [registry_report]: registry_report
      PURITY: 100% pure
  [22] Src [_cap_portal]: _cap_portal → backend
      PURITY: 100% pure
  [23] Src [_cap_grim]: _cap_grim → backend
      PURITY: 100% pure
  [24] Src [_cap_mss]: _cap_mss → backend
      PURITY: 100% pure
  [25] Src [_cap_pillow]: _cap_pillow → backend
      PURITY: 100% pure
  [26] Src [_cap_scrot]: _cap_scrot → backend
      PURITY: 100% pure
  [27] Src [_cap_im]: _cap_im → backend
      PURITY: 100% pure
  [28] Src [_cap_gnome]: _cap_gnome → backend
      PURITY: 100% pure
  [29] Src [_cap_macos]: _cap_macos → backend
      PURITY: 100% pure
  [30] Src [_type_ydotool]: _type_ydotool → backend
      PURITY: 100% pure
  [31] Src [_type_wtype]: _type_wtype → backend
      PURITY: 100% pure
  [32] Src [_type_xdotool]: _type_xdotool → backend
      PURITY: 100% pure
  [33] Src [_type_pynput]: _type_pynput → backend
      PURITY: 100% pure
  [34] Src [_click_ydotool]: _click_ydotool → backend
      PURITY: 100% pure
  [35] Src [_click_xdotool]: _click_xdotool → backend
      PURITY: 100% pure
  [36] Src [_click_pynput]: _click_pynput → backend
      PURITY: 100% pure
  [37] Src [_move_uinput_abs]: _move_uinput_abs → backend
      PURITY: 100% pure
  [38] Src [_move_ydotool]: _move_ydotool → backend
      PURITY: 100% pure
  [39] Src [_move_xdotool]: _move_xdotool → backend
      PURITY: 100% pure
  [40] Src [_move_pynput]: _move_pynput → backend
      PURITY: 100% pure
  [41] Src [_key_ydotool]: _key_ydotool → backend
      PURITY: 100% pure
  [42] Src [_key_xdotool]: _key_xdotool → backend
      PURITY: 100% pure
  [43] Src [_key_pynput]: _key_pynput → backend
      PURITY: 100% pure
  [44] Src [_scroll_ydotool]: _scroll_ydotool → backend
      PURITY: 100% pure
  [45] Src [_scroll_pynput]: _scroll_pynput → backend
      PURITY: 100% pure
  [46] Src [_focus_wmctrl]: _focus_wmctrl → backend
      PURITY: 100% pure
  [47] Src [_focus_pgw]: _focus_pgw → backend
      PURITY: 100% pure
  [48] Src [_winlist_wmctrl]: _winlist_wmctrl → backend
      PURITY: 100% pure
  [49] Src [_focus_atspi]: _focus_atspi → backend
      PURITY: 100% pure
  [50] Src [_locate_tesseract]: _locate_tesseract → backend
      PURITY: 100% pure

LAYERS:
  urirun_connector_kvm/           CC̄=4.1    ←in:0  →out:0
  │ !! backends                  1292L  2C   79m  CC=14     ←2
  │ !! core                       925L  0C   58m  CC=13     ←0
  │ cdp                        348L  0C   18m  CC=8      ←0
  │ launch_backends            282L  0C   16m  CC=11     ←0
  │ control                    214L  0C    9m  CC=13     ←0
  │ strategies                 129L  3C   14m  CC=4      ←0
  │ environment                 94L  0C    3m  CC=13     ←0
  │ connector.manifest.json     89L  0C    0m  CC=0.0    ←0
  │ surface                     60L  0C    2m  CC=7      ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │
  computer-use-preview/           CC̄=2.1    ←in:0  →out:0
  │ !! agent                      512L  1C   21m  CC=13     ←0
  │ playwright                 418L  1C   33m  CC=5      ←0
  │ computer                   198L  2C   27m  CC=1      ←0
  │ kvm                        190L  1C   33m  CC=11     ←0
  │ main                       101L  0C    1m  CC=4      ←0
  │ browserbase                 80L  1C    3m  CC=3      ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ requirements.txt             8L  0C    0m  CC=0.0    ←0
  │ __init__                     2L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=1.5    ←in:0  →out:0
  │ calibrate_abs               75L  0C    4m  CC=2      ←0
  │ quickstart.sh                5L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml              890L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                94L  0C    0m  CC=0.0    ←0
  │ project.sh                  69L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              44L  0C    0m  CC=0.0    ←0
  │ Makefile                    13L  0C    0m  CC=0.0    ←0
  │ tree.sh                      4L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
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
  scan_ms:       4
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 317 func | 14f | 2026-06-25
# generated in 0.00s

NEXT[3] (ranked by impact):
  [1] !! SPLIT           urirun_connector_kvm/backends.py
      WHY: 1292L, 2 classes, max CC=14
      EFFORT: ~4h  IMPACT: 18088

  [2] !! SPLIT           urirun_connector_kvm/core.py
      WHY: 925L, 0 classes, max CC=13
      EFFORT: ~4h  IMPACT: 12025

  [3] !! SPLIT           planfile.yaml
      WHY: 890L, 0 classes, max CC=0
      EFFORT: ~4h  IMPACT: 0


RISKS[3]:
  ⚠ Splitting urirun_connector_kvm/backends.py may break 79 import paths
  ⚠ Splitting urirun_connector_kvm/core.py may break 58 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          3.3 → ≤2.3
  max-CC:      14 → ≤7
  god-modules: 4 → 0
  high-CC(≥15): 0 → ≤0
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
  prev CC̄=3.3 → now CC̄=3.3
```

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
