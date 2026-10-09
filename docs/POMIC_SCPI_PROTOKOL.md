# TEG/PMIC — real SCPI power profile capture

**Kod nie generuje fizycznych pomiarów bez podłączonej aparatury.** Obsługuje pięć niezależnych przyrządów SCPI: napięcie/prąd na wejściu PMIC, napięcie/prąd na wyjściu i napięcie magazynu energii. Zapisuje nowy plik CSV bez nadpisywania istniejących. Parametry i czas odczytu są zbierane *sekwencyjnie*; metrologiczna jednoczesność i kalibracja wymagają osobnego przyrządu DAQ i protokołu.

## Procedura

```bash
python -m pip install pyvisa pyvisa-py

python -m thermo_iot.pmic \
 --meter-vin "ASRL1::INSTR" --meter-iin "ASRL2::INSTR" \
 --meter-vout "ASRL3::INSTR" --meter-iout "ASRL4::INSTR" \
 --meter-vstore "ASRL5::INSTR" \
 --steps 120 --interval-s 1 --output ./pmic-real-001.csv

python -m thermo_iot.pmic --file ./pmic-real-001.csv
```

Adresy VISA to **przykłady**, nie potwierdzone urządzenia. Należy mierzyć tylko na izolowanym, bezpiecznym stanowisku i sprawdzić obciążenie torów miernikami. Dla zimnego startu rozładować bufor do **uzgodnionego poziomu** bez naruszania dopuszczalnych warunków komponentu i potwierdzić to pomiarem w pierwszym wierszu. `time_to_store_target_s` jest określany tylko wtedy, gdy pierwszy pomiar VSTORE <= 0,1 V, a późniejszy >=3,0 V; w przeciwnym razie odpowiedź mówi wprost, że nie zaobserwowano rozruchu od rozładowanego bufora.

## Czego wyniki NIE pokazują

- Sam iloraz `Pout/Pin` nie mierzy sprawności przetwornicy, kiedy `VSTORE` i energia bufora się zmieniają. Model podaje jedynie energię elektryczną na wejściu/wyjściu w określonym przedziale i zmianę napięcia.
- Bez danych o pojemności/ESR/stratach nie da się wyliczyć pełnego bilansu magazynu.
- Bez oscyloskopu o właściwym paśmie nie widać pików RF w czasie transmisji.
- Pięć przyrządów SCPI musi być fizycznie podłączonych i skalibrowanych, a odczyty na wejściu TEG mogą zmieniać jego obciążenie.
- Oznaczenie `measured` w pliku opisuje tylko to, że program zapytał przyrządy. Jest wymagane zdjęcie stanowiska, identyfikatory urządzeń, kalibracja i podpis operatora.

Przykłady i testy automatyczne nie potwierdzają działania PMIC w niskim `ΔT`.
