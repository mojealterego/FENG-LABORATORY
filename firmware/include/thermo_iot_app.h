/* STM32WLE5JC application logic portable across CubeWL board adapters.
 * Platform functions must be implemented by a concrete STM32CubeWL target.
 */
#ifndef THERMO_IOT_APP_H
#define THERMO_IOT_APP_H
#include "thermo_iot_power_policy.h"
#include "thermo_iot_frame.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    void *context;
    bool (*read_capacitor_mv)(void *context, uint16_t *voltage_mv);
    bool (*read_net_power_uw)(void *context, uint32_t *net_power_uw);
    bool (*read_temperature_centi_c)(void *context, int32_t *temperature_centi_c);
    /* -1 means the TEG power meter is unavailable. */
    bool (*read_teg_power_uw)(void *context, int32_t *teg_power_uw);
    bool (*is_joined)(void *context);
    /* The callbacks must be asynchronous-safe and shall return bool accepted. */
    bool (*request_otaa_join)(void *context);
    bool (*request_uplink)(void *context, uint8_t fport,
                           const uint8_t *payload, uint8_t length);
} thermo_iot_platform;

typedef enum {
    THERMO_IOT_APP_CHARGING = 0,
    THERMO_IOT_APP_DEFICIT = 1,
    THERMO_IOT_APP_WAIT = 2,
    THERMO_IOT_APP_JOIN_REQUESTED = 3,
    THERMO_IOT_APP_UPLINK_QUEUED = 4,
    THERMO_IOT_APP_READ_ERROR = 5,
    THERMO_IOT_APP_RADIO_REJECTED = 6,
    THERMO_IOT_APP_INVALID = 7
} thermo_iot_app_status;

typedef struct {
    thermo_iot_power_state energy;
    thermo_iot_platform io;
    uint32_t wakeups;
    uint32_t uplinks_queued;
    uint32_t join_requests;
} thermo_iot_app;

bool thermo_iot_app_init(thermo_iot_app *app,
                         const thermo_iot_platform *platform,
                         const thermo_iot_power_config *power_config);

/* Must be called on each timer wake, after radio task completion, using
 * a monotonic uptime in seconds. This code does NOT integrate scheduler,
 * MCU HAL, RF matching, secure key storage or LoRaWAN MAC by itself.
 */
thermo_iot_app_status thermo_iot_app_step(thermo_iot_app *app, uint64_t now_s);

#endif
