# Thermo-IoT Bench Carrier A0 — native KiCad sources

**Funkcja:** pasywna, dwuwarstwowa płytka *stanowiska laboratoryjnego*, nie docelowy system bezbateryjny i nie płytka z układem LTC3108. Służy do podłączenia zewnętrznie zasilanej płytki Wio-E5, UART USB (3,3 V), toru pomiarowego surowego TEG i oddzielnego pomiaru PMIC.

## Złącza (pad nr 1 wyznacza pad prostokątny)

| Ref | Pad | Net | Cel |
|---|---|---|---|
| J1 | 1,2 | `+3V3_EXT`, `GND` | **tylko laboratoryjny** regulowany zasilacz 3,3 V, ograniczenie prądu |
| J2 | 1..4 | `+3V3_EXT`, `GND`, `MCU_TX`, `MCU_RX` | interfejs Wio-E5 Dev Board (sprawdzić ręcznie pinout przed podłączeniem) |
| J3 | 1..3 | `GND`, `MCU_RX`, `MCU_TX` | konwerter USB-UART logic 3,3 V; RX adaptera -> J2.3, TX -> J2.4 |
| J4 | 1,2 | `TEG_P`, `TEG_N` | wyłącznie pomiar TEG, brak połączenia z obwodami zasilania |
| J5 | 1,2 | `PMIC_VOUT`, `PMIC_RETURN` | wyłącznie pomiar PMIC, brak połączenia z Wio-E5 i J1 |

**OSTRZEŻENIE:** Nie wolno bezpośrednio łączyć 5 V VSTORE LTC3108, jego 2,2 V wyjścia LDO albo niestabilnego napięcia z TEG z pinami MCU. Płytka nie zawiera ogranicznika przepięć, bezpiecznika ani regulatora. Traktować ją jako **przyrząd laboratoryjny do niskich napięć** i zasilać J1 z zabezpieczonego zasilacza 3,3 V; nie instalować na pracującej instalacji przemysłowej.

## Pliki

- `thermo_bench_carrier.kicad_sch`: schemat z 5 złączami i identycznymi nazwami nets.
- `thermo_bench_carrier.kicad_pcb`: dwuwarstwowa PCB z trasami tylko dla zasilania UART+3.3 V/GND, TEG i PMIC są **osobnymi, niepołączonymi parzystymi złączami pomiarowymi**.
- `ThermoBench.pretty/`: wbudowane źródła footprintów 1×2, 1×3, 1×4, raster 2,54 mm.
- `fp-lib-table`: lokalna biblioteka footprintów.

Płytka ma **70 × 44 mm** (obrys x=12..82; y=13..57), przewierty padów 1,0 mm. Przed zamówieniem PCB wymaga weryfikacji w **KiCad ERC/DRC, orientacji pinów, tolerancji mechanicznych i przeglądu DFM**. To nie jest produkcyjnie zweryfikowany Gerber — w repo nie ma autoryzowanego testu sprzętowego ani walidacji EDA.
