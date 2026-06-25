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
project_file('tests/test_kvm.py', 464, 'python').
project_file('tree.sh', 5, 'shell').
project_file('urirun_connector_kvm/__init__.py', 39, 'python').
project_file('urirun_connector_kvm/backends.py', 1292, 'python').
project_file('urirun_connector_kvm/cdp.py', 349, 'python').
project_file('urirun_connector_kvm/control.py', 215, 'python').
project_file('urirun_connector_kvm/core.py', 919, 'python').
project_file('urirun_connector_kvm/environment.py', 95, 'python').
project_file('urirun_connector_kvm/launch_backends.py', 283, 'python').
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
python_function('tests/test_kvm.py', 'test_cdp_start_session_reuses_without_spawn', 1, 4, 4).
python_function('tests/test_kvm.py', 'test_cdp_start_session_launches_and_returns_immediately', 1, 2, 3).
python_function('tests/test_kvm.py', 'test_cdp_await_ready_polls_without_spawn', 1, 4, 4).
python_function('tests/test_kvm.py', 'test_ui_wait_success_has_no_found_collision', 1, 2, 2).
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
python_function('urirun_connector_kvm/cdp.py', 'start_session', 3, 8, 12).
python_function('urirun_connector_kvm/cdp.py', 'await_ready', 1, 4, 6).
python_function('urirun_connector_kvm/cdp.py', 'launch_session', 4, 3, 4).
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
python_function('urirun_connector_kvm/core.py', 'window_close', 1, 6, 6).
python_function('urirun_connector_kvm/core.py', 'window_restore', 1, 5, 13).
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
python_function('urirun_connector_kvm/core.py', 'cdp_ensure', 4, 6, 10).
python_function('urirun_connector_kvm/core.py', 'cdp_session_ready', 1, 4, 10).
python_function('urirun_connector_kvm/core.py', '_cdp_mod', 0, 2, 0).
python_function('urirun_connector_kvm/core.py', 'cdp_navigate', 2, 3, 9).
python_function('urirun_connector_kvm/core.py', 'cdp_ready', 1, 2, 8).
python_function('urirun_connector_kvm/core.py', '_resolve_act_app', 1, 4, 3).
python_function('urirun_connector_kvm/core.py', '_act_retry_loop', 11, 5, 10).
python_function('urirun_connector_kvm/core.py', '_act_reject', 5, 10, 4).
python_function('urirun_connector_kvm/core.py', '_act_ready', 1, 3, 5).
python_function('urirun_connector_kvm/core.py', 'ui_act', 10, 7, 12).
python_function('urirun_connector_kvm/core.py', 'cdp_status', 0, 2, 4).
python_function('urirun_connector_kvm/core.py', 'ui_wait', 6, 4, 12).
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

