<!-- Author: Tom Sapletta · https://tom.sapletta.com — Part of the ifURI solution. -->
# xlang — dowód polyglota dla kontraktów kvm://

Teza: kontrakt trasy (`Contract`/`Wire` w `contracts.py`) jest **predykatem nad zachowaniem**,
walidowalnym wobec implementacji w *dowolnym* języku — a nie zrzutem obiektu Pythona.

## Warunek konieczny
Jedno **neutralne źródło**, N cienkich czytników. `contracts.json` jest **generowany** z
dataclassy (`emit_contracts.py`) — nie ręcznie kopiowany. Ręczna kopia per język to pierwotny
dryf ×N. Każdy język czyta ten sam wygenerowany plik:

| plik          | język | rola                                                                 |
|---------------|-------|----------------------------------------------------------------------|
| `peer.py`     | Python| reużywa kernel `contract_gate` (dowód: kernel sterowany kształtem danych) |
| `peer.mjs`    | JS    | port walidatora ~80 linii + konformans                               |
| `peer.go`     | Go    | trzeci czytnik; rozbraja zero-values (waliduje mapy) i float64-int   |

CLI każdego peera jest identyczne, więc spinają się potokiem niezależnie od języka:
```
peer produce <route>          # wypisz złotą kopertę ok
peer consume <prod> <cons>    # zbuduj wejście konsumenta z koperty na stdin, zwaliduj
peer conform                  # asercje konformansu na całym contracts.json
```

## Uruchom
```bash
bash xlang/run.sh
```
co: (0) regeneruje `contracts.json` ze źródła, (1) puszcza konformans w py/js/go,
(2+3) pełną **macierz 3×3** (każdy producent × każdy konsument) dla obu krawędzi —
pełny handoff `close→restore` i częściowy `capture→click`, (4) wstrzykuje uszkodzoną
kopertę i pokazuje, że **każdy** z trzech walidatorów ją odrzuca z exit 1.

## Tarcia per język (uczciwie)
- **Go**: brakujący `int` w structcie = 0, nieodróżnialny od jawnego zera → walidujemy
  `map[string]any`, nie struct. `encoding/json` daje liczby jako `float64` → token `int`
  sprawdza całkowitość (`v == trunc(v)`).
- **Przekrojowo**: wierność liczb przez JSON i „nieobecne vs null vs zero" — dlatego tokeny
  są zdefiniowane przez typy JSON + całkowitość, nie przez typy języka.

## Zewnętrzny driver konformansu (`conformance_driver.py` / `driver.sh`)
Round-trip (`run.sh`) sprawdza **konsumpcję** — czy konsument umie zbudować poprawne wejście.
Nie łapie tego, że węzeł może przejść własną bramę in-language, a **kłamać na drucie**
(bug serializacji/transportu). Driver domyka lukę: odpytuje każdy węzeł po jego prawdziwym
transporcie (JSON-lines RPC po stdin/stdout podprocesu) i waliduje jego **wyjście** wobec
wspólnego kontraktu. Walidację robi **strona trzecia trzymająca kontrakt** — węzeł ufający
sobie nigdy nie złapie własnego buga produkcji.

```bash
bash xlang/driver.sh
```
Każdy peer ma tryb `serve [--lie]`: handler trasy LICZY kopertę z payloadu (nie zwraca złotego
przykładu — inaczej dowód byłby cyrkularny). `--lie` modeluje błąd serializacji PO walidacji
wejścia (int→string na drucie). Driver:
1. uczciwe węzły → każda odpowiedź py/js/go zgodna z `out` przez transport (**WIRE-HONEST**);
2. te same węzły z `--lie` → kłamstwo **ZŁAPANE** dla każdego języka z identycznym werdyktem
   (`out.screen[0]: '2560' does not satisfy 'int'`), choć każdy węzeł przeszedłby własną bramę wejścia.

Złote przykłady stają się **językowo-neutralnym korpusem testowym**: „implementacja X w języku L
jest zgodna" = „dla każdego przykładowego payloadu handler L produkuje wyjście pasujące do `out`".

## Dwie komplementarne warstwy dowodu
| warstwa            | skrypt        | sprawdza            | granica                       |
|--------------------|---------------|---------------------|-------------------------------|
| round-trip         | `run.sh`      | konsumpcja wejścia  | producent→JSON→konsument      |
| driver konformansu | `driver.sh`   | produkcja wyjścia   | strona trzecia→transport→węzeł|
