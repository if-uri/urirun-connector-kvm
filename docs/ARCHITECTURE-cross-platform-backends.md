# Architektura — jeden connector `kvm` na każdy system, na dekoratorach + bibliotekach

> Cel: złożyć CAŁY stack sterowania pulpitem (dziś rozrzucony po `gillm_capture.py`,
> `tb_handler.py`, `cdp-flat-handler.py` i bieżącym `core.py`) w jeden pakiet
> `urirun-connector-kvm`, który działa na X11, Wayland, Windows i macOS — bo każda
> *zdolność* (capture/key/type/move/launch/facts) ma wymienne **backendy** wybierane
> automatycznie. Stan wyjściowy i komendy: [`lenovo-control-runbook.md`](lenovo-control-runbook.md).

## 1. Problem z obecnym `core.py`

Dzisiejszy `core.py` wybiera narzędzie inline w `_capture_backends()` / `_input_backends()`
i woła je przez `subprocess`. To działa, ale:

- **Tylko narzędzia CLI** (`grim`, `scrot`, `xdotool`, `wtype`, `ydotool`) — nie korzysta
  z bibliotek Pythona (`mss`, `pynput`, `Pillow`), więc na Windows/macOS nie ma czym działać.
- **Brak portalu** — najważniejsza droga na GNOME/Wayland (`gillm_capture`) żyje poza
  connectorem; connector w tej sesji zwraca czarną klatkę albo `ok:false`.
- **Brak `type` / `launch` / `facts`** — te zdolności są w `tb_handler.py`, nie w connectorze.
- Dodanie nowego backendu = edycja kilku funkcji (`_capture_argv`, `_capture_backends`, …).

## 2. Wzorzec: rejestr backendów na dekoratorach

Rozdziel DWIE warstwy:

1. **Powierzchnia URI** — stabilny kontrakt `kvm://`/`app://`/`screen://`, deklarowany
   raz przez `@conn.handler` (jak teraz). To się nie zmienia.
2. **Backendy** — małe funkcje, każda obsługuje jedną zdolność jedną biblioteką/narzędziem,
   ostemplowane dekoratorem: jaką sesję/OS wspiera, jaki ma priorytet, jak sprawdzić
   dostępność. Dyspozytor wybiera pierwszy *dostępny* backend wg priorytetu.

```python
# urirun_connector_kvm/backends.py
from __future__ import annotations
import os, platform, shutil
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True)
class Backend:
    capability: str                 # "capture" | "key" | "type" | "move" | "click" | "launch" | "facts"
    name: str                       # "portal" | "grim" | "mss" | "ydotool" | "pynput" | "xdg" | ...
    fn: Callable[..., dict]
    available: Callable[[], bool]   # cheap probe: is this backend usable on THIS host now?
    priority: int = 50              # higher wins
    sessions: tuple = ()            # ("wayland",) ("x11",) — () = any session
    systems: tuple = ()             # ("Linux","Windows","Darwin") — () = any OS

_REGISTRY: dict[str, list[Backend]] = {}

def backend(capability, name, *, priority=50, sessions=(), systems=(), available=None):
    """Decorator: register `fn` as one backend for `capability`."""
    def deco(fn):
        _REGISTRY.setdefault(capability, []).append(
            Backend(capability, name, fn, available or (lambda: True),
                    priority, tuple(sessions), tuple(systems)))
        _REGISTRY[capability].sort(key=lambda b: -b.priority)
        return fn
    return deco

def _session() -> str:
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE","").lower() == "wayland":
        return "wayland"
    return "x11"

def viable(capability):
    sysname, sess = platform.system(), _session()
    for b in _REGISTRY.get(capability, []):
        if b.systems and sysname not in b.systems:  continue
        if b.sessions and sess not in b.sessions:    continue
        if not b.available():                        continue
        yield b

def dispatch(capability, **kwargs) -> dict[str, Any]:
    """Try viable backends in priority order; first ok() wins, reports `via`."""
    tried, last = [], None
    for b in viable(capability):
        tried.append(b.name)
        res = b.fn(**kwargs) or {}
        if res.get("ok"):
            res.setdefault("via", b.name)
            res.setdefault("wayland", _session() == "wayland")
            return res
        last = res
    err = (last or {}).get("error", "no usable backend")
    detail = f" (tried: {', '.join(tried)})" if tried else " (no backend matched this OS/session)"
    return {"ok": False, "error": err + detail, "capability": capability,
            "system": platform.system(), "session": _session()}
```

Trasy stają się trywialne i niezmienne:

```python
# urirun_connector_kvm/core.py
import urirun
from . import backends as B
conn = urirun.connector("kvm", scheme="kvm")

@conn.handler("input/command/key", isolated=True, meta={"label": "Send a key / chord"})
def key(key: str = "") -> dict:
    if not key: return urirun.fail("key is required", connector="kvm")
    return B.dispatch("key", combo=key)

@conn.handler("input/command/type", isolated=True, meta={"label": "Type literal text"})
def type_text(text: str = "") -> dict:
    if not text: return urirun.fail("text is required", connector="kvm")
    return B.dispatch("type", text=text)

@conn.handler("input/command/move", isolated=True, meta={"label": "Move the pointer"})
def move(x: int = 0, y: int = 0) -> dict:
    return B.dispatch("move", x=x, y=y)

@conn.handler("screen/query/capture", isolated=True, meta={"label": "Capture the screen"})
def capture(output: str = "screen.png") -> dict:
    res = B.dispatch("capture", output=output)
    return urirun.tag(res, "screenshot") if res.get("ok") else res

@conn.handler("host/query/facts", meta={"label": "Report desktop capabilities"})
def facts() -> dict:
    return B.facts()   # session, OS, which backends are viable per capability

# multi-scheme w jednym connectorze — pełny URI omija self.scheme:
@conn.handler("app://host/desktop/command/launch", isolated=True, meta={"label": "Launch a desktop app"})
def launch(app: str = "", compose: str = "", args: list | None = None, settle: float = 0) -> dict:
    return B.dispatch("launch", app=app, compose=compose, args=args or [], settle=settle)

@conn.handler("app://host/desktop/query/list", meta={"label": "List launchable apps"})
def list_apps(filter: str = "") -> dict:
    return B.dispatch("launch_list", filter=filter)
```

> **Jeden connector, wiele schematów.** `conn.handler("app://host/...")` z pełnym URI
> omija `self.scheme="kvm"`, ale zachowuje `meta.connector="kvm"`, więc `app://`,
> `screen://` i `kvm://` żyją w JEDNYM pakiecie. (Sprawdzone w `Connector.uri()` rdzenia urirun.)

## 3. Backendy do zarejestrowania (biblioteki + narzędzia)

Każdy wiersz = jeden `@backend(...)`. Dodanie wsparcia = jedna funkcja, zero zmian w trasach.

### capture
| backend | priorytet | OS / sesja | biblioteka/narzędzie | uwagi |
| --- | --- | --- | --- | --- |
| `portal` | 90 | Linux / Wayland | `dbus`+`gi` (PyGObject) | **port `gillm_capture`** — jedyne na GNOME/Wayland headless |
| `grim` | 70 | Linux / Wayland | `grim` (CLI) | wlroots (sway/Hyprland), nie GNOME |
| `mss` | 65 | Linux(X11)/Windows/macOS | **`mss`** | szybki, czysto-pythonowy grab; brak Wayland |
| `pillow` | 60 | Windows/macOS | **`Pillow`** `ImageGrab` | natywne na Win/mac |
| `gnome-screenshot` | 55 | Linux / Wayland | CLI | przez portal/kompozytor |
| `scrot` | 50 | Linux / X11 | CLI | X11 root |
| `spectacle` | 45 | Linux | CLI (KDE) | |

### key / type / move / click
| backend | priorytet | OS / sesja | biblioteka/narzędzie | uwagi |
| --- | --- | --- | --- | --- |
| `ydotool` | 80 | Linux / Wayland | `ydotool`+`ydotoold` | uinput poniżej kompozytora — dociera wszędzie; akordy |
| `wtype` | 75 | Linux / Wayland | `wtype` | `-M/-k/-m` dla akordów (port z `tb_handler.key`) |
| `pynput` | 65 | X11/Windows/macOS | **`pynput`** | cross-platform; brak Wayland |
| `pyautogui` | 60 | X11/Windows/macOS | **`pyautogui`** | input+screenshot, cięższy |
| `xdotool` | 50 | Linux / X11 | CLI | |

### launch / launch_list
| backend | priorytet | OS | mechanizm | uwagi |
| --- | --- | --- | --- | --- |
| `xdg` | 80 | Linux | wpisy `.desktop` (`gtk-launch`/parsowany `Exec`) | **port `tb_handler.launch`/`list_apps`** — Flatpak/Snap/PATH |
| `macos` | 70 | Darwin | `open -a` / `/Applications` + `mdfind` | katalog `.app` |
| `windows` | 70 | Windows | `os.startfile` / `start` / Start-Menu `.lnk` | katalog skrótów |

### facts (introspekcja — zastępuje `tb_handler.probe`)
Nie dyspozytor, lecz raport: `system`, `session`, dla każdej zdolności lista *viable*
backendów (`viable(cap)`), `ydotoold_running`, liczba aplikacji, GPU/monitory
(`screeninfo`). To realizuje pomysł `env://…/host/query/facts` z planu optymalizacji —
zamienia „deploy-i-zgaduj" w „zapytaj-potem-planuj".

## 4. Zależności jako opcjonalne extras (degradacja, nie twarde wymaganie)

Connector MUSI działać bez żadnej z bibliotek (degraduje do narzędzi CLI lub zwraca
czytelny `ok:false`). Dlatego każdy backend importuje swoją bibliotekę **leniwie** w
`available()` (try/except → False), a w `pyproject.toml`:

```toml
[project.optional-dependencies]
linux   = ["dbus-python; sys_platform=='linux'", "PyGObject; sys_platform=='linux'"]
xshot   = ["mss"]
desktop = ["pynput", "Pillow", "screeninfo"]
heavy   = ["pyautogui", "pywinctl"]
test    = ["pytest>=8"]
```

`pip install "urirun-connector-kvm[desktop,xshot]"` na laptopie z X11/Win/mac;
`...[linux]` tam, gdzie potrzebny portal. Brak extras → tylko backendy CLI (jak dziś).

## 5. Powierzchnia tras po konsolidacji

```
kvm://<node>/input/command/key       # klawisz / akord (ctrl+s, Tab, Return)
kvm://<node>/input/command/type      # literalny tekst                        [NOWE]
kvm://<node>/input/command/move      # ruch myszą (absolutny)
kvm://<node>/input/command/click     # klik                                   [NOWE]
kvm://<node>/screen/query/capture    # zrzut — backend portal/grim/mss/…      [UPGRADE]
kvm://<node>/host/query/facts        # zdolności sesji/OS                     [NOWE]
app://<node>/desktop/query/list      # katalog aplikacji (XDG/mac/win)        [NOWE]
app://<node>/desktop/command/launch  # uruchom app (+ -compose)               [NOWE]
screen://<node>/portal/query/capture # alias capture (zgodność wstecz)        [ALIAS]
```

## 6. Plan migracji (przyrostowo, testy zielone po każdym kroku)

1. **`backends.py`** — rejestr + dyspozytor + `_session()`/`facts()` (powyżej).
2. **Przeportuj istniejące** capture/key/move z `core.py` na `@backend` (grim/scrot/mss
   dla capture; ydotool/wtype/xdotool dla input). Testy `test_kvm.py` zostają zielone —
   trasy bez zmian, tylko ciało woła `B.dispatch`.
3. **Dodaj `portal`** (port `gillm_capture`, `available()` = `python -c "import dbus, gi"`).
   To domyka zrzut na GNOME/Wayland → `screen://…/portal` może zniknąć z osobnego deployu.
4. **Dodaj `type` + akordy** (port `tb_handler.type_text`/`key` → backendy `wtype`/`ydotool`,
   plus `pynput`/`pyautogui` cross-platform).
5. **Dodaj `app://launch` + `list`** (port `tb_handler.launch`/`list_apps`, backend `xdg`;
   potem `macos`/`windows`).
6. **Dodaj `host/query/facts`** (zastępuje `kvm://…/diag/query/which`).
7. **Biblioteki** (`mss`/`pynput`/`Pillow`/`screeninfo`) jako extras (§4) — każda jeden backend.
8. **Test konformności** — dla każdej zdolności: na hoście bez żadnego backendu trasa zwraca
   czytelny `ok:false` (nie wyjątek); `facts` poprawnie listuje viable backendy per OS.

Po tym kroku deploy na lenovo to JEDEN connector zamiast trzech plików:
```bash
urirun host deploy http://192.168.188.201:8766 \
  --connector urirun-connector-kvm \
  --allow 'kvm://**' --allow 'app://**' --allow 'screen://**' \
  --identity ~/.ssh/id_ed25519
```
(CDP/`browser://` zostaje osobnym connectorem `urirun-connector-browser-control` — inna domena.)

## 7. Dlaczego to spełnia cel

- **Każdy system** — `viable()` filtruje po `platform.system()` + sesji; ta sama trasa
  `kvm://…/screen/query/capture` daje portal na GNOME, `mss` na Windows, `Pillow` na macOS.
- **Wiele bibliotek** — `mss`, `pynput`, `Pillow`, `pyautogui`, `dbus`+`gi`, `screeninfo`,
  każda jako jeden `@backend`, leniwie importowana, opcjonalna.
- **Dekoratory** — `@conn.handler` deklaruje stabilny URI; `@backend` rejestruje
  implementacje. Nowa biblioteka/OS = jedna ostemplowana funkcja, zero zmian w trasach.
- **Degradacja** — bez extras działa na samych narzędziach CLI; brak wszystkiego → jasny `ok:false`.
