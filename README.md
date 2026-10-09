# FENG-LABORATORY — Thermo-IoT

Repozytorium rozwojowe projektu **Thermo-IoT** w kontekście FENG 2.27 „Laboratorium Innowatora”.

**Stan na 9 października 2026:** zweryfikowany kod referencyjny, testy i dokumentacja koncepcyjna. **Brak potwierdzonego prototypu, eksperymentów metrologicznych i poziomu TRL.** Ani dostęp do programu, ani dofinansowanie nie są zagwarantowane.

## Dostarczone podsystemy

| Moduł | Zakres | Czego nie dowodzi |
|---|---|---|
| `thermo_iot.energy` | energia superkondensatora, bilans mocy netto, limit duty cycle | mocy na konkretnej rurze |
| `thermo_iot.scheduler` | interwał pomiarowy, rezerwa i ograniczenia mocy | szczytowego prądu TX i cold start |
| `thermo_iot.telemetry` | wersjonowany protokół 8 B, parser TTN v3, idempotentna baza SQLite | pracy LoRaWAN na urządzeniu |
| `thermo_iot.gateway` | offline ingest / report, lokalny webhook z tokenem | bezpiecznej publicznej usługi produkcyjnej |
| `thermo_iot.anomaly` | odporna statystyka odchyleń temperatury | wykrycia wycieków i błędów procesowych |
| `thermo_iot.lab` | analiza pomiarów I–V/TEG z jawnie oznaczonym źródłem danych | kalibracji i jakości pomiarów |
| `firmware/` | przenośny kodek C11 testowany z Pythonem | kompletnego firmware, PCB i modemu |

## Uruchomienie (Python 3.10+ / C11)

```bash
python -m unittest discover -s tests -v
python -m thermo_iot --teg-mw 0.1 --efficiency 0.65 --sleep-uw 8 --cycle-mj 21.9
python -m thermo_iot.gateway ingest --db local-telemetry.sqlite --file examples/ttn_v3_uplink.json
python -m thermo_iot.gateway report --db local-telemetry.sqlite --app district-heat --device pipe-1
python -m thermo_iot.lab --file examples/synthetic_teg_sweep.csv
cc -std=c11 -Wall -Wextra -Werror -pedantic -Ifirmware/include firmware/src/thermo_iot_frame.c firmware/tests/test_frame.c -o /tmp/thermo-iot-frame-tests
/tmp/thermo-iot-frame-tests
```

**Uwaga:** w plikach przykładowych występują wyłącznie **syntetyczne** dane przeznaczone do demonstracji formatu. Lokalny webhook wymaga tokenu i nie jest wystawiany domyślnie poza localhost. Zob. [protokół IoT](docs/PROTOKOL_IOT.md).

## Demonstrator panelu telemetrii (lokalnie)

```bash
python -m thermo_iot.demo --db ./thermo-synthetic-demo.sqlite --count 144
python -m thermo_iot.dashboard --db ./thermo-synthetic-demo.sqlite --port 8766
```

Otwórz `http://127.0.0.1:8766/` na komputerze, na którym działa Python. Dane są **wygenerowane syntetycznie** i zapisywane wyłącznie do nowo utworzonej bazy; skrypt odmawia nadpisania istniejącej bazy. Panel nie pozwala na sterowanie instalacją ani jej urządzeniami. [Opis dashboardu](docs/DASHBOARD.md).

## Baza dokumentacji

- [Karta robocza do wniosku IPB](docs/WNIOSEK_THERMO_IOT.md)
- [Audyt twierdzeń i ryzyk](docs/AUDYT_TWIERDZEN.md)
- [Plan walidacji i progi GO/NO-GO](docs/PLAN_WALIDACJI.md)
- [Model biznesowy i walidacja klientów](docs/MODEL_BIZNESOWY.md)
- [Źródła formalne i naukowe](docs/ZRODLA.md)
- [Architektura MVP](docs/ARCHITEKTURA_MVP.md)
- [Protokół telemetrii / TTN](docs/PROTOKOL_IOT.md)
- [Zasady oceny analityki](docs/ANALITYKA.md)
- [Protokół metrologii TEG i analizy CSV](docs/METROLOGIA_TEG.md)
- [Analiza konkurencji i wcześniejszego stanu techniki](docs/PRIOR_ART_I_WYROZNIK.md)
- [Lista kontrolna gotowości zgłoszenia](docs/GOTOWOSC_ZGLOSZENIA.md)
- [Harmonogram 12 tygodni](docs/HARMONOGRAM_12_TYGODNI.md)
- [BOM funkcjonalny i wymagania techniczne](docs/BOM_I_WYMAGANIA_TECHNICZNE.md)
- [Przegląd kandydatów PMIC/MCU/sensora i ryzyk rozruchu](docs/HARDWARE_PRELIMINARY.md)
- [Energia z profilu czasowego generatora](docs/TRACE_SIMULATION.md)
- [Firmware: histereza i bramka mocy](docs/FIRMWARE_POWER_POLICY.md)
- [Granice bezpieczeństwa IT/OT](SECURITY.md)

## Faza HW / Firmware / Walidacja LoRaWAN (2026-10-09)

**Implementacje repozytoryjne są przeznaczone do prób laboratoryjnych — brak dowodu fizycznej integracji.** Zobacz [macierz stanu dowodowego](docs/STATUS_HARDWARE_TESTS.md).

- [KiCad — schemat i PCB pasywnego adaptera stanowiska](hardware/kicad/) (nie jest finalną płytą PMIC/MCU ani wydanym Gerberem).
- [STM32WLE5JC — aplikacja C11 i wymagany adapter CubeWL](docs/STM32WLE5_FIRMWARE.md) (bez gotowego obrazu `.hex`).
- [Wio-E5: sprzętowy test jednej transmisji i weryfikacja odczytu TTN](docs/TEST_LORAWAN_REAL.md) (wymaga rzeczywistego urządzenia).
- [TEG i PMIC — akwizycja SCPI oraz metrologia](docs/TEG_PMIC_CAPTURE.md) (bez pomiarów rzeczywistych w repo).

Przykładowy test kontrolny portu, **bez emisji**:

```bash
python -m pip install pyserial
python -m thermo_iot.lorawan_fieldtest --port COM3
```

Pojedynczy test fizycznego nadawania (tylko po skonfigurowaniu OTAA/anteny i sprawdzeniu lokalnych wymogów radiowych):

```bash
python -m thermo_iot.lorawan_fieldtest --port COM3 --send --temperature-centic 4300 --capacitor-mv 3000
```

COM3 jest tylko przykładem Windows i musi zostać zastąpiony faktycznym portem. Liczby w tym teście są wpisywane przez operatora; nie dowodzą pracy czujnika. Odbiór należy oddzielnie potwierdzić w The Things Stack.

## Projekt aktywnego harvester'a i ścieżka weryfikacji fizycznej — październik 2026

**Nowe elementy przeznaczone do rzeczywistej budowy demonstratora:**

- [LTC3108GN16 — schemat aktywnego PMIC i projekt PCB w KiCad](hardware/active_power/) — PCB **jeszcze bez poprowadzonych ścieżek**, do przeglądu ERC/DRC; transformator 1:100 poza płytką.
- [Natywny overlay STM32CubeIDE dla STM32WLE5JC / Wio-E5](firmware/stm32wle5jc/make_overlay.py) — generator 4 plików integrowanych z oficjalnym Seeed LoRaWAN End Node; **brak wyprodukowanego pliku ELF/HEX i flash urządzenia**.
- [Pobieranie rzeczywistych parametrów PMIC z pięciu przyrządów SCPI](thermo_iot/pmic.py) — wejście, wyjście, VSTORE, próba cold-start (wymaga własnej aparatury).
- [Próba radiowa Wio-E5 EU868 i weryfikacja odczytu TTN](thermo_iot/lorawan_fieldtest.py) — program istnieje, **brak rzeczywistego raportu odbioru**.
- [Aktualna macierz GO/NO-GO dla sprzętowego MVP](docs/STATUS_HARDWARE_TESTS.md).

**Uwaga:** bit 7 ramki LoRaWAN (0x80) oznacza laboratoryjny odczyt temperatury wewnętrznej MCU. Backend przechowuje te rekordy jako `reference_telemetry` i **wyklucza je z wykrywania anomalii rurociągu**. Nie wolno przedstawiać ich jako pomiaru rury lub wycieku.

## Warunki przed zgłoszeniem

Wymagane są potwierdzone dane pomysłodawców, właścicieli praw IP, zasoby, kompetencje, oświadczenia formalne i oryginalny formularz operatora. Kod i wyniki symulacji nie mogą zastępować protokołów zbudowania i walidacji urządzenia.

Zalecana kolejność: **pomiar TEG → bilans energetyczny/PMIC → podzespoły i prototyp → telemetryka terenowa → zbiór zdarzeń → model predykcyjny → biznes/SLA**.

Prace prowadzone w gałęzi `main`, testowane automatycznie przez GitHub Actions.
