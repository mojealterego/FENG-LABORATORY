# Thermo-IoT — referencyjny protokół telemetryczny i ingest TTN v3

**Stan:** oprogramowanie referencyjne / narzędzie laboratoryjne. Brak sprzętu, kalibracji, urządzeń LoRaWAN, certyfikacji oraz aktywnej usługi. Interfejs nie steruje siecią i nie stanowi zabezpieczenia infrastruktury.

## Ramka v1 / LoRaWAN FPort 10

Ośmiobajtowy komunikat **little endian** `<BhHHB`:

| Offset | Typ | Pole | Zasada |
|---|---|---|---|
| 0 | u8 | wersja | 1 |
| 1–2 | i16 | temperatura [0,01°C] | -40,00°C … 150,00°C |
| 3–4 | u16 | napięcie bufora [mV] | 0 … 5500 mV |
| 5–6 | u16 | moc elektryczna TEG [µW] | 0…65534, 65535 = niedostępna |
| 7 | u8 | flagi diagnostyczne | 0…255, interpretacja zależna od przyszłej specyfikacji firmware |

Wartości są **zdefiniowaną specyfikacją projektową**, a nie danymi zmierzonymi urządzeniem. W szczególności pomiar `teg_power_uw` wymaga właściwego toru pomiarowego, nie wynika z samej temperatury.

## Integracja TTN v3

Adapter korzysta z `end_device_ids.application_ids.application_id`, `end_device_ids.device_id`, `received_at`, `uplink_message.session_key_id`, `f_cnt`, `f_port` oraz `frm_payload`. Pole `decoded_payload` nie jest źródłem prawdy. Wymagane są dane **odszyfrowane przez The Things Stack**; komunikaty z `app_s_key` są odrzucane. Idempotencję definiuje klucz (`application_id`, `device_id`, `session_key_id`, `f_cnt`): ponowny uplink nie powiela rekordu; inny payload dla tej samej ramki jest błędem. Nowa sesja dopuszcza reset licznika FCnt.

**Lokalnie:**

```bash
python -m thermo_iot.gateway ingest --db ./local-telemetry.sqlite --file examples/ttn_v3_uplink.json
python -m thermo_iot.gateway report --db ./local-telemetry.sqlite --app district-heat --device pipe-1
```

**Test webhooka:**

```bash
export THERMO_IOT_WEBHOOK_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m thermo_iot.gateway serve --db ./local-telemetry.sqlite --host 127.0.0.1 --port 8765
```

Zewnętrzne połączenie TTN wymaga poprawnego ustawienia webhooka i tajnego nagłówka HTTP `Authorization: Bearer <token>`. Domyślny serwer nie udostępnia TLS i jest **wyłącznie lokalny**. Do wystawienia publicznego wymagane są reverse proxy z TLS, kontrola źródeł, ochrona przed przeciążeniem i rotacja tokenu. Kontrola nagłówka nie zastępuje autentykacji LoRaWAN na TTN. Nie wpisywać tajnych tokenów do Git ani logów.

**Interpretacja:** `insufficient_history` / `normal` / `anomaly_candidate` / `out_of_order`. Ostatni stan oznacza ramkę przychodzącą z wcześniejszym czasem serwerowym i wyklucza alarm. Kandydat anomalii to odchylenie statystyczne, **nie wykryty wyciek**. Brak modelu obciążenia, progów uzgodnionych z klientem i walidacji na rzeczywistych zdarzeniach.

## Referencje

- The Things Stack: https://www.thethingsindustries.com/docs/the-things-stack/concepts/data-formats/
- LoRa Alliance: https://lora-alliance.org/
