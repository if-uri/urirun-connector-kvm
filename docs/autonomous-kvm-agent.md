# Autonomiczny agent pulpitu oparty o KVM — co działa na każdym systemie i czego brakuje

> Podsumowanie projektowe: jak z `urirun-connector-kvm` zbudować agenta, który
> **autonomicznie wykonuje zadania na pulpicie po URI**, na każdym systemie. Stan
> zweryfikowany **2026-06-25** (m.in. na node `laptop`/lenovo .201).
> Powiązane: [`ARCHITECTURE-cross-platform-backends.md`](ARCHITECTURE-cross-platform-backends.md),
> [`lenovo-control-runbook.md`](lenovo-control-runbook.md).

## 1. Rdzeń przenośności — jedna powierzchnia `kvm://`, wymienne backendy
Każda *akcja* ma backendy wybierane wg OS/sesji + dostępności (`@backend(action,name,platforms,needs_bin/mod)`),
a `kvm://host/doctor/query/report` raportuje co dostępne + podpowiedzi instalacji.

| akcja | Linux-Wayland | Linux-X11 | Windows | macOS |
| --- | --- | --- | --- | --- |
| **capture** | portal / grim / gnome-screenshot | scrot / mss / imagemagick | mss / Pillow | screencapture / mss |
| **type·key·click·move·scroll** | **ydotool** / wtype | xdotool / pynput | pynput | pynput |
| **focus·window_list** | atspi / wmctrl | wmctrl / atspi | pygetwindow | pygetwindow |
| **launch** | XDG `.desktop` (gtk-launch) | XDG | startfile | open -a |
| **locate** | atspi → imgl → tesseract → vql | atspi → imgl → tesseract | tesseract | tesseract |
| **a11y** | AT-SPI | AT-SPI | (UIA — TODO) | (AX — TODO) |

**+ vdisplay** (Xvfb / headless-Wayland / virtual framebuffer) → ten sam stack działa bez
fizycznego monitora (serwery, CI, kontenery). To jest „KVM działający wszędzie".

## 2. Pętla percepcji→lokalizacji→akcji (czy screenshot+VQL+imgl wystarczy?)
**Do pojedynczej nawigacji — tak.** Komplet prymitywów istnieje:
- **perceive** — `screen/query/capture` (downscale `max_width`, `fullSize` do mapowania współrzędnych),
- **locate** — `locate` backendy: **AT-SPI** (rola+nazwa+bbox, bez pikseli) → **imgl** → **tesseract** (OCR, boxy+poligony) → **vql** (`/home/tom/github/oqlos/vql`),
- **act** — KVM `move/click/type/key/scroll` (ydotool/itd.).

Dokładnie pipeline z README: `capture → locate(imgl/img2nl/vql/ocr) → x,y → task: focus/click/type/ctrl+enter`.

## 3. Composite-czasowniki w connectorze (warstwa „komend z bibliotek")
Zamiast ręcznie sklejać 3 connectory, agent woła jeden URI = capture+locate+act+verify:

| URI | rola |
| --- | --- |
| `kvm://node/ui/query/find` | znajdź element po tekście/roli (a11y→imgl→ocr→vql) → kandydaci + bbox |
| `kvm://node/ui/query/locate` | zrzut + OCR/VQL → wszystkie dopasowania z `center` (x,y) |
| `kvm://node/ui/command/click` | znajdź cel i kliknij (akcja a11y albo klik w środek bbox) |
| `kvm://node/ui/command/click-text` | znajdź tekst → klik KVM → opcjonalnie `then_type` + `then_key` (np. ctrl+enter) |
| `kvm://node/ui/command/fill` | znajdź pole, sfokusuj, wpisz wartość (+weryfikacja) |
| `kvm://node/ui/query/wait` | **poll aż element się pojawi** (lub timeout) — pętla zamknięta |
| `kvm://node/ui/query/verify` | **asercja**, że łańcuch znaków jest na ekranie |
| `kvm://node/a11y/command/act` | bezwspółrzędnościowo: focus/click/settext po roli+nazwie (AT-SPI) |

To są „wyspecjalizowane komendy podpięte do bibliotek w connectorze": dodanie nowego
lokalizatora/biblioteki = jeden `@backend("locate", …)`, trasy się nie zmieniają.

## 4. Czego JESZCZE potrzeba do pełnej autonomii
1. **Pętla z weryfikacją** — ZROBIONE w prymitywach (`ui/query/wait`, `ui/query/verify`);
   trzeba ich konsekwentnie używać po każdej akcji (perceive→act→assert→retry).
2. **Lokalizator a11y > piksele** — ZROBIONE (`locate/atspi` priorytet 90 > OCR); rozszerzyć na UIA/AX (Win/mac).
3. **Twardy transform współrzędnych** — logiczne↔fizyczne piksele (HiDPI), offsety monitorów,
   skala zrzutu. Composite łapie zrzut w natywnej rozdzielczości (`ui/query/locate`), ale
   wielomonitorowość wymaga dopięcia offsetów.
4. **Planista perceive-think-act nad action-space URI** — LLM widzi cel NL + obserwację
   (zrzut + boxy + drzewo a11y + lista tras) i emituje następne URI. Wejście: `urirun host ask`
   rozszerzony o obserwację wizualną. Determinizm w rdzeniu, LLM tylko w planerze.
5. **Sesja/auth** — zadania web wymagają zalogowanej aplikacji (np. blocker LinkedIn:
   profil CDP `/tmp/urirun-cdp-profile` nie był zalogowany). Poza zakresem connectora —
   wymaga wcześniej ustawionych profili/sesji.
6. **Bezpieczeństwo akcji nieodwracalnych** — czasowniki publish/send/delete oznaczać
   `safe=false` + bramka dry-run/confirm (jak `shell://…/exec`).
7. **Recovery** — retry/timeout, dismiss-dialog, scroll-to-find (element poza ekranem →
   scroll+recapture). Każde jako mały `@backend`/krok.

## 5. Stan wykonawczy na node `laptop` (.201) — 2026-06-25
- Polityka przywrócona: allow `app/browser/fs/kvm/screen` (gen 30, 35 tras).
- **`ydotool` + `ydotoold` DZIAŁA** (wcześniej brak) → fizyczna emulacja KVM wykonalna.
  `grim`/`gnome-screenshot` (capture), `gtk-launch`/`gio` (launch), 239 aplikacji.
- Wniosek: pętla **capture → locate → KVM-click** jest na .201 gotowa do uruchomienia.
  Brakuje tylko: zalogowanej sesji aplikacji web + treści zadania + (do web) wskazania
  zalogowanego profilu przeglądarki.

## 6. Konkluzja
„KVM na każdy system" = connector-kvm (backendy-dekoratory) + vdisplay — **masz**.
Do nawigowania wystarcza screenshot+VQL/OCR+KVM — **masz**. Do autonomii dochodzą:
composite-verbs (`ui/*` — **zrobione**), pętla weryfikacji (`wait`/`verify` — **zrobione**),
lokalizator a11y (**zrobione**), oraz brakujące: **planista nad URI**, **transform
wielomonitorowy**, **auth/sesje**, **bramki bezpieczeństwa**. Największy zwrot teraz: planista.
