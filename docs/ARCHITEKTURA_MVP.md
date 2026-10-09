# Thermo-IoT — architektura demonstratora cyfrowego i kolejne bramki

## Dostarczony, wykonywalny fragment

```text
[C11 referencyjny koder ramki v1]
        | (8 B binarnie, FPort=10; bez sterownika czujnika i bez stosu LoRaWAN)
        v
[The Things Stack v3 — ZALEŻNOŚĆ ZEWNĘTRZNA, JESZCZE NIE PODŁĄCZONA]
        | webhook HTTP JSON, bearer token / TLS przez reverse proxy
        v
[thermo_iot.gateway] -> [TTN parser] -> [SQLite + de-dupe + kontrola kolejności]
                                            |
                                            v
                                     [median + MAD]
                                            |
                                            v
                                   [candidate / report]
```

Rozwiązanie nie ma implementacji modemu/LoRaWAN stack, samodzielnej firmware aplikacji ani elektronicznego układu pomiarowego. Schemat przedstawia **sprawdzoną warstwę kodową i projektowaną integrację**, nie kompletną instalację.

### Granice odpowiedzialności

1. **Kontrakt urządzenia:** 8 bajtów, little endian, wersjonowanie, granice zakresów i testy C11/Python. Adapter to narzędzie do tworzenia oprogramowania układowego.
2. **Łączność:** TTN jest zewnętrznym dostawcą. To TTN odpowiada za MIC, dekrypcję payloadu i weryfikację ramek; webhook powinien przechodzić przez TLS i uwierzytelnienie aplikacyjne.
3. **Zapis:** SQLite przechowuje dane per aplikacja i per urządzenie, idempotentnie po (`application_id`, `device_id`, `session_key_id`, `f_cnt`). Różne treści tej samej ramki są odrzucane.
4. **Analityka:** median + MAD identyfikuje kandydatów odchyleń i nie jest detektorem awarii. Dane spóźnione są przyjmowane, ale nie podnoszą alertów.
5. **Planowanie energii:** `scheduler.decide_interval` wykorzystuje **dostarczoną z pomiaru moc elektryczną TEG** (nie zgaduje mocy z ΔT), napięcie kondensatora, rezerwę oraz limity radiowe. Status `eligible` nie jest upoważnieniem do emisji ani dowodem energii szczytowej.

### Stan do osiągnięcia przed TRL

| Element | Dowód / kryterium | Stan |
|---|---|---|
| Koder ramki C11+Python | zgodność z wektorem i testy zakresu | implementacja kodowa |
| LoRaWAN end-device | OTAA i odbiór na gateway | brak |
| TEG/PMIC/superkondensator | powtarzalny test cold-start/ESR | brak |
| Czujnik temp. + kalibracja | zestaw danych względem wzorca | brak |
| Projekt PCB/obudowa | pliki CAD/EDA i prototyp | brak |
| Operator pilotażu | zgoda, protokół, lokalizacja | brak |
| SensaaS | rozmowy, ceny, TCO, listy intencyjne | brak |

Nie wystawiać tego serwera na publicznej sieci bez przeglądu bezpieczeństwa, monitoringu, zarządzania sekretami i TLS.
