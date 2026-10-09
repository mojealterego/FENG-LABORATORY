# Thermo-IoT — karta innowacyjnego pomysłu biznesowego (IPB)

**Wnioskodawca / autor:** Andrzej Mikulski — Mojeaterego. **E-mail:** mojealterego21@gmail.com. **Telefon:** +48 455 575 337. **© 2026 Mojeaterego — Andrzej Mikulski. Wszelkie prawa zastrzeżone.**

**Program:** FENG 2.27 Laboratorium Innowatora. **Operator roboczy:** Garage Genius / INVESTIN. **Stan:** 9 października 2026. **Dokument roboczy:** nie jest oficjalnym formularzem.

**Kontrola IP przed złożeniem:** wniosek roboczy jest już w publicznym GitHub. Szczegóły mogące ujawniać nowy wynalazek należy przygotować odrębnie, pod ochroną poufności, i przed przekazaniem operatorowi ocenić z rzecznikiem patentowym oraz w warunkach naboru. Sam zapis „wszelkie prawa zastrzeżone” nie zabezpiecza nowości patentowej. [Procedura](IP_PROTECTION_PL.md).

## Streszczenie

Thermo-IoT jest propozycją bezbateryjnego węzła pomiarowego do wybranych, dostępnych fragmentów infrastruktury ciepłowniczej. Energia ma pochodzić z generatora termoelektrycznego (TEG/cTEG) wykorzystującego gradient pomiędzy rurą a otoczeniem, być kondycjonowana przez PMIC i buforowana w superkondensatorze. Układ budziłby się okresowo, mierzył temperaturę i stan zasilania, a następnie wysyłał pakiet przez LoRaWAN Class A. Dane trafiałyby do platformy diagnostycznej służącej do oceny tendencji, braków danych i alertów. Docelowy model komercjalizacji: Sensing-as-a-Service B2B.

## Problem i klient

Problemem są koszty i utrudniona obsługa rozproszonych punktów pomiarowych, zwłaszcza w miejscach bez łatwego dostępu do zasilania. Główny segment wejścia: operatorzy sieci ciepłowniczych i zakładowe służby utrzymania ruchu. Przed stwierdzeniem wielkości potrzeby należy przeprowadzić 10–15 rozmów z decydentami i zebrać realne koszty interwencji, istniejące rozwiązania telemetryczne i wymogi instalacji na rurociągach.

## Produkt i etapy technologiczne

**MVP-A — pomiar temperatury i energetyki:** TEG/cTEG, styk termiczny, radiator, PMIC uruchamiający się przy niskich napięciach, superkondensator, MCU, LoRaWAN, czujnik temperatury i pomiar parametrów bufora. Program adaptuje interwał pomiaru do *zmierzonej* podaży energii, a nie do samej temperatury rury.

**MVP-B — rozszerzenie warunkowe:** clamp-on ultradźwiękowy pomiar przepływu tylko jeśli budżet energii, warunki akustyczne i kalibracja to dopuszczą. Bezpośredni pomiar ciśnienia nie jest obiecywany przez samą opaskę. ML następuje po zgromadzeniu oznaczonych danych, początkowo stosujemy reguły i statystyki. Żaden komponent nie zastępuje urządzeń bezpieczeństwa ani sterownika sieci.

## Innowacja / przewaga

Literatura naukowa zawiera wcześniejsze rozwiązania TEG+LoRaWAN na rurach, również dla sieci ciepłowniczych. Weryfikowana hipoteza wyróżnika obejmuje połączenie powtarzalnego mocowania, diagnostyki dostępności energetycznej i adaptacyjnej telemetrii. Nie deklarujemy przełomu światowego ani przewagi patentowej przed FTO i porównaniem z minimum dwiema technologiami odniesienia.

## Wykonalność i kamienie milowe

Średni model musi spełnić warunek P_TEG*eff_PMIC > P_spocz + E_cykl/T. Dodatkowo weryfikujemy pojemność rzeczywistego bufora, ESR, cold start, temperatury, konwekcję, dostęp do rury, pokrycie radia, retransmisje i ograniczenia czasu transmisji LoRaWAN EU863–870.

| Etap | Prace | Dowód zakończenia |
|---|---|---|
| 1 | pomiary ΔT i krzywych P–V dla TEG w kilku geometriach | surowe serie danych i protokół |
| 2 | demonstrator PMIC/bufor + profil energetyczny | log zimnego startu i 7 dni pracy w laboratorium |
| 3 | czujnik temperatury + LoRaWAN + serwer | dostarczone pakiety, bilans energii, raport strat |
| 4 | pilot po formalnej zgodzie operatora | podpisany protokół i metryki użyteczności |
| 5 | FTO, analiza konkurencji, rozmowy i TCO | opinie i dokumenty od partnerów |

Na dziś **nie potwierdzono TRL 3/4 ani żadnego wyższego poziomu Thermo-IoT**. Zaawansowane publikacje innych zespołów stanowią uzasadnienie wykonalności *kategorii technologii*, a nie dowód zbudowania naszego urządzenia.

## Model biznesowy i wpływ

Hipoteza: abonament za aktywny punkt telemetryczny z osobną opłatą wdrożeniową i integracyjną; alternatywnie sprzedaż urządzenia i licencja software. Należy uwzględnić BOM, obudowy, bramki LoRaWAN, montaż, serwis, chmurę, jakość i amortyzację. Nie ma jeszcze danych pozwalających podać wiarygodny TAM/SAM/SOM i marżę. Wskaźniki ESG trzeba mierzyć względem bazowej technologii: liczba unikniętych wymian baterii, masy odpadów, wizyty terenowe, straty ciepła i wyliczone na ich podstawie emisje. Rozwiązanie tematycznie wpisuje się w KIS 4 oraz pomocniczo KIS 7 i KIS 10.

## Potrzeby wsparcia

Pożądamy usług dostępnych w programie dla zakwalifikowanej ścieżki TRL: konsultacje metrologiczne/energetyczne, prototypowanie, badanie rynku, analizę FTO i IP, weryfikację modelu cenowego i pitch deck. Zakres i limit wynika z katalogu Lab_żetonów i umowy z operatorem; **50 000 PLN nie jest gwarantowaną wypłatą gotówkową dla pomysłodawcy**.

## Wymagane oświadczenia i dowody przed wysłaniem

Autorzy i role w zespole, kompetencje, pełnoletność, uprawnienia do praw IP, wcześniejsze wsparcie tym samym IPB, dostępne środki i zasoby, brak konfliktów formalnych, podpisy, zgody pilotowe i dowody prototypowania — **wszystko wymaga potwierdzenia przez pomysłodawcę**, nie wolno tego automatycznie poświadczać. Formularz zgłoszeniowy Garage Genius wymaga dołączenia **niezmienionego wzoru DOC/DOCX**. Dokument ten służy jedynie jako podstawa redakcyjna.

## Szansa naboru

Strona PARP podaje zakończenie naboru Garage Genius 30 listopada 2026 r. Status należy sprawdzić w momencie rzeczywistego zgłoszenia.
