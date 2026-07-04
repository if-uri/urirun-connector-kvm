# Wydajność sterowania przez mesh — dlaczego wolno i plan refaktoryzacji

Dokument roboczy do refaktoryzacji. Wszystkie liczby **zmierzone na żywo** na węźle
lenovo (`http://192.168.188.201:8765`, GNOME-Wayland, LAN, RTT <5 ms) podczas sesji
automatyzacji testowego portalu. Cel: wiedzieć **gdzie idzie czas** i **co realnie skróci**,
zanim tkniemy kod.

## TL;DR — dlaczego pętla zadania trwa dziesiątki sekund

Każda operacja URI płaci **stały narzut zimnego startu**, a percepcja dokłada **wolny OCR**:

| składnik | koszt | dlaczego |
|---|---|---|
| round-trip HTTP `POST /run` | ~kilka ms | LAN, pomijalne |
| **spawn izolowanego subprocesu** | **~290 ms / wywołanie** | `isolated=True` forkuje świeży interpreter + re-import connectora |
| **grab ekranu (mutter-screencast)** | **~800 ms / zrzut** | teardown+init strumienia przy KAŻDYM zrzucie (brak ciepłego streamu) |
| **OCR (tesseract, pełny 3200×3800)** | **~5–8 s** | CPU, cały ekran; `max_width=1600` → ~4,6 s bez utraty trafności |
| akcja (type/key) w subprocesie | szybka | koszt to głównie spawn powyżej |

Złożenie na typową pętlę **percepcja→akcja**:
- `settle()` = kilka zrzutów dhash → `N × (290 + 800)` ≈ **3,7 s**,
- jedna kotwica `ui/query/verify` = capture + OCR ≈ `290 + 800 + 4600` ≈ **5,7 s**,
- sekwencja akcji osobno = `N × (290 + praca)`; batch = `290 + N × praca`.

Do tego **retry przy flaky kompozytorze** (brak kontroli DOM) → pojedyncze zadanie potrafi
zająć 15–30 s. Zmierzone end-to-end „otwórz kompozytor → zweryfikuj → wpisz": **24 s** starym
sposobem.

## Zmierzone liczby (baseline)

```
input/key (trywialny op)            ~290 ms      ← spawn isolated-subprocess dominuje
task_run 3–6 kroków (1 wywołanie)   ~360 ms      ← jeden spawn na całą sekwencję
capture scope=all                   1193 ms, 1,0 MB (3200×3800)
capture max_width=480               ~810 ms, 73 KB   ← podłoga grabu, nie transfer
OCR pełny                           8632 ms, 1049 znaków
OCR max_width=1600                  4604 ms, 1002 znaków   ← sweet spot (bez utraty kotwic)
OCR max_width=900                   2884 ms, 285 znaków    ← za mało (traci trafność)
ui/query/verify (1 kotwica)         5748 ms      ← capture+OCR za KAŻDYM razem
settle()                            ~3679 ms     ← kilka zrzutów × podłoga 800 ms
```

## Cztery korzenie problemu

1. **Wszystko startuje na zimno.** Brak ciepłych procesów: izolowany subprocess na każde
   wywołanie (290 ms), re-init screencast na każdy zrzut (800 ms), tesseract ładowany od zera.
2. **Gadatliwy protokół.** Jedno `POST /run` + jeden subprocess na op. Sekwencja 6 kroków =
   6× narzut, zamiast raz.
3. **Ciężka percepcja.** Pełnoekranowy zrzut + pełnoekranowy OCR CPU. OCR to teraz *dominujący*
   koszt pętli.
4. **Brak kontroli DOM.** Bez CDP/pluginu sterowanie idzie przez wizję/OCR/klawiaturę — wolne
   **i** kruche (fokus pola, otwarcie kompozytora niekonsekwentne) → retry mnożą czas.

## Co już zrobione (po stronie klienta, `vguard.py`) — 3–7×

| technika | zysk | mechanizm |
|---|---|---|
| `batch()` → `task_run` | **6,9×** na sekwencjach | N kroków w jednym subprocesie/round-tripie |
| `verify_texts()` | **3,8×** na percepcji | 1 capture + 1 OCR sprawdza WIELE kotwic (zamiast N×) |
| OCR `max_width=1600` | **1,9×** | mniej pikseli, bez utraty trafności |
| małe zrzuty dhash/settle | 14× mniej danych | `max_width=480` do detekcji zmiany |
| `guarded_batch()` | pewność | batch + postcond `verify_texts` + retry |

**Wyczerpane po stronie klienta.** Dalsze skoki wymagają zmian w connectorze/runtime.

## Plan refaktoryzacji (connector kvm + runtime) — kolejność wg zysk/koszt

### Tier 1 — ciepły screencast (największy lever percepcji)
Trzymać **otwarty strumień pipewire/mutter-screencast** i wyciągać klatkę na żądanie zamiast
teardown+init na każdy zrzut.
- **Zysk:** zrzut **800 → ~50–100 ms** (~8–16×). To przyspiesza `settle`, każdą kotwicę i całą
  pętlę wizyjną.
- **Gdzie:** backend capture w connectorze kvm (`backends.py` / mutter/pipewire).
- **Ryzyko:** trzymanie streamu (zasoby, uprawnienia portalu); fallback do zimnego grabu.

### Tier 2 — szybszy OCR (drugi lever percepcji)
Tesseract CPU pełnoekranowy = 4,6 s. Opcje (najlepiej łącznie):
- **easyocr + GPU** (env: `easyocr=false`) → OCR z ~4,6 s na <1 s, jeśli jest CUDA.
- **naprawić crop** — capture ignoruje `crop_*`/`monitor` (zmierzone: identyczny wynik). OCR
  regionu kotwicy (½ pikseli) → ~2×.
- **tuning tesseract** — `--psm 6`, `--oem 1`, grayscale, mniejszy region.
- **Zysk:** percepcja `verify_texts` z ~4,8 s na <1–2 s.
- **Gdzie:** connector ocr (`ocr://…/image/query/text`) + capture crop w kvm.

### Tier 3 — ciepły worker / de-izolacja tanich handlerów
Izolowany subprocess na każde wywołanie = 290 ms. `batch` już to amortyzuje w sekwencjach,
ale pojedyncze ops i tak płacą.
- **Opcja A:** długożyjący worker connectora (jeden proces obsługuje ops przez kolejkę).
- **Opcja B:** `isolated=False` dla tanich, bezpiecznych handlerów input (bez subprocesu).
- **Zysk:** 290 → ~10 ms na pojedynczy op.
- **Ryzyko:** izolacja jest dla bezpieczeństwa/odporności na crash — de-izolować selektywnie.

### Tier 4 — kontrola DOM (pewność + prędkość dla web)
Bez CDP/pluginu sterowanie przeglądarką jest wolne i kruche (fokus, otwarcie kompozytora).
- **Rozwiązanie:** chrome-plugin (`browser://` po DOM) albo CDP (`--remote-debugging-port`).
- **Zysk:** klik/wpis po selektorze — **niezawodny**, bez OCR/zgadywania; `method_router` już to
  preferuje gdy `cdp.reachable|plugin`.
- **Blokada dziś:** plugin wymaga `Load unpacked` (kopiowanie plików blokuje zepsuty `fs`-write
  — patrz niżej), CDP wymaga restartu przeglądarki.

### Tier 5 — naprawić `fs://` write (odblokowuje transfer/plugin)
`fs://…/write_text`/`write-b64` zwraca `ok:True`, ale plik **znika** (isolated-write nie
utrwala się). Blokuje kopiowanie plików na węzeł (i tym samym instalację pluginu).
- **Zysk:** działający transfer host↔node (`uri-cp` + `archive/unpack-b64` już gotowe po stronie
  klienta) → odblokowuje Tier 4.
- **Gdzie:** handler fs — zapis musi trafiać na realny FS, nie do efemerycznego isolated.

## Zasady, których trzymać się w refaktorze (lekcje sesji)

- **Perceive-once → decide/check-many.** Jeden zrzut/OCR karmi wiele sprawdzeń (`verify_texts`),
  nie N× capture+OCR.
- **Batch domyślnie.** Sekwencje jako `task_run`, nie N wywołań.
- **Ciepłe zamiast zimnego.** Stream, worker, model OCR — trzymać rozgrzane.
- **Wybór metody z profilu env, nie hardkod** (`method_router`): OCR/wizja/DOM zależnie od tego,
  co DZIAŁA i jak pewnie — [[verify-before-act]], [[lenovo-browser-control]].
- **Szybko ZAWSZE ze strażnikiem.** Prędkość bez postcond cicho zawodzi (type bez fokusu) —
  `guarded_batch`.

## Szacowany efekt refaktoru

Zakładając Tier 1+2+3 w connectorze:
- zrzut 800 → ~80 ms, OCR 4,6 s → ~1 s, op 290 → ~10 ms.
- Pętla percepcja→akcja z ~15 s (baseline) i ~8,6 s (klient) → **~1,5–2 s** (connector).
- Z Tier 4 (DOM): sterowanie web **niezawodne** i sub-sekundowe, bez retry.
