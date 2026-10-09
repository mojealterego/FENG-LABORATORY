/* Thermo-IoT MCU-independent deterministic transmission gate (C11). */
#ifndef THERMO_IOT_POWER_POLICY_H
#define THERMO_IOT_POWER_POLICY_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint16_t voltage_start_mv;
    uint16_t voltage_stop_mv;
    uint32_t min_interval_s;
    uint32_t max_interval_s;
    uint32_t duty_interval_s;
    uint32_t cycle_energy_uj;
    uint16_t energy_margin_percent;
} thermo_iot_power_config;

typedef enum {
    THERMO_IOT_POWER_CHARGING = 0,
    THERMO_IOT_POWER_DEFICIT = 1,
    THERMO_IOT_POWER_WAIT = 2,
    THERMO_IOT_POWER_READY = 3
} thermo_iot_power_decision;

typedef struct {
    thermo_iot_power_decision decision;
    uint32_t interval_s;
    uint64_t next_eligible_s;
} thermo_iot_power_result;

typedef struct {
    thermo_iot_power_config config;
    bool active;
    bool checked_once;
    bool armed_ready;
    bool has_attempt;
    uint64_t last_attempt_s;
    uint64_t last_check_s;
    uint64_t next_allowed_s;
    uint32_t last_interval_s;
    uint32_t attempts;
    uint32_t successes;
} thermo_iot_power_state;

/* Validates hysteresis thresholds, intervals, energy and a margin >= 100%. */
bool thermo_iot_power_init(
    thermo_iot_power_state *state, const thermo_iot_power_config *config
);

/* Net harvested power is measured AFTER PMIC conversion and standby losses.
 * Only average power is screened: radio current sag, MCU brownout and PMIC
 * startup must be verified separately. now_s is a monotonic boot-time clock.
 */
bool thermo_iot_power_check(
    thermo_iot_power_state *state, uint64_t now_s,
    uint16_t capacitor_mv, uint32_t net_harvest_power_uw,
    thermo_iot_power_result *result
);

/* One radio attempt following a READY result at the same measured timestamp.
 * Failure also triggers cooldown: TX may have occupied the radio subband.
 */
bool thermo_iot_power_mark_attempt(
    thermo_iot_power_state *state, uint64_t now_s, bool success
);

#endif
