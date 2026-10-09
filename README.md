# FENG-LABORATORY — Thermo-IoT

Robocza baza projektu [Thermo-IoT](docs/WNIOSEK_THERMO_IOT.md) w kontekście FENG 2.27 Laboratorium Innowatora. Jest to **koncepcja + analiza wykonalności i kod symulacyjny**, a nie prototyp fizyczny ani złożony wniosek.

## Dokumenty

- [Karta aplikacyjna IPB](docs/WNIOSEK_THERMO_IOT.md)
- [Audyt twierdzeń i kluczowych ryzyk](docs/AUDYT_TWIERDZEN.md)
- [Plan R1–R5 i kryteria GO/NO-GO](docs/PLAN_WALIDACJI.md)
- [Model biznesowy i walidacja klientów](docs/MODEL_BIZNESOWY.md)
- [Źródła naukowe i formalne](docs/ZRODLA.md)

## Model energetyczny — Python 3.10+

    python -m unittest discover -s tests -v
    python -m thermo_iot --teg-mw 0.1 --efficiency 0.65 --sleep-uw 8 --cycle-mj 21.9

Model operuje na **zmierzonej** mocy TEG przed przetwornicą, odlicza stratę sprawności i średnią moc spoczynku oraz ograniczenie duty cycle radia. Energia bufora wynika z 0.5*C*(Vhi²−Vlo²). Symulator nie modeluje uruchamiania przetwornicy, szczytowego prądu TX, ESR ani profili temperatury — wynik **nie jest dowodem pracy w terenie**.

Dla **hipotetycznych**, a nie zmierzonych, 0,1 mW mocy TEG, sprawności PMIC 65%, spoczynku 8 µW i energii cyklu 21,9 mJ minimalny okres energetyczny wynosi około 384 s. Gęstość cTEG z literatury 1,26 mW/m² przy 50°C dla powierzchni 0,01 m² oznacza 12,6 µW **na tym konkretnym źródłowym założeniu** — a nie w dowolnej rurze.

## Stan wiarygodności

**Na 2026-10-09:** nie otrzymano dowodów zbudowania urządzenia, patentu/FTO, potwierdzonego TRL 3/4, wyników pilotażu, umów z zespołem lub potwierdzenia praw IP. Celem repo jest zbudowanie dokumentacji i weryfikowalnej warstwy obliczeniowej przed doświadczeniami sprzętowymi.

Nabór Garage Genius według PARP trwa do **30.11.2026**. Operator wymaga oryginalnego niezmodyfikowanego pliku DOC/DOCX i opisuje wsparcie w systemie Lab_żetonów, a nie gwarantowanej wypłacie gotówki: https://garagegenius.investin.pl/formularz/.

Repozytorium jest publiczne. Strategię ujawniania nowatorskich rozwiązań uzgodnić z rzecznikiem patentowym. Prace prowadzone w gałęzi **main**, CI testuje zestaw unittest.
