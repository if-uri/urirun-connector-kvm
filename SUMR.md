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

workflow[name="contract-ci"] {
  trigger: manual;
  step-1: run cmd=bash ci/contract_ci.sh;
}

workflow[name="xlang"] {
  trigger: manual;
  step-1: run cmd=bash xlang/run.sh && bash xlang/driver.sh && bash xlang/transport_swap.sh;
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

*256 nodes · 321 edges · 20 modules · CC̄=3.8*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `main` *(in xlang.rust.src.main)* | 13 ⚠ | 0 | 49 | **49** |
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 40 | 6 | **46** |
| `_ok` *(in urirun_connector_kvm.core)* | 1 | 41 | 1 | **42** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `capture` *(in urirun_connector_kvm.core)* | 14 ⚠ | 0 | 31 | **31** |
| `main` *(in xlang.peer)* | 21 ⚠ | 0 | 31 | **31** |
| `_run` *(in urirun_connector_kvm.backends)* | 4 | 25 | 4 | **29** |
| `_apply_capture_postprocessing` *(in urirun_connector_kvm.core)* | 10 ⚠ | 1 | 27 | **28** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.12s
# nodes: 256 | edges: 321 | modules: 20
# CC̄=3.8

HUBS[20]:
  xlang.rust.src.main.main
    CC=13  in:0  out:49  total:49
  urirun_connector_kvm.backends.backend
    CC=1  in:40  out:6  total:46
  urirun_connector_kvm.core._ok
    CC=1  in:41  out:1  total:42
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.capture
    CC=14  in:0  out:31  total:31
  xlang.peer.main
    CC=21  in:0  out:31  total:31
  urirun_connector_kvm.backends._run
    CC=4  in:25  out:4  total:29
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:26  total:26
  xlang.rust.src.main.consumer_input_check
    CC=12  in:2  out:24  total:26
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  xlang.emit_jsonschema.to_schema
    CC=17  in:5  out:20  total:25
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.environment.browser_sessions
    CC=17  in:0  out:22  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  xlang.conformance_driver.main
    CC=15  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21

MODULES:
  ci.contract_codegen  [8 funcs]
    _base  CC=2  out:1
    _camel  CC=2  out:5
    _const  CC=3  out:1
    _py_value  CC=8  out:16
    _snake  CC=1  out:2
    go_stub  CC=2  out:12
    js_stub  CC=4  out:20
    py_stub  CC=6  out:12
  ci.contract_shape_lint  [7 funcs]
    _fn_for_route  CC=7  out:8
    _fn_params  CC=2  out:3
    _fn_source  CC=2  out:1
    _is_implemented  CC=2  out:1
    _required_inp_keys  CC=4  out:3
    check_route  CC=17  out:14
    main  CC=5  out:7
  ci.cross_process_roundtrip  [3 funcs]
    _ok_example  CC=4  out:3
    consume  CC=2  out:5
    produce  CC=1  out:2
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  computer-use-preview.computers.computer  [1 funcs]
    navigate  CC=1  out:0
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
  xlang.conformance_driver  [2 funcs]
    drive  CC=4  out:8
    main  CC=15  out:21
  xlang.emit_contracts  [3 funcs]
    _contract_to_json  CC=3  out:2
    build_doc  CC=3  out:2
    main  CC=1  out:8
  xlang.emit_jsonschema  [3 funcs]
    build_doc  CC=2  out:3
    main  CC=1  out:7
    to_schema  CC=17  out:20
  xlang.jsonschema_proof  [2 funcs]
    _valid  CC=4  out:5
    main  CC=10  out:16
  xlang.peer  [36 funcs]
    carried  CC=4  out:4
    check  CC=2  out:1
    conform  CC=18  out:8
    cur  CC=7  out:5
    dig  CC=7  out:5
    ex  CC=2  out:1
    fail  CC=1  out:1
    findWire  CC=3  out:2
    handle  CC=19  out:4
    inp  CC=4  out:4
  xlang.rust.src.main  [10 funcs]
    conform  CC=16  out:18
    consumer_input_check  CC=12  out:24
    contracts  CC=1  out:3
    doc  CC=1  out:2
    find_wire  CC=4  out:4
    load_doc  CC=5  out:13
    main  CC=13  out:49
    ok_example  CC=4  out:7
    wire_payload  CC=5  out:7
    wires  CC=1  out:3

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
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
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._list_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.strategies.CdpStrategy.available → urirun_connector_kvm.strategies.is_browser
  urirun_connector_kvm.surface.current → urirun_connector_kvm.surface._active_window
  urirun_connector_kvm.cdp.start_session → urirun_connector_kvm.cdp._copy_auth
  urirun_connector_kvm.cdp.start_session → urirun_connector_kvm.cdp._find_chrome
  urirun_connector_kvm.cdp.start_session → computer-use-preview.computers.computer.Computer.navigate
  urirun_connector_kvm.cdp.launch_session → urirun_connector_kvm.cdp.start_session
  urirun_connector_kvm.cdp.launch_session → urirun_connector_kvm.cdp.await_ready
  urirun_connector_kvm.cdp.find → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.cdp.act → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.core.capture → urirun_connector_kvm.core._apply_capture_postprocessing
  urirun_connector_kvm.core.display_info → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.display_info → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.type_text → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.type_text → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.key → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.key → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._positioned_click
  urirun_connector_kvm.core.move → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.move → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.wait → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.wait → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.scroll → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.scroll → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._positioned_click
  urirun_connector_kvm.core.triple_click → urirun_connector_kvm.core._ok
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
# generated in 0.12s
# nodes: 256 | edges: 321 | modules: 20
# CC̄=3.8

HUBS[20]:
  xlang.rust.src.main.main
    CC=13  in:0  out:49  total:49
  urirun_connector_kvm.backends.backend
    CC=1  in:40  out:6  total:46
  urirun_connector_kvm.core._ok
    CC=1  in:41  out:1  total:42
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core.capture
    CC=14  in:0  out:31  total:31
  xlang.peer.main
    CC=21  in:0  out:31  total:31
  urirun_connector_kvm.backends._run
    CC=4  in:25  out:4  total:29
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.core._fail_from
    CC=1  in:25  out:3  total:28
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:26  total:26
  xlang.rust.src.main.consumer_input_check
    CC=12  in:2  out:24  total:26
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  xlang.emit_jsonschema.to_schema
    CC=17  in:5  out:20  total:25
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.environment.browser_sessions
    CC=17  in:0  out:22  total:22
  urirun_connector_kvm.core.window_restore
    CC=5  in:0  out:22  total:22
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  xlang.conformance_driver.main
    CC=15  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21

MODULES:
  ci.contract_codegen  [8 funcs]
    _base  CC=2  out:1
    _camel  CC=2  out:5
    _const  CC=3  out:1
    _py_value  CC=8  out:16
    _snake  CC=1  out:2
    go_stub  CC=2  out:12
    js_stub  CC=4  out:20
    py_stub  CC=6  out:12
  ci.contract_shape_lint  [7 funcs]
    _fn_for_route  CC=7  out:8
    _fn_params  CC=2  out:3
    _fn_source  CC=2  out:1
    _is_implemented  CC=2  out:1
    _required_inp_keys  CC=4  out:3
    check_route  CC=17  out:14
    main  CC=5  out:7
  ci.cross_process_roundtrip  [3 funcs]
    _ok_example  CC=4  out:3
    consume  CC=2  out:5
    produce  CC=1  out:2
  computer-use-preview.agent  [3 funcs]
    _dispatch_action  CC=11  out:16
    _dispatch_legacy_action  CC=11  out:20
    multiply_numbers  CC=1  out:0
  computer-use-preview.computers.computer  [1 funcs]
    navigate  CC=1  out:0
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
  xlang.conformance_driver  [2 funcs]
    drive  CC=4  out:8
    main  CC=15  out:21
  xlang.emit_contracts  [3 funcs]
    _contract_to_json  CC=3  out:2
    build_doc  CC=3  out:2
    main  CC=1  out:8
  xlang.emit_jsonschema  [3 funcs]
    build_doc  CC=2  out:3
    main  CC=1  out:7
    to_schema  CC=17  out:20
  xlang.jsonschema_proof  [2 funcs]
    _valid  CC=4  out:5
    main  CC=10  out:16
  xlang.peer  [36 funcs]
    carried  CC=4  out:4
    check  CC=2  out:1
    conform  CC=18  out:8
    cur  CC=7  out:5
    dig  CC=7  out:5
    ex  CC=2  out:1
    fail  CC=1  out:1
    findWire  CC=3  out:2
    handle  CC=19  out:4
    inp  CC=4  out:4
  xlang.rust.src.main  [10 funcs]
    conform  CC=16  out:18
    consumer_input_check  CC=12  out:24
    contracts  CC=1  out:3
    doc  CC=1  out:2
    find_wire  CC=4  out:4
    load_doc  CC=5  out:13
    main  CC=13  out:49
    ok_example  CC=4  out:7
    wire_payload  CC=5  out:7
    wires  CC=1  out:3

EDGES:
  examples.calibrate_abs.cap → examples.calibrate_abs.run
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
  urirun_connector_kvm.launch_backends._launch_macos → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._launch_windows → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.launch_backends._list_xdg → urirun_connector_kvm.launch_backends._desktop_entries
  urirun_connector_kvm.launch_backends._list_macos → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.strategies.CdpStrategy.available → urirun_connector_kvm.strategies.is_browser
  urirun_connector_kvm.surface.current → urirun_connector_kvm.surface._active_window
  urirun_connector_kvm.cdp.start_session → urirun_connector_kvm.cdp._copy_auth
  urirun_connector_kvm.cdp.start_session → urirun_connector_kvm.cdp._find_chrome
  urirun_connector_kvm.cdp.start_session → computer-use-preview.computers.computer.Computer.navigate
  urirun_connector_kvm.cdp.launch_session → urirun_connector_kvm.cdp.start_session
  urirun_connector_kvm.cdp.launch_session → urirun_connector_kvm.cdp.await_ready
  urirun_connector_kvm.cdp.find → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.cdp.act → urirun_connector_kvm.cdp._run
  urirun_connector_kvm.core.capture → urirun_connector_kvm.core._apply_capture_postprocessing
  urirun_connector_kvm.core.display_info → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.display_info → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.type_text → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.type_text → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.key → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.key → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.click → urirun_connector_kvm.core._positioned_click
  urirun_connector_kvm.core.move → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.move → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.wait → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.wait → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.scroll → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.scroll → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._ok
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._fail_from
  urirun_connector_kvm.core.double_click → urirun_connector_kvm.core._positioned_click
  urirun_connector_kvm.core.triple_click → urirun_connector_kvm.core._ok
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 47f 9338L | python:27,shell:7,yaml:3,toml:2,json:1,txt:1,go:1,rust:1 | 2026-06-27
# generated in 0.02s
# CC̅=3.8 | critical:13/447 | dups:0 | cycles:0

HEALTH[13]:
  🟡 CC    _running_browser_processes CC=15 (limit:15)
  🟡 CC    browser_sessions CC=17 (limit:15)
  🟡 CC    conform CC=18 (limit:15)
  🟡 CC    handle CC=19 (limit:15)
  🟡 CC    main CC=21 (limit:15)
  🟡 CC    check CC=27 (limit:15)
  🟡 CC    consumerInputCheck CC=19 (limit:15)
  🟡 CC    conform CC=16 (limit:15)
  🟡 CC    check_route CC=17 (limit:15)
  🟡 CC    to_schema CC=17 (limit:15)
  🟡 CC    main CC=15 (limit:15)
  🟡 CC    check CC=30 (limit:15)
  🟡 CC    conform CC=16 (limit:15)

REFACTOR[1]:
  1. split 13 high-CC methods  (CC>15)

PIPELINES[255]:
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
  [23] Src [_kvm_endpoint]: _kvm_endpoint
      PURITY: 100% pure
  [24] Src [launch_session]: launch_session → start_session → _copy_auth
      PURITY: 100% pure
  [25] Src [find]: find → _run
      PURITY: 100% pure
  [26] Src [act]: act → _run
      PURITY: 100% pure
  [27] Src [capture]: capture → _apply_capture_postprocessing
      PURITY: 100% pure
  [28] Src [display_info]: display_info → _ok
      PURITY: 100% pure
  [29] Src [type_text]: type_text → _ok
      PURITY: 100% pure
  [30] Src [key]: key → _ok
      PURITY: 100% pure
  [31] Src [click]: click → _ok
      PURITY: 100% pure
  [32] Src [move]: move → _ok
      PURITY: 100% pure
  [33] Src [wait]: wait → _ok
      PURITY: 100% pure
  [34] Src [scroll]: scroll → _ok
      PURITY: 100% pure
  [35] Src [double_click]: double_click → _ok
      PURITY: 100% pure
  [36] Src [triple_click]: triple_click → _ok
      PURITY: 100% pure
  [37] Src [right_click]: right_click → _ok
      PURITY: 100% pure
  [38] Src [middle_click]: middle_click → _ok
      PURITY: 100% pure
  [39] Src [hover]: hover → _ok
      PURITY: 100% pure
  [40] Src [drag_and_drop]: drag_and_drop → _ok
      PURITY: 100% pure
  [41] Src [click_abs]: click_abs → _ok
      PURITY: 100% pure
  [42] Src [task_run]: task_run → _ok
      PURITY: 100% pure
  [43] Src [focus]: focus → _ok
      PURITY: 100% pure
  [44] Src [window_list]: window_list → _ok
      PURITY: 100% pure
  [45] Src [window_close]: window_close → _cdp_mod
      PURITY: 100% pure
  [46] Src [window_restore]: window_restore → _cdp_mod
      PURITY: 100% pure
  [47] Src [proc_kill]: proc_kill → _ok
      PURITY: 100% pure
  [48] Src [a11y_act]: a11y_act → _ok
      PURITY: 100% pure
  [49] Src [_click_hit]: _click_hit → _positioned_click
      PURITY: 100% pure
  [50] Src [ui_find]: ui_find → _router_return → _ok
      PURITY: 100% pure

LAYERS:
  xlang/                          CC̄=4.6    ←in:0  →out:0
  │ !! peer.go                    542L  1C   17m  CC=27     ←1
  │ !! main.rs                    479L  0C   17m  CC=30     ←1
  │ !! conformance_driver         123L  1C    5m  CC=15     ←0
  │ !! emit_jsonschema            109L  0C    4m  CC=17     ←0
  │ run.sh                      98L  0C    1m  CC=0.0    ←0
  │ jsonschema_proof            69L  0C    2m  CC=10     ←0
  │ emit_contracts              62L  0C    3m  CC=3      ←0
  │ driver.sh                   26L  0C    0m  CC=0.0    ←0
  │ transport_swap.sh           24L  0C    0m  CC=0.0    ←0
  │ Cargo.toml                  19L  0C    0m  CC=0.0    ←0
  │ !! peer.mjs                     0L  1C   49m  CC=19     ←0
  │ peer                         0L  0C    2m  CC=4      ←0
  │ transport_swap               0L  1C    4m  CC=12     ←0
  │
  urirun_connector_kvm/           CC̄=4.4    ←in:0  →out:1
  │ !! backends                  1387L  1C   80m  CC=14     ←1
  │ !! core                      1038L  0C   59m  CC=14     ←0
  │ connector.manifest.json    454L  0C    0m  CC=0.0    ←0
  │ !! environment                401L  0C   12m  CC=17     ←0
  │ launch_backends            284L  0C   16m  CC=11     ←0
  │ cdp                        221L  0C    9m  CC=7      ←1
  │ control                    212L  0C    9m  CC=13     ←0
  │ contracts                  207L  0C    0m  CC=0.0    ←0
  │ strategies                 132L  3C   14m  CC=4      ←0
  │ surface                     58L  0C    2m  CC=7      ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │
  ci/                             CC̄=4.2    ←in:0  →out:3
  │ !! contract_shape_lint        143L  0C    8m  CC=17     ←0
  │ contract_codegen           140L  0C    8m  CC=8      ←0
  │ cross_process_roundtrip     83L  0C    4m  CC=6      ←0
  │ contract_ci.sh              68L  0C    0m  CC=0.0    ←0
  │
  computer-use-preview/           CC̄=2.1    ←in:0  →out:0
  │ !! agent                      512L  1C   21m  CC=13     ←0
  │ playwright                 418L  1C   33m  CC=5      ←0
  │ computer                   198L  2C   27m  CC=1      ←1
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
  │ !! planfile.yaml             1059L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                94L  0C    0m  CC=0.0    ←0
  │ project.sh                  69L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              44L  0C    0m  CC=0.0    ←0
  │ Makefile                    17L  0C    0m  CC=0.0    ←0
  │ tree.sh                      4L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     computer-use-preview/computers/playwright/__init__.py  0L
     xlang/peer.mjs                            0L
     xlang/peer.py                             0L
     xlang/transport_swap.py                   0L

COUPLING:
                                                              ci                      xlang.rust  computer-use-preview.computers            urirun_connector_kvm
                              ci                              ──                               3                                                                
                      xlang.rust                              ←3                              ──                                                                
  computer-use-preview.computers                                                                                              ──                              ←1
            urirun_connector_kvm                                                                                               1                              ──
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
  scan_ms:       3
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 443 func | 27f | 2026-06-27
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           urirun_connector_kvm/backends.py
      WHY: 1387L, 1 classes, max CC=14
      EFFORT: ~4h  IMPACT: 19418

  [2] !! SPLIT           urirun_connector_kvm/core.py
      WHY: 1038L, 0 classes, max CC=14
      EFFORT: ~4h  IMPACT: 14532

  [3] !! SPLIT-FUNC      check  CC=30  fan=26
      WHY: CC=30 exceeds 15
      EFFORT: ~1h  IMPACT: 780

  [4] !  SPLIT-FUNC      main  CC=21  fan=31
      WHY: CC=21 exceeds 15
      EFFORT: ~1h  IMPACT: 651

  [5] !! SPLIT-FUNC      check  CC=27  fan=11
      WHY: CC=27 exceeds 15
      EFFORT: ~1h  IMPACT: 297

  [6] !  SPLIT-FUNC      conform  CC=16  fan=18
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 288

  [7] !  SPLIT-FUNC      browser_sessions  CC=17  fan=16
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 272

  [8] !  SPLIT-FUNC      _running_browser_processes  CC=15  fan=16
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 240

  [9] !  SPLIT-FUNC      to_schema  CC=17  fan=13
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 221

  [10] !  SPLIT-FUNC      check_route  CC=17  fan=11
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 187


RISKS[3]:
  ⚠ Splitting urirun_connector_kvm/backends.py may break 80 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths
  ⚠ Splitting urirun_connector_kvm/core.py may break 59 import paths

METRICS-TARGET:
  CC̄:          3.8 → ≤2.7
  max-CC:      30 → ≤15
  god-modules: 5 → 0
  high-CC(≥15): 13 → ≤6
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
  prev CC̄=3.6 → now CC̄=3.8
```

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
