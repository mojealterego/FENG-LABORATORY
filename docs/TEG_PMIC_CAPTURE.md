# Realne pomiary TEG i PMIC — protokół stanowiska

## Stan faktyczny

W repozytorium znajduje się kod do pobierania odczytów przez SCPI, **nie ma jednak surowych wyników pomiarów fizycznego układu Thermo-IoT**. Testy CI używają fałszywych implementacji przyrządów, a oznaczenie `measured` w pliku z programu SCPI opisuje pochodzenie elektrycznych odczytów, nie dowodzi ważności kalibracji ani pomiaru temperatury.

## Podłączenie (wyłącznie niskie napięcia, nadzorowane przez operatora)

Wymagane: TEG na kontrolowanej próbce gorącej/zimnej, 2 niezależne przyrządy DC z interfejsem SCPI (woltomierz równolegle do obciążenia, amperomierz szeregowo), zestaw rezystancji testowych, dwa skalibrowane termometry do bezpośrednich powierzchni TEG, lista instrumentów i granic pomiaru, formularz kalibracji. Stosować procedury BHP do gorących powierzchni, izolować instalację od sieci przemysłowej i nie otwierać czynnych rur.

**Uwaga:** obciążenie amperomierza (burden voltage) może zmienić charakterystykę TEG; odczyty są wykonywane po kolei i nie są automatycznie zsynchronizowane. Stabilność `ΔT` oraz rozrzut wyników należy raportować oddzielnie.

```bash
python -m pip install pyvisa pyvisa-py
python -m thermo_iot.bench_scpi \
  --voltmeter "ASRL1::INSTR" --ammeter "ASRL2::INSTR" \
  --loads-ohm "10,22,47,100" --hot-c 55.5 --cold-c 22.5 \
  --run-id calibration-a01 --output ./measurement-a01.csv
python -m thermo_iot.lab --file ./measurement-a01.csv
```

Parametry VISA są **ilustracyjne** i trzeba je zastąpić identyfikatorami rzeczywistych przyrządów. Osoba wykonująca test potwierdza zmianę opornika frazą `READY` przed każdym odczytem. Program nie steruje źródłem ciepła ani rezystorami, nie dopisuje do istniejących plików i zapisuje odczyty w istniejącym schemacie `thermo_iot.lab`. Należy dołączyć do każdego `run_id`: numer seryjny i ważność kalibracji, zdjęcie stanowiska, materiał/montaż TEG, zakres i niepewność przetworników, czasy stabilizacji i pomiar temperatur.

**Osobny pomiar PMIC:** nie należy uznawać szczytu mocy `V_TEG×I_TEG` za moc dostarczoną do bufora. Trzeba zmierzyć:
- `V_IN` i `I_IN` PMIC w stanie rozruchu i ustalonym, przy rzeczywistym `ΔT`;
- `V_OUT`, `I_OUT`, sprawność pod rzeczywistym obciążeniem, temperaturę komponentów;
- czas cold-start przy rozładowanym magazynie energii;
- upływ i ESR superkondensatora, piki prądu i napięcia w trakcie LoRa TX/RX.

Dopiero rzeczywiste profile elektryczne wolno podstawić do modeli `thermo_iot.energy`, `thermo_iot.trace` i `thermo_iot.radio_budget`. Bez tych pomiarów brak dowodu TRL. **Nie używać danych syntetycznych jako pomiarów rzeczywistych.**
