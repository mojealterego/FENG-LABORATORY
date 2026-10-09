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
python -m thermo_iot.lorawan_fieldtest --port COM3 --send --temperature-centic 4300 --capacitor-mv 3000 \
  --app-id thermo-lab --device-id thermo-test --report rf-attempt-001.json
```

Pierwsza komenda sprawdza AT/region/OTAA/FPort **bez transmisji**. Druga wykonuje `AT+JOIN` oraz `AT+MSGHEX` dla ramki v1 (FPort=10), wyłącznie po jawnej fladze `--send`. Podane liczby są **wpisane ręcznie**, a nie pochodzą z przetwornika ADC.

## Dwustopniowy protokół wysłania i niezależnego odbioru

**Przed emisją:** operator wybiera nowy plik `rf-attempt-001.json`. Program sprawdza, że plik nie istnieje, a następnie generuje losowy, niezerowy **7-bitowy znacznik próby** w dolnych bitach flag i zawsze ustawia **0x80** (telemetria referencyjna, NIE pomiar rurociągu). Dzięki temu backend wyklucza ręcznie wpisane temperatury z detektora awarii.

**Etap A: komendy sprzętowe** `--send --report` wymagają fizycznego Wio-E5, zewnętrznej anteny, legalnej konfiguracji EU868 i skonfigurowanego konta TTN. Po zakończeniu AT+JOIN i AT+MSGHEX skrypt zapisuje raport z czasem rozpoczęcia/zakończenia operacji oraz dokładnymi 8 bajtami — stan `pending_external_ttn_receipt`. **To nie jest dowód odbioru radiowego.**

**Etap B: eksport niezależnego, rzeczywistego uplinku z TTN** (z konsoli The Things Stack, po wykonaniu próby) i weryfikacja bez portu szeregowego:

```bash
python -m thermo_iot.lorawan_fieldtest \
  --verify-report rf-attempt-001.json \
  --ttn-receipt ttn-actual-uplink.json
```

Wymagane: ten sam app_id, device_id, FPort=10, pełne 8 bajtów zawierające znacznik próby, poprawny FCnt, session_key_id, czas TTN `received_at` przypadający od rozpoczęcia próby do maksymalnie 5 minut po jej zakończeniu. Import odrzuca poprzednie pakiety z identyczną temperaturą ale innym znacznikiem i wszystkie pakiety sprzed próby. Samo dopasowanie nie dowodzi autentyczności pliku JSON — należy zachować oryginalny eksport TTN, zegar stanowiska, konfigurację urządzenia, RSSI/SNR i niezależny dziennik operatora.

**Uwaga do metrologii:** `--temperature-centic`, `--capacitor-mv`, `--teg-power-uw` oznaczają wartości **ręcznie podane przez operatora**; nie powstają z fizycznych czujników. Bit 0x80 blokuje ich wykorzystanie do statystyki wycieków, również gdy urządzenie zostanie odebrane przez bramkę.

**Zastrzeżenia:** 7-bitowy znacznik nie jest kryptograficznym nonce, a zegar komputera nie jest synchronizowany automatycznie z TTN. Ta metoda zwiększa odporność na omyłkowe przypisanie starego uplinku, ale nie zapewnia formalnego dowodu transmisji ani odporności na fałszowanie. Najwyższą wiarygodność zapewnia operator i niezależna weryfikacja logów TTN.

**Prawa autorskie:** © 2026 Mojeaterego — Andrzej Mikulski. Wszelkie prawa zastrzeżone. Kontakt: mojealterego21@gmail.com, +48 455 575 337.
