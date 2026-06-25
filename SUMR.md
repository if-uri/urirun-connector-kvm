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

## Workflows

## Dependencies

### Runtime

```text markpact:deps python
urirun>=0.4.14
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

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

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

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 12f 2104L | shell:3,python:3,yaml:3,toml:1,json:1 | 2026-06-25
# generated in 0.00s
# CC̅=3.9 | critical:3/99 | dups:0 | cycles:0

HEALTH[3]:
  🟡 CC    _parse_desktop CC=15 (limit:15)
  🟡 CC    _locate_tesseract CC=26 (limit:15)
  🟡 CC    capture CC=15 (limit:15)

REFACTOR[1]:
  1. split 3 high-CC methods  (CC>15)

PIPELINES[68]:
  [1] Src [is_x11]: is_x11 → is_wayland
      PURITY: 100% pure
  [2] Src [missing]: missing → have_bin
      PURITY: 100% pure
  [3] Src [available]: available → platform_tag → is_wayland
      PURITY: 100% pure
  [4] Src [registry_report]: registry_report
      PURITY: 100% pure
  [5] Src [_cap_portal]: _cap_portal → backend
      PURITY: 100% pure
  [6] Src [_cap_grim]: _cap_grim → backend
      PURITY: 100% pure
  [7] Src [_cap_mss]: _cap_mss → backend
      PURITY: 100% pure
  [8] Src [_cap_pillow]: _cap_pillow → backend
      PURITY: 100% pure
  [9] Src [_cap_scrot]: _cap_scrot → backend
      PURITY: 100% pure
  [10] Src [_cap_im]: _cap_im → backend
      PURITY: 100% pure
  [11] Src [_cap_gnome]: _cap_gnome → backend
      PURITY: 100% pure
  [12] Src [_cap_macos]: _cap_macos → backend
      PURITY: 100% pure
  [13] Src [_type_ydotool]: _type_ydotool → backend
      PURITY: 100% pure
  [14] Src [_type_wtype]: _type_wtype → backend
      PURITY: 100% pure
  [15] Src [_type_xdotool]: _type_xdotool → backend
      PURITY: 100% pure
  [16] Src [_type_pynput]: _type_pynput → backend
      PURITY: 100% pure
  [17] Src [_click_ydotool]: _click_ydotool → backend
      PURITY: 100% pure
  [18] Src [_click_xdotool]: _click_xdotool → backend
      PURITY: 100% pure
  [19] Src [_click_pynput]: _click_pynput → backend
      PURITY: 100% pure
  [20] Src [_move_ydotool]: _move_ydotool → backend
      PURITY: 100% pure
  [21] Src [_move_xdotool]: _move_xdotool → backend
      PURITY: 100% pure
  [22] Src [_move_pynput]: _move_pynput → backend
      PURITY: 100% pure
  [23] Src [_key_ydotool]: _key_ydotool → backend
      PURITY: 100% pure
  [24] Src [_key_xdotool]: _key_xdotool → backend
      PURITY: 100% pure
  [25] Src [_key_pynput]: _key_pynput → backend
      PURITY: 100% pure
  [26] Src [_scroll_ydotool]: _scroll_ydotool → backend
      PURITY: 100% pure
  [27] Src [_scroll_pynput]: _scroll_pynput → backend
      PURITY: 100% pure
  [28] Src [_focus_wmctrl]: _focus_wmctrl → backend
      PURITY: 100% pure
  [29] Src [_focus_pgw]: _focus_pgw → backend
      PURITY: 100% pure
  [30] Src [_winlist_wmctrl]: _winlist_wmctrl → backend
      PURITY: 100% pure
  [31] Src [_launch_xdg]: _launch_xdg → backend
      PURITY: 100% pure
  [32] Src [_launch_macos]: _launch_macos → backend
      PURITY: 100% pure
  [33] Src [_launch_windows]: _launch_windows → backend
      PURITY: 100% pure
  [34] Src [_list_xdg]: _list_xdg → backend
      PURITY: 100% pure
  [35] Src [_list_macos]: _list_macos → backend
      PURITY: 100% pure
  [36] Src [_focus_atspi]: _focus_atspi → backend
      PURITY: 100% pure
  [37] Src [_locate_tesseract]: _locate_tesseract → backend
      PURITY: 100% pure
  [38] Src [_locate_easyocr]: _locate_easyocr → backend
      PURITY: 100% pure
  [39] Src [bbox_center]: bbox_center
      PURITY: 100% pure
  [40] Src [_locate_atspi]: _locate_atspi → backend
      PURITY: 100% pure
  [41] Src [_locate_imgl]: _locate_imgl → backend
      PURITY: 100% pure
  [42] Src [_locate_vql]: _locate_vql → backend
      PURITY: 100% pure
  [43] Src [uinput_abs_click]: uinput_abs_click → _uinput_create_abs
      PURITY: 100% pure
  [44] Src [surface_report]: surface_report → platform_tag → is_wayland
      PURITY: 100% pure
  [45] Src [capture]: capture → _ok
      PURITY: 100% pure
  [46] Src [type_text]: type_text → _ok
      PURITY: 100% pure
  [47] Src [key]: key → _ok
      PURITY: 100% pure
  [48] Src [click]: click → _ok
      PURITY: 100% pure
  [49] Src [move]: move → _ok
      PURITY: 100% pure
  [50] Src [scroll]: scroll → _ok
      PURITY: 100% pure

LAYERS:
  urirun_connector_kvm/           CC̄=3.9    ←in:0  →out:0
  │ !! backends                  1111L  2C   71m  CC=26     ←0
  │ !! core                       457L  0C   28m  CC=15     ←0
  │ connector.manifest.json     75L  0C    0m  CC=0.0    ←0
  │ __init__                    30L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ planfile.yaml              188L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                94L  0C    0m  CC=0.0    ←0
  │ project.sh                  69L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              38L  0C    0m  CC=0.0    ←0
  │ Makefile                    13L  0C    0m  CC=0.0    ←0
  │ tree.sh                      4L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=0.0    ←in:0  →out:0
  │ quickstart.sh                5L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │

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
# code2llm/evolution | 99 func | 2f | 2026-06-25
# generated in 0.00s

NEXT[4] (ranked by impact):
  [1] !! SPLIT           urirun_connector_kvm/backends.py
      WHY: 1111L, 2 classes, max CC=26
      EFFORT: ~4h  IMPACT: 28886

  [2] !! SPLIT-FUNC      _locate_tesseract  CC=26  fan=28
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 728

  [3] !  SPLIT-FUNC      capture  CC=15  fan=24
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 360

  [4] !  SPLIT-FUNC      _parse_desktop  CC=15  fan=10
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 150


RISKS[1]:
  ⚠ Splitting urirun_connector_kvm/backends.py may break 71 import paths

METRICS-TARGET:
  CC̄:          3.9 → ≤2.7
  max-CC:      26 → ≤13
  god-modules: 1 → 0
  high-CC(≥15): 3 → ≤1
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
  prev CC̄=3.8 → now CC̄=3.9
```

## Intent

Cross-platform KVM connector (screen capture + keyboard/mouse) for ifuri and urirun
