# urirun-connector-kvm

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Interfaces](#interfaces)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Makefile Targets](#makefile-targets)
- [Code Analysis](#code-analysis)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Intent](#intent)

## Metadata

- **name**: `urirun-connector-kvm`
- **version**: `0.3.0`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, testql(1), app.doql.less, project/(3 analysis files)

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
  step-1: run cmd=urirun-connector-kvm manifest;
}

workflow[name="bindings"] {
  trigger: manual;
  step-1: run cmd=urirun-connector-kvm bindings;
}

workflow[name="smoke"] {
  trigger: manual;
  step-1: run cmd=urirun-connector-kvm bindings | urirun connectors smoke - \;
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

## Interfaces

### CLI Entry Points

- `urirun-kvm`

### testql Scenarios

#### `testql-scenarios/generated-cli-tests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-cli-tests.testql.toon.yaml
# SCENARIO: CLI Command Tests
# TYPE: cli
# GENERATED: true

CONFIG[2]{key, value}:
  cli_command, python -m urirun-connector-kvm
  timeout_ms, 10000

# Test 1: CLI help command
SHELL "python -m urirun-connector-kvm --help" 5000
ASSERT_EXIT_CODE 0
ASSERT_STDOUT_CONTAINS "usage"

# Test 2: CLI version command
SHELL "python -m urirun-connector-kvm --version" 5000
ASSERT_EXIT_CODE 0

# Test 3: CLI main workflow (dry-run)
SHELL "python -m urirun-connector-kvm --help" 10000
ASSERT_EXIT_CODE 0
```

## Workflows

## Configuration

```yaml
project:
  name: urirun-connector-kvm
  version: 0.3.0
  env: local
```

## Dependencies

### Runtime

```text markpact:deps python
urirun>=0.4.14
```

## Deployment

```bash markpact:run
pip install urirun-connector-kvm

# development install
pip install -e .[dev]
```

## Makefile Targets

- `help`
- `manifest`
- `bindings`
- `smoke`
- `test`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# urirun-connector-kvm | 8f 1902L | python:4,shell:3,less:1 | 2026-06-25
# stats: 109 func | 2 cls | 8 mod | CC̄=3.8 | critical:8 | cycles:0
# alerts[5]: CC _locate_tesseract=26; CC _parse_desktop=15; CC capture=15; CC _locate_easyocr=14; CC task_run=13
# hotspots[5]: _locate_tesseract fan=25; capture fan=23; _locate_easyocr fan=18; uinput_abs_click fan=15; _launch_xdg fan=14
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[8]:
  app.doql.less,61
  examples/quickstart.sh,6
  project.sh,69
  tests/test_kvm.py,160
  tree.sh,5
  urirun_connector_kvm/__init__.py,31
  urirun_connector_kvm/backends.py,1112
  urirun_connector_kvm/core.py,458
D:
  tests/test_kvm.py:
    e: test_key_requires_value,test_type_requires_value,test_no_backend_reports_install_hint,test_backend_decorator_registers_and_sorts,test_dispatch_falls_through_on_failure,test_unavailable_backend_skipped_by_needs,test_bindings_are_isolated_handlers,test_runtime_executes_from_compiled_registry,test_doctor_reports_backends,test_capture_tags_screenshot_as_frozen_artifact,test_manifest_prose_plus_derived_routes,test_cli_bindings_and_manifest
    test_key_requires_value()
    test_type_requires_value()
    test_no_backend_reports_install_hint(monkeypatch)
    test_backend_decorator_registers_and_sorts()
    test_dispatch_falls_through_on_failure()
    test_unavailable_backend_skipped_by_needs(monkeypatch)
    test_bindings_are_isolated_handlers()
    test_runtime_executes_from_compiled_registry(monkeypatch)
    test_doctor_reports_backends()
    test_capture_tags_screenshot_as_frozen_artifact(monkeypatch)
    test_manifest_prose_plus_derived_routes()
    test_cli_bindings_and_manifest(capsys)
  urirun_connector_kvm/__init__.py:
  urirun_connector_kvm/backends.py:
    e: is_wayland,is_x11,platform_tag,have_bin,have_mod,backend,dispatch,registry_report,_run,_portal_python,_cap_portal,_cap_grim,_cap_mss,_cap_pillow,_cap_scrot,_cap_im,_cap_gnome,_cap_macos,_ydotool_socket,ensure_ydotoold,_yd_env,_yd_keyseq,_type_ydotool,_type_wtype,_type_xdotool,_type_pynput,_click_ydotool,_click_xdotool,_click_pynput,_move_ydotool,_move_xdotool,_move_pynput,_key_ydotool,_key_xdotool,_key_pynput,_scroll_ydotool,_scroll_pynput,_focus_wmctrl,_focus_pgw,_winlist_wmctrl,_xdg_app_dirs,_parse_desktop,_desktop_entries,_strip_field_codes,_find_app,_launch_xdg,_launch_macos,_launch_windows,_list_xdg,_list_macos,_atspi_python,_focus_atspi,_a11y_atspi,_tsv_lines,_locate_tesseract,_easyocr_reader,_locate_easyocr,bbox_center,_locate_atspi,_capture_tmp,_locate_imgl,_locate_vql,_ui_io,_ui_iow,uinput_available,_uinput_create_abs,uinput_abs_click,_gnome_monitors,surface_report,Backend,BackendError
    Backend: missing(0),available(0)
    BackendError:
    is_wayland()
    is_x11()
    platform_tag()
    have_bin(name)
    have_mod(name)
    backend(action;name)
    dispatch(action)
    registry_report()
    _run(argv)
    _portal_python()
    _cap_portal(output)
    _cap_grim(output)
    _cap_mss(output;monitor)
    _cap_pillow(output)
    _cap_scrot(output)
    _cap_im(output)
    _cap_gnome(output)
    _cap_macos(output)
    _ydotool_socket()
    ensure_ydotoold()
    _yd_env()
    _yd_keyseq(combo)
    _type_ydotool(text)
    _type_wtype(text)
    _type_xdotool(text)
    _type_pynput(text)
    _click_ydotool(button)
    _click_xdotool(button)
    _click_pynput(button)
    _move_ydotool(x;y)
    _move_xdotool(x;y)
    _move_pynput(x;y)
    _key_ydotool(keys)
    _key_xdotool(keys)
    _key_pynput(keys)
    _scroll_ydotool(dy)
    _scroll_pynput(dy)
    _focus_wmctrl(title)
    _focus_pgw(title)
    _winlist_wmctrl()
    _xdg_app_dirs()
    _parse_desktop(path)
    _desktop_entries()
    _strip_field_codes(exec_line)
    _find_app(query)
    _launch_xdg(app;compose;args;settle)
    _launch_macos(app;args;settle)
    _launch_windows(app;args;settle)
    _list_xdg(filter)
    _list_macos(filter)
    _atspi_python()
    _focus_atspi(title)
    _a11y_atspi(app;role;name;op;text;nth)
    _tsv_lines(tsv;min_conf)
    _locate_tesseract(image;query;text;role;min_conf)
    _easyocr_reader()
    _locate_easyocr(image;query;text;role;min_conf)
    bbox_center(bbox)
    _locate_atspi(text;role;app;nth)
    _capture_tmp()
    _locate_imgl(text;role)
    _locate_vql(text;role)
    _ui_io(nr)
    _ui_iow(nr;sz)
    uinput_available()
    _uinput_create_abs()
    uinput_abs_click(x;y;sw;sh;button;do_click;settle)
    _gnome_monitors()
    surface_report()
  urirun_connector_kvm/core.py:
    e: _ok,_fail_from,capture,type_text,key,click,move,scroll,click_abs,task_run,focus,window_list,a11y_act,_click_hit,ui_find,ui_click,ui_fill,ui_wait,ui_verify,_capture_native,ui_locate,ui_click_text,doctor,launch,list_apps,urirun_bindings,connector_manifest,main
    _ok()
    _fail_from(action;exc)
    capture(output;monitor;max_width;base64;cx;cy;zoom;crop_w;crop_h)
    type_text(text)
    key(key;keys)
    click(button;x;y)
    move(x;y)
    scroll(dy)
    click_abs(x;y;sw;sh;button;do_click)
    task_run(steps)
    focus(title)
    window_list()
    a11y_act(app;role;name;action;text;nth)
    _click_hit(hit;app;role;text)
    ui_find(text;role;app;nth)
    ui_click(text;role;app)
    ui_fill(text;role;app;value;verify)
    ui_wait(text;role;app;timeout;interval)
    ui_verify(expect;app)
    _capture_native(monitor)
    ui_locate(query;min_conf;monitor)
    ui_click_text(text;button;nth;min_conf;then_type;then_key;monitor)
    doctor()
    launch(app;compose;args;settle)
    list_apps(filter)
    urirun_bindings()
    connector_manifest()
    main(argv)
```

### `project/logic.pl`

```prolog markpact:analysis path=project/logic.pl
% ── Project Metadata ─────────────────────────────────────
project_metadata('urirun-connector-kvm', '0.3.0', 'python').

% ── Project Files ────────────────────────────────────────
project_file('app.doql.less', 61, 'less').
project_file('examples/quickstart.sh', 6, 'shell').
project_file('project.sh', 69, 'shell').
project_file('tests/test_kvm.py', 160, 'python').
project_file('tree.sh', 5, 'shell').
project_file('urirun_connector_kvm/__init__.py', 31, 'python').
project_file('urirun_connector_kvm/backends.py', 1112, 'python').
project_file('urirun_connector_kvm/core.py', 458, 'python').

% ── Python Functions ─────────────────────────────────────
python_function('tests/test_kvm.py', 'test_key_requires_value', 0, 2, 1).
python_function('tests/test_kvm.py', 'test_type_requires_value', 0, 2, 1).
python_function('tests/test_kvm.py', 'test_no_backend_reports_install_hint', 1, 2, 2).
python_function('tests/test_kvm.py', 'test_backend_decorator_registers_and_sorts', 0, 3, 3).
python_function('tests/test_kvm.py', 'test_dispatch_falls_through_on_failure', 0, 2, 3).
python_function('tests/test_kvm.py', 'test_unavailable_backend_skipped_by_needs', 1, 2, 2).
python_function('tests/test_kvm.py', 'test_bindings_are_isolated_handlers', 0, 6, 3).
python_function('tests/test_kvm.py', 'test_runtime_executes_from_compiled_registry', 1, 3, 8).
python_function('tests/test_kvm.py', 'test_doctor_reports_backends', 0, 5, 2).
python_function('tests/test_kvm.py', 'test_capture_tags_screenshot_as_frozen_artifact', 1, 2, 3).
python_function('tests/test_kvm.py', 'test_manifest_prose_plus_derived_routes', 0, 5, 2).
python_function('tests/test_kvm.py', 'test_cli_bindings_and_manifest', 1, 5, 3).
python_function('urirun_connector_kvm/backends.py', 'is_wayland', 0, 2, 3).
python_function('urirun_connector_kvm/backends.py', 'is_x11', 0, 2, 3).
python_function('urirun_connector_kvm/backends.py', 'platform_tag', 0, 5, 2).
python_function('urirun_connector_kvm/backends.py', 'have_bin', 1, 1, 1).
python_function('urirun_connector_kvm/backends.py', 'have_mod', 1, 2, 1).
python_function('urirun_connector_kvm/backends.py', 'backend', 2, 1, 5).
python_function('urirun_connector_kvm/backends.py', 'dispatch', 1, 11, 9).
python_function('urirun_connector_kvm/backends.py', 'registry_report', 0, 3, 4).
python_function('urirun_connector_kvm/backends.py', '_run', 1, 3, 3).
python_function('urirun_connector_kvm/backends.py', '_portal_python', 0, 5, 3).
python_function('urirun_connector_kvm/backends.py', '_cap_portal', 1, 2, 13).
python_function('urirun_connector_kvm/backends.py', '_cap_grim', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_cap_mss', 2, 2, 6).
python_function('urirun_connector_kvm/backends.py', '_cap_pillow', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_cap_scrot', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_cap_im', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_cap_gnome', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_cap_macos', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_ydotool_socket', 0, 2, 2).
python_function('urirun_connector_kvm/backends.py', 'ensure_ydotoold', 0, 4, 7).
python_function('urirun_connector_kvm/backends.py', '_yd_env', 0, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_yd_keyseq', 1, 6, 6).
python_function('urirun_connector_kvm/backends.py', '_type_ydotool', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_type_wtype', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_type_xdotool', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_type_pynput', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_click_ydotool', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_click_xdotool', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_click_pynput', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_move_ydotool', 2, 1, 5).
python_function('urirun_connector_kvm/backends.py', '_move_xdotool', 2, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_move_pynput', 2, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_key_ydotool', 1, 2, 5).
python_function('urirun_connector_kvm/backends.py', '_key_xdotool', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_key_pynput', 1, 6, 8).
python_function('urirun_connector_kvm/backends.py', '_scroll_ydotool', 1, 1, 5).
python_function('urirun_connector_kvm/backends.py', '_scroll_pynput', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_focus_wmctrl', 1, 1, 2).
python_function('urirun_connector_kvm/backends.py', '_focus_pgw', 1, 2, 4).
python_function('urirun_connector_kvm/backends.py', '_winlist_wmctrl', 0, 3, 6).
python_function('urirun_connector_kvm/backends.py', '_xdg_app_dirs', 0, 8, 8).
python_function('urirun_connector_kvm/backends.py', '_parse_desktop', 1, 15, 9).
python_function('urirun_connector_kvm/backends.py', '_desktop_entries', 0, 5, 7).
python_function('urirun_connector_kvm/backends.py', '_strip_field_codes', 1, 6, 4).
python_function('urirun_connector_kvm/backends.py', '_find_app', 1, 8, 3).
python_function('urirun_connector_kvm/backends.py', '_launch_xdg', 4, 7, 14).
python_function('urirun_connector_kvm/backends.py', '_launch_macos', 3, 5, 7).
python_function('urirun_connector_kvm/backends.py', '_launch_windows', 3, 5, 8).
python_function('urirun_connector_kvm/backends.py', '_list_xdg', 1, 7, 7).
python_function('urirun_connector_kvm/backends.py', '_list_macos', 1, 5, 7).
python_function('urirun_connector_kvm/backends.py', '_atspi_python', 0, 5, 3).
python_function('urirun_connector_kvm/backends.py', '_focus_atspi', 1, 5, 9).
python_function('urirun_connector_kvm/backends.py', '_a11y_atspi', 6, 4, 10).
python_function('urirun_connector_kvm/backends.py', '_tsv_lines', 2, 8, 14).
python_function('urirun_connector_kvm/backends.py', '_locate_tesseract', 5, 26, 25).
python_function('urirun_connector_kvm/backends.py', '_easyocr_reader', 0, 5, 4).
python_function('urirun_connector_kvm/backends.py', '_locate_easyocr', 5, 14, 18).
python_function('urirun_connector_kvm/backends.py', 'bbox_center', 1, 1, 1).
python_function('urirun_connector_kvm/backends.py', '_locate_atspi', 4, 9, 5).
python_function('urirun_connector_kvm/backends.py', '_capture_tmp', 0, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_locate_imgl', 2, 6, 7).
python_function('urirun_connector_kvm/backends.py', '_locate_vql', 2, 11, 9).
python_function('urirun_connector_kvm/backends.py', '_ui_io', 1, 1, 0).
python_function('urirun_connector_kvm/backends.py', '_ui_iow', 2, 1, 0).
python_function('urirun_connector_kvm/backends.py', 'uinput_available', 0, 2, 2).
python_function('urirun_connector_kvm/backends.py', '_uinput_create_abs', 0, 3, 4).
python_function('urirun_connector_kvm/backends.py', 'uinput_abs_click', 7, 6, 15).
python_function('urirun_connector_kvm/backends.py', '_gnome_monitors', 0, 4, 8).
python_function('urirun_connector_kvm/backends.py', 'surface_report', 0, 11, 6).
python_function('urirun_connector_kvm/core.py', '_ok', 0, 1, 1).
python_function('urirun_connector_kvm/core.py', '_fail_from', 2, 1, 3).
python_function('urirun_connector_kvm/core.py', 'capture', 9, 15, 23).
python_function('urirun_connector_kvm/core.py', 'type_text', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'key', 2, 4, 5).
python_function('urirun_connector_kvm/core.py', 'click', 3, 5, 7).
python_function('urirun_connector_kvm/core.py', 'move', 2, 2, 5).
python_function('urirun_connector_kvm/core.py', 'scroll', 1, 2, 5).
python_function('urirun_connector_kvm/core.py', 'click_abs', 6, 2, 6).
python_function('urirun_connector_kvm/core.py', 'task_run', 1, 13, 11).
python_function('urirun_connector_kvm/core.py', 'focus', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'window_list', 0, 2, 4).
python_function('urirun_connector_kvm/core.py', 'a11y_act', 6, 3, 6).
python_function('urirun_connector_kvm/core.py', '_click_hit', 4, 3, 4).
python_function('urirun_connector_kvm/core.py', 'ui_find', 4, 2, 5).
python_function('urirun_connector_kvm/core.py', 'ui_click', 3, 2, 5).
python_function('urirun_connector_kvm/core.py', 'ui_fill', 5, 5, 9).
python_function('urirun_connector_kvm/core.py', 'ui_wait', 5, 3, 7).
python_function('urirun_connector_kvm/core.py', 'ui_verify', 2, 3, 6).
python_function('urirun_connector_kvm/core.py', '_capture_native', 1, 1, 4).
python_function('urirun_connector_kvm/core.py', 'ui_locate', 3, 3, 8).
python_function('urirun_connector_kvm/core.py', 'ui_click_text', 7, 8, 11).
python_function('urirun_connector_kvm/core.py', 'doctor', 0, 1, 6).
python_function('urirun_connector_kvm/core.py', 'launch', 4, 4, 5).
python_function('urirun_connector_kvm/core.py', 'list_apps', 1, 2, 4).
python_function('urirun_connector_kvm/core.py', 'urirun_bindings', 0, 1, 1).
python_function('urirun_connector_kvm/core.py', 'connector_manifest', 0, 1, 2).
python_function('urirun_connector_kvm/core.py', 'main', 1, 1, 2).

% ── Python Classes ───────────────────────────────────────
python_class('urirun_connector_kvm/backends.py', 'Backend').
python_method('Backend', 'missing', 0, 5, 2).
python_method('Backend', 'available', 0, 3, 2).
python_class('urirun_connector_kvm/backends.py', 'BackendError').

% ── Dependencies ─────────────────────────────────────────

% ── Makefile Targets ─────────────────────────────────────
makefile_target('help', '').
makefile_target('manifest', '').
makefile_target('bindings', '').
makefile_target('smoke', '').
makefile_target('test', '').

% ── Taskfile Tasks ───────────────────────────────────────

% ── Environment Variables ────────────────────────────────

% ── TestQL Scenarios ─────────────────────────────────────
testql_scenario('generated-cli-tests.testql.toon.yaml', 'cli').

% ── Semantic Facts from SUMD.md ──────────────────────────
sumd_declared_file('app.doql.less', 'doql').
sumd_declared_file('testql-scenarios/generated-cli-tests.testql.toon.yaml', 'testql').
sumd_declared_file('project/map.toon.yaml', 'analysis').
sumd_declared_file('project/logic.pl', 'analysis').
sumd_declared_file('project/calls.toon.yaml', 'analysis').
sumd_interface('cli', 'argparse').
sumd_interface('cli', '').
sumd_workflow('manifest', 'manual').
sumd_workflow_step('manifest', 1, 'urirun-connector-kvm manifest').
sumd_workflow('bindings', 'manual').
sumd_workflow_step('bindings', 1, 'urirun-connector-kvm bindings').
sumd_workflow('smoke', 'manual').
sumd_workflow_step('smoke', 1, 'urirun-connector-kvm bindings | urirun connectors smoke - \').
sumd_workflow('test', 'manual').
sumd_workflow_step('test', 1, 'pip install -e . && python3 -m pytest -q && $(MAKE) smoke').
```

## Call Graph

*90 nodes · 139 edges · 2 modules · CC̄=3.9*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 38 | 6 | **44** |
| `capture` *(in urirun_connector_kvm.core)* | 15 ⚠ | 0 | 43 | **43** |
| `_locate_tesseract` *(in urirun_connector_kvm.backends)* | 26 ⚠ | 0 | 41 | **41** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `uinput_abs_click` *(in urirun_connector_kvm.backends)* | 6 | 0 | 31 | **31** |
| `_run` *(in urirun_connector_kvm.backends)* | 3 | 25 | 3 | **28** |
| `_locate_easyocr` *(in urirun_connector_kvm.backends)* | 14 ⚠ | 0 | 26 | **26** |
| `ui_click_text` *(in urirun_connector_kvm.core)* | 8 | 0 | 23 | **23** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.04s
# nodes: 90 | edges: 139 | modules: 2
# CC̄=3.9

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:38  out:6  total:44
  urirun_connector_kvm.core.capture
    CC=15  in:0  out:43  total:43
  urirun_connector_kvm.backends._locate_tesseract
    CC=26  in:0  out:41  total:41
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.backends.uinput_abs_click
    CC=6  in:0  out:31  total:31
  urirun_connector_kvm.backends._run
    CC=3  in:25  out:3  total:28
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.core._ok
    CC=1  in:22  out:1  total:23
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core._fail_from
    CC=1  in:18  out:3  total:21
  urirun_connector_kvm.backends.dispatch
    CC=11  in:1  out:17  total:18
  urirun_connector_kvm.backends._launch_xdg
    CC=7  in:0  out:14  total:14
  urirun_connector_kvm.backends._cap_portal
    CC=2  in:0  out:14  total:14
  urirun_connector_kvm.core.ui_fill
    CC=5  in:0  out:13  total:13
  urirun_connector_kvm.backends._locate_imgl
    CC=6  in:0  out:13  total:13
  urirun_connector_kvm.backends._xdg_app_dirs
    CC=8  in:1  out:11  total:12
  urirun_connector_kvm.backends._uinput_create_abs
    CC=3  in:1  out:10  total:11
  urirun_connector_kvm.backends._parse_desktop
    CC=15  in:1  out:10  total:11
  urirun_connector_kvm.backends._a11y_atspi
    CC=4  in:1  out:10  total:11

MODULES:
  urirun_connector_kvm.backends  [65 funcs]
    available  CC=3  out:2
    missing  CC=5  out:2
    _a11y_atspi  CC=4  out:10
    _atspi_python  CC=5  out:4
    _cap_gnome  CC=1  out:2
    _cap_grim  CC=1  out:2
    _cap_im  CC=1  out:2
    _cap_macos  CC=1  out:2
    _cap_mss  CC=2  out:6
    _cap_pillow  CC=1  out:3
  urirun_connector_kvm.core  [25 funcs]
    _capture_native  CC=1  out:4
    _click_hit  CC=3  out:7
    _fail_from  CC=1  out:3
    _ok  CC=1  out:1
    a11y_act  CC=3  out:6
    capture  CC=15  out:43
    click  CC=5  out:9
    click_abs  CC=2  out:9
    doctor  CC=1  out:6
    focus  CC=3  out:5

EDGES:
  urirun_connector_kvm.backends.is_x11 → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.platform_tag → urirun_connector_kvm.backends.is_wayland
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_bin
  urirun_connector_kvm.backends.Backend.missing → urirun_connector_kvm.backends.have_mod
  urirun_connector_kvm.backends.Backend.available → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends.dispatch → urirun_connector_kvm.backends.platform_tag
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._portal_python
  urirun_connector_kvm.backends._cap_portal → urirun_connector_kvm.backends._run
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
  urirun_connector_kvm.backends._yd_env → urirun_connector_kvm.backends.ensure_ydotoold
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_wtype → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._type_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._type_pynput → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._click_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._click_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._click_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._click_pynput → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._move_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._move_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._move_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._move_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._move_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._move_pynput → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._key_ydotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._key_ydotool → urirun_connector_kvm.backends._yd_keyseq
  urirun_connector_kvm.backends._key_ydotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._key_ydotool → urirun_connector_kvm.backends._yd_env
  urirun_connector_kvm.backends._key_xdotool → urirun_connector_kvm.backends.backend
  urirun_connector_kvm.backends._key_xdotool → urirun_connector_kvm.backends._run
  urirun_connector_kvm.backends._key_pynput → urirun_connector_kvm.backends.backend
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
