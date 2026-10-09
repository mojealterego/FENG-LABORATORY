# Thermo-IoT — realistyczny plan inkubacji 12 tygodni

Horyzont orientacyjny na podstawie komunikatu operatora o realizacji **około 3 miesięcy**. Rozpoczęcie planu jest zależne od przyjęcia do programu. Etapy nie stanowią potwierdzonych zobowiązań, harmonogram należy uzgodnić indywidualnie.

| Tygodnie | Działanie | Mierzalny dowód | Bramki |
|---|---|---|---|
| 1–2 | Spis IP, benchmark TEG+LoRa, audyt instalowalności | rejestr autorów, analiza konkurencji, 10 rozmów, wstępne stanowisko próbne | prawa IP i warunki dostępności rur |
| 3–4 | Kontrolowane próby `ΔT` i kilka krzywych P–V | skalibrowane logi, analiza niepewności, odtwarzalny protokół | dodatnia i użyteczna moc w najgorszym profilu |
| 5–6 | Pomiary PMIC/cold-start/superkondensator + profil TX | oscyloskopy, przebiegi, ESR, rozruch, 7 dni laboratoryjnych | zamknięty bilans energetyczny |
| 7–8 | Płytka demonstracyjna lub moduły deweloperskie, telemetria LoRaWAN | logi OTAA, utrata pakietów, pobory prądu | spełnienie wymogów łączności i sprawności |
| 9–10 | Proponowany PoC u operatora **tylko po zgodzie** | procedury BHP/OT, raport montażu oraz pomiarów; wywiady | podpisane zgody i możliwość instalacji |
| 11–12 | Model jednostkowej ekonomiki, FTO, pitch deck | niezależny raport FTO jeśli mieści się w usługach, TCO, prezentacja | decyzja inwestycyjna GO/NO-GO |

## Warunki awaryjne

- Jeżeli brakuje prawa do technologii lub koliduje z patentami, nie przedstawiać formalnego oświadczenia o pełni praw.
- Jeżeli próbki nie zapewnią dodatniego bilansu przy realnych warunkach, zamiast obiecywać ultradźwięki, zredukować MVP do temperatury albo wskazać odrębne źródło zasilania.
- Jeżeli nie ma możliwości legalnego dostępu do rury pod izolacją, dobrać inny punkt pomiarowy albo zrezygnować z tego wariantu.
- Jeżeli nie ma zgody partnera, zakończyć jako demonstrator laboratoryjny; pilotaż i TRL w warunkach operacyjnych pozostają celami na dalszy etap.
- Efekt ESG i oszczędności przed walidacją nie są liczbami możliwymi do deklarowania.

Opracowane narzędzia software służą dokumentacji i protokołowi pomiarowemu, nie stanowią fizycznej demonstracji.
