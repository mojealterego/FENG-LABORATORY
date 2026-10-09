#include "thermo_iot_power_policy.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

bool thermo_iot_power_init(
    thermo_iot_power_state *state, const thermo_iot_power_config *config
) {
    if (state == NULL || config == NULL
        || config->voltage_stop_mv >= config->voltage_start_mv
        || config->voltage_start_mv > 5500u
        || config->min_interval_s == 0u
        || config->max_interval_s < config->min_interval_s
        || config->duty_interval_s == 0u
        || config->cycle_energy_uj == 0u
        || config->energy_margin_percent < 100u
        || config->energy_margin_percent > 1000u) {
        return false;
    }
    memset(state, 0, sizeof(*state));
    state->config = *config;
    return true;
}

bool thermo_iot_power_check(
    thermo_iot_power_state *state, uint64_t now_s,
    uint16_t capacitor_mv, uint32_t net_harvest_power_uw,
    thermo_iot_power_result *result
) {
    if (state == NULL || result == NULL || capacitor_mv > 5500u
        || (state->checked_once && now_s < state->last_check_s)) {
        return false;
    }
    state->last_check_s = now_s;
    state->checked_once = true;
    state->armed_ready = false;
    result->interval_s = 0u;
    result->next_eligible_s = state->next_allowed_s;

    if (capacitor_mv < state->config.voltage_stop_mv) {
        state->active = false;
    } else if (capacitor_mv >= state->config.voltage_start_mv) {
        state->active = true;
    }
    if (!state->active) {
        result->decision = THERMO_IOT_POWER_CHARGING;
        return true;
    }
    if (net_harvest_power_uw == 0u) {
        result->decision = THERMO_IOT_POWER_DEFICIT;
        return true;
    }
    const uint64_t numerator = (uint64_t)state->config.cycle_energy_uj
                             * (uint64_t)state->config.energy_margin_percent;
    const uint64_t denominator = (uint64_t)net_harvest_power_uw * 100u;
    uint64_t interval = numerator / denominator;
    if (numerator % denominator != 0u) {
        ++interval;
    }
    if (interval < state->config.min_interval_s) {
        interval = state->config.min_interval_s;
    }
    if (interval < state->config.duty_interval_s) {
        interval = state->config.duty_interval_s;
    }
    if (interval > state->config.max_interval_s) {
        result->decision = THERMO_IOT_POWER_DEFICIT;
        return true;
    }
    result->interval_s = (uint32_t)interval;
    if (state->has_attempt) {
        if (state->last_attempt_s > UINT64_MAX - interval) {
            return false;
        }
        const uint64_t dynamic_cooldown = state->last_attempt_s + interval;
        if (result->next_eligible_s < dynamic_cooldown) {
            result->next_eligible_s = dynamic_cooldown;
        }
    }
    if (now_s < result->next_eligible_s) {
        result->decision = THERMO_IOT_POWER_WAIT;
        return true;
    }
    result->decision = THERMO_IOT_POWER_READY;
    result->next_eligible_s = now_s;
    state->last_interval_s = (uint32_t)interval;
    state->armed_ready = true;
    return true;
}

bool thermo_iot_power_mark_attempt(
    thermo_iot_power_state *state, uint64_t now_s, bool success
) {
    if (state == NULL || !state->checked_once || !state->armed_ready
        || now_s != state->last_check_s
        || now_s > UINT64_MAX - (uint64_t)state->last_interval_s) {
        return false;
    }
    state->next_allowed_s = now_s + (uint64_t)state->last_interval_s;
    state->has_attempt = true;
    state->last_attempt_s = now_s;
    state->armed_ready = false;
    if (state->attempts < UINT32_MAX) {
        ++state->attempts;
    }
    if (success && state->successes < UINT32_MAX) {
        ++state->successes;
    }
    return true;
}
