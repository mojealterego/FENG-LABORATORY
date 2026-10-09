#include "thermo_iot_app.h"
#include <limits.h>
#include <stddef.h>

bool thermo_iot_app_init(thermo_iot_app *app,
                         const thermo_iot_platform *platform,
                         const thermo_iot_power_config *power_config) {
    if (app == NULL || platform == NULL || power_config == NULL
        || platform->read_capacitor_mv == NULL
        || platform->read_net_power_uw == NULL
        || platform->read_temperature_centi_c == NULL
        || platform->read_teg_power_uw == NULL
        || platform->is_joined == NULL
        || platform->request_otaa_join == NULL
        || platform->request_uplink == NULL) {
        return false;
    }
    *app = (thermo_iot_app){0};
    app->io = *platform;
    return thermo_iot_power_init(&app->energy, power_config);
}

thermo_iot_app_status thermo_iot_app_step(thermo_iot_app *app, uint64_t now_s) {
    if (app == NULL) {
        return THERMO_IOT_APP_INVALID;
    }
    uint16_t voltage_mv = 0;
    uint32_t net_power_uw = 0;
    if (!app->io.read_capacitor_mv(app->io.context, &voltage_mv)
        || !app->io.read_net_power_uw(app->io.context, &net_power_uw)) {
        return THERMO_IOT_APP_READ_ERROR;
    }
    thermo_iot_power_result verdict;
    if (!thermo_iot_power_check(&app->energy, now_s, voltage_mv, net_power_uw, &verdict)) {
        return THERMO_IOT_APP_INVALID;
    }
    if (app->wakeups != UINT32_MAX) {
        app->wakeups++;
    }
    if (verdict.decision == THERMO_IOT_POWER_CHARGING) {
        return THERMO_IOT_APP_CHARGING;
    }
    if (verdict.decision == THERMO_IOT_POWER_DEFICIT) {
        return THERMO_IOT_APP_DEFICIT;
    }
    if (verdict.decision == THERMO_IOT_POWER_WAIT) {
        return THERMO_IOT_APP_WAIT;
    }
    if (!app->io.is_joined(app->io.context)) {
        const bool requested = app->io.request_otaa_join(app->io.context);
        (void)thermo_iot_power_mark_attempt(&app->energy, now_s, false);
        if (!requested) {
            return THERMO_IOT_APP_RADIO_REJECTED;
        }
        if (app->join_requests < UINT32_MAX) {
            app->join_requests++;
        }
        return THERMO_IOT_APP_JOIN_REQUESTED;
    }
    int32_t temperature = 0;
    int32_t teg_uw = -1;
    if (!app->io.read_temperature_centi_c(app->io.context, &temperature)
        || !app->io.read_teg_power_uw(app->io.context, &teg_uw)) {
        (void)thermo_iot_power_mark_attempt(&app->energy, now_s, false);
        return THERMO_IOT_APP_READ_ERROR;
    }
    uint8_t data[THERMO_IOT_FRAME_LEN];
    if (!thermo_iot_encode_frame(temperature, voltage_mv, teg_uw, 0u, data)) {
        (void)thermo_iot_power_mark_attempt(&app->energy, now_s, false);
        return THERMO_IOT_APP_INVALID;
    }
    const bool accepted = app->io.request_uplink(
        app->io.context, THERMO_IOT_FPORT, data, THERMO_IOT_FRAME_LEN
    );
    /* Radio acceptance is not a gateway receipt; conservatively apply cooldown
     * to both accepted and rejected requests because RF may have been started.
     */
    (void)thermo_iot_power_mark_attempt(&app->energy, now_s, accepted);
    if (!accepted) {
        return THERMO_IOT_APP_RADIO_REJECTED;
    }
    if (app->uplinks_queued < UINT32_MAX) {
        app->uplinks_queued++;
    }
    return THERMO_IOT_APP_UPLINK_QUEUED;
}
