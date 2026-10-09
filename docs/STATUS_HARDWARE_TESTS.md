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


### Wynik kolejnego przebiegu CAD po korekcie siatki

Po wyrównaniu 13 symboli (w tym 16 pinów LTC3108) i końców przewodów do siatki 1,27 mm:

- aktywny harvester: **ostrzeżenia ERC zmniejszone z 82 do 27**, **0 błędów ERC**;
- pozostałe 27 ostrzeżeń to **13 ostrzeżeń biblioteki symboli, 13 ostrzeżeń biblioteki footprintów i 1 świadomie nieobsadzone wyjście VOUT2**;
- pasywny adapter: nadal **0 naruszeń DRC, 0 niepodłączonych padów**;
- aktywna PCB: nadal **30 brakujących połączeń miedzianych**; 13 ostrzeżeń dopasowania footprintów — nadal NO-GO do fabrykacji;
- dla obu schematów rzeczywisty eksport netlisty XML przeszedł audyt wszystkich spodziewanych pinów i ich sieci;
- wygenerowano siedem warstw Gerber oraz plik wierceń **wyłącznie pasywnej płytki do przeglądu, nie do produkcji**.

[GitHub Actions: audyt KiCad po korekcie siatki](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37954140570).

**Ważne:** zielony przebieg oznacza powodzenie diagnostyki i kontraktów połączeń, a nie pomyślny DRC aktywnego projektu. Raport ten jawnie nadal pokazuje 30 niepołączonych ścieżek.

### 9 października 2026 — rzeczywisty pełny cross-link obrazu STM32WLE5JCIx

**GitHub Actions 37956017016: SUCCESS.** Rozwiązano źródła i definicje kompilatora z oficjalnego projektu Seeed STM32CubeIDE (`.project/.cproject`) przypiętego do rewizji `163c05379b1805dd8f2c061d4557a69985acc953`, dołączono nakładkę 8-bajtowego Thermo-IoT, startup Cortex-M4 i linker script STM32WLE5JCIX. Narzędzia `arm-none-eabi-gcc` i `arm-none-eabi-objcopy` wygenerowały **rzeczywiste `.elf`, `.hex`, `.map`** dostępne jako artefakt CI.

- Zużycie FLASH: **63 564 B / 262 144 B (24,25%)**.
- Dane: **DATA = 228 B, BSS = 8068 B**, TEXT = 63 328 B.
- SHA-256 HEX: `e9a3d1df50e8c5a0eb3a52d03a78ce236c72ead47e3924e0c9d1b1b63d66a4ea`.
- [Artefakt obrazu referencyjnego do weryfikacji](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37956017016/artifacts/11627633166).

Ta walidacja **zamyka problem kompilowalności obrazu RF** dla konkretnego targetu. **Nie zamyka** wymogu pełnego firmware czujnikowego: brak kodu kalibracji prawdziwego czujnika temperatury rury, ADC pomiaru superkondensatora i PMIC, włączenia modelu zarządzania energią do docelowego schedulera LoRaWAN, zapisu kluczy OTAA/NVM i automatycznego STOP2. Nie wolno przedstawiać tego obrazu jako zatwierdzonego firmware produkcyjnego ani jako fizycznego MVP.

**Prawa oryginalnych części Thermo-IoT:** © 2026 Mojeaterego — Andrzej Mikulski. Wszelkie prawa zastrzeżone. Prawa do źródeł Seeed, STM32CubeWL i zależności pozostają przy ich autorach.

## Bramki odbioru fizycznego MVP — integralność dowodów bez publikacji IP

`thermo_iot.mvp_acceptance` weryfikuje offline SHA-256 siedmiu wymaganych artefaktów oraz ich podstawowy kontrakt: pomiary oznaczone przez operatora, PMIC cold-start, dopasowanie niezależnego uplinku do świeżej próby, zero naruszeń DRC aktywnej płytki, dokument flash, co najmniej siedem dni śladu energetycznego. Uruchamia się na prywatnych plikach użytkownika. Odczyty oznaczone `measured` i dopasowany JSON TTN nie stanowią niezależnego poświadczenia autentyczności. Wynik zawsze podaje `physically_validated=false` oraz wymaga podpisu odpowiedzialnego inżyniera po realnym badaniu urządzenia. Przed kolejnym ujawnieniem potencjalnie nowego elementu technicznego obowiązuje [kontrola IP](IP_PROTECTION_PL.md).
