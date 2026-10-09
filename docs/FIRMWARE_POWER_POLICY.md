# Firmware — laboratoryjna bramka transmitowania

W katalogu `firmware/` znajdują się dwa niezależne komponenty w C11: kodek 8-bajtowej ramki i deterministyczna polityka energetyczna.

## Mechanizm

Funkcja `thermo_iot_power_check` analizuje napięcie bufora, **zmierzoną średnią moc netto po PMIC i stratach spoczynkowych**, konfigurowalny koszt jednego cyklu oraz minimalny odstęp radiowy. Wyniki: `CHARGING`, `DEFICIT`, `WAIT`, `READY`.

Włączenie następuje przy napięciu `voltage_start_mv`, wyłączenie przy zejściu poniżej `voltage_stop_mv`, co ogranicza drgania stanu w pobliżu progu. Przy spadku podaży mocy wymagany interwał jest **wydłużany również po poprzedniej transmisji** (test regresyjny). Każda próba radiowa, nawet zakończona błędem, zaczyna czas blokady. Zegar `now_s` jest monotoniczny — cofnięcie czasu i przepełnienie zegara skutkują odmową decyzji.

## API referencyjne

```c
thermo_iot_power_config config = {
    .voltage_start_mv = 2800,
    .voltage_stop_mv = 2400,
    .min_interval_s = 60,
    .max_interval_s = 3600,
    .duty_interval_s = 300,
    .cycle_energy_uj = 21900,
    .energy_margin_percent = 200,
};
thermo_iot_power_state state;
thermo_iot_power_result result;
if (thermo_iot_power_init(&state, &config)
    && thermo_iot_power_check(&state, 0, 3000, 100, &result)
    && result.decision == THERMO_IOT_POWER_READY) {
    /* W rzeczywistym MCU należy najpierw ponownie zweryfikować napięcie */
    /* i wykonać pomiar, LoRaWAN oraz ocenę skutku transmisji. */
    (void)thermo_iot_power_mark_attempt(&state, 0, false);
}
```

## Granice stosowania i BHP

**To nie jest firmware dla konkretnego MCU, stos LoRaWAN ani układ zabezpieczenia zasilania.** Napięcie startowe, rezerwa kondensatora, sprawność i energia w cyklu są parametrami do zmierzenia; przy zbyt dużym ESR samo napięcie na buforze nie potwierdza możliwości obciążenia prądem TX. `READY` nie oznacza dopuszczenia emisji zgodnie z wymaganiami ETSI. Parametr `duty_interval_s` musi wynikać z odpowiedniej podstrefy częstotliwości, faktycznego SF i airtime; sam stały odstęp nie wystarcza do oceny pełnej zgodności.

Stan blokady należy odtwarzać po resecie z trwałego, wiarygodnego źródła; `thermo_iot_power_init` zeruje pamięć RAM i **nie zachowuje odstępu po restarcie**. Przed uruchomieniem na urządzeniu trzeba dołożyć brownout/supervisor, preflight napięcia po obciążeniu, watchdoga, obsługę OTAA, utratę sesji i bezpieczny mechanizm zapisu stanu. Brak interfejsów HAL — stąd nie deklarujemy kompletnego urządzenia.

Test lokalny:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -Ifirmware/include firmware/src/thermo_iot_power_policy.c firmware/tests/test_power_policy.c -o /tmp/thermo_power_tests
/tmp/thermo_power_tests
```
