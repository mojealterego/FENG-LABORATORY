#include "thermo_iot_power_policy.h"
#include <stdint.h>
#include <stdio.h>

#define CHECK(cond) do { if (!(cond)) { fprintf(stderr, "FAILED line %d: %s\n", __LINE__, #cond); return 1; } } while (0)

static thermo_iot_power_config sample_config(void) {
    const thermo_iot_power_config config = {
        .voltage_start_mv = 2800u,
        .voltage_stop_mv = 2400u,
        .min_interval_s = 60u,
        .max_interval_s = 3600u,
        .duty_interval_s = 300u,
        .cycle_energy_uj = 21900u,
        .energy_margin_percent = 200u,
    };
    return config;
}

static int test_validation(void) {
    thermo_iot_power_state state;
    thermo_iot_power_config config = sample_config();
    CHECK(!thermo_iot_power_init(NULL, &config));
    CHECK(!thermo_iot_power_init(&state, NULL));
    config.voltage_start_mv = 2300u;
    CHECK(!thermo_iot_power_init(&state, &config));
    config = sample_config();
    config.max_interval_s = 1u;
    CHECK(!thermo_iot_power_init(&state, &config));
    config = sample_config();
    config.energy_margin_percent = 99u;
    CHECK(!thermo_iot_power_init(&state, &config));
    config = sample_config();
    CHECK(thermo_iot_power_init(&state, &config));
    return 0;
}

static int test_hysteresis_and_intervals(void) {
    thermo_iot_power_state state;
    thermo_iot_power_config config = sample_config();
    thermo_iot_power_result result;
    CHECK(thermo_iot_power_init(&state, &config));
    CHECK(thermo_iot_power_check(&state, 10u, 2600u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_CHARGING);
    CHECK(!thermo_iot_power_mark_attempt(&state, 10u, false));
    CHECK(thermo_iot_power_check(&state, 100u, 2800u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    CHECK(result.interval_s == 438u);
    CHECK(thermo_iot_power_mark_attempt(&state, 100u, true));
    CHECK(thermo_iot_power_check(&state, 120u, 2500u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_WAIT);
    CHECK(result.next_eligible_s == 538u);
    CHECK(thermo_iot_power_check(&state, 538u, 2500u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    CHECK(thermo_iot_power_check(&state, 539u, 2399u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_CHARGING);
    CHECK(thermo_iot_power_check(&state, 540u, 2500u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_CHARGING);
    CHECK(thermo_iot_power_check(&state, 541u, 2800u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    return 0;
}

static int test_zero_net_and_duty_limit(void) {
    thermo_iot_power_state state;
    thermo_iot_power_config config = sample_config();
    thermo_iot_power_result result;
    CHECK(thermo_iot_power_init(&state, &config));
    CHECK(thermo_iot_power_check(&state, 1u, 3000u, 0u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_DEFICIT);
    CHECK(thermo_iot_power_check(&state, 2u, 3000u, 100000u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    CHECK(result.interval_s == 300u);
    CHECK(thermo_iot_power_mark_attempt(&state, 2u, true));
    CHECK(thermo_iot_power_check(&state, 301u, 3000u, 100000u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_WAIT);
    CHECK(thermo_iot_power_check(&state, 302u, 3000u, 100000u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    CHECK(thermo_iot_power_check(&state, 303u, 3000u, 1u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_DEFICIT);
    return 0;
}

static int test_reduced_harvest_extends_existing_cooldown(void) {
    thermo_iot_power_state state;
    thermo_iot_power_config config = sample_config();
    thermo_iot_power_result result;
    CHECK(thermo_iot_power_init(&state, &config));
    CHECK(thermo_iot_power_check(&state, 0u, 3000u, 1000u, &result));
    CHECK(result.interval_s == 300u);
    CHECK(thermo_iot_power_mark_attempt(&state, 0u, true));
    CHECK(thermo_iot_power_check(&state, 300u, 3000u, 100u, &result));
    CHECK(result.interval_s == 438u);
    CHECK(result.decision == THERMO_IOT_POWER_WAIT);
    CHECK(result.next_eligible_s == 438u);
    CHECK(thermo_iot_power_check(&state, 438u, 3000u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    return 0;
}

static int test_monotonicity_and_overflow(void) {
    thermo_iot_power_state state;
    thermo_iot_power_config config = sample_config();
    thermo_iot_power_result result;
    CHECK(thermo_iot_power_init(&state, &config));
    CHECK(thermo_iot_power_check(&state, UINT64_MAX - 3u, 2900u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    CHECK(!thermo_iot_power_mark_attempt(&state, UINT64_MAX - 3u, true));
    CHECK(thermo_iot_power_check(&state, 10u, 2900u, 100u, &result) == false);
    CHECK(thermo_iot_power_init(&state, &config));
    CHECK(thermo_iot_power_check(&state, 400u, 3000u, 100u, &result));
    CHECK(thermo_iot_power_mark_attempt(&state, 400u, false));
    CHECK(!thermo_iot_power_mark_attempt(&state, 400u, false));
    CHECK(!thermo_iot_power_check(&state, 399u, 3000u, 100u, &result));
    CHECK(thermo_iot_power_check(&state, 838u, 3000u, 100u, &result));
    CHECK(result.decision == THERMO_IOT_POWER_READY);
    return 0;
}

int main(void) {
    CHECK(test_validation() == 0);
    CHECK(test_hysteresis_and_intervals() == 0);
    CHECK(test_zero_net_and_duty_limit() == 0);
    CHECK(test_reduced_harvest_extends_existing_cooldown() == 0);
    CHECK(test_monotonicity_and_overflow() == 0);
    puts("Thermo-IoT power policy: PASS");
    return 0;
}
