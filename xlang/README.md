<!-- Author: Tom Sapletta · https://tom.sapletta.com — Part of the ifURI solution. -->
# xlang — dowód polyglota dla kontraktów kvm://

Teza: kontrakt trasy (`Contract`/`Wire` w `contracts.py`) jest **predykatem nad zachowaniem**,
walidowalnym wobec implementacji w *dowolnym* języku — a nie zrzutem obiektu Pythona.

## Warunek konieczny
Jedno **neutralne źródło**, N cienkich czytników. `contracts.json` jest **generowany** z
dataclassy (`emit_contracts.py`) — nie ręcznie kopiowany. Ręczna kopia per język to pierwotny
dryf ×N. Każdy język czyta ten sam wygenerowany plik:

| plik              | język | rola                                                                 |
|-------------------|-------|----------------------------------------------------------------------|
| `peer.py`         | Python| reużywa kernel `contract_gate` (dowód: kernel sterowany kształtem danych) |
| `peer.mjs`        | JS    | port walidatora ~80 linii + konformans                               |
| `peer.go`         | Go    | trzeci czytnik; rozbraja zero-values (waliduje mapy) i float64-int   |
| `rust/src/main.rs`| Rust  | OPCJONALNY czwarty czytnik (gdy `cargo` jest); dowód, że N≠3         |

Rust jest dołączany dynamicznie: `run.sh`/`driver.sh`/`transport_swap.sh` budują go gdy `cargo`
jest dostępny i wpinają węzeł `rs`; bez `cargo` brama py/js/go zostaje zielona. To czyni „N czytników"
dosłownym — liczba języków nie jest zaszyta w trójkę.

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

## Niezmienniczość transportu (`transport_swap.py` / `transport_swap.sh`)
Tożsamość operacji to **URI, nie transport**. Każdy peer ma drugi tryb `serve-http` —
TEN SAM handler za HTTP zamiast stdio (port efemeryczny, węzeł wypisuje `READY <port>`).
Driver dla każdego języka uruchamia oba transporty i na każdej trasie × złotym payloadzie
sprawdza: koperta po stdio zgodna z `out`, koperta po HTTP zgodna z `out`, i **obie identyczne**.

```bash
bash xlang/transport_swap.sh
```
Wynik: dla py/js/go `5/5 koperta identyczna, 5/5 zgodna z out` → **TRANSPORT-INVARIANT**.
Gdyby koperta zależała od transportu, „kontrakt" byłby naprawdę szczegółem transportu.

## Konsument NIEPISANY RĘCZNIE (`emit_jsonschema.py` / `jsonschema_proof.sh`)
Czytniki py/js/go/rust pisaliśmy ręcznie. Ostatni krok: neutralne źródło ma feedować też
konsumentów, których NIKT nie pisze — codegen, bramy API, tooling IDE — czytających STANDARD,
nie nasz mini-język. `emit_jsonschema.py` tłumaczy ten sam dataclass-owy źródło na **JSON Schema
(draft 2020-12)**; `jsonschema_proof.py` waliduje nim złoty korpus **off-the-shelf** walidatorem
(biblioteka `jsonschema`, implementacja specyfikacji IETF) — ZEROWYM własnym kodem walidacji.

```bash
bash xlang/jsonschema_proof.sh
```
Wynik: `9/9 złotych przykładów` przechodzi standardowy walidator, a to samo kłamstwo na drucie
jest **ZŁAPANE** (`screen/0: '2560' is not of type 'integer'`). Niuans tłumaczenia: nasze `oneOf`
znaczy „pasuje do CO NAJMNIEJ jednego" (walidator zwraca przy pierwszym trafieniu) → mapuje się na
`anyOf` z draftu, NIE na `oneOf` (które jest XOR).

## Egzekucja w CZASIE KOMPILACJI (`emit_typescript.py` / `typescript_proof.sh`)
Warstwy wyżej egzekwują kontrakt w RUNTIME. Ostatnia przenosi egzekucję do CZASU KOMPILACJI:
`emit_typescript.py` generuje typy TS (`ts/contracts.d.ts`) z tego samego źródła, a `tsc` sprawdza
konsumenta ZANIM program się uruchomi. `ts/check_ok.ts` (screen to liczby) MUSI się skompilować;
`ts/check_bad.ts` (to samo kłamstwo: screen jako stringi) MUSI nie — `tsc` zwraca
`error TS2322: Type 'string' is not assignable to type 'number'`. Udana kompilacja `check_bad.ts`
= brak zębów = porażka bramy.

```bash
bash xlang/typescript_proof.sh
```
To inny RODZAJ zębów niż reszta: błąd łapany przed uruchomieniem, nie podczas walidacji w locie.

## Pięć komplementarnych warstw dowodu
| warstwa            | skrypt                | sprawdza                       | granica                          |
|--------------------|-----------------------|--------------------------------|----------------------------------|
| round-trip         | `run.sh`              | konsumpcja wejścia             | producent→JSON→konsument         |
| driver konformansu | `driver.sh`           | produkcja wyjścia              | strona trzecia→transport→węzeł   |
| swap transportu    | `transport_swap.sh`   | niezależność od transportu     | węzeł × stdio vs HTTP            |
| standardowy schemat| `jsonschema_proof.sh` | konsument niepisany ręcznie    | off-the-shelf walidator schematu |
| czas kompilacji    | `typescript_proof.sh` | egzekucja przed uruchomieniem  | `tsc` na generowanych typach     |

## Egzekwowane, nie tylko uruchamialne
Dowód to **niezmiennik bramy**, nie demo do ręcznego odpalania:
- `make contract-ci` — pełna brama 9/9 (self-conformance → kompozycja → IPC → shape-lint →
  polyglot → driver → swap transportu → standardowy schemat → czas kompilacji); `ci/contract_ci.sh`
  woła skrypty wprost dla czytelnych logów.
- `make xlang` — sam dowód polyglota (trzy skrypty po kolei).
- `tests/test_xlang_polyglot.py` — parytet pod `URIRUN_CONTRACT_CHECK=1 pytest`: ta sama brama
  co `test_contract_composition.py`. Testy polyglota pomijają się bez `node`/`go`; dowód JSON Schema
  jest python-only i działa na python-only CI (pomija się tylko bez biblioteki `jsonschema`).
