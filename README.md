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

## Warunki przed zgłoszeniem

Wymagane są potwierdzone dane pomysłodawców, właścicieli praw IP, zasoby, kompetencje, oświadczenia formalne i oryginalny formularz operatora. Kod i wyniki symulacji nie mogą zastępować protokołów zbudowania i walidacji urządzenia.

Zalecana kolejność: **pomiar TEG → bilans energetyczny/PMIC → podzespoły i prototyp → telemetryka terenowa → zbiór zdarzeń → model predykcyjny → biznes/SLA**.

Prace prowadzone w gałęzi `main`, testowane automatycznie przez GitHub Actions.
