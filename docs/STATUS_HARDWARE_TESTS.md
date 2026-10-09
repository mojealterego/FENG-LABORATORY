# Thermo-IoT — rejestr weryfikacji hardware MVP

**Aktualizacja:** 9.10.2026. Wykonane zostały realne pliki KiCad, kod firmware/interoperability, akwizycja SCPI i testy hostowe. **Nie wykonano prac wymagających fizycznego sprzętu.**

| Wymóg | Plik/wyjście | Dowód uzyskany | Brakujący twardy warunek |
|---|---|---|---|
| Schemat aktywnego generatora | `hardware/active_power/ltc3108_power_breakout.kicad_sch` | zapisany schemat LTC3108 GN16, kondensatory/wyprowadzenia | otworzenie KiCad, 100% zweryfikowana netlista, elektryczny ERC i zasilanie docelowej płytki MCU |
| PCB aktywne | `hardware/active_power/ltc3108_power_breakout.kicad_pcb` | rozmieszczenie footprints i nets | **trasowanie wszystkich nets, realny DRC, zamówienie, test PCB** |
| PCB pomocnicze | `hardware/kicad/thermo_bench_carrier.kicad_pcb` | płytka adaptera laboratoryjnego z trasami UART/3.3V | KiCad ERC/DRC, montaż, test ciągłości i zasilania |
| Firmware STM32WLE5JC | `firmware/stm32wle5jc/make_overlay.py`, `firmware/src/thermo_iot_app.c` | testowany hostowo application core C11 i generator overlay dla prawdziwego Seeed SDK | trzy skompilowane obiekty Cortex-M4/ARM EABI5; nadal brak całego linked `.elf/.hex` STM32CubeIDE, integracji czujnika, ADC, zasilania, SWD/flash i pracy bezbateryjnej |
| Pomiar TEG | `thermo_iot/bench_scpi.py` + `thermo_iot.lab` | kod akwizycji przyrządowej i analizy krzywych P-V | fizyczne stanowisko, seria I-V, `ΔT` na obu stronach TEG, protokół kalibracji |
| Pomiar PMIC | `thermo_iot/pmic.py` | kod dla Vin/Iin, Vout/Iout i VSTORE, cold-start | 5 realnych przyrządów / DAQ, rejestr surowych danych, ESR oraz piki |
| Realny uplink LoRaWAN | `thermo_iot.lorawan_fieldtest` | kod AT+JOIN/MSGHEX i weryfikacja eksportu TTN | podłączona antena i Wio-E5, network server, bramka/zasięg, RSSI/SNR/FCnt + niezależnie otrzymany uplink |
| Ochrona wiarygodności procesu | `thermo_iot.telemetry` | rama flags 0x80 quarantined as `reference_telemetry`, testy regresji | sprawdzenie na rzeczywistym środowisku przez operatora |

## Procedura realnego zamknięcia

1. Wybór konkretnych elementów i zatwierdzenie pinoutu transformatora LPR6235-752SML, kondensatorów i footprintów SSOP16/obudowy. Układ LTC3108 VSTORE ok. 5V **NIE jest napięciem zasilania MCU**; wybór zasilania MCU musi zapewnić zakres 1,8–3,6V.
2. KiCad: sprawdzenie obu projektów, poprawa footprintów, aktywne PCB do trasowania, raporty ERC/DRC, Gerber/Excellon i niezależny przegląd.
3. Wykonanie laminatu, montaż w bezpiecznym izolowanym układzie pomiarowym, inspekcja, test ciągłości bez zasilania.
4. Instrumentacja TEG/PMIC dla kilku gradientów (w tym niskich, lecz osiągalnych), obciążenia i docelowego radiatora; archiwizacja `measured` CSV, numerów instrumentów, zdjęć, dat kalibracji.
5. Generacja overlay, praca w STM32CubeIDE z Seeed `LoRaWAN_End_Node`, build dla **STM32WLE5JC**, SWD flash, upewnienie się co do kluczy OTAA bez ich publikacji. Stan synchronizacji LoRaWAN musi przetrwać reset zgodnie ze stosem.
6. Pojedynczy fizyczny uplink EU868 przy właściwej antenie; do protokołu dołączyć rzeczywisty eksport TTN, timestamp, RSSI/SNR, fCnt, payload, własny pomiar energii TX/RX.
7. Długookresowy test funkcjonowania z energii TEG przy rzeczywistych warunkach, analiza trwałości i niezawodności, zgody operatora infrastruktury. **Dopiero wtedy można mówić o zweryfikowanym urządzeniu lub przyznać realistyczny TRL.**

**Bez twardych dowodów 3–7 wynik pozostaje projektem laboratoryjnym o zweryfikowanej części software.** Nie wolno opisać tego jako zbudowanego czy funkcjonującego węzła bezbateryjnego.

## Oficjalne źródła hardware

- LTC3108 Rev D: https://www.analog.com/media/en/technical-documentation/data-sheets/3108fc.pdf
- Seeed LoRaWAN firmware: https://github.com/Seeed-Studio/LoRaWan-E5-Node
- Seeed Wio-E5 mini: https://wiki.seeedstudio.com/LoRa_E5_mini/


## Automatyczny audyt KiCad — 2026-10-09 (pierwszy przebieg)

**Wykonano realną analizę za pomocą `kicad-cli 10.0.6` w GitHub Actions**, zamiast wyłącznie sprawdzenia nawiasów plików:

| Projekt | Import/netlista | ERC | PCB DRC i połączenia |
|---|---|---|---|
| Pasywny `thermo_bench_carrier` | poprawny eksport | 0 błędów, **14 ostrzeżeń** w przebiegu początkowym | **0 naruszeń, 0 niepodłączonych padów** |
| Aktywny `ltc3108_power_breakout` | poprawny eksport | 0 błędów, **82 ostrzeżenia** w przebiegu początkowym | **13 ostrzeżeń mismatch footprintów i 30 niepodłączonych połączeń** |

Ostrzeżenia ERC dotyczą głównie niewłączonych do konfiguracji bibliotek i końcówek poza siatką; lokalne źródła symboli `.kicad_sym` oraz `sym-lib-table` dodano do repo, ale usunięcie ostrzeżeń **wymaga ponownej walidacji**. W nowszych przebiegach obowiązuje dodatkowo sprawdzanie **rzeczywistej XML-netlisty KiCad** względem pinów, w tym rozdzielenia `VOUT/VSTORE`, logiki `MCU_TX/MCU_RX` oraz linii transformatora.

**Pełny aktywny PCB: NO-GO do zamówienia.** Brak ścieżek dla 30 wymaganych połączeń nie jest kwestią kosmetyczną. Projekty nie mają podpisu inżyniera, niezależnego przeglądu ani walidacji mechanicznej.

[Zarchiwizowany pierwszy audyt KiCad 10](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37952674687)

Automatycznie wygenerowane Gerbery/Excellon dla **pasywnej płytki laboratoryjnej** są artefaktami do przeglądu, wyraźnie oznaczonymi `NOT_FOR_FABRICATION`. Ich wygenerowanie nie jest dowodem wyprodukowania ani uruchomienia fizycznej płytki.
