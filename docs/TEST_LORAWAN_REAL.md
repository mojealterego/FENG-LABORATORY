# Procedura realnego testu LoRaWAN — Wio-E5 mini, STM32WLE5JC

**Nie wykonano emisji radiowej ani potwierdzonego uplinku w czasie tworzenia repozytorium.** Do takiej walidacji wymagane są fizyczny moduł, antena EU868, komputer z UART/USB, bramka w zasięgu oraz konto LoRaWAN Network Server.

## Konkretny target

Wio-E5 mini / Development Kit z MCU ST **STM32WLE5JC**. Na początkowym etapie używamy fabrycznego firmware AT producenta, a aplikacja testowa jest programem **hosta** Python. Ten zestaw nie jest jeszcze samodzielnym firmware Thermo-IoT na MCU. Test ten sprawdza tor radiowy i format 8 B bez konieczności wcześniejszego usunięcia fabrycznego oprogramowania.

Źródła: https://wiki.seeedstudio.com/LoRa_E5_mini/ i https://files.seeedstudio.com/products/317990687/res/LoRa-E5%20AT%20Command%20Specification_V1.0%20.pdf .

## Prerekwizyty

1. Uruchomić Wio-E5 z anteną w legalnej sieci EU868; zapewnić odpowiednią licencję, zgodę i spełnić lokalne ograniczenia radiowe/duty-cycle; w trybie testowym **jeden** pakiet i nie częściej niż dopuszcza konfiguracja.
2. Utworzyć aplikację i urządzenie OTAA w The Things Stack; fabryczne DevEUI/JoinEUI/AppKey przechowywać poza repozytorium, wprowadzić według instrukcji Seeed. Program nie zapisuje kluczy i ich nie konfiguruje.
3. Ustalić ścieżkę portu szeregowgo (Windows COMx, Linux /dev/ttyUSBx), 9600 8N1. Zainstalować lokalnie `python -m pip install pyserial`.
4. Z komputera z portem szeregowym uruchomić:

```bash
python -m thermo_iot.lorawan_fieldtest --port COM3
python -m thermo_iot.lorawan_fieldtest --port COM3 --send --temperature-centic 4300 --capacitor-mv 3000
```

Pierwsza komenda sprawdza AT/region/OTAA/FPort **bez transmisji**. Druga wykonuje `AT+JOIN` oraz `AT+MSGHEX` dla ramki v1 (FPort=10), wyłącznie po jawnej fladze `--send`. Podane liczby są **wpisane ręcznie**, a nie pochodzą z przetwornika ADC.

## Weryfikacja dostarczenia

**`+MSGHEX: Done` oznacza koniec operacji po stronie modemu, nie potwierdza odbioru przez TTN.** Aby potwierdzić zawartość, w konsoli TTN otworzyć Live Data, eksportować pełny faktyczny uplink v3 jako JSON; nie eksportować ani nie commitować tokenów/kluczy. Porównać pochodzący niezależnie z TTN zapis z wysłanymi polami:

```bash
python -m thermo_iot.lorawan_fieldtest --port COM3 --send --temperature-centic 4300 --capacitor-mv 3000 \
  --ttn-receipt ttn-actual-uplink.json --app-id thermo-lab --device-id thermo-test
```

Program porównuje: application_id, device_id, FPort=10, pole binarne `frm_payload`, licznik FCnt, session_key_id oraz czas. Wynik `ttn_receipt_content_matches` nie jest kryptograficznym potwierdzeniem źródła pliku. Przy realnym odbiorze trzeba zarchiwizować podpisany protokół, identyfikator urządzenia, potwierdzony uplink z konsoli TTN, RSSI/SNR, SF/BW i profil poboru energii oraz zweryfikować zgodność licznika, czasu i sesji.

**Bramka TRL:** raport realnej pracy może powstać dopiero po wykonaniu prób; same testy mock serial nie stanowią testów radiowych.
