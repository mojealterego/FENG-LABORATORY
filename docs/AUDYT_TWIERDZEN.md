# Thermo-IoT — audyt twierdzeń i ryzyk (2026-10-09)

## Krytyczne korekty materiału wejściowego

| Twierdzenie | Ocena dowodowa | Sposób naprawy |
|---|---|---|
| „Innowacja globalnie przełomowa” | Niepotwierdzona | Istnieją publikacje TEG+LoRaWAN oraz TEG na ciepłociągach; udowodnić konkretny wyróżnik, nie obiecywać pierwszeństwa. |
| „TRL 3 / TRL 4” | Niepoparty protokołem Thermo-IoT | Brakuje dokumentacji prototypu, pomiarów i testów tego zespołu. TRL ustalić po uzyskaniu dowodów. |
| „cTEG 1,26 mW/m² przy 50°C” | Potwierdzone tylko dla opisanego układu w artykule ACS | Nie ekstrapolować do 4–5°C, innej geometrii ani innych warunków chłodzenia. |
| „21,9 mJ na cały cykl” | Założenie projektowe | Pomiar MCU, TEG, sensorów, LoRa TX/RX, OTAA, retransmisji i cold-start przy wybranym SF. |
| „Naładowanie w kilkanaście sekund” | Niepoparte danymi | Wymaga rzeczywistej mocy netto. Przy 1 mW i 21,9 mJ idealny czas to 21,9 s; przy 10 µW to 2190 s. |
| „Superkondensator nieskończenie trwały” | Fałszywe jako gwarancja | Zmierzyć ESR, upływ, żywotność kalendarzową i temperaturę pracy. |
| „Przepływ clamp-on z błędem poniżej 3%” | Niezweryfikowany w tej aplikacji | Weryfikować względem wzorca na rzeczywistych rurach, geometriach i zaburzeniach przepływu. |
| „Ciśnienie z opaski bez ingerencji” | Nieudowodnione | MVP bez bezpośredniego pomiaru ciśnienia. |
| „AI wykrywa mikrowycieki” | Niezweryfikowane | Potrzebny zbiór prawdy, recall, precision, false alarms/day i opóźnienie. |
| „Setki tysięcy zł oszczędności na węzeł rocznie” | Brak modelu | Policzyć TCO, koszty strat i unikanie interwencji z klientem. |
| „50 tys. zł gwarantowane dla każdego” | Niepotwierdzone | Wsparcie GarageGenius ma postać usług w systemie Lab_żetonów. |
| „Pełnia praw do IP” | Nie do zadeklarowania bez danych | Wykaz autorów, umowy, licencje, konsultacja patentowa/FTO. |
| „TRL 6/7 i maksymalna punktacja zagwarantowane” | Nieuprawnione | Zastąpić mierzalnymi kamieniami milowymi. |
| „Bezobsługowy montaż na izolowanych rurach” | Brak potwierdzenia | Procedura operatora, inspekcja izolacji, testy termiczne i BHP. |

## Bilans weryfikowalny rachunkowo

Publikowana gęstość cTEG 1,26 mW/m² przy 50°C i ilustracyjna powierzchnia 0,01 m² to moc 12,6 µW (zakładając poprawne przeniesienie jednostki i warunku). Dla 21,9 mJ: 21,9 mJ / 12,6 µW = około 1738 s, tj. około 29 minut, przed stratami. Przy sprawności PMIC 65% i obciążeniu spoczynkowym 8 µW: moc netto 0,19 µW, więc minimalna przerwa energetyczna wynosi około 32 h. To **scenariusz, nie wynik laboratoryjny Thermo-IoT**.

Przykładowa energia idealnego superkondensatora 2,5 F pomiędzy 3,3 V i 2 V: E = 0,5*C*(Vhi²−Vlo²) = 8,6125 J. Rzeczywiste prądy szczytowe, sprawność przetwornicy i utrata pojemności mogą zmniejszać zasób.

Istnieją prace wykazujące 0,5–2 mW przy ΔT około 1–2 K na innych układach (Applied Energy 2021), dlatego nie wolno traktować wyników różnych konstrukcji jako przelicznika ΔT→moc dla naszego węzła.
