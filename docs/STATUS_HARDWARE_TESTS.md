# Thermo-IoT — status dowodowy prac (9 października 2026)

| Element żądania | Artefakt w `main` | Zakres ukończony w oprogramowaniu | Warunek fizycznego / formalnego zaliczenia |
|---|---|---|---|
| Schemat elektroniczny | `hardware/kicad/thermo_bench_carrier.kicad_sch` | Native KiCad schemat **pasywnego adaptera pomiarowego** pięciu złączy | KiCad ERC, dobór docelowego PMIC/TEG i regulatora po testach, pełny schemat aktywnego urządzenia |
| Projekt PCB | `hardware/kicad/thermo_bench_carrier.kicad_pcb` i biblioteka `.pretty` | PCB 70×44 mm dwustronna, trasy 3,3 V/UART/GND, izolowane złącza pomiarowe | otwarcie w KiCad, DRC, review DFM, zamówienie, montaż, badania EMC / termiczne |
| Firmware konkretnego MCU | `firmware/src/thermo_iot_app.c`, `thermo_iot_power_policy.c`, `thermo_iot_frame.c` | Host-verified **C11 application core** dla planowanego STM32WLE5JC | dołączenie STM32CubeWL HAL, BSP, I2C/ADC, OTAA keys, NVM LoRaWAN, RTC/STOP2; cross-compile HEX + SWD flash + urządzenie |
| Pomiar TEG/PMIC | `thermo_iot.bench_scpi`, `thermo_iot.lab` | Sterowana przez operatora akwizycja z pary woltomierz+amperomierz, analiza mocy | fizyczny TEG, przyrządy kalibrowane, rejestr temperatur na module, cold-start PMIC, scenariusze najgorszego przypadku |
| Rzeczywista transmisja LoRaWAN | `thermo_iot.lorawan_fieldtest` + parser TTN | Procedura UART Wio-E5 EU868, join OTAA, 8 B na FPort 10 i porównanie eksportu TTN | fizyczny moduł/antena/gateway; `AT+MSGHEX: Done` nie wystarcza — oryginalny odebrany uplink TTN + parametry RF |
| Jakość oprogramowania | `.github/workflows/tests.yml` | automatyczne Python/C11, JSON backend, sanity KiCad | testy sprzętowe, KiCad ERC/DRC, EMC, radio i laboratoryjny raport osobno |

**Pomiary rzeczywiste: BRAK. Sprzętowo zweryfikowany PCB: BRAK. Wgrany program MCU: BRAK. Potwierdzony realny uplink: BRAK.** Nie nadajemy projektu poziomu TRL na podstawie testów offline.

## Konkretny plan zamknięcia dowodowego

1. Zweryfikować elektryczne podłączenie J2 na aktualnej rewizji Wio-E5, uniknąć równoczesnych zasilaczy USB i J1. Na PCB brakuje ochrony zasilania; nie podłączać do instalacji bez dodatkowego zabezpieczenia.
2. Otworzyć KiCad 9/10 i przejść ERC/DRC, sprawdzić footprinty i pozycje mechaniczne; odnotować dokładną wersję narzędzia i raporty. Test spójności nawiasów oraz nets w CI nie jest ERC/DRC.
3. Sprawdzić parametry TEG (V-I, P-I), napięcie uruchomienia PMIC, ładowanie bufora i profil TX/RX dla konkretnego SF przy kontrolowanym `ΔT`.
4. Dołączyć CubeWL LoRaWAN End Node (RF PA4/PA5, USART1 PB6/PB7 zgodnie z Seeed), wykonać cross-compile i zaprogramować Wio-E5 po zachowaniu identyfikatorów fabrycznych; skonfigurować bezpieczną OTAA.
5. Test radiowy wyłącznie z anteną i prawidłową konfiguracją EU868. Utrwalić odczyt z TTN (RSSI, SNR, fCnt, payload oraz datę) i zestawić ze śladem TX.
6. Wykonać 7-dniowy test bez zasilania zewnętrznego, raportować czas niedostępności, zużycie energii, brak radiowy, dryft sensorów oraz decyzję GO/NO-GO.

## Kryterium akceptacji

**Faza cyfrowa:** repozytorium, testy CI i reprodukowalne pliki. **Faza demonstratora fizycznego:** wymaga własnej próbki hardware i rzeczywistych wyników. Brak ich nie można zastąpić syntetycznymi rekordami, symulacją ani wnioskiem grantowym.
