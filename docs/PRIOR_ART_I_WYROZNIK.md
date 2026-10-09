# Thermo-IoT — prior art i weryfikowalna hipoteza nowości (9.10.2026)

## Co wiadomo z literatury

| Źródło | Potwierdzone podejście | Wpływ na naszą narrację |
|---|---|---|
| Feng, Yazawa, Lu, ACS Applied Electronic Materials (2022), DOI: 10.1021/acsaelm.1c00922 | Elastyczny/konforemny TEG dla rur; gęstość mocy 1,26 mW/m² przy 50°C w opublikowanej konstrukcji. | Samo użycie cTEG na cylindrze i zbieranie ciepła z rur **nie jest wystarczającą nowością**. |
| *Design and optimization of low-temperature gradient thermoelectric harvester for wireless sensor network node on water pipelines*, Applied Energy 283 (2021), DOI: 10.1016/j.apenergy.2020.116240 | Zbadana konstrukcja odzysku energii ze słabych gradientów na przewodach wodnych. | Twierdzenie, że niskotemperaturowy harvesting na rurach jest nieopisany, byłoby nieprawidłowe. |
| Koolivand i in., IEEE Sensors Journal 25(17) (2025), DOI: 10.1109/JSEN.2025.3588959 | Praca terenowa nad systemem wykrywania wycieków na ciepłociągach, z TEG zasilanym z gradientu rur zasilanie–powrót, TDR i komunikacją radiową LoRa z dronem. W publikacji podano pozycjonowanie z błędem poniżej ±0,55 m. | **Bezpośrednia konkurencja naukowa**. Nie twierdzić, że wcześniejszych autonomicznych czujników wycieków z TEG na rurach ciepłowniczych nie ma. |

## Hipoteza różnicująca do przetestowania

Możliwy kierunek: połączenie konstrukcji montażu na dostępnych odcinkach rur, samodiagnostyki dostępności energii, reguł pracy w nieustalonych warunkach `ΔT`, interoperacyjności z LoRaWAN i ekonomicznego modelu dostaw danych. **To hipoteza produktowa, nie potwierdzony wynalazek**, może nie być zdolna do ochrony patentowej.

Różnice w stosunku do pracy IEEE 2025, które trzeba wykazać empirycznie:
- w IEEE zasilanie wykorzystuje gradient między dwoma rurami układu twin-pipe; Thermo-IoT proponuje także punkty z lokalnym chłodzeniem do otoczenia;
- w IEEE czujnik wycieku stosuje TDR i komunikację LoRa do huba/drona; Thermo-IoT w MVP stosuje okresową telemetrię temperatury i LoRaWAN do bramy;
- odrębność konstrukcji, podsystemu PMIC, autonomiczności, kosztów cyklu życia i funkcji diagnostycznych **pozostaje do zbadania**.

## Krytyczne braki do FTO

1. Przegląd zgłoszeń rodzin patentowych cTEG, mocowania na rurach, radiatorów, systemów energy harvesting, LoRaWAN telemetry i obwodów uruchomieniowych.
2. Dokumentacja `claim chart` — każda potencjalna nowa cecha vs zastrzeżenia patentowe.
3. Jurysdykcje, status prawny, daty pierwszeństwa, wygaśnięcie i właściciele IP.
4. Profesjonalna opinia rzecznika patentowego z zakresem faktycznego produktu i rynków.
5. Analiza skutków publicznego ujawnienia w repozytorium. **Nie publikować szczegółów nowego mechanizmu, których patentowalność ma być dopiero oceniona.**

Publikacje naukowe dowodzą stanu techniki. Nie są prawną opinią Freedom to Operate ani pełnym badaniem rynku.

## Źródła pierwotne

- https://pubs.acs.org/doi/10.1021/acsaelm.1c00922
- https://www.sciencedirect.com/science/article/pii/S0306261920316342
- https://doi.org/10.1109/JSEN.2025.3588959
- https://portal.findresearcher.sdu.dk/en/publications/thermally-powered-autonomous-water-leakage-detection-system-for-d/
