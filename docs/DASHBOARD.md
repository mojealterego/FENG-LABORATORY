# Thermo-IoT — lokalny dashboard laboratoryjny

## Dostarczony interfejs

Wariant read-only wyświetla listę zarejestrowanych urządzeń, sumaryczne dane o przyjętych pakietach, odchyleniach statystycznych, ostatniej temperaturze i napięciu bufora oraz wykres 100 ostatnich próbek. Nie zawiera danych testowych zaszytych w UI — odczytuje lokalną bazę SQLite utworzoną przez adapter The Things Stack.

Uruchomienie (Python 3.10+):

```bash
python -m thermo_iot.gateway ingest --db ./thermo-demo.sqlite --file examples/ttn_v3_uplink.json
python -m thermo_iot.dashboard --db ./thermo-demo.sqlite --host 127.0.0.1 --port 8766
```

Otworzyć na **tym samym komputerze**: `http://127.0.0.1:8766/`.

Lokalne punkty GET:
- `/api/devices` — grupuje urządzenia, pakiety, kandydatów anomalii;
- `/api/history?app=district-heat&device=pipe-1&limit=100` — tylko najnowsze, do 200;
- `/`, `/app.js`, `/app.css` — zasoby lokalne bez zewnętrznych zależności.

Serwer HTTP akceptuje tylko interfejs `localhost`, operacje zapisu są wyłączone, SQLite otwiera się w trybie `mode=ro`, API stosuje walidację parametrów i zapytania SQL z parametrami, strona ma restrykcyjne CSP oraz `Cache-Control: no-store`.

**Ograniczenia:** brak logowania, TLS, uprawnień operatorów, skalowania, alarmów certyfikowanych i integracji sterowania OT. Nie należy przekierowywać tego serwera do Internetu. Dane z przykładowego JSON są fikcyjne i nie odzwierciedlają warunków pracy w sieci ciepłowniczej.
