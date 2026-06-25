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

