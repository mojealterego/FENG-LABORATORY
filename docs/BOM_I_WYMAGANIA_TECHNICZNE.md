# Thermo-IoT — BOM funkcjonalny i wymagania zakupowe do zweryfikowania

**Żadna pozycja nie została zamówiona lub przetestowana w ramach tego repozytorium.** Brak numerów części i cen nie jest luką do uzupełnienia domysłami; parametry zostaną ustalone po pomiarze źródła i wywiadach z operatorami.

| Blok | Wymaganie wstępne | Dowód wyboru |
|---|---|---|
| TEG/cTEG | napięcie obwodu otwartego oraz P–V pod obciążeniem przy rzeczywistym `ΔT` na module | serie z `thermo_iot.lab`, niezależne próby montażu |
| Kontakt i radiator | mały opór termiczny, powtarzalny docisk, materiał odporny na korozję, montaż z zatwierdzeniem operatora | testy mechaniczne i termiczne |
| PMIC harvesting | cold-start przy najgorszym zmierzonym napięciu/rezystancji źródła, mały Iq | oscyloskop, protokół startu i sprawność vs moc |
| Superkondensator | właściwe napięcie z marginesem, ESR, upływ i żywotność temperaturowa | charakterystyki w wybranym zakresie temperatur i piki TX |
| MCU | realny deep sleep, pomiar napięcia bufora, watchdog, nadzór brownout | rejestrowany prąd w całej sekwencji |
| LoRa radio | dołączenie do sieci, FPort=10, spełnienie ograniczeń regionalnych, RAM/flash dla stosu | logi OTAA, airtime i delivery rate |
| Pomiar temperatury | znana niepewność toru, wpływ termiczny opaski | porównanie ze wzorcem |
| Pomiar mocy TEG | pomiar różnicowy lub układ instrumentacji adekwatny do `V×I` | charakterystyki błędu i wpływu toru pomiarowego |
| PCB/obudowa | szczelność, ESD/EMC, izolacja elektryczna, odporność na wodę i temperaturę | testy środowiskowe, bezpieczny dostęp |
| Lokalny gateway / backend | wiarygodny uplink TTN, brak komunikatów sterujących, autoryzacja i segmentacja | test end-to-end z realnymi paczkami |

## Wzór kryterium GO dla zasilania

Warunek konieczny dla okresu pomiarowego `T`:

`P_TEG,meas * η_PMIC > P_spocz,meas + E_cykl,meas / T`

Osobno trzeba spełnić warunek napięcia cold-start i prądu szczytowego transmisji, uwzględniając ESR superkondensatora. Sam dodatni bilans średniej mocy nie wystarcza.

## Faza 1 / Faza 2

**Faza 1:** TEG, PMIC, bufor, mikrokontroler, temperatura, napięcie i LoRaWAN Class A.

**Faza 2:** clamp-on ultradźwięki / pomiar przepływu tylko po stwierdzeniu nadwyżki energetycznej, weryfikacji geometrii rur oraz wzorcowaniu. Ciśnienia zewnętrzna opaska nie mierzy bez osobnego sensora/metody.

Integrację SCADA/OT należy realizować wyłącznie w trybie odczytu po zgodzie partnera.
