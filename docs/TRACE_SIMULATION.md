# Thermo-IoT — symulacja okresowej pracy na zmiennym profilu mocy

Program `thermo_iot.trace` oblicza zmiany idealnie dostępnej energii superkondensatora w czasie i bada wykonalność cykli pomiarowo-radiowych na danych `elapsed_s,teg_power_uw,evidence_type`. Moc jest **mocą elektryczną generatora przed PMIC**, a nie gradientem temperatury czy prognozą mocy z publikacji. W każdym przedziale czasowym obowiązuje poprzedni odczyt (sample-and-hold), a odstępy próbkowania i nadawania są niezależne.

Model odejmuje uśrednione obciążenie spoczynkowe, przyjmuje stałą sprawność przetwornicy i odejmuje jednostkowy koszt cyklu, jeżeli przed rozpoczęciem dostępna energia przekracza `reserve_fraction*E_max + energy_margin*E_cycle`. Zlicza próby zaakceptowane **jedynie energetycznie**, odroczenia, nadwyżkę niewchłoniętą przez pełny kondensator i czas bez energii użytecznej.

## Demonstracja

```bash
python -m thermo_iot.trace --file examples/synthetic_teg_trace.csv --period-s 600 --initial-voltage-v 2.8 --efficiency 0.65 --sleep-uw 8 --cycle-mj 21.9
```

Dołączony profil jest **syntetyczny**. Liczby `successful_cycles` i `delivery_fraction` nie oznaczają odebranych pakietów przez bramę, lecz zdolność idealizowanego bufora do pokrycia energii. Odmowa próby nie jest awarią fizycznego urządzenia. Input z etykietą `measured` sam w sobie **nie dowodzi** jakości pomiaru — do niego trzeba dołączyć protokół metrologiczny.

## Ograniczenia i następna weryfikacja

- Nie modeluje zimnego startu, ESR, spadków napięcia przy TX, rozrzutu pojemności ani ograniczeń termicznych.
- Nie modeluje OTAA, ADR/SF, retransmisji i pełnych warunków regionalnych LoRaWAN; `period_s` jest tylko ograniczony przez zadany duty-cycle oraz airtime.
- Model nie ma komponentu cieplnego; **moc TEG musi pochodzić z pomiarów** na obu stronach modułu i charakterystyk napięciowo-prądowych pod obciążeniem.
- Nie używać danych syntetycznych jako dowodu TRL ani wypełnienia kryterium innowacyjności.
- Następny etap: stanowisko TEG/PMIC, surowe profile wejścia PMIC i pomiary zasilania w każdym stanie oraz walidacja przebiegu napięcia kondensatora.

Pakiet testów obejmuje: bilans energii, stan bez mocy, wymogi duty-cycle, skok mocy, przepełnienie bufora, złe dane i rozdzielenie danych syntetycznych od rzeczywistych.
