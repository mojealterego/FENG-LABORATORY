# Thermo-IoT — protokół pomiaru termogeneratora (TEG)

## Status i granica dowodowa

Kalkulator `thermo_iot.lab` analizuje wartości w pliku CSV. **Nie mierzy** urządzenia i nie nadaje żadnego poziomu TRL. Do repozytorium dołączono wyłącznie **dane syntetyczne** do testowania formatów, nie wyniki do wniosku grantowego. Formalną wiarygodność pomiaru ocenia się odrębnie na podstawie wyposażenia, protokołu, kalibracji, powtarzalności oraz spójnego podpisu operatora.

## Ścieżka laboratoryjna i aparatura

1. Zinwentaryzować generator TEG, układ zacisku, średnicę i materiał rury, pastę termoprzewodzącą, radiator i izolację. Zidentyfikować przekroje termiczne i ryzyko uszkodzenia izolacji instalacji; próbki testować na stanowisku, nie na nieautoryzowanej sieci.
2. Na obu **stronach samego modułu TEG** umieścić czujniki temperatury wraz z identyfikacją torów i świadectwami kalibracji, a nie tylko czujniki „temperatury rury” i „temperatury powietrza”.
3. Zarejestrować napięcie i prąd dla kilku obciążeń przy kontrolowanej temperaturze. Sprawdzić zakresy instrumentów i ich obciążenie. Protokół powinien zawierać niepewność pomiarową, numer urządzenia, operatora i datę.
4. Powtórzyć całą procedurę dla kilku niezależnych montaży i konfiguracji, mierząc temperatury i moc elektryczną przy różnych profilach otoczenia.
5. Oddzielnie zbadać zimny start PMIC, sprawność przy rzeczywistych obciążeniach, prąd upływu i rezystancję ESR kondensatora, piki TX i realny średni pobór w czasie.
6. Dopiero na podstawie **mocy na wejściu PMIC**, a nie szczytu P–V na rezystorze, ocenić realistyczny `EnergyScenario` z przedziałami niepewności.

## Format danych

`run_id,measurement_utc,hot_c,cold_c,voltage_mv,current_ma,evidence_type`

- `run_id` — identyfikator jednej krzywej I–V w określonej konfiguracji; min. 3 punkty pomiarowe.
- `measurement_utc` — ISO8601 ze strefą (np. `2026-10-09T10:00:00Z`).
- `hot_c`, `cold_c` — temperatury bezpośrednio na stronach TEG w °C; `hot_c > cold_c`.
- `voltage_mv`, `current_ma` — napięcie pod obciążeniem (mV) i odpowiadający mu prąd (mA).
- `evidence_type` — dosłownie `synthetic` lub `measured`, bez mieszania. Sam napis `measured` **nie potwierdza** wiarygodności metrologicznej.

Wynik: `P [W] = U [mV] × I [mA] × 10⁻⁶`, wyłącznie największa moc spośród faktycznie dostarczonych punktów I–V. **Nie wyznaczamy teoretycznego MPP przez dopasowanie lub ekstrapolację.** Wykrywamy różnicę `ΔT` między punktami przekraczającą 1 K i dodajemy ostrzeżenie termicznego dryftu.

## Uruchomienie

```bash
python -m thermo_iot.lab --file examples/synthetic_teg_sweep.csv
python -m unittest discover -s tests -v
```

Wynik z załączonych fikcyjnych danych oznaczony jest `synthetic`, nie stanowi dowodu pracy przy `ΔT = 4–5°C` ani przy jakimkolwiek innym gradiencie dla docelowego urządzenia.

## Minimalny pakiet dowodów do grantów/TRL

- zdjęcia stanowiska, numer/wersja układu, obudowa i schemat styku termicznego,
- surowe CSV oraz metadane kalibracji,
- krzywe I–V / P–V oraz niepewność pomiaru,
- profile pomiarowe podczas startu, nadawania i ładowania,
- logi z prób długookresowych i testy środowiskowe,
- podsumowanie wartości `p5 / median / p95` dla mocy netto w docelowych warunkach.

Nie należy wykorzystywać danych syntetycznych z repozytorium jako wyników eksperymentalnych we wniosku.
