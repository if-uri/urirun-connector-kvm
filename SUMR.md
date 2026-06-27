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
  runtime: "urirun>=0.4.14, urirun-cdp>=0.1.0";
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
urirun-cdp>=0.1.0
```

## Call Graph

*183 nodes · 254 edges · 12 modules · CC̄=3.5*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 40 | 6 | **46** |
| `_ok` *(in urirun_connector_kvm.core)* | 1 | 41 | 1 | **42** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `capture` *(in urirun_connector_kvm.core)* | 14 ⚠ | 0 | 30 | **30** |
| `_run` *(in urirun_connector_kvm.backends)* | 4 | 25 | 4 | **29** |
| `_fail_from` *(in urirun_connector_kvm.core)* | 1 | 25 | 3 | **28** |
| `_apply_capture_postprocessing` *(in urirun_connector_kvm.core)* | 10 ⚠ | 1 | 27 | **28** |
| `_locate_easyocr` *(in urirun_connector_kvm.backends)* | 14 ⚠ | 0 | 26 | **26** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.08s
# nodes: 183 | edges: 254 | modules: 12
# CC̄=3.5

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:40  out:6  total:46
  urirun_connector_kvm.core._ok
    CC=1  in:41  out:1  total:42
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.capture
    CC=14  in:0  out:30  total:30
  urirun_connector_kvm.backends._run
    CC=4  in:25  out:4  total:29
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:26  total:26
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.environment.browser_sessions
    CC=17  in:0  out:22  total:22
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action
    CC=11  in:0  out:20  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  computer-use-preview.computers.kvm.kvm.KvmComputer._run
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.environment._running_browser_processes
    CC=15  in:1  out:17  total:18
  urirun_connector_kvm.core.cdp_ensure
    CC=6  in:0  out:18  total:18

MODULES:
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  computer-use-preview.computers.computer  [1 funcs]
    navigate  CC=1  out:0
  computer-use-preview.computers.kvm.kvm  [1 funcs]
    _run  CC=11  out:17
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [73 funcs]
    available  CC=3  out:2
    _a11y_atspi  CC=6  out:11
    _atspi_python  CC=5  out:4
    _calib  CC=3  out:3
    _cap_gnome  CC=1  out:2
    _cap_grim  CC=4  out:7
    _cap_im  CC=1  out:2
    _cap_macos  CC=1  out:2
    _cap_mss  CC=2  out:6
    _cap_mutter  CC=2  out:8
  urirun_connector_kvm.cdp  [8 funcs]
    _copy_auth  CC=4  out:8
    _find_chrome  CC=4  out:4
    _run  CC=3  out:8
    act  CC=2  out:3
    await_ready  CC=4  out:7
    find  CC=1  out:1
    launch_session  CC=3  out:8
    start_session  CC=7  out:12
  urirun_connector_kvm.control  [8 funcs]
    _check_post_condition  CC=4  out:3
    _safe_avail  CC=2  out:1
    _try_act_one  CC=9  out:9
    _try_locate_one  CC=4  out:7
    _verify_value  CC=6  out:7
    act  CC=12  out:12
    report  CC=2  out:2
    route  CC=13  out:8
  urirun_connector_kvm.core  [55 funcs]
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
  urirun_connector_kvm.environment  [12 funcs]
    _browser_name_from_binary  CC=9  out:2
    _check_cookies_for_services  CC=9  out:12
    _find_cookie_db  CC=6  out:7
    _parse_browser_args  CC=5  out:6
    _proc_argv  CC=4  out:5
    _proc_ppid  CC=4  out:6
    _running_browser_processes  CC=15  out:17
    _safe  CC=2  out:2
    action_matrix  CC=6  out:16
    atspi_ready  CC=4  out:3
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
  computer-use-preview.agent.BrowserAgent._dispatch_action → computer-use-preview.agent.multiply_numbers
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action → computer-use-preview.agent.multiply_numbers
  urirun_connector_kvm.launch_backends._parse_desktop → urirun_connector_kvm.launch_backends._parse_desktop_section
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._xdg_app_dirs
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._parse_desktop
  urirun_connector_kvm.launch_backends._find_app → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._resolve_launch_argv → urirun_connector_kvm.launch_backends._find_app
  urirun_connector_kvm.launch_backends._resolve_launch_argv → urirun_connector_kvm.launch_backends._strip_field_codes
  urirun_connector_kvm.launch_backends._inject_chrome_flags → urirun_connector_kvm.launch_backends._cdp_port
  urirun_connector_kvm.launch_backends._inject_chrome_flags → urirun_connector_kvm.launch_backends._inject_cdp_profile
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._resolve_launch_argv
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._inject_chrome_flags
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._cdp_wait
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_macos → computer-use-preview.computers.kvm.kvm.KvmComputer._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → computer-use-preview.computers.kvm.kvm.KvmComputer._run
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
  urirun_connector_kvm.backends.Backend.available → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends.dispatch → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends._run → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._portal_python
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends._mutter_python
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._is_wlroots_compositor → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._is_wlroots_compositor
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_mss → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_pillow → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends._run
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
# nodes: 183 | edges: 254 | modules: 12
# CC̄=3.5

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:40  out:6  total:46
  urirun_connector_kvm.core._ok
    CC=1  in:41  out:1  total:42
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.capture
    CC=14  in:0  out:30  total:30
  urirun_connector_kvm.backends._run
    CC=4  in:25  out:4  total:29
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:26  total:26
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.environment.browser_sessions
    CC=17  in:0  out:22  total:22
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action
    CC=11  in:0  out:20  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  computer-use-preview.computers.kvm.kvm.KvmComputer._run
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.environment._running_browser_processes
    CC=15  in:1  out:17  total:18
  urirun_connector_kvm.core.cdp_ensure
    CC=6  in:0  out:18  total:18

MODULES:
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  computer-use-preview.computers.computer  [1 funcs]
    navigate  CC=1  out:0
  computer-use-preview.computers.kvm.kvm  [1 funcs]
    _run  CC=11  out:17
  examples.calibrate_abs  [2 funcs]
    cap  CC=1  out:9
    run  CC=2  out:1
  urirun_connector_kvm.backends  [73 funcs]
    available  CC=3  out:2
    _a11y_atspi  CC=6  out:11
    _atspi_python  CC=5  out:4
    _calib  CC=3  out:3
    _cap_gnome  CC=1  out:2
    _cap_grim  CC=4  out:7
    _cap_im  CC=1  out:2
    _cap_macos  CC=1  out:2
    _cap_mss  CC=2  out:6
    _cap_mutter  CC=2  out:8
  urirun_connector_kvm.cdp  [8 funcs]
    _copy_auth  CC=4  out:8
    _find_chrome  CC=4  out:4
    _run  CC=3  out:8
    act  CC=2  out:3
    await_ready  CC=4  out:7
    find  CC=1  out:1
    launch_session  CC=3  out:8
    start_session  CC=7  out:12
  urirun_connector_kvm.control  [8 funcs]
    _check_post_condition  CC=4  out:3
    _safe_avail  CC=2  out:1
    _try_act_one  CC=9  out:9
    _try_locate_one  CC=4  out:7
    _verify_value  CC=6  out:7
    act  CC=12  out:12
    report  CC=2  out:2
    route  CC=13  out:8
  urirun_connector_kvm.core  [55 funcs]
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
  urirun_connector_kvm.environment  [12 funcs]
    _browser_name_from_binary  CC=9  out:2
    _check_cookies_for_services  CC=9  out:12
    _find_cookie_db  CC=6  out:7
    _parse_browser_args  CC=5  out:6
    _proc_argv  CC=4  out:5
    _proc_ppid  CC=4  out:6
    _running_browser_processes  CC=15  out:17
    _safe  CC=2  out:2
    action_matrix  CC=6  out:16
    atspi_ready  CC=4  out:3
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
  computer-use-preview.agent.BrowserAgent._dispatch_action → computer-use-preview.agent.multiply_numbers
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action → computer-use-preview.agent.multiply_numbers
  urirun_connector_kvm.launch_backends._parse_desktop → urirun_connector_kvm.launch_backends._parse_desktop_section
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._xdg_app_dirs
  urirun_connector_kvm.launch_backends._desktop_entries → urirun_connector_kvm.launch_backends._parse_desktop
  urirun_connector_kvm.launch_backends._find_app → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._resolve_launch_argv → urirun_connector_kvm.launch_backends._find_app
  urirun_connector_kvm.launch_backends._resolve_launch_argv → urirun_connector_kvm.launch_backends._strip_field_codes
  urirun_connector_kvm.launch_backends._inject_chrome_flags → urirun_connector_kvm.launch_backends._cdp_port
  urirun_connector_kvm.launch_backends._inject_chrome_flags → urirun_connector_kvm.launch_backends._inject_cdp_profile
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._resolve_launch_argv
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._inject_chrome_flags
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.launch_backends._cdp_wait
  urirun_connector_kvm.launch_backends._launch_xdg → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_macos → computer-use-preview.computers.kvm.kvm.KvmComputer._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → computer-use-preview.computers.kvm.kvm.KvmComputer._run
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
  urirun_connector_kvm.backends.Backend.available → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends.dispatch → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends._run → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._portal_python
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends._mutter_python
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_mutter → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._is_wlroots_compositor → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends._is_wlroots_compositor
  urirun_connector_kvm.backends._cap_grim → urirun_connector_kvm.backends.session_env
  urirun_connector_kvm.backends._cap_mss → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_pillow → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_scrot → urirun_connector_kvm.backends._run
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 29f 6772L | python:19,shell:3,yaml:3,txt:1,toml:1,json:1 | 2026-06-27
# generated in 0.01s
# CC̅=3.5 | critical:2/323 | dups:0 | cycles:0

HEALTH[2]:
  🟡 CC    _running_browser_processes CC=15 (limit:15)
  🟡 CC    browser_sessions CC=17 (limit:15)

REFACTOR[1]:
  1. split 2 high-CC methods  (CC>15)

PIPELINES[202]:
  [1] Src [cap]: cap → run
      PURITY: 100% pure
  [2] Src [magenta_frac]: magenta_frac
      PURITY: 100% pure
  [3] Src [find_box]: find_box
      PURITY: 100% pure
  [4] Src [__init__]: __init__
      PURITY: 100% pure
  [5] Src [_handle_scroll_at]: _handle_scroll_at
      PURITY: 100% pure
  [6] Src [_handle_drag_and_drop]: _handle_drag_and_drop
      PURITY: 100% pure
  [7] Src [_dispatch_action]: _dispatch_action → multiply_numbers
      PURITY: 100% pure
  [8] Src [_dispatch_legacy_action]: _dispatch_legacy_action → multiply_numbers
      PURITY: 100% pure
  [9] Src [handle_action]: handle_action
      PURITY: 100% pure
  [10] Src [handle_legacy_action]: handle_legacy_action
      PURITY: 100% pure
  [11] Src [get_model_response]: get_model_response
      PURITY: 100% pure
  [12] Src [get_text]: get_text
      PURITY: 100% pure
  [13] Src [extract_function_calls]: extract_function_calls
      PURITY: 100% pure
  [14] Src [_build_function_response]: _build_function_response
      PURITY: 100% pure
  [15] Src [_trim_old_screenshots]: _trim_old_screenshots
      PURITY: 100% pure
  [16] Src [_generate_response]: _generate_response
      PURITY: 100% pure
  [17] Src [_render_turn]: _render_turn
      PURITY: 100% pure
  [18] Src [_execute_function_calls]: _execute_function_calls
      PURITY: 100% pure
  [19] Src [run_one_iteration]: run_one_iteration
      PURITY: 100% pure
  [20] Src [_get_safety_confirmation]: _get_safety_confirmation
      PURITY: 100% pure
  [21] Src [agent_loop]: agent_loop
      PURITY: 100% pure
  [22] Src [denormalize_x]: denormalize_x
      PURITY: 100% pure
  [23] Src [denormalize_y]: denormalize_y
      PURITY: 100% pure
  [24] Src [main]: main
      PURITY: 100% pure
  [25] Src [_handle_new_page]: _handle_new_page
      PURITY: 100% pure
  [26] Src [__enter__]: __enter__
      PURITY: 100% pure
  [27] Src [__exit__]: __exit__
      PURITY: 100% pure
  [28] Src [open_web_browser]: open_web_browser
      PURITY: 100% pure
  [29] Src [click_at]: click_at
      PURITY: 100% pure
  [30] Src [double_click_at]: double_click_at
      PURITY: 100% pure
  [31] Src [triple_click_at]: triple_click_at
      PURITY: 100% pure
  [32] Src [middle_click_at]: middle_click_at
      PURITY: 100% pure
  [33] Src [right_click_at]: right_click_at
      PURITY: 100% pure
  [34] Src [mouse_down]: mouse_down
      PURITY: 100% pure
  [35] Src [mouse_up]: mouse_up
      PURITY: 100% pure
  [36] Src [type_text]: type_text
      PURITY: 100% pure
  [37] Src [wait]: wait
      PURITY: 100% pure
  [38] Src [hover_at]: hover_at
      PURITY: 100% pure
  [39] Src [type_text_at]: type_text_at
      PURITY: 100% pure
  [40] Src [_horizontal_document_scroll]: _horizontal_document_scroll
      PURITY: 100% pure
  [41] Src [scroll_document]: scroll_document
      PURITY: 100% pure
  [42] Src [scroll_at]: scroll_at
      PURITY: 100% pure
  [43] Src [wait_5_seconds]: wait_5_seconds
      PURITY: 100% pure
  [44] Src [go_back]: go_back
      PURITY: 100% pure
  [45] Src [go_forward]: go_forward
      PURITY: 100% pure
  [46] Src [search]: search
      PURITY: 100% pure
  [47] Src [navigate]: navigate
      PURITY: 100% pure
  [48] Src [key_combination]: key_combination
      PURITY: 100% pure
  [49] Src [press_key]: press_key
      PURITY: 100% pure
  [50] Src [key_down]: key_down
      PURITY: 100% pure

LAYERS:
  urirun_connector_kvm/           CC̄=4.4    ←in:0  →out:3
  │ !! backends                  1367L  1C   80m  CC=14     ←1
  │ !! core                      1013L  0C   59m  CC=14     ←0
  │ connector.manifest.json    454L  0C    0m  CC=0.0    ←0
  │ !! environment                401L  0C   12m  CC=17     ←0
  │ launch_backends            284L  0C   16m  CC=11     ←0
  │ cdp                        221L  0C    9m  CC=7      ←0
  │ control                    212L  0C    9m  CC=13     ←0
  │ strategies                 132L  3C   14m  CC=4      ←0
  │ surface                     58L  0C    2m  CC=7      ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │
  computer-use-preview/           CC̄=2.1    ←in:0  →out:0
  │ !! agent                      512L  1C   21m  CC=13     ←0
  │ playwright                 418L  1C   33m  CC=5      ←0
  │ computer                   198L  2C   27m  CC=1      ←1
  │ kvm                        190L  1C   33m  CC=11     ←1
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
  │ !! planfile.yaml              734L  0C    0m  CC=0.0    ←0
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

COUPLING:
                                  computer-use-preview.computers            urirun_connector_kvm
  computer-use-preview.computers                              ──                              ←3
            urirun_connector_kvm                               3                              ──
  CYCLES: none

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 0 groups | 0f 0L | 2026-06-27

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
# code2llm/evolution | 319 func | 14f | 2026-06-27
# generated in 0.00s

NEXT[5] (ranked by impact):
  [1] !! SPLIT           urirun_connector_kvm/backends.py
      WHY: 1367L, 1 classes, max CC=14
      EFFORT: ~4h  IMPACT: 19138

  [2] !! SPLIT           urirun_connector_kvm/core.py
      WHY: 1013L, 0 classes, max CC=14
      EFFORT: ~4h  IMPACT: 14182

  [3] !  SPLIT-FUNC      browser_sessions  CC=17  fan=16
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 272

  [4] !  SPLIT-FUNC      _running_browser_processes  CC=15  fan=16
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 240

  [5] !! SPLIT           planfile.yaml
      WHY: 734L, 0 classes, max CC=0
      EFFORT: ~4h  IMPACT: 0


RISKS[3]:
  ⚠ Splitting urirun_connector_kvm/backends.py may break 80 import paths
  ⚠ Splitting urirun_connector_kvm/core.py may break 59 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          3.5 → ≤2.4
  max-CC:      17 → ≤8
  god-modules: 4 → 0
  high-CC(≥15): 2 → ≤1
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
  prev CC̄=3.3 → now CC̄=3.5
```

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
