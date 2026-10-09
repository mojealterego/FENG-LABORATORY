# Thermo-IoT — zweryfikowana lista podzespołów do testów i decyzje konstrukcyjne

**9 października 2026 r. — karta do przygotowania stanowiska laboratoryjnego.** Nie jest to projekt PCB, zatwierdzony BOM ani dokumentacja produkcyjna. Poniższe parametry pochodzą z oficjalnych stron producentów (linki niżej); parametry całego systemu pozostają hipotezami do pomiaru.

## Krótka lista elementów do weryfikacji

| Funkcja | Kandydat | Dane producenta istotne dla wykonalności | Ryzyko/do sprawdzenia |
|---|---|---|---|
| TEG PMIC przy bardzo niskim napięciu | **Analog Devices LTC3108** | start z wejścia od ok. 20 mV przy wymaganym transformatorze; do wyboru VOUT 2,35/3,3/4,1/5 V | **20 mV to minimalne napięcie wejściowe układu, nie gwarantowana moc wyjściowa przy dowolnym TEG.** |
| TEG PMIC przy zmiennej polaryzacji | **Analog Devices LTC3109** | start od około ±30 mV, automatyczna obsługa polaryzacji; rozwiązanie transformatorowe | złożoność transformatorów, straty i moc przy starcie |
| Alternatywne PMIC z MPPT | **Texas Instruments BQ25570** | cold start **≥600 mV**, po uruchomieniu harvesting od około 100 mV; bufor supercap i buck | jeśli TEG nie osiągnie 600 mV podczas zimnego startu, układ nie uruchomi się samodzielnie w tej konfiguracji; brak zgody na przyjmowanie 100 mV jako warunku rozruchowego |
| SoC z radiem LoRa | **ST STM32WLE5C8** | zasilanie 1,8–3,6 V, LoRa i zgodność ze stosem LoRaWAN; radio TX ok. 15 mA @10 dBm albo 87 mA @20 dBm w warunkach katalogowych | prąd **radia**, nie całej płytki. Sprawdzić piki, SF, moc TX, długość nadawania i RF matching |
| Pomiar temperatury płytki | **ST STTS22H** | zasilanie 1,5–3,6 V, tryb one-shot, prąd 1,75 µA według producenta, temperatura pracy do 125°C | deklaracja dokładności ±0,5°C obowiązuje -10…60°C; nie przenosić jej na temperaturę gorącej rury |
| Magazyn energii | Superkondensator, **parametry do wybrania** | zakres V, pojemność znamionowa i tolerancje, ESR, upływ, dopuszczalna temperatura | źródła i układy balansowania zależą od docelowego napięcia; 2,5 F jest założeniem symulacyjnym, nie zamówionym elementem |

## Wstępne rozdzielenie torów

```text
Połączenie termiczne na stanowisku: rura -> cTEG/TEG -> radiator/otoczenie
                               |
                          VTEG / ITEG
                               |
                  [PMIC / cold-start / PGOOD]
                               |
                 [magazyn energii + ochrona]
                               |
         [tor zasilania oceniony dla impulsu TX]
                /                    \
        [STM32WLE5C8]          [STTS22H]
                |
        [LoRaWAN Class A / antena]
```

Nie zasilać nadajnika STM32WLE5 bezpośrednio z wyjścia LDO LTC3108 (2,2 V, typowy limit 3 mA), którego prąd jest mniejszy od opublikowanego prądu samego radia. Należy przeanalizować zasilanie z bufora przez odpowiedni tor i rzeczywiste napięcie podczas impulsu. Dobór transformatora, kondensatorów, wyprowadzeń oraz zabezpieczenia nie jest możliwy wyłącznie na podstawie tej architektury.

## Korekta założenia 21,9 mJ

Dane ST podają radio TX około **87 mA przy +20 dBm**. Jeśli hipotetycznie radio nadawałoby 0,2 s przy 3,3 V, energia samego toru TX wynosi `3,3 V × 0,087 A × 0,2 s = 0,05742 J`, czyli **57,42 mJ**, jeszcze przed MCU, pomiarem i nasłuchem RX. Wynik ten nie dowodzi, że każda konfiguracja LoRaWAN potrzebuje 57,42 mJ, ale obala traktowanie 21,9 mJ jako uniwersalnego limitu energetycznego.

Testowy, pierwszorzędowy model `thermo_iot.radio_budget` liczy energię TX/RX oraz zgrubną zmianę napięcia kondensatora:

```python
from thermo_iot.radio_budget import RadioBurst, estimate_burst
result = estimate_burst(RadioBurst())
print(result)
```

Wynik oparty jest na hipotetycznych czasach i ESR; model nie odwzorowuje dynamiki regulatora, prądów startowych ani strat transmitancji. Należy wykonać pomiary na wybranym zestawie zasilania i module radiowym.

## Kolejność decyzji

1. Na kontrolowanym stanowisku sprawdzić `ΔT` po obu stronach TEG, napięcie jałowe oraz charakterystykę V-I i moc przy zadanym obciążeniu.
2. W odniesieniu do realnych danych TEG porównać cold start oraz stabilną moc PMIC LTC3108/LTC3109/BQ25570 z właściwymi obwodami producenta.
3. Wybrać magazyn z wystarczającą rezerwą napięcia, temperatury, ESR i prądu szczytowego (obejmującą MCU oraz TX/RX). Oszacować kondensator po uwzględnieniu dryftu parametrów.
4. Zweryfikować powtarzalność montażu TEG, parametry radiatora i miejsce czujnika na **dostępnym stanowisku** bez ingerencji w czynne ciepłociągi bez zgody.
5. Dopiero po potwierdzeniu kryteriów zamrozić BOM, schemat KiCad, mapę pinów, projekt RF/PCB oraz plan testów EMC.

## Źródła pierwotne

- LTC3108: https://www.analog.com/en/products/ltc3108.html
- LTC3109: https://www.analog.com/en/products/ltc3109.html
- BQ25570: https://www.ti.com/product/BQ25570
- STM32WLE5C8: https://www.st.com/en/microcontrollers-microprocessors/stm32wle5c8.html
- STTS22H: https://www.st.com/en/mems-and-sensors/stts22h.html

Bez testów FTO i praw autorskich nie ujawniać publicznie szczegółów potencjalnie chronionego rozwiązania mocowania.
