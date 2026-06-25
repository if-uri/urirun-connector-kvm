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
# urirun-connector-kvm | 27f 5574L | python:23,shell:3,less:1 | 2026-06-25
# stats: 215 func | 13 cls | 27 mod | CC̄=4.1 | critical:17 | cycles:0
# alerts[5]: CC _locate_easyocr=14; CC _line_match=13; CC _wayland_present=13; CC route=13; CC task_run=13
# hotspots[5]: _locate_easyocr fan=18; capture fan=16; uinput_abs_click fan=15; launch_session fan=15; _tsv_lines fan=14
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[27]:
  app.doql.less,61
  computer-use-preview/agent.py,513
  computer-use-preview/computers/__init__.py,26
  computer-use-preview/computers/browserbase/__init__.py,1
  computer-use-preview/computers/browserbase/browserbase.py,81
  computer-use-preview/computers/computer.py,199
  computer-use-preview/computers/kvm/__init__.py,3
  computer-use-preview/computers/kvm/kvm.py,191
  computer-use-preview/computers/playwright/__init__.py,1
  computer-use-preview/computers/playwright/playwright.py,419
  computer-use-preview/main.py,102
  computer-use-preview/test_agent.py,112
  computer-use-preview/test_main.py,70
  examples/calibrate_abs.py,76
  examples/quickstart.sh,6
  project.sh,69
  tests/test_kvm.py,413
  tree.sh,5
  urirun_connector_kvm/__init__.py,39
  urirun_connector_kvm/backends.py,1262
  urirun_connector_kvm/cdp.py,308
  urirun_connector_kvm/control.py,217
  urirun_connector_kvm/core.py,833
  urirun_connector_kvm/environment.py,94
  urirun_connector_kvm/launch_backends.py,282
  urirun_connector_kvm/strategies.py,130
  urirun_connector_kvm/surface.py,61
D:
  computer-use-preview/agent.py:
    e: multiply_numbers,BrowserAgent
    BrowserAgent: __init__(4),_handle_scroll_at(1),_handle_drag_and_drop(1),_dispatch_action(1),_dispatch_legacy_action(1),handle_action(2),handle_legacy_action(1),get_model_response(2),get_text(1),extract_function_calls(1),_build_function_response(3),_trim_old_screenshots(0),_generate_response(0),_render_turn(2),_execute_function_calls(1),run_one_iteration(0),_get_safety_confirmation(1),agent_loop(0),denormalize_x(1),denormalize_y(1)
    multiply_numbers(x;y)
  computer-use-preview/computers/__init__.py:
  computer-use-preview/computers/browserbase/__init__.py:
  computer-use-preview/computers/browserbase/browserbase.py:
    e: BrowserbaseComputer
    BrowserbaseComputer: __init__(2),__enter__(0),__exit__(3)
  computer-use-preview/computers/computer.py:
    e: EnvState,Computer
    EnvState:
    Computer: screen_size(0),open_web_browser(0),click_at(2),double_click_at(2),triple_click_at(2),middle_click_at(2),right_click_at(2),mouse_down(2),mouse_up(2),type_text(2),wait(1),hover_at(2),type_text_at(5),scroll_document(1),scroll_at(4),wait_5_seconds(0),go_back(0),go_forward(0),search(0),navigate(1),key_combination(1),press_key(1),key_down(1),key_up(1),take_screenshot(0),drag_and_drop(4),current_state(0)  # Defines an interface for environments.
  computer-use-preview/computers/kvm/__init__.py:
  computer-use-preview/computers/kvm/kvm.py:
    e: KvmComputer
    KvmComputer: __init__(3),__enter__(0),__exit__(0),_run(4),_state(0),screen_size(0),current_state(0),take_screenshot(0),_click(3),click_at(2),double_click_at(2),triple_click_at(2),middle_click_at(2),right_click_at(2),hover_at(2),mouse_down(2),mouse_up(2),drag_and_drop(4),type_text(2),type_text_at(5),key_combination(1),press_key(1),key_down(1),key_up(1),scroll_document(1),scroll_at(4),wait(1),wait_5_seconds(0),open_web_browser(0),navigate(1),search(0),go_back(0),go_forward(0)  # Computer Use executor backed by a urirun node's kvm:// surfa
  computer-use-preview/computers/playwright/__init__.py:
  computer-use-preview/computers/playwright/playwright.py:
    e: PlaywrightComputer
    PlaywrightComputer: __init__(4),_handle_new_page(1),__enter__(0),__exit__(3),open_web_browser(0),click_at(2),double_click_at(2),triple_click_at(2),middle_click_at(2),right_click_at(2),mouse_down(2),mouse_up(2),type_text(2),wait(1),hover_at(2),type_text_at(5),_horizontal_document_scroll(1),scroll_document(1),scroll_at(4),wait_5_seconds(0),go_back(0),go_forward(0),search(0),navigate(1),key_combination(1),press_key(1),key_down(1),key_up(1),take_screenshot(0),drag_and_drop(4),current_state(0),screen_size(0),highlight_mouse(2)  # Connects to a local Playwright instance.
  computer-use-preview/main.py:
    e: main
    main()
  computer-use-preview/test_agent.py:
    e: TestBrowserAgent
    TestBrowserAgent: setUp(0),test_multiply_numbers(0),test_handle_action_open_web_browser(0),test_handle_action_click_at(0),test_handle_action_type_text_at(0),test_handle_action_scroll_document(0),test_handle_action_navigate(0),test_handle_action_unknown_function(0),test_denormalize_x(0),test_denormalize_y(0),test_run_one_iteration_no_function_calls(1),test_run_one_iteration_with_function_call(2)
  computer-use-preview/test_main.py:
    e: TestMain
    TestMain: test_main_playwright(3),test_main_browserbase(3)
  examples/calibrate_abs.py:
    e: run,cap,magenta_frac,find_box
    run(route;payload)
    cap()
    magenta_frac(a)
    find_box(a)
  tests/test_kvm.py:
    e: test_key_requires_value,test_type_requires_value,test_no_backend_reports_install_hint,test_backend_decorator_registers_and_sorts,test_dispatch_falls_through_on_failure,test_unavailable_backend_skipped_by_needs,test_bindings_are_isolated_handlers,test_runtime_executes_from_compiled_registry,test_doctor_reports_backends,test_capture_tags_screenshot_as_frozen_artifact,test_manifest_prose_plus_derived_routes,test_cli_bindings_and_manifest,test_router_prefers_cdp_when_reachable,test_router_falls_through_cdp_to_vision,test_router_empty_target_is_error,test_ui_act_retries_then_succeeds,test_ui_act_rejects_bad_verb,test_is_wayland_detects_via_socket_when_env_absent,test_platform_tag_wayland_via_socket,test_session_env_fills_display_and_bus,test_session_env_preserves_existing_vars,test_chrome_launch_injects_dedicated_profile_and_debug_port,test_chrome_launch_default_keeps_real_profile,test_non_chrome_launch_skips_cdp,test_vision_strategy_is_environment_gated,test_environment_profile_shape,test_report_includes_environment,test_cdp_port_prefers_client_url,test_spread_strips_envelope_reserved_keys,test_cdp_navigate_has_no_url_collision
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
    test_router_prefers_cdp_when_reachable(monkeypatch)
    test_router_falls_through_cdp_to_vision(monkeypatch)
    test_router_empty_target_is_error()
    test_ui_act_retries_then_succeeds(monkeypatch)
    test_ui_act_rejects_bad_verb()
    test_is_wayland_detects_via_socket_when_env_absent(monkeypatch)
    test_platform_tag_wayland_via_socket(monkeypatch)
    test_session_env_fills_display_and_bus(monkeypatch;tmp_path)
    test_session_env_preserves_existing_vars(monkeypatch)
    test_chrome_launch_injects_dedicated_profile_and_debug_port(monkeypatch)
    test_chrome_launch_default_keeps_real_profile(monkeypatch)
    test_non_chrome_launch_skips_cdp(monkeypatch)
    test_vision_strategy_is_environment_gated(monkeypatch)
    test_environment_profile_shape()
    test_report_includes_environment()
    test_cdp_port_prefers_client_url(monkeypatch)
    test_spread_strips_envelope_reserved_keys()
    test_cdp_navigate_has_no_url_collision(monkeypatch)
  urirun_connector_kvm/__init__.py:
  urirun_connector_kvm/backends.py:
    e: _runtime_dir,_wayland_socket,_x_display,is_wayland,is_x11,platform_tag,have_bin,have_mod,backend,dispatch,registry_report,_run,_portal_python,_cap_portal,_cap_grim,_cap_mss,_cap_pillow,_cap_scrot,_cap_im,_cap_gnome,_cap_macos,_ydotool_socket,ensure_ydotoold,_yd_env,_yd_keyseq,session_env,_clipboard_set,_type_ydotool,_type_wtype,_type_xdotool,_type_pynput,_click_ydotool,_click_xdotool,_click_pynput,_move_uinput_abs,_move_ydotool,_move_xdotool,_move_pynput,_key_ydotool,_key_xdotool,_key_pynput,_scroll_ydotool,_scroll_pynput,_focus_wmctrl,_focus_pgw,_winlist_wmctrl,_atspi_python,_focus_atspi,_a11y_atspi,_tsv_lines,_tesseract_words_by_line,_line_match,_tesseract_query_matches,_locate_tesseract,_easyocr_reader,_locate_easyocr,bbox_center,_locate_atspi,_capture_tmp,_locate_imgl,_locate_vql,_ui_io,_ui_iow,uinput_available,_uinput_create_abs,_screen_wh,_read_text,_calib,_compute_abs_coords,_uinput_emit_clicks,uinput_abs_click,_gnome_monitors,_wayland_present,_surface_warnings,_os_level_reliable,_surface_flags,surface_report,Backend,BackendError
    Backend: missing(0),available(0)
    BackendError:
    _runtime_dir()
    _wayland_socket()
    _x_display()
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
    session_env()
    _clipboard_set(text)
    _type_ydotool(text)
    _type_wtype(text)
    _type_xdotool(text)
    _type_pynput(text)
    _click_ydotool(button)
    _click_xdotool(button)
    _click_pynput(button)
    _move_uinput_abs(x;y)
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
    _atspi_python()
    _focus_atspi(title)
    _a11y_atspi(app;role;name;op;text;nth)
    _tsv_lines(tsv;min_conf)
    _tesseract_words_by_line(tsv_stdout;min_conf)
    _line_match(ws;ql;terms)
    _tesseract_query_matches(tsv_stdout;ql;min_conf)
    _locate_tesseract(image;query;text;role;name;min_conf)
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
    _screen_wh()
    _read_text(path)
    _calib()
    _compute_abs_coords(px;py;sw;sh)
    _uinput_emit_clicks(ev;fd;button;clicks)
    uinput_abs_click(x;y;sw;sh;button;do_click;settle;clicks)
    _gnome_monitors()
    _wayland_present()
    _surface_warnings(waylandish;multi;fractional;mons;unconfirmed)
    _os_level_reliable(wl;multi;fractional;unconfirmed;confirmed_simple)
    _surface_flags(linux;mons;wl)
    surface_report()
  urirun_connector_kvm/cdp.py:
    e: endpoint,_pages,reachable,navigate,page_ready,_find_chrome,_copy_auth,launch_session,_ws_connect,_ws_send,_ws_recv,_call,_evaluate,_run,find,act
    endpoint()
    _pages()
    reachable()
    navigate(url)
    page_ready(timeout)
    _find_chrome()
    _copy_auth(src;dst)
    launch_session(url;user_data_dir;copy_from;wait)
    _ws_connect(ws_url;timeout)
    _ws_send(s;data)
    _ws_recv(s)
    _call(s;_id;method;params)
    _evaluate(expr)
    _run(op;text;role;name;value)
    find(text;role;name)
    act(op;text;role;name;value)
  urirun_connector_kvm/control.py:
    e: strategy,_try_locate_one,_try_act_one,route,_check_post_condition,act,_verify_value,report,_safe_avail
    strategy(cls)
    _try_locate_one(st;target;attempts)
    _try_act_one(st;op;target;verify;value;app;attempts)
    route(op;text;role;app;name;value;verify;cheap)
    _check_post_condition(expect;gone;text;name;app)
    act(op;text;role;app;name;value;expect;gone;retries;settle;safe)
    _verify_value(value;app)
    report()
    _safe_avail(s)
  urirun_connector_kvm/core.py:
    e: _ok,_fail_from,_spread,_positioned_click,_apply_capture_postprocessing,capture,display_info,type_text,key,click,move,wait,scroll,double_click,triple_click,right_click,middle_click,hover,drag_and_drop,click_abs,task_run,focus,window_list,proc_kill,a11y_act,_click_hit,_router_return,ui_find,ui_click,ui_fill,ui_strategies,env_profile,_surface_mod,surface_current,cdp_ensure,_cdp_mod,cdp_navigate,cdp_ready,_resolve_act_app,_act_retry_loop,_act_reject,_act_ready,ui_act,cdp_status,ui_wait,ui_verify,_capture_native,ui_locate,ui_click_text,doctor,launch,list_apps,urirun_bindings,connector_manifest,main
    _ok()
    _fail_from(action;exc)
    _spread(d)
    _positioned_click(button;x;y;clicks)
    _apply_capture_postprocessing(out;cx;cy;zoom;crop_w;crop_h;max_width)
    capture(output;monitor;max_width;base64;cx;cy;zoom;crop_w;crop_h)
    display_info()
    type_text(text)
    key(key;keys)
    click(button;x;y)
    move(x;y)
    wait(seconds;ms)
    scroll(dy)
    double_click(x;y)
    triple_click(x;y)
    right_click(x;y)
    middle_click(x;y)
    hover(x;y)
    drag_and_drop(x;y;destination_x;destination_y)
    click_abs(x;y;sw;sh;button;do_click)
    task_run(steps)
    focus(title)
    window_list()
    proc_kill(pid;name;signal)
    a11y_act(app;role;name;action;text;nth)
    _click_hit(hit;app;role;text)
    _router_return(action;r)
    ui_find(text;role;app;nth;name)
    ui_click(text;role;app;name)
    ui_fill(text;role;app;value;verify;name)
    ui_strategies()
    env_profile()
    _surface_mod()
    surface_current()
    cdp_ensure(url;user_data_dir;copy_from;wait)
    _cdp_mod()
    cdp_navigate(url;ready_timeout)
    cdp_ready(timeout)
    _resolve_act_app(app)
    _act_retry_loop(op;text;role;app;name;value;cheap;retries;settle;budget;start)
    _act_reject(do;text;name;value;safe)
    _act_ready(ready_timeout)
    ui_act(do;text;role;name;value;app;retries;settle;ready_timeout;safe)
    cdp_status()
    ui_wait(text;role;app;timeout;interval;name)
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
  urirun_connector_kvm/environment.py:
    e: _safe,atspi_ready,profile
    _safe(fn)
    atspi_ready()
    profile()
  urirun_connector_kvm/launch_backends.py:
    e: _cdp_port,_cdp_wait,_xdg_app_dirs,_parse_desktop_section,_parse_desktop,_desktop_entries,_strip_field_codes,_find_app,_resolve_launch_argv,_inject_cdp_profile,_inject_chrome_flags,_launch_xdg,_launch_macos,_launch_windows,_list_xdg,_list_macos
    _cdp_port()
    _cdp_wait(port;wait)
    _xdg_app_dirs()
    _parse_desktop_section(fh)
    _parse_desktop(path)
    _desktop_entries()
    _strip_field_codes(exec_line)
    _find_app(query)
    _resolve_launch_argv(app;extra)
    _inject_cdp_profile(argv;cdp_port)
    _inject_chrome_flags(argv;debug)
    _launch_xdg(app;compose;args;settle;debug)
    _launch_macos(app;args;settle)
    _launch_windows(app;args;settle)
    _list_xdg(filter)
    _list_macos(filter)
  urirun_connector_kvm/strategies.py:
    e: is_browser,CdpStrategy,AtspiStrategy,VisionStrategy
    CdpStrategy: available(1),locate(1),click(1),fill(1)
    AtspiStrategy: available(1),locate(1),click(1),fill(1)
    VisionStrategy: available(1),locate(1),_click_xy(3),click(1),fill(1)
    is_browser(app)
  urirun_connector_kvm/surface.py:
    e: _active_window,current
    _active_window()
    current()
```

### `project/logic.pl`

```prolog markpact:analysis path=project/logic.pl
% ── Project Metadata ─────────────────────────────────────
project_metadata('urirun-connector-kvm', '0.3.0', 'python').

% ── Project Files ────────────────────────────────────────
project_file('app.doql.less', 61, 'less').
project_file('computer-use-preview/agent.py', 513, 'python').
project_file('computer-use-preview/computers/__init__.py', 26, 'python').
project_file('computer-use-preview/computers/browserbase/__init__.py', 1, 'python').
project_file('computer-use-preview/computers/browserbase/browserbase.py', 81, 'python').
project_file('computer-use-preview/computers/computer.py', 199, 'python').
project_file('computer-use-preview/computers/kvm/__init__.py', 3, 'python').
project_file('computer-use-preview/computers/kvm/kvm.py', 191, 'python').
project_file('computer-use-preview/computers/playwright/__init__.py', 1, 'python').
project_file('computer-use-preview/computers/playwright/playwright.py', 419, 'python').
project_file('computer-use-preview/main.py', 102, 'python').
project_file('computer-use-preview/test_agent.py', 112, 'python').
project_file('computer-use-preview/test_main.py', 70, 'python').
project_file('examples/calibrate_abs.py', 76, 'python').
project_file('examples/quickstart.sh', 6, 'shell').
project_file('project.sh', 69, 'shell').
project_file('tests/test_kvm.py', 413, 'python').
project_file('tree.sh', 5, 'shell').
project_file('urirun_connector_kvm/__init__.py', 39, 'python').
project_file('urirun_connector_kvm/backends.py', 1262, 'python').
project_file('urirun_connector_kvm/cdp.py', 308, 'python').
project_file('urirun_connector_kvm/control.py', 217, 'python').
project_file('urirun_connector_kvm/core.py', 833, 'python').
project_file('urirun_connector_kvm/environment.py', 94, 'python').
project_file('urirun_connector_kvm/launch_backends.py', 282, 'python').
project_file('urirun_connector_kvm/strategies.py', 130, 'python').
project_file('urirun_connector_kvm/surface.py', 61, 'python').

% ── Python Functions ─────────────────────────────────────
python_function('computer-use-preview/agent.py', 'multiply_numbers', 2, 1, 0).
python_function('computer-use-preview/main.py', 'main', 0, 4, 9).
python_function('examples/calibrate_abs.py', 'run', 2, 2, 1).
python_function('examples/calibrate_abs.py', 'cap', 0, 1, 8).
python_function('examples/calibrate_abs.py', 'magenta_frac', 1, 1, 2).
python_function('examples/calibrate_abs.py', 'find_box', 1, 2, 4).
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
python_function('tests/test_kvm.py', 'test_router_prefers_cdp_when_reachable', 1, 2, 2).
python_function('tests/test_kvm.py', 'test_router_falls_through_cdp_to_vision', 1, 4, 5).
python_function('tests/test_kvm.py', 'test_router_empty_target_is_error', 0, 2, 1).
python_function('tests/test_kvm.py', 'test_ui_act_retries_then_succeeds', 1, 3, 3).
python_function('tests/test_kvm.py', 'test_ui_act_rejects_bad_verb', 0, 2, 1).
python_function('tests/test_kvm.py', 'test_is_wayland_detects_via_socket_when_env_absent', 1, 3, 3).
python_function('tests/test_kvm.py', 'test_platform_tag_wayland_via_socket', 1, 3, 3).
python_function('tests/test_kvm.py', 'test_session_env_fills_display_and_bus', 2, 6, 5).
python_function('tests/test_kvm.py', 'test_session_env_preserves_existing_vars', 1, 2, 2).
python_function('tests/test_kvm.py', 'test_chrome_launch_injects_dedicated_profile_and_debug_port', 1, 6, 7).
python_function('tests/test_kvm.py', 'test_chrome_launch_default_keeps_real_profile', 1, 6, 6).
python_function('tests/test_kvm.py', 'test_non_chrome_launch_skips_cdp', 1, 3, 5).
python_function('tests/test_kvm.py', 'test_vision_strategy_is_environment_gated', 1, 3, 3).
python_function('tests/test_kvm.py', 'test_environment_profile_shape', 0, 5, 2).
python_function('tests/test_kvm.py', 'test_report_includes_environment', 0, 3, 1).
python_function('tests/test_kvm.py', 'test_cdp_port_prefers_client_url', 1, 4, 3).
python_function('tests/test_kvm.py', 'test_spread_strips_envelope_reserved_keys', 0, 4, 1).
python_function('tests/test_kvm.py', 'test_cdp_navigate_has_no_url_collision', 1, 2, 2).
python_function('urirun_connector_kvm/backends.py', '_runtime_dir', 0, 3, 3).
python_function('urirun_connector_kvm/backends.py', '_wayland_socket', 0, 7, 5).
python_function('urirun_connector_kvm/backends.py', '_x_display', 0, 6, 4).
python_function('urirun_connector_kvm/backends.py', 'is_wayland', 0, 3, 4).
python_function('urirun_connector_kvm/backends.py', 'is_x11', 0, 3, 4).
python_function('urirun_connector_kvm/backends.py', 'platform_tag', 0, 5, 2).
python_function('urirun_connector_kvm/backends.py', 'have_bin', 1, 1, 1).
python_function('urirun_connector_kvm/backends.py', 'have_mod', 1, 2, 1).
python_function('urirun_connector_kvm/backends.py', 'backend', 2, 1, 5).
python_function('urirun_connector_kvm/backends.py', 'dispatch', 1, 11, 9).
python_function('urirun_connector_kvm/backends.py', 'registry_report', 0, 3, 4).
python_function('urirun_connector_kvm/backends.py', '_run', 1, 4, 4).
python_function('urirun_connector_kvm/backends.py', '_portal_python', 0, 5, 3).
python_function('urirun_connector_kvm/backends.py', '_cap_portal', 1, 2, 11).
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
python_function('urirun_connector_kvm/backends.py', 'session_env', 0, 8, 6).
python_function('urirun_connector_kvm/backends.py', '_clipboard_set', 1, 7, 8).
python_function('urirun_connector_kvm/backends.py', '_type_ydotool', 1, 2, 7).
python_function('urirun_connector_kvm/backends.py', '_type_wtype', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_type_xdotool', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_type_pynput', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_click_ydotool', 1, 1, 4).
python_function('urirun_connector_kvm/backends.py', '_click_xdotool', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_click_pynput', 1, 1, 3).
python_function('urirun_connector_kvm/backends.py', '_move_uinput_abs', 2, 1, 6).
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
python_function('urirun_connector_kvm/backends.py', '_atspi_python', 0, 5, 3).
python_function('urirun_connector_kvm/backends.py', '_focus_atspi', 1, 5, 7).
python_function('urirun_connector_kvm/backends.py', '_a11y_atspi', 6, 6, 10).
python_function('urirun_connector_kvm/backends.py', '_tsv_lines', 2, 8, 14).
python_function('urirun_connector_kvm/backends.py', '_tesseract_words_by_line', 2, 7, 8).
python_function('urirun_connector_kvm/backends.py', '_line_match', 3, 13, 8).
python_function('urirun_connector_kvm/backends.py', '_tesseract_query_matches', 3, 6, 7).
python_function('urirun_connector_kvm/backends.py', '_locate_tesseract', 6, 9, 13).
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
python_function('urirun_connector_kvm/backends.py', '_screen_wh', 0, 8, 10).
python_function('urirun_connector_kvm/backends.py', '_read_text', 1, 2, 3).
python_function('urirun_connector_kvm/backends.py', '_calib', 0, 3, 3).
python_function('urirun_connector_kvm/backends.py', '_compute_abs_coords', 4, 6, 5).
python_function('urirun_connector_kvm/backends.py', '_uinput_emit_clicks', 4, 2, 6).
python_function('urirun_connector_kvm/backends.py', 'uinput_abs_click', 8, 9, 15).
python_function('urirun_connector_kvm/backends.py', '_gnome_monitors', 0, 5, 12).
python_function('urirun_connector_kvm/backends.py', '_wayland_present', 0, 13, 9).
python_function('urirun_connector_kvm/backends.py', '_surface_warnings', 5, 11, 2).
python_function('urirun_connector_kvm/backends.py', '_os_level_reliable', 5, 5, 1).
python_function('urirun_connector_kvm/backends.py', '_surface_flags', 3, 11, 6).
python_function('urirun_connector_kvm/backends.py', 'surface_report', 0, 4, 6).
python_function('urirun_connector_kvm/cdp.py', 'endpoint', 0, 2, 2).
python_function('urirun_connector_kvm/cdp.py', '_pages', 0, 8, 7).
python_function('urirun_connector_kvm/cdp.py', 'reachable', 0, 2, 2).
python_function('urirun_connector_kvm/cdp.py', 'navigate', 1, 1, 2).
python_function('urirun_connector_kvm/cdp.py', 'page_ready', 1, 4, 6).
python_function('urirun_connector_kvm/cdp.py', '_find_chrome', 0, 4, 3).
python_function('urirun_connector_kvm/cdp.py', '_copy_auth', 2, 4, 7).
python_function('urirun_connector_kvm/cdp.py', 'launch_session', 4, 10, 15).
python_function('urirun_connector_kvm/cdp.py', '_ws_connect', 2, 6, 12).
python_function('urirun_connector_kvm/cdp.py', '_ws_send', 2, 4, 9).
python_function('urirun_connector_kvm/cdp.py', '_ws_recv', 1, 6, 6).
python_function('urirun_connector_kvm/cdp.py', '_call', 4, 4, 7).
python_function('urirun_connector_kvm/cdp.py', '_evaluate', 1, 4, 6).
python_function('urirun_connector_kvm/cdp.py', '_run', 5, 2, 6).
python_function('urirun_connector_kvm/cdp.py', 'find', 3, 1, 1).
python_function('urirun_connector_kvm/cdp.py', 'act', 5, 2, 3).
python_function('urirun_connector_kvm/control.py', 'strategy', 1, 1, 3).
python_function('urirun_connector_kvm/control.py', '_try_locate_one', 3, 4, 5).
python_function('urirun_connector_kvm/control.py', '_try_act_one', 7, 9, 7).
python_function('urirun_connector_kvm/control.py', 'route', 8, 13, 6).
python_function('urirun_connector_kvm/control.py', '_check_post_condition', 5, 4, 3).
python_function('urirun_connector_kvm/control.py', 'act', 11, 12, 10).
python_function('urirun_connector_kvm/control.py', '_verify_value', 2, 6, 7).
python_function('urirun_connector_kvm/control.py', 'report', 0, 2, 2).
python_function('urirun_connector_kvm/control.py', '_safe_avail', 1, 2, 1).
python_function('urirun_connector_kvm/core.py', '_ok', 0, 1, 1).
python_function('urirun_connector_kvm/core.py', '_fail_from', 2, 1, 3).
python_function('urirun_connector_kvm/core.py', '_spread', 1, 4, 1).
python_function('urirun_connector_kvm/core.py', '_positioned_click', 4, 8, 7).
python_function('urirun_connector_kvm/core.py', '_apply_capture_postprocessing', 7, 10, 9).
python_function('urirun_connector_kvm/core.py', 'capture', 9, 6, 16).
python_function('urirun_connector_kvm/core.py', 'display_info', 0, 4, 9).
python_function('urirun_connector_kvm/core.py', 'type_text', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'key', 2, 4, 5).
python_function('urirun_connector_kvm/core.py', 'click', 3, 3, 5).
python_function('urirun_connector_kvm/core.py', 'move', 2, 2, 5).
python_function('urirun_connector_kvm/core.py', 'wait', 2, 3, 7).
python_function('urirun_connector_kvm/core.py', 'scroll', 1, 2, 5).
python_function('urirun_connector_kvm/core.py', 'double_click', 2, 2, 4).
python_function('urirun_connector_kvm/core.py', 'triple_click', 2, 2, 4).
python_function('urirun_connector_kvm/core.py', 'right_click', 2, 2, 4).
python_function('urirun_connector_kvm/core.py', 'middle_click', 2, 2, 4).
python_function('urirun_connector_kvm/core.py', 'hover', 2, 2, 5).
python_function('urirun_connector_kvm/core.py', 'drag_and_drop', 4, 2, 7).
python_function('urirun_connector_kvm/core.py', 'click_abs', 6, 2, 6).
python_function('urirun_connector_kvm/core.py', 'task_run', 1, 13, 11).
python_function('urirun_connector_kvm/core.py', 'focus', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'window_list', 0, 2, 4).
python_function('urirun_connector_kvm/core.py', 'proc_kill', 3, 12, 14).
python_function('urirun_connector_kvm/core.py', 'a11y_act', 6, 3, 7).
python_function('urirun_connector_kvm/core.py', '_click_hit', 4, 7, 7).
python_function('urirun_connector_kvm/core.py', '_router_return', 2, 5, 4).
python_function('urirun_connector_kvm/core.py', 'ui_find', 5, 1, 3).
python_function('urirun_connector_kvm/core.py', 'ui_click', 4, 1, 3).
python_function('urirun_connector_kvm/core.py', 'ui_fill', 6, 2, 4).
python_function('urirun_connector_kvm/core.py', 'ui_strategies', 0, 1, 3).
python_function('urirun_connector_kvm/core.py', 'env_profile', 0, 2, 3).
python_function('urirun_connector_kvm/core.py', '_surface_mod', 0, 2, 0).
python_function('urirun_connector_kvm/core.py', 'surface_current', 0, 1, 4).
python_function('urirun_connector_kvm/core.py', 'cdp_ensure', 4, 3, 7).
python_function('urirun_connector_kvm/core.py', '_cdp_mod', 0, 2, 0).
python_function('urirun_connector_kvm/core.py', 'cdp_navigate', 2, 3, 9).
python_function('urirun_connector_kvm/core.py', 'cdp_ready', 1, 2, 8).
python_function('urirun_connector_kvm/core.py', '_resolve_act_app', 1, 4, 3).
python_function('urirun_connector_kvm/core.py', '_act_retry_loop', 11, 5, 10).
python_function('urirun_connector_kvm/core.py', '_act_reject', 5, 10, 4).
python_function('urirun_connector_kvm/core.py', '_act_ready', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'ui_act', 10, 7, 12).
python_function('urirun_connector_kvm/core.py', 'cdp_status', 0, 4, 6).
python_function('urirun_connector_kvm/core.py', 'ui_wait', 6, 6, 12).
python_function('urirun_connector_kvm/core.py', 'ui_verify', 2, 3, 6).
python_function('urirun_connector_kvm/core.py', '_capture_native', 1, 1, 4).
python_function('urirun_connector_kvm/core.py', 'ui_locate', 3, 3, 9).
python_function('urirun_connector_kvm/core.py', 'ui_click_text', 7, 8, 11).
python_function('urirun_connector_kvm/core.py', 'doctor', 0, 1, 6).
python_function('urirun_connector_kvm/core.py', 'launch', 4, 4, 5).
python_function('urirun_connector_kvm/core.py', 'list_apps', 1, 2, 4).
python_function('urirun_connector_kvm/core.py', 'urirun_bindings', 0, 1, 1).
python_function('urirun_connector_kvm/core.py', 'connector_manifest', 0, 1, 2).
python_function('urirun_connector_kvm/core.py', 'main', 1, 1, 2).
python_function('urirun_connector_kvm/environment.py', '_safe', 1, 2, 2).
python_function('urirun_connector_kvm/environment.py', 'atspi_ready', 0, 4, 3).
python_function('urirun_connector_kvm/environment.py', 'profile', 0, 13, 14).
python_function('urirun_connector_kvm/launch_backends.py', '_cdp_port', 0, 3, 5).
python_function('urirun_connector_kvm/launch_backends.py', '_cdp_wait', 2, 6, 7).
python_function('urirun_connector_kvm/launch_backends.py', '_xdg_app_dirs', 0, 8, 8).
python_function('urirun_connector_kvm/launch_backends.py', '_parse_desktop_section', 1, 11, 5).
python_function('urirun_connector_kvm/launch_backends.py', '_parse_desktop', 1, 5, 5).
python_function('urirun_connector_kvm/launch_backends.py', '_desktop_entries', 0, 5, 7).
python_function('urirun_connector_kvm/launch_backends.py', '_strip_field_codes', 1, 6, 4).
python_function('urirun_connector_kvm/launch_backends.py', '_find_app', 1, 8, 3).
python_function('urirun_connector_kvm/launch_backends.py', '_resolve_launch_argv', 2, 3, 4).
python_function('urirun_connector_kvm/launch_backends.py', '_inject_cdp_profile', 2, 6, 3).
python_function('urirun_connector_kvm/launch_backends.py', '_inject_chrome_flags', 2, 10, 6).
python_function('urirun_connector_kvm/launch_backends.py', '_launch_xdg', 5, 6, 12).
python_function('urirun_connector_kvm/launch_backends.py', '_launch_macos', 3, 5, 7).
python_function('urirun_connector_kvm/launch_backends.py', '_launch_windows', 3, 5, 8).
python_function('urirun_connector_kvm/launch_backends.py', '_list_xdg', 1, 7, 7).
python_function('urirun_connector_kvm/launch_backends.py', '_list_macos', 1, 5, 7).
python_function('urirun_connector_kvm/strategies.py', 'is_browser', 1, 4, 3).
python_function('urirun_connector_kvm/surface.py', '_active_window', 0, 6, 3).
python_function('urirun_connector_kvm/surface.py', 'current', 0, 7, 7).

% ── Python Classes ───────────────────────────────────────
python_class('computer-use-preview/agent.py', 'BrowserAgent').
python_method('BrowserAgent', '__init__', 4, 1, 10).
python_method('BrowserAgent', '_handle_scroll_at', 1, 3, 5).
python_method('BrowserAgent', '_handle_drag_and_drop', 1, 1, 3).
python_method('BrowserAgent', '_dispatch_action', 1, 11, 13).
python_method('BrowserAgent', '_dispatch_legacy_action', 1, 11, 15).
python_method('BrowserAgent', 'handle_action', 2, 2, 2).
python_method('BrowserAgent', 'handle_legacy_action', 1, 1, 1).
python_method('BrowserAgent', 'get_model_response', 2, 4, 5).
python_method('BrowserAgent', 'get_text', 1, 6, 2).
python_method('BrowserAgent', 'extract_function_calls', 1, 5, 1).
python_method('BrowserAgent', '_build_function_response', 3, 3, 4).
python_method('BrowserAgent', '_trim_old_screenshots', 0, 13, 2).
python_method('BrowserAgent', '_generate_response', 0, 4, 2).
python_method('BrowserAgent', '_render_turn', 2, 5, 7).
python_method('BrowserAgent', '_execute_function_calls', 1, 7, 7).
python_method('BrowserAgent', 'run_one_iteration', 0, 12, 11).
python_method('BrowserAgent', '_get_safety_confirmation', 1, 4, 5).
python_method('BrowserAgent', 'agent_loop', 0, 2, 1).
python_method('BrowserAgent', 'denormalize_x', 1, 1, 2).
python_method('BrowserAgent', 'denormalize_y', 1, 1, 2).
python_class('computer-use-preview/computers/browserbase/browserbase.py', 'BrowserbaseComputer').
python_method('BrowserbaseComputer', '__init__', 2, 1, 2).
python_method('BrowserbaseComputer', '__enter__', 0, 1, 9).
python_method('BrowserbaseComputer', '__exit__', 3, 3, 2).
python_class('computer-use-preview/computers/computer.py', 'EnvState').
python_class('computer-use-preview/computers/computer.py', 'Computer').
python_method('Computer', 'screen_size', 0, 1, 0).
python_method('Computer', 'open_web_browser', 0, 1, 0).
python_method('Computer', 'click_at', 2, 1, 0).
python_method('Computer', 'double_click_at', 2, 1, 0).
python_method('Computer', 'triple_click_at', 2, 1, 0).
python_method('Computer', 'middle_click_at', 2, 1, 0).
python_method('Computer', 'right_click_at', 2, 1, 0).
python_method('Computer', 'mouse_down', 2, 1, 0).
python_method('Computer', 'mouse_up', 2, 1, 0).
python_method('Computer', 'type_text', 2, 1, 0).
python_method('Computer', 'wait', 1, 1, 0).
python_method('Computer', 'hover_at', 2, 1, 0).
python_method('Computer', 'type_text_at', 5, 1, 0).
python_method('Computer', 'scroll_document', 1, 1, 0).
python_method('Computer', 'scroll_at', 4, 1, 0).
python_method('Computer', 'wait_5_seconds', 0, 1, 0).
python_method('Computer', 'go_back', 0, 1, 0).
python_method('Computer', 'go_forward', 0, 1, 0).
python_method('Computer', 'search', 0, 1, 0).
python_method('Computer', 'navigate', 1, 1, 0).
python_method('Computer', 'key_combination', 1, 1, 0).
python_method('Computer', 'press_key', 1, 1, 0).
python_method('Computer', 'key_down', 1, 1, 0).
python_method('Computer', 'key_up', 1, 1, 0).
python_method('Computer', 'take_screenshot', 0, 1, 0).
python_method('Computer', 'drag_and_drop', 4, 1, 0).
python_method('Computer', 'current_state', 0, 1, 0).
python_class('computer-use-preview/computers/kvm/kvm.py', 'KvmComputer').
python_method('KvmComputer', '__init__', 3, 2, 2).
python_method('KvmComputer', '__enter__', 0, 3, 3).
python_method('KvmComputer', '__exit__', 0, 1, 0).
python_method('KvmComputer', '_run', 4, 11, 9).
python_method('KvmComputer', '_state', 0, 2, 4).
python_method('KvmComputer', 'screen_size', 0, 1, 0).
python_method('KvmComputer', 'current_state', 0, 1, 1).
python_method('KvmComputer', 'take_screenshot', 0, 1, 1).
python_method('KvmComputer', '_click', 3, 1, 3).
python_method('KvmComputer', 'click_at', 2, 1, 1).
python_method('KvmComputer', 'double_click_at', 2, 1, 3).
python_method('KvmComputer', 'triple_click_at', 2, 1, 3).
python_method('KvmComputer', 'middle_click_at', 2, 1, 3).
python_method('KvmComputer', 'right_click_at', 2, 1, 3).
python_method('KvmComputer', 'hover_at', 2, 1, 3).
python_method('KvmComputer', 'mouse_down', 2, 1, 3).
python_method('KvmComputer', 'mouse_up', 2, 1, 1).
python_method('KvmComputer', 'drag_and_drop', 4, 1, 3).
python_method('KvmComputer', 'type_text', 2, 2, 2).
python_method('KvmComputer', 'type_text_at', 5, 3, 4).
python_method('KvmComputer', 'key_combination', 1, 1, 3).
python_method('KvmComputer', 'press_key', 1, 1, 2).
python_method('KvmComputer', 'key_down', 1, 1, 2).
python_method('KvmComputer', 'key_up', 1, 1, 1).
python_method('KvmComputer', 'scroll_document', 1, 1, 1).
python_method('KvmComputer', 'scroll_at', 4, 3, 3).
python_method('KvmComputer', 'wait', 1, 1, 3).
python_method('KvmComputer', 'wait_5_seconds', 0, 1, 1).
python_method('KvmComputer', 'open_web_browser', 0, 3, 2).
python_method('KvmComputer', 'navigate', 1, 1, 3).
python_method('KvmComputer', 'search', 0, 1, 1).
python_method('KvmComputer', 'go_back', 0, 1, 2).
python_method('KvmComputer', 'go_forward', 0, 1, 2).
python_class('computer-use-preview/computers/playwright/playwright.py', 'PlaywrightComputer').
python_method('PlaywrightComputer', '__init__', 4, 1, 0).
python_method('PlaywrightComputer', '_handle_new_page', 1, 1, 2).
python_method('PlaywrightComputer', '__enter__', 0, 1, 11).
python_method('PlaywrightComputer', '__exit__', 3, 4, 3).
python_method('PlaywrightComputer', 'open_web_browser', 0, 1, 1).
python_method('PlaywrightComputer', 'click_at', 2, 1, 4).
python_method('PlaywrightComputer', 'double_click_at', 2, 1, 4).
python_method('PlaywrightComputer', 'triple_click_at', 2, 1, 4).
python_method('PlaywrightComputer', 'middle_click_at', 2, 1, 4).
python_method('PlaywrightComputer', 'right_click_at', 2, 1, 4).
python_method('PlaywrightComputer', 'mouse_down', 2, 1, 5).
python_method('PlaywrightComputer', 'mouse_up', 2, 1, 5).
python_method('PlaywrightComputer', 'type_text', 2, 2, 4).
python_method('PlaywrightComputer', 'wait', 1, 1, 2).
python_method('PlaywrightComputer', 'hover_at', 2, 1, 4).
python_method('PlaywrightComputer', 'type_text_at', 5, 4, 6).
python_method('PlaywrightComputer', '_horizontal_document_scroll', 1, 2, 4).
python_method('PlaywrightComputer', 'scroll_document', 1, 4, 3).
python_method('PlaywrightComputer', 'scroll_at', 4, 5, 6).
python_method('PlaywrightComputer', 'wait_5_seconds', 0, 1, 2).
python_method('PlaywrightComputer', 'go_back', 0, 1, 3).
python_method('PlaywrightComputer', 'go_forward', 0, 1, 3).
python_method('PlaywrightComputer', 'search', 0, 1, 1).
python_method('PlaywrightComputer', 'navigate', 1, 2, 4).
python_method('PlaywrightComputer', 'key_combination', 1, 4, 8).
python_method('PlaywrightComputer', 'press_key', 1, 1, 1).
python_method('PlaywrightComputer', 'key_down', 1, 1, 5).
python_method('PlaywrightComputer', 'key_up', 1, 1, 5).
python_method('PlaywrightComputer', 'take_screenshot', 0, 1, 1).
python_method('PlaywrightComputer', 'drag_and_drop', 4, 1, 6).
python_method('PlaywrightComputer', 'current_state', 0, 1, 4).
python_method('PlaywrightComputer', 'screen_size', 0, 2, 0).
python_method('PlaywrightComputer', 'highlight_mouse', 2, 2, 2).
python_class('computer-use-preview/test_agent.py', 'TestBrowserAgent').
python_method('TestBrowserAgent', 'setUp', 0, 1, 2).
python_method('TestBrowserAgent', 'test_multiply_numbers', 0, 1, 2).
python_method('TestBrowserAgent', 'test_handle_action_open_web_browser', 0, 1, 3).
python_method('TestBrowserAgent', 'test_handle_action_click_at', 0, 1, 3).
python_method('TestBrowserAgent', 'test_handle_action_type_text_at', 0, 1, 3).
python_method('TestBrowserAgent', 'test_handle_action_scroll_document', 0, 1, 3).
python_method('TestBrowserAgent', 'test_handle_action_navigate', 0, 1, 3).
python_method('TestBrowserAgent', 'test_handle_action_unknown_function', 0, 1, 3).
python_method('TestBrowserAgent', 'test_denormalize_x', 0, 1, 2).
python_method('TestBrowserAgent', 'test_denormalize_y', 0, 1, 2).
python_method('TestBrowserAgent', 'test_run_one_iteration_no_function_calls', 1, 1, 6).
python_method('TestBrowserAgent', 'test_run_one_iteration_with_function_call', 2, 1, 9).
python_class('computer-use-preview/test_main.py', 'TestMain').
python_method('TestMain', 'test_main_playwright', 3, 1, 5).
python_method('TestMain', 'test_main_browserbase', 3, 1, 5).
python_class('urirun_connector_kvm/backends.py', 'Backend').
python_method('Backend', 'missing', 0, 5, 2).
python_method('Backend', 'available', 0, 3, 2).
python_class('urirun_connector_kvm/backends.py', 'BackendError').
python_class('urirun_connector_kvm/strategies.py', 'CdpStrategy').
python_method('CdpStrategy', 'available', 1, 1, 2).
python_method('CdpStrategy', 'locate', 1, 2, 2).
python_method('CdpStrategy', 'click', 1, 1, 2).
python_method('CdpStrategy', 'fill', 1, 1, 2).
python_class('urirun_connector_kvm/strategies.py', 'AtspiStrategy').
python_method('AtspiStrategy', 'available', 1, 1, 1).
python_method('AtspiStrategy', 'locate', 1, 2, 2).
python_method('AtspiStrategy', 'click', 1, 1, 4).
python_method('AtspiStrategy', 'fill', 1, 1, 4).
python_class('urirun_connector_kvm/strategies.py', 'VisionStrategy').
python_method('VisionStrategy', 'available', 1, 1, 2).
python_method('VisionStrategy', 'locate', 1, 2, 2).
python_method('VisionStrategy', '_click_xy', 3, 3, 4).
python_method('VisionStrategy', 'click', 1, 1, 5).
python_method('VisionStrategy', 'fill', 1, 1, 5).

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
sumd_workflow_step('manifest', 1, 'urirun-kvm manifest').
sumd_workflow('bindings', 'manual').
sumd_workflow_step('bindings', 1, 'urirun-kvm bindings').
sumd_workflow('smoke', 'manual').
sumd_workflow_step('smoke', 1, 'urirun-kvm bindings | urirun connectors smoke - \').
sumd_workflow('test', 'manual').
sumd_workflow_step('test', 1, 'pip install -e . && python3 -m pytest -q && $(MAKE) smoke').
```

## Call Graph

*176 nodes · 247 edges · 10 modules · CC̄=3.3*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `backend` *(in urirun_connector_kvm.backends)* | 1 | 39 | 6 | **45** |
| `task_run` *(in urirun_connector_kvm.core)* | 13 ⚠ | 0 | 41 | **41** |
| `_ok` *(in urirun_connector_kvm.core)* | 1 | 37 | 1 | **38** |
| `_run` *(in urirun_connector_kvm.backends)* | 4 | 26 | 4 | **30** |
| `_apply_capture_postprocessing` *(in urirun_connector_kvm.core)* | 10 ⚠ | 1 | 27 | **28** |
| `_fail_from` *(in urirun_connector_kvm.core)* | 1 | 23 | 3 | **26** |
| `_locate_easyocr` *(in urirun_connector_kvm.backends)* | 14 ⚠ | 0 | 26 | **26** |
| `profile` *(in urirun_connector_kvm.environment)* | 13 ⚠ | 0 | 25 | **25** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/if-uri/urirun-connector-kvm
# generated in 0.08s
# nodes: 176 | edges: 247 | modules: 10
# CC̄=3.3

HUBS[20]:
  urirun_connector_kvm.backends.backend
    CC=1  in:39  out:6  total:45
  urirun_connector_kvm.core.task_run
    CC=13  in:0  out:41  total:41
  urirun_connector_kvm.core._ok
    CC=1  in:37  out:1  total:38
  urirun_connector_kvm.backends._run
    CC=4  in:26  out:4  total:30
  urirun_connector_kvm.core._apply_capture_postprocessing
    CC=10  in:1  out:27  total:28
  urirun_connector_kvm.core._fail_from
    CC=1  in:23  out:3  total:26
  urirun_connector_kvm.backends._locate_easyocr
    CC=14  in:0  out:26  total:26
  urirun_connector_kvm.environment.profile
    CC=13  in:0  out:25  total:25
  urirun_connector_kvm.core.ui_click_text
    CC=8  in:0  out:23  total:23
  urirun_connector_kvm.backends.uinput_abs_click
    CC=9  in:1  out:21  total:22
  urirun_connector_kvm.backends._locate_vql
    CC=11  in:0  out:21  total:21
  urirun_connector_kvm.core.proc_kill
    CC=12  in:0  out:21  total:21
  computer-use-preview.agent.BrowserAgent._dispatch_legacy_action
    CC=11  in:0  out:20  total:20
  urirun_connector_kvm.backends.dispatch
    CC=11  in:2  out:17  total:19
  urirun_connector_kvm.core._positioned_click
    CC=8  in:6  out:12  total:18
  urirun_connector_kvm.core.ui_act
    CC=7  in:0  out:17  total:17
  urirun_connector_kvm.backends._screen_wh
    CC=8  in:2  out:15  total:17
  urirun_connector_kvm.core.capture
    CC=6  in:0  out:17  total:17
  urirun_connector_kvm.cdp.launch_session
    CC=10  in:0  out:17  total:17
  urirun_connector_kvm.backends._compute_abs_coords
    CC=6  in:1  out:15  total:16

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
  urirun_connector_kvm.control  [8 funcs]
    _check_post_condition  CC=4  out:3
    _safe_avail  CC=2  out:1
    _try_act_one  CC=9  out:9
    _try_locate_one  CC=4  out:7
    _verify_value  CC=6  out:7
    act  CC=12  out:12
    report  CC=2  out:2
    route  CC=13  out:8
  urirun_connector_kvm.core  [51 funcs]
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
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
