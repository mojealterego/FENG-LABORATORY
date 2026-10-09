# Minimalny model analityki dla Thermo-IoT

Na obecnym etapie powstał **offline screening** odchyleń temperatury oparty na medianie i MAD. To nie jest model wykrywania wycieków i **nie** generuje decyzji sterujących siecią. Funkcja zwraca status: insufficient_history, normal albo anomaly_candidate. Próg bezwzględny (domyślnie 0,5°C) chroni przed artefaktami przy niemal stałej linii bazowej; pozostałe alarmy są wyznaczane przez czterokrotną skalę odpornego odchylenia.

Wersja pilotażowa musi:
1. porównywać aktualny odczyt z bazą odniesienia z dopasowaniem do obciążenia, pory doby i warunków otoczenia;
2. odrzucać nielogiczne dane i utraty łączności, prowadzić rejestr jakości;
3. wprowadzić próg liczby kolejnych obserwacji lub potwierdzenie u operatora przed alarmem operacyjnym;
4. walidować wszystkie alerty względem oznaczonych zdarzeń rzeczywistych;
5. raportować precision, recall, false alarms per node-month, detection latency i przerwy transmisji.

Przykład offline (Python):

    from thermo_iot.anomaly import detect_temperature_anomaly
    wynik = detect_temperature_anomaly([50.0, 50.1, 49.9, 50.0, 50.2], 60.0)
    print(wynik)

Model nie może być używany jako element systemu bezpieczeństwa ani zastąpić istniejących urządzeń SCADA.
