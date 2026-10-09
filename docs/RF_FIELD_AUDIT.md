# Thermo-IoT — prywatny audyt odbioru The Things Stack v3

**Funkcja:** strukturalna analiza rzeczywistych lub syntetycznych *eksportów* zdarzeń aplikacyjnych TTN, bez przechwytywania radia, bez dostępu do konta i bez zmiany urządzeń. **Wyniki nie dowodzą fizycznego nadawania i nie są deklaracją PDR.**

## Przygotowanie wejścia

Z oficjalnego dziennika aplikacji TTN wyeksportować serię `uplink_message` jako plik **JSONL**: jedna kompletna koperta JSON na linię, zawierająca `end_device_ids`, `received_at`, `uplink_message.session_key_id`, `f_cnt`, `f_port=10` i kanoniczne `frm_payload`. Opcjonalnie `uplink_message.rx_metadata` z RSSI i SNR. **Żadnych kluczy, tokenów TTN, metadanych osób, prywatnego hardware ani innowacyjnej konstrukcji nie publikować do GitHub.**

```bash
python -m thermo_iot.rf_audit \
  --file private/mvp-evidence/ttn-uplinks.jsonl \
  --app-id thermo-lab --device-id pipe-1
```

Aplikacja wymaga identycznego `app_id`, `device_id` dla każdego zdarzenia i prawidłowej ramki 8 B Thermo-IoT v1. Plik jest ograniczony do 8 MB, 10 000 zdarzeń i 64 KiB na linię; odrzuca powtórzone klucze JSON, wartości niezależne od protokołu i błędne metadane. Skrypt **nie łączy się z siecią** i nie pobiera danych bezpośrednio z TTN — operator musi dostarczyć poprawny plik.

## Interpretacja wyników

- `unique_uplinks`: liczba unikalnych par `(session_key_id,f_cnt)`, nie liczba wszystkich wysłanych ramek.
- `duplicate_events`: zduplikowane zdarzenia z identycznym sensorem i licznikiem; sprzeczny payload w tej samej parze jest błędem.
- `observed_sessions`: liczba widzianych sesji LoRaWAN; skok licznika między sesjami **nie** jest interpretowany jako strata.
- `counter_discontinuity_estimate`: suma luk numeracyjnych w obserwowanej sesji. **To nie jest packet delivery rate ani dowód utraty wiadomości RF**, ponieważ nie widać wszystkich prób, retransmisji i resetów.
- `counter_regressions`: obserwowane obniżenia fCnt w tej samej sesji, mogą oznaczać opóźnione zdarzenia lub problem utrzymania licznika.
- `reference_lab_frames`: flagi 0x80 z wewnętrzną temperaturą MCU i ręcznie zadanymi parametrami; wykluczone z `pipe_measurement_frames`.
- `median_rssi_dbm`, `median_snr_db`: tylko wartości w przesłanych `rx_metadata`, przy wielu bramkach brana jest najlepsza zaobserwowana wartość; brak danych = `null`, nie 0.
- `median_observed_gap_s` i `maximum_observed_gap_s`: odstępy między **odebranymi** unikalnymi rekordami, nie czas pracy mikrokontrolera ani dowód autonomii.

**Granice:** nawet poprawny plik JSONL może być spreparowany. Do odbioru technicznego trzeba mieć oryginalny eksport z niezależnego, uwierzytelnionego TTN, zsynchronizowane zegary, log wszystkich prób nadawania, pomiar TX/RX i energetyczny zapis TEG/PMIC. Kontrola procedur i podpis operatora pozostają obowiązkowe.

**© 2026 Mojeaterego — Andrzej Mikulski. Wszelkie prawa zastrzeżone.** Kontakt: mojealterego21@gmail.com, +48 455 575 337. Prawa do The Things Stack i rozwiązań osób trzecich pozostają przy ich właścicielach.
