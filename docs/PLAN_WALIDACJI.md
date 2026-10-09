# Thermo-IoT — testy i bramki GO/NO-GO

Każdy wynik pomiaru wymaga: daty, konfiguracji TEG/PMIC, temperatur po obu stronach TEG, wzorca, danych surowych, kalibracji i podpisu osoby wykonującej test.

| Bramka | Eksperyment | Kryterium GO | Kryterium NO-GO |
|---|---|---|---|
| R1 Termika | co najmniej 3 profile rurociągu i 48 h pomiarów każdy | znamy p5/medianę/p95 rzeczywistego ΔT **na module** | brak technicznego kontaktu cieplnego lub niedozwolone usunięcie izolacji |
| R2 Harvesting | I–V, P–V, cold-start, standby, ESR, upływ superkondensatora | 7 dni pracy bez zewnętrznego zasilania w zdefiniowanym profilu | ujemny bilans lub brak rozruchu |
| R3 Radio | TX, RX1/RX2, join, retransmisje, SF, strata pakietów | minimum 95% dostarczonych pakietów przy uzgodnionym interwale, legalny airtime | brak pokrycia lub przekroczenie limitów radiowych |
| R4 Pomiar | czujnik temperatury vs wzorzec i dryft | błąd uzgodniony z klientem | nieakceptowalna niepewność |
| R5 Rynki/IP | FTO, analiza konkurencji, 10–15 wywiadów | 2 podmioty zainteresowane pilotażem i kalkulacja TCO | ograniczenia IP lub brak możliwości instalacji |

**Wersja A:** temperatura, napięcie i stan energetyczny. **Wersja B:** przepływ clamp-on po referencyjnych próbach z wzorcowym przepływomierzem; ciśnienie wymaga osobnej metody pomiarowej i zgody instalacyjnej.

## Macierz ryzyk

- **Brak mocy (wysokie):** radiator i opaska, niskie straty PMIC, większa powierzchnia, adaptive duty cycling, wyraźny próg NO-GO.
- **Niedostateczne piki prądu (wysokie):** analiza ESR/sag, przetwornica, sekwencjonowanie wybudzenia.
- **Awaria mechaniczna/korozja (wysokie):** testy środowiskowe i powtarzalność montażu.
- **Izolacja rurociągu (wysokie):** pilotaż w uzgodnionych punktach węzła, procedura operatora.
- **Prior art / IP (wysokie):** profesjonalny FTO i strategia design-around.
- **Fałszywe alarmy (wysokie):** etykietowanie zdarzeń, operator zatwierdzający decyzję, KPI false alarms/30 d.
- **Bariery IT/OT (wysokie):** segmentacja dostępu, rotacja kluczy, telemetryka tylko do odczytu.
- **Długie zakupy B2G (średnie):** niewielki PoC z uzgodnionymi KPI przed ofertą abonamentową.

## Dane niezbędne przed deklaracją TRL

Działający demonstrator sprzętu, zdjęcia i BOM, powtarzalne testy, protokół środowiska pomiarowego, dane radiowe, powiązanie z warunkami instalacyjnymi. Repozytorium nie zawiera jeszcze tych dowodów — obecny kalkulator mocy jest tylko analizą.
