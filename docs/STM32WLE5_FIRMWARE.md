# Thermo-IoT — aplikacja firmware dla STM32WLE5JC

**Cel sprzętowy:** moduł Seeed Wio-E5 / STM32WLE5JC z radiem Sub-GHz. Repozytorium zawiera **wykonywalną bibliotekę logiki aplikacji w C11** i testy wstrzykniętych peryferiów. Nie zawiera kompletnego obrazu flash `.elf/.hex`, stosu LoRaWAN, HAL STM32 ani fabrycznie zweryfikowanego firmware. Dlatego **nie jest jeszcze samodzielnym obrazem firmware**.

## Implementacja w kodzie

- `firmware/src/thermo_iot_app.c`: deterministyczna pętla wybudzenia i pomiaru, bramka zasilania z histerezą, uruchomienie OTAA, 8-bajtowa ramka FPort=10, konserwatywny cooldown po żądaniach nadawania i odrzuceniach;
- `firmware/src/thermo_iot_power_policy.c`: narzucony interwał z mocy netto, blokada transmisji przy braku energii i stany WAIT/CHARGING;
- `firmware/src/thermo_iot_frame.c`: wersjonowana ramka temperatury i parametrów energetycznych, zgodna z backendem Python;
- `firmware/include/thermo_iot_app.h`: port interfejsów dostarczanych przez środowisko STM32CubeWL.

## Integracja z oficjalnym STM32CubeWL (nie zaimplementowana)

Użyć aplikacji `LoRaWAN_End_Node` z pakietu Seeed Studio: https://github.com/Seeed-Studio/LoRaWan-E5-Node, dostosowanego do RF_PA4/PA5 i USART1 PB6/PB7. ST opisuje jego `LoRaWAN_Init`, `SendTxData` i `LmHandlerSend`: https://www.st.com/resource/en/application_note/dm00660451.pdf .

Konkretny adapter `thermo_iot_platform` musi:
1. Mapować napięcie z **skalibrowanego** toru ADC; przyjąć odczyt dopiero po potwierdzeniu tolerancji i pomiarów prądu szczytowego;
2. Zwracać moc **netto po PMIC i poborze spoczynkowym** z miernika energii lub konserwatywnie oszacowanego budżetu; nie wymyślać jej z `ΔT`;
3. Zapewnić odczyt temperatury przez docelowy sensor i obsługę sensor-not-present;
4. Sprawdzać realny status OTAA i kolejkować uplink przez `LmHandlerSend`; sukces oznacza jedynie przyjęcie do kolejki, **nie odbiór przez gateway**;
5. Zintegrować harmonogram wybudzania z RTC/STOP2, nadzór brownout i watchdog;
6. Przechowywać sesję LoRaWAN i liczniki niezależnie od RAM oraz zachowywać politykę duty-cycle przez reset (nie można opierać jej wyłącznie na zegarze po uruchomieniu);
7. Bezpiecznie provisionować DevEUI/JoinEUI/AppKey poza publicznym repozytorium.

Bez tych zależności nie wolno oznaczać firmware za gotowe do samodzielnego wdrożenia na Wio-E5.

## Testy offline

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -Ifirmware/include \
  firmware/src/thermo_iot_app.c firmware/src/thermo_iot_power_policy.c \
  firmware/src/thermo_iot_frame.c firmware/tests/test_app.c -o /tmp/thermo_firmware_tests
/tmp/thermo_firmware_tests
```

**Wersja bez przeprogramowania MCU:** oddzielny harness `python -m thermo_iot.lorawan_fieldtest` obsługuje fabryczne AT firmware Wio-E5 i pozwala zbadać radio i backend po fizycznym podłączeniu.

## Potwierdzenie budowy linkowanego obrazu referencyjnego (9.10.2026)

**Nowa funkcja:** `firmware/stm32wle5jc/build_cube_gcc.py` samoczynnie odczytuje pliki projektu producenta STM32CubeIDE, kompiluje zależności i wykonuje linkowanie ELF w pełnej architekturze ARM Cortex-M4. Reprodukowalna konfiguracja CI w `.github/workflows/stm32-native-image.yml`.

Wynik: [GitHub Actions 37956017016](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37956017016) **SUCCESS**, z archiwum `.elf/.hex/.map`. Jest to obraz do **laboratoryjnej integracji RF**, nie obraz finalnego sensora TEG i nie wgrany fizycznie firmware. Samo istnienie `.hex` nie dowodzi, że węzeł nadaje, posiada bezpieczne klucze, czy jest zasilany TEG.
